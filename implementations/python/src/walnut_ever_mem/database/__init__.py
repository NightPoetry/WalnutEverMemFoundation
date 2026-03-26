"""Database initialization and schema management."""

import asyncio
import logging
from typing import Any

import asyncpg

from walnut_ever_mem.config import WalnutConfig

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Initialize and manage database schema.

    The schema is dynamically generated based on configuration,
    particularly the embedding dimension.
    """

    def __init__(self, config: WalnutConfig):
        self.config = config
        self.dimension = config.embedding.dimension

    def _get_create_chat_records_sql(self) -> str:
        """Generate chat_records table SQL with configured dimension."""
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

    def _get_create_pointers_sql(self) -> str:
        """Generate pointers table SQL with configured dimension."""
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

    def _get_create_indexes_sql(self) -> list[str]:
        """Generate index creation SQL."""
        return [
            "CREATE INDEX IF NOT EXISTS idx_chat_records_session ON chat_records(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_chat_records_created ON chat_records(created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_pointers_source ON pointers(source_id);",
            "CREATE INDEX IF NOT EXISTS idx_pointers_target ON pointers(target_id);",
        ]

    def _get_enable_vector_extension_sql(self) -> str:
        """Enable pgvector extension."""
        return "CREATE EXTENSION IF NOT EXISTS vector;"

    async def initialize(self, conn: asyncpg.Connection | None = None) -> None:
        """Initialize the database schema.

        Args:
            conn: Optional existing connection. If None, creates a new one.
        """
        should_close = False
        if conn is None:
            conn = await asyncpg.connect(self.config.db.connection_url)
            should_close = True

        try:
            async with conn.transaction():
                logger.info(f"Initializing database with embedding dimension: {self.dimension}")

                await conn.execute(self._get_enable_vector_extension_sql())
                logger.info("Enabled pgvector extension")

                await conn.execute(self._get_create_chat_records_sql())
                logger.info("Created chat_records table")

                await conn.execute(self._get_create_pointers_sql())
                logger.info("Created pointers table")

                for index_sql in self._get_create_indexes_sql():
                    await conn.execute(index_sql)
                logger.info("Created indexes")

                await self._record_schema_version(conn)
                logger.info("Database initialization complete")

        finally:
            if should_close:
                await conn.close()

    async def _record_schema_version(self, conn: asyncpg.Connection) -> None:
        """Record schema version for migrations."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version     INT PRIMARY KEY,
                dimension   INT NOT NULL,
                applied_at  TIMESTAMP DEFAULT NOW()
            );
        """)

        exists = await conn.fetchval(
            "SELECT 1 FROM schema_version WHERE version = 1"
        )
        if not exists:
            await conn.execute(
                "INSERT INTO schema_version (version, dimension) VALUES (1, $1)",
                self.dimension
            )

    async def verify_schema(self, conn: asyncpg.Connection | None = None) -> dict[str, Any]:
        """Verify the database schema is correct.

        Returns:
            Dict with verification results.
        """
        should_close = False
        if conn is None:
            conn = await asyncpg.connect(self.config.db.connection_url)
            should_close = True

        try:
            result = {
                "tables_exist": False,
                "vector_extension": False,
                "dimension_match": False,
                "recorded_dimension": None,
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
            if should_close:
                await conn.close()

    async def drop_schema(self, conn: asyncpg.Connection | None = None) -> None:
        """Drop all tables (use with caution!).

        Args:
            conn: Optional existing connection.
        """
        should_close = False
        if conn is None:
            conn = await asyncpg.connect(self.config.db.connection_url)
            should_close = True

        try:
            async with conn.transaction():
                await conn.execute("DROP TABLE IF EXISTS pointers CASCADE;")
                await conn.execute("DROP TABLE IF EXISTS chat_records CASCADE;")
                await conn.execute("DROP TABLE IF EXISTS schema_version CASCADE;")
                logger.warning("Dropped all tables")

        finally:
            if should_close:
                await conn.close()


async def init_database(config: WalnutConfig) -> None:
    """Convenience function to initialize database.

    Args:
        config: WalnutEverMem configuration.
    """
    initializer = DatabaseInitializer(config)
    await initializer.initialize()


async def main() -> None:
    """CLI entry point for database initialization."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize WalnutEverMem database")
    parser.add_argument(
        "--dimension", "-d",
        type=int,
        default=1536,
        help="Embedding vector dimension (default: 1536)",
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
        embedding=EmbeddingConfig(dimension=args.dimension)
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

    print(f"Initializing database with dimension {args.dimension}...")
    await initializer.initialize()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
