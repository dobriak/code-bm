"""Settings bootstrap — ensures the settings table has a default row on startup."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from raidio.db.models import Setting
from raidio.db.settings import Settings as AppSettings

logger = logging.getLogger(__name__)


async def ensure_default_settings(session: AsyncSession, app_settings: AppSettings) -> None:
    """Create the default settings row if it doesn't exist."""
    result = await session.execute(select(Setting))
    existing = result.scalar_one_or_none()

    if existing is not None:
        logger.info("Settings row already exists (id=%d)", existing.id)
        return

    setting = Setting(
        library_path=app_settings.library_path,
        jingles_path=app_settings.jingles_path,
    )
    session.add(setting)
    await session.commit()
    logger.info("Created default settings row")
