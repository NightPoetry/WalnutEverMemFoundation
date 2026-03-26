"""Database initialization and schema management."""

import argparse
import asyncio
import logging
import sqlite3
from typing import Any

from walnut_ever_mem.config import DatabaseConfig, EmbeddingConfig, WalnutConfig

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Initialize and manage database schema.

    The schema is dynamically generated based on configuration,
    particularly the embedding dimension.

    Supports both SQLite (default) and PostgreSQL backends.
    """

    def __init__(self, config: WalnutConfig):
        self.config = config
        self.dimension = config.embedding.dimension
        self.backend = config.db.backend

    def _get_create_chat_records_sql_sqlite(self) -> str:
        """Generate chat_records table SQL for SQLite."""
        return f"""
        CREATE TABLE IF NOT EXISTS chat_records (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT NOT NULL,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            embedding       BLOB,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata        TEXT
        );
        """

    def _get_create_pointers_sql_sqlite(self) -> str:
        """Generate pointers table SQL for SQLite."""
        return f"""
        CREATE TABLE IF NOT EXISTS pointers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id       INTEGER NOT NULL REFERENCES chat_records(id) ON DELETE CASCADE,
            target_id       INTEGER NOT NULL REFERENCES chat_records(id) ON DELETE CASCADE,
            embedding       BLOB NOT NULL,
            pointer_type    TEXT DEFAULT 'embedding',
            summary         TEXT,
            relevance_score REAL,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_count    INTEGER DEFAULT 0,
            last_accessed   TIMESTAMP
        );
        """

    def _get_create_chat_records_sql_postgresql(self) -> str:
        """Generate chat_records table SQL for PostgreSQL with pgvector."""
        return f"""
        CREATE TABLE IF NOT EXISTS chat_records (
            id              BIGSERIAL PRIMARY KEY,
            session_id      VARCHAR(64) NOT NULL,
            role            VARCHAR(16) NOT NULL,
            content         TEXT NOT NULL,
            embedding       VECTOR({self.dimension}),
            created_at      TIMESTAMP DEFAULT NOW(),
            metadata        JSONB
        );
        """

    def _get_create_pointers_sql_postgresql(self) -> str:
        """Generate pointers table SQL for PostgreSQL with pgvector."""
        return f"""
        CREATE TABLE IF NOT EXISTS pointers (
            id              BIGSERIAL PRIMARY KEY,
            source_id       BIGINT NOT NULL REFERENCES chat_records(id) ON DELETE CASCADE,
            target_id       BIGINT NOT NULL REFERENCES chat_records(id) ON DELETE CASCADE,
            embedding       VECTOR({self.dimension}) NOT NULL,
            pointer_type    VARCHAR(32) DEFAULT 'embedding',
            summary         TEXT,
            relevance_score FLOAT,
            created_at      TIMESTAMP DEFAULT NOW(),
            access_count    INT DEFAULT 0,
            last_accessed   TIMESTAMP
        );
        """

    def _get_create_indexes_sql_sqlite(self) -> list[str]:
        """Generate index creation SQL for SQLite."""
        return [
            "CREATE INDEX IF NOT EXISTS idx_chat_records_session ON chat_records(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_chat_records_created ON chat_records(created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_pointers_source ON pointers(source_id);",
            "CREATE INDEX IF NOT EXISTS idx_pointers_target ON pointers(target_id);",
        ]

    def _get_create_indexes_sql_postgresql(self) -> list[str]:
        """Generate index creation SQL for PostgreSQL."""
        return [
            "CREATE INDEX IF NOT EXISTS idx_chat_records_session ON chat_records(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_chat_records_created ON chat_records(created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_pointers_source ON pointers(source_id);",
            "CREATE INDEX IF NOT EXISTS idx_pointers_target ON pointers(target_id);",
        ]

    def _get_enable_vector_extension_sql(self) -> str:
        """Enable pgvector extension for PostgreSQL."""
        return "CREATE EXTENSION IF NOT EXISTS vector;"

    async def initialize_sqlite(self) -> None:
        """Initialize SQLite database schema."""
        self.config.db.ensure_sqlite_dir()
        db_path = self.config.db.sqlite_path

        logger.info(f"Initializing SQLite database at: {db_path}")
        logger.info(f"Embedding dimension: {self.dimension}")

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            cursor.execute(self._get_create_chat_records_sql_sqlite())
            logger.info("Created chat_records table")

            cursor.execute(self._get_create_pointers_sql_sqlite())
            logger.info("Created pointers table")

            for index_sql in self._get_create_indexes_sql_sqlite():
                cursor.execute(index_sql)
            logger.info("Created indexes")

            self._record_schema_version_sqlite(cursor)
            conn.commit()
            logger.info("Database initialization complete")

        finally:
            conn.close()

    def _record_schema_version_sqlite(self, cursor: sqlite3.Cursor) -> None:
        """Record schema version for SQLite."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version     INTEGER PRIMARY KEY,
                dimension   INTEGER NOT NULL,
                applied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cursor.execute("SELECT 1 FROM schema_version WHERE version = 1")
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO schema_version (version, dimension) VALUES (1, ?)",
                (self.dimension,),
            )

    async def initialize_postgresql(self) -> None:
        """Initialize PostgreSQL database schema."""
        import asyncpg

        conn = await asyncpg.connect(self.config.db.connection_url)
        try:
            async with conn.transaction():
                logger.info(f"Initializing PostgreSQL with embedding dimension: {self.dimension}")

                await conn.execute(self._get_enable_vector_extension_sql())
                logger.info("Enabled pgvector extension")

                await conn.execute(self._get_create_chat_records_sql_postgresql())
                logger.info("Created chat_records table")

                await conn.execute(self._get_create_pointers_sql_postgresql())
                logger.info("Created pointers table")

                for index_sql in self._get_create_indexes_sql_postgresql():
                    await conn.execute(index_sql)
                logger.info("Created indexes")

                await self._record_schema_version_postgresql(conn)
                logger.info("Database initialization complete")

        finally:
            await conn.close()

    async def _record_schema_version_postgresql(self, conn) -> None:
        """Record schema version for PostgreSQL."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version     INT PRIMARY KEY,
                dimension   INT NOT NULL,
                applied_at  TIMESTAMP DEFAULT NOW()
            );
        """)

        exists = await conn.fetchval("SELECT 1 FROM schema_version WHERE version = 1")
        if not exists:
            await conn.execute(
                "INSERT INTO schema_version (version, dimension) VALUES (1, $1)",
                self.dimension,
            )

    async def initialize(self) -> None:
        """Initialize the database schema based on configured backend."""
        if self.backend == "sqlite":
            await self.initialize_sqlite()
        else:
            await self.initialize_postgresql()

    async def verify_schema_sqlite(self) -> dict[str, Any]:
        """Verify SQLite database schema."""
        db_path = self.config.db.sqlite_path
        result = {
            "tables_exist": False,
            "dimension_match": False,
            "recorded_dimension": None,
            "backend": "sqlite",
            "path": db_path,
        }

        if not self.config.db.sqlite_file_path.exists():
            return result

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('chat_records', 'pointers', 'schema_version')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            result["tables_exist"] = len(tables) == 3

            if result["tables_exist"]:
                cursor.execute("SELECT dimension FROM schema_version WHERE version = 1")
                row = cursor.fetchone()
                if row:
                    result["recorded_dimension"] = row[0]
                    result["dimension_match"] = row[0] == self.dimension

            return result

        finally:
            conn.close()

    async def verify_schema_postgresql(self) -> dict[str, Any]:
        """Verify PostgreSQL database schema."""
        import asyncpg

        conn = await asyncpg.connect(self.config.db.connection_url)
        try:
            result = {
                "tables_exist": False,
                "vector_extension": False,
                "dimension_match": False,
                "recorded_dimension": None,
                "backend": "postgresql",
            }

            ext = await conn.fetchval(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            )
            result["vector_extension"] = ext is not None

            tables = await conn.fetch("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('chat_records', 'pointers', 'schema_version')
            """)
            result["tables_exist"] = len(tables) == 3

            if result["tables_exist"]:
                dim = await conn.fetchval(
                    "SELECT dimension FROM schema_version WHERE version = 1"
                )
                result["recorded_dimension"] = dim
                result["dimension_match"] = dim == self.dimension

            return result

        finally:
            await conn.close()

    async def verify_schema(self) -> dict[str, Any]:
        """Verify the database schema is correct."""
        if self.backend == "sqlite":
            return await self.verify_schema_sqlite()
        return await self.verify_schema_postgresql()

    async def drop_schema_sqlite(self) -> None:
        """Drop all SQLite tables."""
        db_path = self.config.db.sqlite_path
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS pointers;")
            cursor.execute("DROP TABLE IF EXISTS chat_records;")
            cursor.execute("DROP TABLE IF EXISTS schema_version;")
            conn.commit()
            logger.warning("Dropped all tables")
        finally:
            conn.close()

    async def drop_schema_postgresql(self) -> None:
        """Drop all PostgreSQL tables."""
        import asyncpg

        conn = await asyncpg.connect(self.config.db.connection_url)
        try:
            async with conn.transaction():
                await conn.execute("DROP TABLE IF EXISTS pointers CASCADE;")
                await conn.execute("DROP TABLE IF EXISTS chat_records CASCADE;")
                await conn.execute("DROP TABLE IF EXISTS schema_version CASCADE;")
                logger.warning("Dropped all tables")
        finally:
            await conn.close()

    async def drop_schema(self) -> None:
        """Drop all tables (use with caution!)."""
        if self.backend == "sqlite":
            await self.drop_schema_sqlite()
        else:
            await self.drop_schema_postgresql()


async def init_database(config: WalnutConfig) -> None:
    """Convenience function to initialize database.

    Args:
        config: WalnutEverMem configuration.
    """
    initializer = DatabaseInitializer(config)
    await initializer.initialize()


async def main() -> None:
    """CLI entry point for database initialization."""
    parser = argparse.ArgumentParser(description="Initialize WalnutEverMem database")
    parser.add_argument(
        "--dimension", "-d",
        type=int,
        default=1536,
        help="Embedding vector dimension (default: 1536)",
    )
    parser.add_argument(
        "--backend",
        choices=["sqlite", "postgresql"],
        default="sqlite",
        help="Database backend (default: sqlite)",
    )
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default="walnut_memory.db",
        help="SQLite database path (default: walnut_memory.db)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="PostgreSQL host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5432,
        help="PostgreSQL port (default: 5432)",
    )
    parser.add_argument(
        "--database",
        type=str,
        default="walnut_memory",
        help="PostgreSQL database name (default: walnut_memory)",
    )
    parser.add_argument(
        "--user",
        type=str,
        default="postgres",
        help="PostgreSQL user (default: postgres)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="",
        help="PostgreSQL password",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before initialization",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify schema without modifying",
    )
    args = parser.parse_args()

    config = WalnutConfig(
        db=DatabaseConfig(
            backend=args.backend,
            sqlite_path=args.sqlite_path,
            host=args.host,
            port=args.port,
            database=args.database,
            user=args.user,
            password=args.password,
        ),
        embedding=EmbeddingConfig(dimension=args.dimension),
    )
    initializer = DatabaseInitializer(config)

    if args.verify:
        result = await initializer.verify_schema()
        print("Schema verification result:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        return

    if args.drop:
        print("Dropping existing schema...")
        await initializer.drop_schema()

    print(f"Initializing {args.backend} database with dimension {args.dimension}...")
    await initializer.initialize()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
