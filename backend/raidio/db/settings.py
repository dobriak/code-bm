from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(default="sqlite+aiosqlite:///database/raidio.db")
    library_path: str = Field(default="/srv/music")
    jingles_path: str = Field(default="/srv/jingles")
    cover_cache_path: str = Field(default="./cache/covers")
    liquidsoap_host: str = Field(default="127.0.0.1")
    liquidsoap_telnet_port: int = Field(default=1234)
    icecast_host: str = Field(default="127.0.0.1")
    icecast_port: int = Field(default=8000)
    icecast_mount: str = Field(default="/raidio.mp3")
    icecast_source_password: str = Field(default="change-me")
    admin_email: str = Field(default="admin@example.com")
    admin_password_hash: str = Field(default="$2b$12$placeholder")
    jwt_secret: str = Field(default="change-me-to-random-secret")


@lru_cache
def get_settings() -> Settings:
    return Settings()
