"""Interactive CLI for WalnutEverMem configuration and initialization."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from walnut_ever_mem.config import DatabaseConfig, EmbeddingConfig, WalnutConfig
from walnut_ever_mem.database import DatabaseInitializer


def prompt_text(message: str, default: str = "") -> str:
    """Simple text prompt with default value."""
    hint = f" [{default}]" if default else ""
    while True:
        try:
            result = input(f"{message}{hint}: ").strip()
            return result if result else default
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(1)


def prompt_choice(message: str, choices: list[str], default: int = 0) -> int:
    """Simple choice prompt."""
    print(f"\n{message}")
    for i, choice in enumerate(choices):
        marker = ">" if i == default else " "
        print(f"  {marker} {i + 1}. {choice}")

    while True:
        try:
            result = input(f"Select [1-{len(choices)}] (default {default + 1}): ").strip()
            if not result:
                return default
            idx = int(result) - 1
            if 0 <= idx < len(choices):
                return idx
            print(f"Please enter a number between 1 and {len(choices)}")
        except ValueError:
            print("Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(1)


def prompt_yes_no(message: str, default: bool = True) -> bool:
    """Simple yes/no prompt."""
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            result = input(f"{message} {hint}: ").strip().lower()
            if not result:
                return default
            return result in ("y", "yes", "true", "1")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(1)


def interactive_config() -> WalnutConfig:
    """Run interactive configuration wizard."""
    print("\n" + "=" * 50)
    print("  WalnutEverMem Configuration Wizard")
    print("=" * 50)

    print("\n[Database Configuration]")
    print("-" * 30)

    backend_idx = prompt_choice(
        "Select database backend:",
        ["SQLite (recommended, zero-config)", "PostgreSQL (for production)"],
        default=0,
    )
    backend = "sqlite" if backend_idx == 0 else "postgresql"

    db_config_kwargs: dict[str, Any] = {"backend": backend}

    if backend == "sqlite":
        db_path = prompt_text("SQLite database path", default="walnut_memory.db")
        db_config_kwargs["sqlite_path"] = db_path
    else:
        print("\nPostgreSQL Configuration:")
        db_config_kwargs["host"] = prompt_text("Host", default="localhost")
        db_config_kwargs["port"] = int(prompt_text("Port", default="5432"))
        db_config_kwargs["database"] = prompt_text("Database name", default="walnut_memory")
        db_config_kwargs["user"] = prompt_text("User", default="postgres")
        db_config_kwargs["password"] = prompt_text("Password", default="")

    print("\n[Embedding Configuration]")
    print("-" * 30)

    embed_config_kwargs: dict[str, Any] = {}

    provider_idx = prompt_choice(
        "Select embedding provider:",
        ["OpenAI", "Cohere", "Local (sentence-transformers)", "Custom"],
        default=0,
    )
    providers = ["openai", "cohere", "local", "custom"]
    embed_config_kwargs["provider"] = providers[provider_idx]

    if embed_config_kwargs["provider"] == "openai":
        model_idx = prompt_choice(
            "Select OpenAI embedding model:",
            ["text-embedding-3-small (1536 dim)", "text-embedding-3-large (3072 dim)"],
            default=0,
        )
        dimensions = [1536, 3072]
        model_names = ["text-embedding-3-small", "text-embedding-3-large"]
        embed_config_kwargs["dimension"] = dimensions[model_idx]
        embed_config_kwargs["model_name"] = model_names[model_idx]

        api_key = prompt_text("OpenAI API Key (leave empty to use env var)", default="")
        if api_key:
            embed_config_kwargs["api_key"] = api_key

    elif embed_config_kwargs["provider"] == "cohere":
        embed_config_kwargs["dimension"] = 1024
        embed_config_kwargs["model_name"] = "embed-v3"
        api_key = prompt_text("Cohere API Key", default="")
        if api_key:
            embed_config_kwargs["api_key"] = api_key

    elif embed_config_kwargs["provider"] == "local":
        embed_config_kwargs["dimension"] = int(prompt_text("Embedding dimension", default="384"))
        embed_config_kwargs["model_name"] = prompt_text("Model name", default="all-MiniLM-L6-v2")

    else:
        embed_config_kwargs["dimension"] = int(prompt_text("Embedding dimension", default="1536"))
        embed_config_kwargs["model_name"] = prompt_text("Model name", default="custom")
        embed_config_kwargs["api_base"] = prompt_text("API base URL", default="")

    print("\n[Retrieval Configuration]")
    print("-" * 30)

    retrieval_config_kwargs: dict[str, Any] = {}

    retrieval_config_kwargs["similarity_threshold"] = float(
        prompt_text("Similarity threshold (0.0-1.0)", default="0.7")
    )
    retrieval_config_kwargs["max_pointers_per_node"] = int(
        prompt_text("Max pointers per node", default="100")
    )

    print("\n[Summary]")
    print("-" * 30)
    print(f"Database: {backend}")
    if backend == "sqlite":
        print(f"  Path: {db_config_kwargs.get('sqlite_path')}")
    else:
        print(f"  Host: {db_config_kwargs.get('host')}:{db_config_kwargs.get('port')}")
        print(f"  Database: {db_config_kwargs.get('database')}")
    print(f"Embedding: {embed_config_kwargs.get('provider')}")
    print(f"  Model: {embed_config_kwargs.get('model_name')}")
    print(f"  Dimension: {embed_config_kwargs.get('dimension')}")
    print(f"Retrieval:")
    print(f"  Similarity threshold: {retrieval_config_kwargs.get('similarity_threshold')}")
    print(f"  Max pointers per node: {retrieval_config_kwargs.get('max_pointers_per_node')}")

    if not prompt_yes_no("\nProceed with this configuration?", default=True):
        print("Configuration cancelled.")
        sys.exit(0)

    return WalnutConfig(
        db=DatabaseConfig(**db_config_kwargs),
        embedding=EmbeddingConfig(**embed_config_kwargs),
    )


def save_config(config: WalnutConfig, path: str = ".env") -> None:
    """Save configuration to .env file."""
    lines = [
        "# WalnutEverMem Configuration",
        "# Generated by walnut-init",
        "",
        "# Database Configuration",
        f"WALNUT_DB__BACKEND={config.db.backend}",
    ]

    if config.db.backend == "sqlite":
        lines.append(f"WALNUT_DB__SQLITE_PATH={config.db.sqlite_path}")
    else:
        lines.extend([
            f"WALNUT_DB__HOST={config.db.host}",
            f"WALNUT_DB__PORT={config.db.port}",
            f"WALNUT_DB__DATABASE={config.db.database}",
            f"WALNUT_DB__USER={config.db.user}",
            f"WALNUT_DB__PASSWORD={config.db.password}",
        ])

    lines.extend([
        "",
        "# Embedding Configuration",
        f"WALNUT_EMBED__DIMENSION={config.embedding.dimension}",
        f"WALNUT_EMBED__PROVIDER={config.embedding.provider}",
        f"WALNUT_EMBED__MODEL_NAME={config.embedding.model_name}",
    ])

    if config.embedding.api_key:
        lines.append(f"WALNUT_EMBED__API_KEY={config.embedding.api_key}")
    if config.embedding.api_base:
        lines.append(f"WALNUT_EMBED__API_BASE={config.embedding.api_base}")

    lines.extend([
        "",
        "# Retrieval Configuration",
        f"WALNUT_RETRIEVE__SIMILARITY_THRESHOLD={config.retrieval.similarity_threshold}",
        f"WALNUT_RETRIEVE__MAX_POINTERS_PER_NODE={config.retrieval.max_pointers_per_node}",
        "",
        "# Debug Mode",
        f"WALNUT_DEBUG={str(config.debug).lower()}",
    ])

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nConfiguration saved to: {path}")


async def init_interactive() -> None:
    """Run interactive initialization."""
    print("\nWelcome to WalnutEverMem!")
    print("This wizard will help you set up your infinite context memory.\n")

    config = interactive_config()

    save = prompt_yes_no("\nSave configuration to .env file?", default=True)
    if save:
        save_config(config)

    init_db = prompt_yes_no("\nInitialize database now?", default=True)
    if init_db:
        print("\nInitializing database...")
        initializer = DatabaseInitializer(config)
        await initializer.initialize()
        print("Database initialized successfully!")

    print("\n" + "=" * 50)
    print("  Setup Complete!")
    print("=" * 50)
    print("\nQuick Start:")
    print("  from walnut_ever_mem import WalnutConfig, MemoryService")
    print("  config = WalnutConfig.from_file('.env')")
    print("  memory = MemoryService.from_config(config)")
    print("  await memory.remember('session-1', 'user', 'Hello!')")
    print()


def main_interactive() -> None:
    """Entry point for interactive CLI."""
    asyncio.run(init_interactive())


if __name__ == "__main__":
    main_interactive()
