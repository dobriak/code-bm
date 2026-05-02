"""Audio analysis — Phase B of scanner.

Worker pool of async tasks consuming an asyncio.Queue.
Each worker shells out to ffmpeg silencedetect and parses stderr.
Filters for intro/outro quiet passages on tracks > 240 s.
Writes QuietPassage rows; updates Track.audio_analyzed_at and analysis_status.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import UTC, datetime

from sqlalchemy import delete

from raidio.db.models import AnalysisStatus, QuietPassage, QuietRegion, Track

logger = logging.getLogger(__name__)

# Regex to parse ffmpeg silencedetect output
_SILENCE_START_RE = re.compile(r"silence_start\s*:\s*([\d.]+)")
_SILENCE_END_RE = re.compile(r"silence_end\s*:\s*([\d.]+)\s*\|\s*silence_duration\s*:\s*([\d.]+)")

# Filters
_MIN_TRACK_DURATION_S = 240  # Only analyze tracks longer than 4 minutes
_INTRO_WINDOW_S = 60  # Intro region: first 60 seconds
_OUTRO_WINDOW_S = 120  # Outro region: last 120 seconds


def parse_silencedetect_output(stderr: str) -> list[dict]:
    """Parse ffmpeg silencedetect stderr into silence regions.

    Args:
        stderr: The raw stderr output from ffmpeg silencedetect.

    Returns:
        List of dicts with 'start' and 'end' keys (in seconds).
    """
    silences: list[dict] = []
    lines = stderr.splitlines()

    current_start: float | None = None

    for line in lines:
        # Look for silence_start
        start_match = _SILENCE_START_RE.search(line)
        if start_match:
            current_start = float(start_match.group(1))
            continue

        # Look for silence_end (which also gives us duration)
        end_match = _SILENCE_END_RE.search(line)
        if end_match and current_start is not None:
            end = float(end_match.group(1))
            silences.append({"start": current_start, "end": end})
            current_start = None

    # Handle case where silence extends to end of file (no silence_end)
    if current_start is not None:
        # We don't know the end — skip this one
        pass

    return silences


def filter_quiet_passages(
    silences: list[dict],
    track_duration_s: float,
    min_duration_s: float,
) -> list[dict]:
    """Filter silence regions to only intro/outro passages.

    Args:
        silences: Raw silence regions from parse_silencedetect_output.
        track_duration_s: Total track duration in seconds.
        min_duration_s: Minimum silence duration to keep.

    Returns:
        Filtered list of dicts with 'start_ms', 'end_ms', 'duration_ms', 'region'.
    """
    filtered: list[dict] = []

    for silence in silences:
        duration_s = silence["end"] - silence["start"]

        if duration_s < min_duration_s:
            continue

        start_s = silence["start"]
        end_s = silence["end"]

        # Determine region
        region = None
        if start_s < _INTRO_WINDOW_S:
            region = QuietRegion.INTRO
        elif end_s > track_duration_s - _OUTRO_WINDOW_S:
            region = QuietRegion.OUTRO

        if region is None:
            continue

        filtered.append({
            "start_ms": int(start_s * 1000),
            "end_ms": int(end_s * 1000),
            "duration_ms": int(duration_s * 1000),
            "region": region,
        })

    return filtered


class AnalysisWorkerPool:
    """Worker pool for audio analysis tasks.

    Usage::

        pool = AnalysisWorkerPool(session_factory=factory, min_quiet_duration_s=2.0)
        pool.enqueue(track_id)
        await pool.start()
        # ... later
        await pool.stop()
    """

    def __init__(
        self,
        session_factory,
        min_quiet_duration_s: float = 2.0,
        num_workers: int | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._min_quiet_duration_s = min_quiet_duration_s
        self._queue: asyncio.Queue[int] = asyncio.Queue()
        self._running = False
        self._tasks: list[asyncio.Task] = []

        if num_workers is None:
            num_workers = min(os_cpu_count() or 1, 4)
        self._num_workers = num_workers

    def enqueue(self, track_id: int) -> None:
        """Enqueue a track for analysis."""
        self._queue.put_nowait(track_id)

    def enqueue_many(self, track_ids: list[int]) -> None:
        """Enqueue multiple tracks for analysis."""
        for tid in track_ids:
            self._queue.put_nowait(tid)

    async def start(self) -> None:
        """Start the worker pool."""
        if self._running:
            return
        self._running = True
        for i in range(self._num_workers):
            task = asyncio.create_task(self._worker(i))
            self._tasks.append(task)
        logger.info(
            "Analysis worker pool started with %d workers, queue depth: %d",
            self._num_workers,
            self._queue.qsize(),
        )

    async def stop(self) -> None:
        """Stop the worker pool (drains remaining items)."""
        self._running = False
        # Cancel all workers
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("Analysis worker pool stopped")

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes tracks from the queue."""
        logger.info("Analysis worker %d started", worker_id)
        while self._running:
            try:
                track_id = await asyncio.wait_for(self._queue.get(), timeout=2.0)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            try:
                await self._analyze_track(track_id)
            except Exception:
                logger.exception("Analysis worker %d failed on track %d", worker_id, track_id)

    async def _analyze_track(self, track_id: int) -> None:
        """Analyze a single track for quiet passages."""
        async with self._session_factory() as session:
            track = await session.get(Track, track_id)
            if not track:
                return

            # Skip if already analyzed
            if track.analysis_status == AnalysisStatus.DONE:
                return

            # Skip short tracks
            duration_s = (track.duration_ms or 0) / 1000.0
            if duration_s < _MIN_TRACK_DURATION_S:
                track.analysis_status = AnalysisStatus.DONE
                track.audio_analyzed_at = datetime.now(tz=UTC).replace(tzinfo=None)
                await session.commit()
                return

            # Mark as running
            track.analysis_status = AnalysisStatus.RUNNING
            await session.commit()

            try:
                # Run ffmpeg silencedetect
                proc = await asyncio.create_subprocess_exec(
                    "ffmpeg",
                    "-i", track.path,
                    "-af", f"silencedetect=noise=-30dB:d={self._min_quiet_duration_s}",
                    "-f", "null", "-",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

                if proc.returncode != 0 and "silence_start" not in stderr_text:
                    track.analysis_status = AnalysisStatus.ERROR
                    track.analysis_error = f"ffmpeg exited with code {proc.returncode}"
                    await session.commit()
                    return

                # Parse and filter
                silences = parse_silencedetect_output(stderr_text)
                passages = filter_quiet_passages(
                    silences, duration_s, self._min_quiet_duration_s
                )

                # Clear existing passages and write new ones
                await session.execute(
                    delete(QuietPassage).where(QuietPassage.track_id == track_id)
                )

                for p in passages:
                    qp = QuietPassage(
                        track_id=track_id,
                        start_ms=p["start_ms"],
                        end_ms=p["end_ms"],
                        duration_ms=p["duration_ms"],
                        region=p["region"],
                        db_threshold=-30.0,
                    )
                    session.add(qp)

                track.analysis_status = AnalysisStatus.DONE
                track.audio_analyzed_at = datetime.now(tz=UTC).replace(tzinfo=None)
                track.analysis_error = None
                logger.info(
                    "Track %d (%s): found %d quiet passages",
                    track_id, track.title or track.path, len(passages),
                )

            except FileNotFoundError:
                track.analysis_status = AnalysisStatus.ERROR
                track.analysis_error = "ffmpeg not found"
            except Exception as exc:
                track.analysis_status = AnalysisStatus.ERROR
                track.analysis_error = str(exc)[:500]
                logger.error("Analysis failed for track %d: %s", track_id, exc)

            await session.commit()


def os_cpu_count() -> int | None:
    """Get CPU count (wraps os.cpu_count for testability)."""
    return os.cpu_count()
