"""Walker — async recursive directory scanner for audio files.

Yields (absolute_path, file_size, mtime) for every .mp3 file found.
Uses os.scandir for performance.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ScannedFile:
    """A single file discovered by the walker."""

    path: str
    file_size: int
    mtime: float


async def scan_library(path: str) -> list[ScannedFile]:
    """Walk a directory tree and return all .mp3 files.

    Args:
        path: Root directory to scan.

    Returns:
        List of ScannedFile for every .mp3 found (recursively).

    Raises:
        FileNotFoundError: If the root directory does not exist.
    """
    root = Path(path)
    if not root.is_dir():
        raise FileNotFoundError(f"Library path does not exist: {path}")

    files: list[ScannedFile] = []
    for entry in os.scandir(root):
        if entry.is_dir(follow_symlinks=True):
            files.extend(_walk_dir(entry.path))
        elif _is_mp3(entry.name):
            stat = entry.stat(follow_symlinks=True)
            files.append(
                ScannedFile(
                    path=str(Path(entry.path).resolve()),
                    file_size=stat.st_size,
                    mtime=stat.st_mtime,
                )
            )

    return files


def _walk_dir(path: str) -> list[ScannedFile]:
    """Synchronous recursive walk — kept simple for performance."""
    files: list[ScannedFile] = []
    try:
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=True):
                files.extend(_walk_dir(entry.path))
            elif _is_mp3(entry.name):
                stat = entry.stat(follow_symlinks=True)
                files.append(
                    ScannedFile(
                        path=str(Path(entry.path).resolve()),
                        file_size=stat.st_size,
                        mtime=stat.st_mtime,
                    )
                )
    except PermissionError:
        pass
    return files


def _is_mp3(name: str) -> bool:
    """Check if a filename looks like an MP3."""
    return name.lower().endswith((".mp3", ".mpeg", ".mpga"))
