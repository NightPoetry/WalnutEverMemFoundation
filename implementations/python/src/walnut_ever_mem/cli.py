"""CLI interface for WalnutEverMem."""

import argparse
import asyncio
import logging

from walnut_ever_mem.config import DatabaseConfig, EmbeddingConfig, WalnutConfig
from walnut_ever_mem.database import DatabaseInitializer

logging.basicConfig(level=logging.INFO)


async def init_db() -> None:
    """Initialize database with default configuration."""
    parser = argparse.ArgumentParser(description="Initialize WalnutEverMem database")
    parser.add_argument(
        "--dimension", "-d",
        type=int,
        default=1536,
        help="Embedding vector dimension (default: 1536)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Database host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5432,
        help="Database port (default: 5432)",
    )
    parser.add_argument(
        "--database",
        type=str,
        default="walnut_memory",
        help="Database name (default: walnut_memory)",
    )
    parser.add_argument(
        "--user",
        type=str,
        default="postgres",
        help="Database user (default: postgres)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default="",
        help="Database password",
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

    print(f"Initializing database with dimension {args.dimension}...")
    await initializer.initialize()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(init_db())
