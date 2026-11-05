import asyncio
import ssl
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import config


class AsyncSessionFactory:
    """Create a SQLAlchemy async session per running event loop.

    A module-level engine is tied to the loop that created it. pytest-asyncio
    creates a fresh loop for each test, so reusing one global engine causes
    "Event loop is closed" errors. This factory keeps a separate engine per loop.
    """

    def __init__(self):
        self._sessionmakers: Dict[int, async_sessionmaker[AsyncSession]] = {}
        self._engines = {}

    def _get_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        loop = asyncio.get_running_loop()
        loop_id = id(loop)

        sessionmaker = self._sessionmakers.get(loop_id)
        if sessionmaker is not None:
            return sessionmaker

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        engine = create_async_engine(
            config.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={"ssl": ssl_context},
        )
        sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
        self._sessionmakers[loop_id] = sessionmaker
        self._engines[loop_id] = engine
        return sessionmaker

    def __call__(self):
        return self._get_sessionmaker()()

    async def close_all(self):
        for engine in self._engines.values():
            await engine.dispose()
        self._sessionmakers.clear()
        self._engines.clear()


ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

engine = create_async_engine(
    config.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"ssl": ssl_context},
)

async_session = AsyncSessionFactory()
