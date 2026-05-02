from dataclasses import dataclass

from mutagen import File as MutagenFile
from mutagen.mp3 import MP3


@dataclass
class TrackTags:
    artist: str | None
    album: str | None
    title: str | None
    genre: str | None
    year: int | None
    track_number: int | None
    disc_number: int | None
    duration_ms: int | None
    bitrate_kbps: int | None
    sample_rate_hz: int | None
    cover_art_bytes: bytes | None
    cover_art_mime: str | None


def read_tags(path: str) -> TrackTags:
    try:
        audio = MutagenFile(path)
    except Exception:
        return _empty_tags()

    if audio is None:
        return _empty_tags()

    tags = audio.tags if audio.tags else {}

    artist = _get_tag(tags, ("artist", "albumartist", "album artist"))
    album = _get_tag(tags, ("album",))
    title = _get_tag(tags, ("title", "songname"))
    genre = _get_tag(tags, ("genre",))

    year = _get_year(tags)
    track_number = _get_track_number(tags)
    disc_number = _get_disc_number(tags)

    duration_ms = None
    bitrate_kbps = None
    sample_rate_hz = None

    if isinstance(audio, MP3):
        duration_ms = int(audio.info.length * 1000) if audio.info.length else None
        bitrate_kbps = int(audio.info.bitrate / 1000) if audio.info.bitrate else None
        sample_rate_hz = int(audio.info.sample_rate) if audio.info.sample_rate else None

    cover_art_bytes = None
    cover_art_mime = None

    for key in ("covr", "coverart", "pictures"):
        if key in tags:
            pictures = tags[key]
            if isinstance(pictures, list) and pictures:
                pic = pictures[0]
                cover_art_bytes = bytes(pic)
                cover_art_mime = _guess_mime(pic)
            elif hasattr(pictures, "data"):
                cover_art_bytes = bytes(pictures.data)
                cover_art_mime = _guess_mime(pictures)
            break
    else:
        for attr in ("pictures", "cover", "covr"):
            if hasattr(tags, attr):
                val = getattr(tags, attr)
                if val:
                    if isinstance(val, list):
                        pic = val[0]
                    else:
                        pic = val
                    if hasattr(pic, "data"):
                        cover_art_bytes = bytes(pic.data)
                        cover_art_mime = _guess_mime(pic)
                    break

    return TrackTags(
        artist=artist,
        album=album,
        title=title,
        genre=genre,
        year=year,
        track_number=track_number,
        disc_number=disc_number,
        duration_ms=duration_ms,
        bitrate_kbps=bitrate_kbps,
        sample_rate_hz=sample_rate_hz,
        cover_art_bytes=cover_art_bytes,
        cover_art_mime=cover_art_mime,
    )


def _get_tag(tags, keys):
    for key in keys:
        for tag_key in tags.keys():
            normalized_key = key.lower().replace(" ", "").replace("_", "")
            normalized_tag = tag_key.lower().replace(" ", "").replace("_", "")
            if normalized_tag == normalized_key:
                val = tags[tag_key]
                if val:
                    if isinstance(val, list):
                        return str(val[0])
                    return str(val)
    return None


def _get_year(tags) -> int | None:
    for key in ("date", "year"):
        if key in tags:
            val = tags[key]
            if val:
                s = str(val[0]) if isinstance(val, list) else str(val)
                year_match = s.split("-")[0]
                if year_match.isdigit() and len(year_match) == 4:
                    return int(year_match)
    return None


def _get_track_number(tags) -> int | None:
    for key in ("tracknumber", "track", "tracknumber/position"):
        if key in tags:
            val = tags[key]
            if val:
                s = str(val[0]) if isinstance(val, list) else str(val)
                s = s.split("/")[0].strip()
                if s.isdigit():
                    return int(s)
    return None


def _get_disc_number(tags) -> int | None:
    for key in ("discnumber", "disc", "partofaset"):
        if key in tags:
            val = tags[key]
            if val:
                s = str(val[0]) if isinstance(val, list) else str(val)
                s = s.split("/")[0].strip()
                if s.isdigit():
                    return int(s)
    return None


def _guess_mime(picture) -> str:
    if hasattr(picture, "mime"):
        return picture.mime
    if hasattr(picture, "imageattr"):
        return picture.imageattr
    return "image/jpeg"


def _empty_tags() -> TrackTags:
    return TrackTags(
        artist=None,
        album=None,
        title=None,
        genre=None,
        year=None,
        track_number=None,
        disc_number=None,
        duration_ms=None,
        bitrate_kbps=None,
        sample_rate_hz=None,
        cover_art_bytes=None,
        cover_art_mime=None,
    )
