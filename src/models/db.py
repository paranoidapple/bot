from __future__ import annotations

import asyncpg
import aiofiles

import json
import typing as t

from os import getenv

if t.TYPE_CHECKING:
    from .bot import Bot


class DatabaseStateConflict(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class Database:
    """A database class for an `asyncpg.Pool` which proxies methods for an `asyncpg.Pool`."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.user = getenv("user") or "postgres"
        self.password = getenv("password") or "postgres"
        self.host = "localhost"
        self.db_name = "intellicat"
        self.port = 5432
        self.pool: asyncpg.Pool | None = None

        DatabaseModel.db = self
        DatabaseModel.bot = self.bot

    def __getattr__(self, item):
        """Proxies methods and properties not in the database class into the connection pool."""
        return getattr(self.pool, item)

    @property
    def dsn(self) -> str:
        """The database's connection URI."""
        return f"postgres://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}"

    async def init_connection(self, conn: asyncpg.Connection):
        await conn.set_type_codec(
            "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )

    async def connect(self) -> None:
        """Starts a new connection via a connection pool."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn, init=self.init_connection
            )
            await self.ensure_schema()
        else:
            raise DatabaseStateConflict("Already connected to database")

    async def close(self) -> None:
        """Closes the connection pool."""
        if self.pool:
            await self.pool.close()
        else:
            raise DatabaseStateConflict("Not connected to database")

    async def ensure_schema(self) -> None:
        """Ensures the bot database and its schema exists. (run after creating pool)"""
        SCHEMA_SCRIPT_PATH = f"{self.bot.base_dir}/db/schema.sql"
        async with aiofiles.open(SCHEMA_SCRIPT_PATH, 'r') as f:
            async with self.acquire() as conn:
                await conn.execute(await f.read())


class DatabaseModel:  # (thanks hypergonial)
    """Utility for database models."""

    db: Database
    bot: Bot
