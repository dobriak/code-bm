import hashlib
from pathlib import Path


def store_cover(data: bytes, mime: str) -> Path:
    sha = hashlib.sha1(data).hexdigest()
    ext = _mime_to_ext(mime)
    cache_dir = Path("cache/covers")
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{sha}.{ext}"
    if not path.exists():
        path.write_bytes(data)
    return path


def _mime_to_ext(mime: str) -> str:
    if "png" in mime.lower():
        return "png"
    return "jpg"
