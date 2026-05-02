import asyncio
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileInfo:
    absolute_path: str
    file_size: int
    mtime: float


async def scan_library(path: str) -> AsyncGenerator[FileInfo, None]:
    queue = asyncio.Queue()
    await queue.put(Path(path))

    while not queue.empty():
        item_path = await queue.get()

        if item_path.is_dir():
            try:
                async for entry in _scan_dir(item_path):
                    await queue.put(entry)
            except PermissionError:
                continue
        elif item_path.suffix.lower() == ".mp3":
            try:
                stat = item_path.stat()
                yield FileInfo(
                    absolute_path=str(item_path),
                    file_size=stat.st_size,
                    mtime=stat.st_mtime,
                )
            except OSError:
                continue

        queue.task_done()


async def _scan_dir(dir_path: Path) -> AsyncGenerator[Path, None]:
    asyncio.get_running_loop()

    def _sync_scan():
        try:
            with os.scandir(dir_path) as entries:
                for entry in entries:
                    yield Path(entry.path)
        except PermissionError:
            return

    for path in _sync_scan():
        yield path
