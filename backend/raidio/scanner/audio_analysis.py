from __future__ import annotations

import asyncio
import os
import re
import subprocess
from dataclasses import dataclass

from raidio.db.models import AnalysisStatus, QuietPassage, QuietRegion, Track
from raidio.db.settings import get_settings


@dataclass
class SilenceDetectionResult:
    track_id: int
    passages: list[dict]
    error: str | None = None


@dataclass
class AnalysisTask:
    track_id: int
    path: str
    duration_ms: int
    min_quiet_duration_s: int


def parse_silencedetect_output(stderr: str) -> list[dict]:
    passages = []
    pattern = re.compile(
        r"\[silencedetect\s+@\s+0x[0-9a-f]+\]\s+(silence_start|silence_end):\s*([\d.]+)"
    )
    entries: list[tuple[str, float]] = []

    for match in pattern.finditer(stderr):
        event_type = match.group(1)
        value = float(match.group(2))
        entries.append((event_type, value))

    i = 0
    while i < len(entries) - 1:
        if entries[i][0] == "silence_start" and entries[i + 1][0] == "silence_end":
            start = entries[i][1]
            end = entries[i + 1][1]
            duration = end - start
            passages.append({
                "start_s": start,
                "end_s": end,
                "duration_s": duration,
            })
            i += 2
        else:
            i += 1

    return passages


async def run_silencedetect(path: str, min_duration_s: float) -> list[dict]:
    cmd = [
        "ffmpeg", "-i", path,
        "-af", f"silencedetect=noise=-30dB:d={min_duration_s}",
        "-f", "null", "-"
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        stderr_str = stderr.decode("utf-8", errors="replace")
        if "does not contain data" not in stderr_str:
            raise RuntimeError(f"ffmpeg failed: {stderr_str[:500]}")
    return parse_silencedetect_output(stderr.decode("utf-8", errors="replace"))


def filter_passages(
    passages: list[dict],
    track_duration_s: float,
    min_duration_s: float,
) -> list[dict]:
    filtered = []
    intro_cutoff = 60.0
    outro_start = max(0, track_duration_s - 120.0)

    for p in passages:
        if p["duration_s"] < min_duration_s:
            continue
        start = p["start_s"]
        end = p["end_s"]

        is_intro = end <= intro_cutoff
        is_outro = start >= outro_start

        if not (is_intro or is_outro):
            continue

        region = QuietRegion.INTRO if is_intro else QuietRegion.OUTRO
        filtered.append({
            "start_ms": int(start * 1000),
            "end_ms": int(end * 1000),
            "duration_ms": int(p["duration_s"] * 1000),
            "region": region,
            "db_threshold": -30.0,
        })

    return filtered


class AnalysisWorker:
    def __init__(self, worker_id: int, task_queue: asyncio.Queue, result_queue: asyncio.Queue):
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.result_queue = result_queue

    async def run(self) -> None:
        while True:
            try:
                task = await asyncio.wait_for(self.task_queue.get(), timeout=5.0)
            except TimeoutError:
                continue

            if task is None:
                self.task_queue.task_done()
                break

            track_id, path, duration_ms, min_quiet_duration_s = task
            passages: list[dict] = []
            error: str | None = None

            try:
                duration_s = duration_ms / 1000.0
                raw = await run_silencedetect(path, min_quiet_duration_s)
                passages = filter_passages(raw, duration_s, min_quiet_duration_s)
            except Exception as e:
                error = str(e)[:200]

            await self.result_queue.put(
                SilenceDetectionResult(
                    track_id=track_id,
                    passages=passages,
                    error=error,
                )
            )
            self.task_queue.task_done()


async def enqueue_analysis_tasks(
    track_ids: list[int],
    task_queue: asyncio.Queue,
    db_session,
) -> None:
    from sqlalchemy import select

    result = await db_session.execute(
        select(Track).where(Track.id.in_(track_ids))
    )
    tracks = result.scalars().all()
    settings = get_settings()
    min_quiet = settings.min_quiet_duration_s if hasattr(settings, "min_quiet_duration_s") else 2

    for track in tracks:
        if track.duration_ms and track.duration_ms > 240000:
            await task_queue.put(AnalysisTask(
                track_id=track.id,
                path=track.path,
                duration_ms=track.duration_ms,
                min_quiet_duration_s=min_quiet,
            ))


async def process_analysis_results(
    result_queue: asyncio.Queue,
    db_session,
) -> None:
    from datetime import datetime

    pending_results: dict[int, SilenceDetectionResult] = {}

    while True:
        try:
            result = await asyncio.wait_for(result_queue.get(), timeout=1.0)
        except TimeoutError:
            if not pending_results:
                continue

        pending_results[result.track_id] = result

        while pending_results:
            track_id = next(iter(pending_results))
            res = pending_results[track_id]

            track_result = await db_session.get(Track, res.track_id)
            if not track_result:
                del pending_results[track_id]
                continue

            if res.error:
                track_result.analysis_status = AnalysisStatus.ERROR
                track_result.analysis_error = res.error
            else:
                await db_session.execute(
                    QuietPassage.__table__.delete().where(
                        QuietPassage.track_id == track_id
                    )
                )

                for p in res.passages:
                    passage = QuietPassage(
                        track_id=track_id,
                        start_ms=p["start_ms"],
                        end_ms=p["end_ms"],
                        duration_ms=p["duration_ms"],
                        region=p["region"],
                        db_threshold=p["db_threshold"],
                    )
                    db_session.add(passage)

                track_result.analysis_status = AnalysisStatus.DONE
                track_result.audio_analyzed_at = datetime.utcnow()
                track_result.analysis_error = None

            await db_session.commit()
            del pending_results[track_id]


async def run_analysis_pool(
    track_ids: list[int],
    db_session,
) -> None:
    n_workers = min(os.cpu_count() or 1, 4)
    task_queue: asyncio.Queue = asyncio.Queue()
    result_queue: asyncio.Queue = asyncio.Queue()

    await enqueue_analysis_tasks(track_ids, task_queue, db_session)

    for _ in range(n_workers):
        await task_queue.put(None)

    workers = [
        AnalysisWorker(i, task_queue, result_queue)
        for i in range(n_workers)
    ]

    await asyncio.gather(
        *[w.run() for w in workers],
        process_analysis_results(result_queue, db_session),
    )


async def reanalyze_track(db_session, track_id: int) -> None:

    track = await db_session.get(Track, track_id)
    if not track:
        return

    track.analysis_status = AnalysisStatus.PENDING
    track.analysis_error = None
    await db_session.commit()

    await run_analysis_pool([track_id], db_session)
