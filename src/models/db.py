from __future__ import annotations

import asyncpg

import json
import typing as t

if t.TYPE_CHECKING:
    from .bot import Bot


class DatabaseStateConflict(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class Database:
    """A database class for an `asyncpg.Pool` which proxies methods for an `asyncpg.Pool`."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.user = "postgres"
        self.password = "postgres"
        self.host = "localhost"
        self.db_name = "intellicat"
        self.port = 5432
        self.pool: asyncpg.Pool | None = None

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
            await self.ensure_db()
            self.pool = await asyncpg.create_pool(
                dsn=self.dsn, init=self.init_connection
            )
        else:
            raise DatabaseStateConflict("Already connected to database")

    async def close(self) -> None:
        """Closes the connection pool."""
        if self.pool:
            await self.pool.close()
        else:
            raise DatabaseStateConflict("Not connected to database")

    async def ensure_db(self) -> None:
        """Ensures the bot database and its schema exists."""
        try:
            conn = await asyncpg.connect(dsn=self.dsn)
            await conn.execute(
                """
                    ALTER TABLE swear_counter 
                    ADD COLUMN IF NOT EXISTS user_id BIGINT, 
                    ADD COLUMN IF NOT EXISTS guild_id BIGINT, 
                    ADD COLUMN IF NOT EXISTS swears JSON,
                    ADD UNIQUE (user_id, guild_id);
                    
                    ALTER TABLE tags 
                    ADD COLUMN IF NOT EXISTS guild_id BIGINT, 
                    ADD COLUMN IF NOT EXISTS key TEXT, 
                    ADD COLUMN IF NOT EXISTS value TEXT, 
                    ADD UNIQUE (key);
                """
            )  # Update tables

        except asyncpg.InvalidCatalogNameError:  # Database does not exist
            sys_conn = await asyncpg.connect(
                database="template1", user=self.user, password=self.password
            )
            await sys_conn.execute(f"CREATE DATABASE {self.db_name}")
            await sys_conn.close()

        except asyncpg.UndefinedTableError:
            pass

        finally:
            # Create databases
            conn = await asyncpg.connect(dsn=self.dsn)
            await conn.execute(
                """
                    CREATE TABLE IF NOT EXISTS swear_counter (
                        user_id BIGINT, 
                        guild_id BIGINT, 
                        swears JSONB, 
                        UNIQUE (user_id, guild_id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS tags (
                        guild_id BIGINT, 
                        key TEXT, 
                        value TEXT, 
                        UNIQUE (key)
                    );
                """
            )
