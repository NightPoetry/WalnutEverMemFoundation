# WalnutEverMemFoundation

> ⚠️ **WARNING: This project is currently in the engineering testing phase.**
> 
> **Please do NOT download or use it at this time. It is NOT functional yet.**
> 
> This repository is under active development and will be announced when ready for use.

A binary-logic based infinite context memory foundation for LLMs, serving as an AI memory OS that requires Skill modules for practical use.

## Purpose

Current AI systems lack infinite context capacity. Yet humans also lack infinite context—what enables us to function as if we had it? The answer lies in external records: chat histories, documents, notes. We achieve "infinite context" through comparison, retrieval, and browsing.

However, existing memory frameworks embed strong subjective biases:

- **Human subjectivity**: Manually designed hierarchies, arbitrary categorizations, predefined sections
- **AI subjectivity**: Pre-processing messages into structured formats before storage

These approaches work quickly in early stages but suffer from poor generalization. They impose structure from the outside rather than letting structure emerge from within.

## Design Philosophy

**Structure should be a reflection of the environment, not a product of subjective design.**

If we remove all subjective design, retrieval would require scanning from the first record to the last—accurate but impossibly slow. The slowness comes from wasted effort: every query repeats the full scan, even for identical questions.

The solution exists in classical computer science: **memoization**. This concept also manifests as **dynamic programming** in mathematical formulations.

The key insight: records are generated through use, making them intrinsically tied to the environment. When the environment is stable, the resulting tree-structured index becomes the most efficient and precise index possible.

### What if the environment changes drastically?

The system has a fallback: if the existing index fails to locate needed information, it reverts to full sequential search. It becomes slower, but never weaker.

This mirrors physical reality: when encountering a truly novel environment, how could past experience yield instant results? If past experience does yield instant results, it only proves the environment hasn't changed much.

## Theoretical Foundation: Binary Logic

All logic can be expressed as binary logic. Therefore, any computational problem can be solved through pairwise comparison between an intermediate memory and memories in the memory bank.

However, transforming multi-valued logic into binary logic requires a conversion process—not everything can be directly solved with binary logic. This conversion process is precisely the **AI's learning process at the memory level**.

### Learning, Not Fine-tuning

This learning differs fundamentally from gradient-based fine-tuning:

- The AI learns by accumulating demonstrations and cases into its memory structure
- It learns how to transform external retrieval problems into internal binary-structure retrieval problems
- Learning occurs through language-level exploration: direct instruction or self-discovery through experimentation

### No Gradient Descent Required

Given the mechanism, the AI can discover paths to implement binary logic transformations on its own. More importantly:

- Through repeated instruction and guidance during use, natural tree structures and retrieval structures emerge
- No gradient descent needed—direct transfer of human experience
- The structure is a natural product of interaction, not optimization

### This is an Initial Exploration

We don't know the final outcome, but we can at least achieve an infinite-context AI memory tool. According to binary logic principles, with sufficient quality instruction, it should work.

### Future Considerations

The current tree-structured index may have optimization potential. Natural retrieval structures in the real world might be graph structures or other forms—this remains an open question for further exploration.

## System Architecture

### Base Storage: Sequential Chat Records

The foundation is a sequential storage of chat records—the raw memory stream. No pre-processing, no categorization. Records exist exactly as they occurred.

### Workspace Memory

**Note**: Workspace memory is external to this system. This foundation only provides infinite context storage and retrieval. How the calling system uses it—as workspace memory, as user context, or otherwise—is an external concern.

The foundation simply provides:
- Create new context streams (via `session_id`)
- Append records to a stream
- Retrieve relevant records via pointer-enhanced search

### Retrieval Process: Pairwise Comparison

To find information, the system compares workspace memory against chat records sequentially:

```
Query: "Where did I say I wanted to travel yesterday?"
    ↓
Current record → Compare → Not found → Previous record
    ↓
Compare → Found → Generate pointer
```

### Pointer Mechanism: The Tree Emerges

When a target is found, a **pointer** is created at the current position, pointing to the target record. Future queries on related topics:

1. Encounter the pointer
2. Jump directly to the target
3. Skip intermediate records

Multiple such pointers form a **tree structure**—the index emerges from successful retrievals.

### Retrieval Algorithm

```
At each node:
  1. Check the chat record at this position
  2. Check all quick pointers stored at this node
  3. Continue backward sequentially
```

**Best case**: Pointer chain leads directly to target  
**Worst case**: Degrades to full sequential scan

### Open Problems

- **Pointer invalidation**: When environment changes, some pointers may become obsolete. A cleanup mechanism is not yet designed.
- **Pointer representation**: Multiple forms possible:
  - **Summary pointer**: Textual summary of target content
  - **Embedding pointer**: Vector representation of target

Which has better generalization? For weaker AI, embedding may generalize better. For stronger AI, summaries might allow the model to generalize on its own. This remains an open question.

**Current choice**: Embedding-based pointers.

### Implementation

- **Storage**: Relational database (records are fundamentally text)
- **Index**: Embedding vectors for pointer representation

### Database Schema

```sql
-- Chat records: the sequential memory stream
CREATE TABLE chat_records (
    id              BIGSERIAL PRIMARY KEY,
    session_id      VARCHAR(64) NOT NULL,
    role            VARCHAR(16) NOT NULL,      -- 'user' | 'assistant' | 'system'
    content         TEXT NOT NULL,
    embedding       VECTOR(1536),              -- content embedding (optional)
    created_at      TIMESTAMP DEFAULT NOW(),
    metadata        JSONB                      -- extensible metadata
);

-- Pointers: the emergent tree structure
CREATE TABLE pointers (
    id              BIGSERIAL PRIMARY KEY,
    source_id       BIGINT NOT NULL REFERENCES chat_records(id),
    target_id       BIGINT NOT NULL REFERENCES chat_records(id),
    embedding       VECTOR(1536) NOT NULL,     -- pointer embedding for matching
    pointer_type    VARCHAR(32) DEFAULT 'embedding',  -- 'embedding' | 'summary'
    summary         TEXT,                      -- for summary-type pointers
    relevance_score FLOAT,                     -- relevance at creation time
    created_at      TIMESTAMP DEFAULT NOW(),
    access_count    INT DEFAULT 0,             -- for cleanup heuristics
    last_accessed   TIMESTAMP
);

-- Indexes for efficient retrieval
CREATE INDEX idx_chat_records_session ON chat_records(session_id);
CREATE INDEX idx_chat_records_created ON chat_records(created_at DESC);
CREATE INDEX idx_pointers_source ON pointers(source_id);
CREATE INDEX idx_pointers_target ON pointers(target_id);
```

### Entity Relationship

```
┌─────────────────┐         ┌─────────────────┐
│  chat_records   │         │    pointers     │
├─────────────────┤         ├─────────────────┤
│ id (PK)         │◄────────│ source_id (FK)  │
│ session_id      │         │ target_id (FK)  │──► chat_records.id
│ role            │         │ embedding       │
│ content         │         │ pointer_type    │
│ embedding       │         │ access_count    │
│ created_at      │         └─────────────────┘
└─────────────────┘
```

### Notes

- `chat_records`: Append-only, maintains chronological order. Multiple sessions supported via `session_id`.
- `pointers`: The emergent index; `source_id` is where pointer lives, `target_id` is where it points
- `VECTOR(1536)`: Assumes OpenAI embedding dimension; adjust as needed
- This foundation is agnostic to how sessions are used—workspace memory, user context, etc. are external concerns

## Scope: Toward AGI

This system addresses all problems that are logically solvable by humans.

### The Logic-Statistics Framework

- **Logically solvable problems**: All can be transformed into binary problems, which our system handles natively
- **Logically unsolvable problems**: These are statistical problems. Statistics itself can be implemented through logic—we build statistical tools under logical control, then use these tools to process what lies beyond pure logic

### The Path to AGI

With this infinite memory foundation, we have a pathway to approach AGI at the macro level:

```
Logic Layer (Binary Operations)
        ↓
    Controls
        ↓
Statistical Tools (for non-logical domains)
```

The memory foundation serves as the substrate where logical reasoning accumulates and structures itself. Statistical tools, built and invoked through logic, extend capability into domains where pure logic cannot reach—mirroring how humans use formal methods to handle uncertainty.

## Installation

```bash
pip install walnut-ever-mem
```

## Quick Start

### 1. Interactive CLI Setup

The easiest way to get started:

```bash
walnut-init
```

This launches an interactive wizard that guides you through configuration:

```
==================================================
  WalnutEverMem Configuration Wizard
==================================================

[Database Configuration]
------------------------------
Select database backend:
  > 1. SQLite (recommended, zero-config)
    2. PostgreSQL (for production)
Select [1-2] (default 1): 1

SQLite database path [walnut_memory.db]: ./data/memory.db

[Embedding Configuration]
------------------------------
Select embedding provider:
  > 1. OpenAI
    2. Cohere
    3. Local (sentence-transformers)
    4. Custom
Select [1-4] (default 1): 1

Select OpenAI embedding model:
  > 1. text-embedding-3-small (1536 dim)
    2. text-embedding-3-large (3072 dim)
Select [1-2] (default 1): 1

OpenAI API Key (leave empty to use env var): sk-xxx

[Retrieval Configuration]
------------------------------
Similarity threshold (0.0-1.0) [0.7]: 
Max pointers per node [100]: 

[Summary]
------------------------------
Database: sqlite
  Path: ./data/memory.db
Embedding: openai
  Model: text-embedding-3-small
  Dimension: 1536
Retrieval:
  Similarity threshold: 0.7
  Max pointers per node: 100

Proceed with this configuration? [Y/n]: y

Configuration saved to: .env
Initialize database now? [Y/n]: y

Database initialized successfully!
```

### 2. Web API

Start the REST API server:

```bash
walnut-server
# or
python -m walnut_ever_mem.web_api
```

The API will be available at `http://localhost:8000`.

#### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root info |
| GET | `/status` | System status |
| POST | `/init` | Initialize database |
| GET | `/config` | Get configuration |
| POST | `/remember` | Store a memory |
| POST | `/recall` | Search memories |
| GET | `/sessions/{id}/context` | Get session context |

#### Initialize via API

```bash
curl -X POST http://localhost:8000/init \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "db_backend": "sqlite",
      "sqlite_path": "memory.db",
      "embedding_dimension": 1536
    }
  }'
```

#### Store a Memory

```bash
curl -X POST http://localhost:8000/remember \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-123",
    "role": "user",
    "content": "I want to visit Paris next summer",
    "embedding": [0.1, 0.2, ...]
  }'
```

#### Recall Memories

```bash
curl -X POST http://localhost:8000/recall \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user-123",
    "query": "travel plans",
    "query_embedding": [0.1, 0.2, ...],
    "max_results": 5
  }'
```

### 3. Library API

Use as a Python library:

```python
import asyncio
from walnut_ever_mem import WalnutConfig
from walnut_ever_mem.database import init_database
from walnut_ever_mem.services import MemoryService

async def main():
    # Load or create configuration
    config = WalnutConfig()  # Uses defaults or .env file
    
    # Initialize database
    await init_database(config)
    
    # Create memory service
    memory = MemoryService.from_config(config)
    
    # Store memories
    await memory.remember(
        session_id="user-123",
        role="user",
        content="I love pizza with extra cheese",
    )
    
    # Recall memories
    results = await memory.recall(
        query="food preferences",
        session_id="user-123",
        max_results=5,
    )
    
    for result in results:
        print(f"Score: {result.score:.2f}")
        print(f"Content: {result.record.content}")
        print(f"Via pointer: {result.via_pointer}")

asyncio.run(main())
```

#### Custom Configuration

```python
from walnut_ever_mem import WalnutConfig, DatabaseConfig, EmbeddingConfig

# SQLite with custom path
config = WalnutConfig(
    db=DatabaseConfig(
        backend="sqlite",
        sqlite_path="/data/memories.db",
    ),
    embedding=EmbeddingConfig(
        dimension=1536,
        provider="openai",
    ),
)

# PostgreSQL for production
config = WalnutConfig(
    db=DatabaseConfig(
        backend="postgresql",
        host="db.example.com",
        port=5432,
        database="walnut_prod",
        user="app_user",
        password="secret",
    ),
    embedding=EmbeddingConfig(
        dimension=3072,
        provider="openai",
        model_name="text-embedding-3-large",
    ),
)
```

#### With Custom Embedding Provider

```python
import numpy as np
from walnut_ever_mem.services import MemoryService, RetrievalService

class MyEmbeddingProvider:
    """Custom embedding provider."""
    
    @property
    def dimension(self) -> int:
        return 384
    
    async def embed(self, text: str) -> np.ndarray:
        # Your embedding logic here
        return np.random.rand(384).astype(np.float32)

async def main():
    config = WalnutConfig(
        embedding=EmbeddingConfig(dimension=384, provider="custom")
    )
    
    await init_database(config)
    
    embedding_provider = MyEmbeddingProvider()
    memory = MemoryService(
        repo=repo,
        config=config,
        embedding_provider=embedding_provider,
    )
    
    # Now remembers with automatic embedding
    await memory.remember("session-1", "user", "Hello!")
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WALNUT_DB__BACKEND` | `sqlite` | Database backend |
| `WALNUT_DB__SQLITE_PATH` | `walnut_memory.db` | SQLite file path |
| `WALNUT_DB__HOST` | `localhost` | PostgreSQL host |
| `WALNUT_DB__PORT` | `5432` | PostgreSQL port |
| `WALNUT_DB__DATABASE` | `walnut_memory` | PostgreSQL database |
| `WALNUT_DB__USER` | `postgres` | PostgreSQL user |
| `WALNUT_DB__PASSWORD` | `""` | PostgreSQL password |
| `WALNUT_EMBED__DIMENSION` | `1536` | Embedding dimension |
| `WALNUT_EMBED__PROVIDER` | `openai` | Embedding provider |
| `WALNUT_EMBED__MODEL_NAME` | `text-embedding-3-small` | Model name |
| `WALNUT_EMBED__API_KEY` | `None` | API key |
| `WALNUT_RETRIEVE__SIMILARITY_THRESHOLD` | `0.7` | Min similarity |
| `WALNUT_RETRIEVE__MAX_POINTERS_PER_NODE` | `100` | Max pointers |

### .env File Example

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit as needed
WALNUT_DB__BACKEND=sqlite
WALNUT_DB__SQLITE_PATH=./data/memory.db
WALNUT_EMBED__DIMENSION=1536
WALNUT_EMBED__PROVIDER=openai
WALNUT_EMBED__API_KEY=sk-your-key
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `walnut-init` | Interactive configuration wizard |
| `walnut-init --verify` | Verify database schema |
| `walnut-init --drop` | Drop and reinitialize database |
| `walnut-server` | Start REST API server |
| `walnut-server --port 8080` | Start on custom port |

## Core Principle

```
Environment → Usage → Records → Index Structure
```

Not:

```
Human Design → Predefined Structure → Forced Index
```

The index emerges from interaction, not from assumption.

## License

Apache License 2.0
