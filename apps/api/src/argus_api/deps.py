from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from argus_core.db.session import session_scope
from argus_core.settings import Settings, get_settings


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_scope() as session:
        yield session


def get_settings_dep() -> Settings:
    return get_settings()
