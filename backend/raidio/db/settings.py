"""Application settings loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration values for the Raidio backend.

    Values are loaded from environment variables, falling back to .env file.
    """

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Admin credentials
    admin_email: str = "admin@raidio.local"
    admin_password_hash: str = ""
    jwt_secret: str = "change-me"

    # Paths
    library_path: str = "/srv/music"
    jingles_path: str = "/srv/jingles"
    cover_cache_path: str = "./cache/covers"
    database_path: str = "database/raidio.db"

    @property
    def database_abs_path(self) -> Path:
        """Absolute path to the database file (resolved from project root)."""
        return (Path(__file__).resolve().parents[3] / self.database_path).resolve()

    @property
    def cover_cache_abs_path(self) -> Path:
        """Absolute path to the cover cache directory."""
        return (Path(__file__).resolve().parents[3] / self.cover_cache_path).resolve()

    # Liquidsoap
    liquidsoap_host: str = "127.0.0.1"
    liquidsoap_telnet_port: int = 1234

    # Icecast
    icecast_host: str = "127.0.0.1"
    icecast_port: int = 8000
    icecast_mount: str = "/raidio.mp3"
    icecast_source_password: str = "hackme"
