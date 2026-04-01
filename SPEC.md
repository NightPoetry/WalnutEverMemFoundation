# WalnutEverMem System Specification

> ⚠️ This document describes the complete system architecture and implementation details.
> It serves as the single source of truth for all language implementations.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration System](#configuration-system)
4. [Data Models](#data-models)
5. [Database Layer](#database-layer)
6. [Repository Layer](#repository-layer)
7. [Service Layer](#service-layer)
8. [API Layer](#api-layer)
9. [CLI Interface](#cli-interface)
10. [Web API](#web-api)

---

## Overview

### Purpose

WalnutEverMem is a binary-logic based infinite context memory foundation for LLMs. It provides:

- Sequential storage of chat records
- Memoization-based retrieval with emergent tree structure
- Pointer mechanism for O(1) jumps in future retrievals

### Key Concepts

1. **Chat Record**: A single message in the memory stream
2. **Pointer**: A reference from one record to another, enabling fast retrieval
3. **Session**: Isolated context identified by `session_id`
4. **Embedding**: Vector representation of content for similarity matching

### Memory Scanning Algorithm

WalnutEverMem implements a **memory scanning algorithm** with objective indexing principles:

**Core Principle**: On-demand retrieval with pairwise comparison and pointer-based optimization.

**Algorithm Flow**:

```
1. User submits query with context
2. System extracts query embedding (semantic representation)
3. Starting from latest record, scan backwards:
   a. Compute pairwise similarity: query_embedding ↔ record_embedding
   b. If similarity >= threshold:
      - Add to results
      - Create pointer from start position to this record (for future jumps)
   c. Check existing pointers at current position
   d. If pointer matches query, jump to target (O(1) access)
4. Return sorted results by relevance
```

**Key Characteristics**:

- **On-Demand (按需)**: Only retrieves when queried, no pre-computed indexes
- **Pairwise Comparison (两两比对)**: Query context compared with each memory sequentially
- **Pointer Creation (留下指针)**: Successful retrievals create shortcuts for future
- **Emergent Tree (涌现树结构)**: Over time, pointers form efficient retrieval paths
- **RAG-Based (基于 RAG)**: Uses vector similarity (cosine similarity) for semantic matching

**Comparison with File-Based Memory Scanning**:

| Aspect | Traditional File Scanning | WalnutEverMem |
|--------|--------------------------|---------------|
| Storage | Markdown files | Database (SQLite/PostgreSQL) |
| Matching | Text keyword matching | Vector embedding similarity |
| Speed | O(n) linear scan | O(1) pointer jumps + vector search |
| Intelligence | Surface-level text | Deep semantic understanding |
| Indexing | Scan result records | Pointer data structure with metadata |

**Why This Design?**

- **Database + Vectors**: Faster than file scanning, supports semantic search
- **Pointer Mechanism**: Implements memoization - successful retrievals optimize future queries
- **Sequential + Jumps**: Combines thorough scan (sequential) with fast access (pointers)
- **No Index Bloat**: Only creates pointers for actual queries, not pre-computed

---

## Architecture

### Layer Structure

```
┌─────────────────────────────────────────────┐
│                   API Layer                  │
│  (CLI, Web API, Library Interface)          │
├─────────────────────────────────────────────┤
│                Service Layer                 │
│  (MemoryService, RetrievalService)          │
├─────────────────────────────────────────────┤
│              Repository Layer                │
│  (ChatRecordRepository, PointerRepository)  │
├─────────────────────────────────────────────┤
│              Database Layer                  │
│  (SQLite / PostgreSQL with pgvector)        │
├─────────────────────────────────────────────┤
│              Configuration                   │
│  (Environment, .env, Programmatic)          │
└─────────────────────────────────────────────┘
```

### Directory Structure

#### Python Implementation

```
implementations/python/src/walnut_ever_mem/
├── __init__.py              # Package exports
├── config/
│   ├── __init__.py
│   └── config.py            # Configuration classes
├── database/
│   ├── __init__.py
│   └── init_db.py           # Database initialization
├── models/
│   └── __init__.py          # Data models
├── repository/
│   └── __init__.py          # Repository layer
├── services/
│   └── __init__.py          # Business logic
├── utils/
│   └── __init__.py          # Utility functions
├── cli.py                   # CLI entry point
├── cli_interactive.py       # Interactive CLI wizard
└── web_api.py               # FastAPI web server
```

#### Node.js/TypeScript Implementation

```
implementations/nodejs/walnut_ever_mem/src/
├── index.ts                 # Main exports
├── cli/
│   ├── init.ts              # Interactive CLI wizard
│   └── server.ts            # Express.js web server
├── config/
│   └── index.ts             # Configuration with Zod validation
├── models/
│   └── index.ts             # Data model definitions
├── repository/
│   └── index.ts             # Repository layer (SQLite/PostgreSQL)
└── services/
    └── index.ts             # Business logic and retrieval
```

#### Key Differences

| Aspect | Python | Node.js |
|--------|--------|---------|
| Package root | `src/walnut_ever_mem/` | `walnut_ever_mem/src/` |
| Config validation | pydantic | zod |
| Database (SQLite) | aiosqlite | better-sqlite3 |
| Database (PostgreSQL) | asyncpg | pg |
| Web framework | FastAPI | Express |
| CLI framework | typer + inquirer | commander + inquirer |

---

## Configuration System

### Configuration Classes

#### DatabaseConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `backend` | `"sqlite"` \| `"postgresql"` | `"sqlite"` | Database backend |
| `sqlite_path` | string | `"walnut_memory.db"` | SQLite file path |
| `host` | string | `"localhost"` | PostgreSQL host |
| `port` | integer | `5432` | PostgreSQL port |
| `database` | string | `"walnut_memory"` | PostgreSQL database name |
| `user` | string | `"postgres"` | PostgreSQL user |
| `password` | string | `""` | PostgreSQL password |

**Computed Properties:**
- `connection_url`: Returns connection URL based on backend
- `sqlite_file_path`: Returns Path object for SQLite file

**Methods:**
- `ensure_sqlite_dir()`: Creates parent directory if not exists

#### EmbeddingConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `dimension` | integer | `1536` | Vector dimension (64-4096) |
| `provider` | `"openai"` \| `"cohere"` \| `"local"` \| `"custom"` | `"openai"` | Embedding provider |
| `model_name` | string | `"text-embedding-3-small"` | Model identifier |
| `api_key` | string \| null | `null` | API key for provider |
| `api_base` | string \| null | `null` | Custom API base URL |

**Validation:**
- `dimension` must be between 64 and 4096

#### RetrievalConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `similarity_threshold` | float | `0.7` | Min similarity for matching (0.0-1.0) |
| `max_pointers_per_node` | integer | `100` | Max pointers per record (1-1000) |
| `pointer_cleanup_threshold` | integer | `1000` | Trigger cleanup threshold |

#### WalnutConfig (Main Config)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `db` | DatabaseConfig | factory | Database configuration |
| `embedding` | EmbeddingConfig | factory | Embedding configuration |
| `retrieval` | RetrievalConfig | factory | Retrieval configuration |
| `debug` | boolean | `false` | Enable debug mode |

**Methods:**
- `from_file(path)`: Load from .env file
- `to_dict()`: Export as dictionary

### Environment Variables

All configuration supports environment variables with prefix `WALNUT_`:

```
WALNUT_DB__BACKEND=sqlite
WALNUT_DB__SQLITE_PATH=memory.db
WALNUT_EMBED__DIMENSION=1536
WALNUT_EMBED__PROVIDER=openai
WALNUT_RETRIEVE__SIMILARITY_THRESHOLD=0.7
```

---

## Data Models

### MessageRole (Enum)

| Value | Description |
|-------|-------------|
| `user` | User message |
| `assistant` | AI assistant message |
| `system` | System message |

### PointerType (Enum)

| Value | Description |
|-------|-------------|
| `embedding` | Vector-based pointer |
| `summary` | Text summary pointer |

### ChatRecord

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | integer \| null | No | `null` | Auto-generated ID |
| `session_id` | string | Yes | - | Session identifier |
| `role` | MessageRole | Yes | - | Message sender role |
| `content` | string | Yes | - | Message content |
| `embedding` | number[] \| null | No | `null` | Content embedding vector |
| `created_at` | DateTime | No | `now()` | Creation timestamp |
| `metadata` | object | No | `{}` | Additional metadata |

**Methods:**
- `to_db_dict()`: Convert to database insert format
- `from_db_row(row)`: Create from database row

### Pointer

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | integer \| null | No | `null` | Auto-generated ID |
| `source_id` | integer | Yes | - | Record where pointer lives |
| `target_id` | integer | Yes | - | Record pointer points to |
| `embedding` | number[] | Yes | - | Vector for matching |
| `pointer_type` | PointerType | No | `embedding` | Type of pointer |
| `summary` | string \| null | No | `null` | Summary text |
| `relevance_score` | float \| null | No | `null` | Relevance at creation |
| `created_at` | DateTime | No | `now()` | Creation timestamp |
| `access_count` | integer | No | `0` | Times accessed |
| `last_accessed` | DateTime \| null | No | `null` | Last access time |

**Methods:**
- `to_db_dict()`: Convert to database insert format
- `from_db_row(row)`: Create from database row

### SearchResult

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `record` | ChatRecord | Yes | - | Found record |
| `score` | float | Yes | - | Relevance score |
| `via_pointer` | boolean | No | `false` | Found via pointer jump |
| `pointer_source_id` | integer \| null | No | `null` | Source if via pointer |

### RetrievalContext

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search query |
| `embedding` | number[] | Yes | - | Query embedding |
| `session_id` | string | Yes | - | Session to search |
| `max_results` | integer | No | `10` | Max results |
| `min_similarity` | float | No | `0.7` | Min similarity |

### RetrievalResult

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `results` | SearchResult[] | `[]` | Search results |
| `pointers_created` | integer | `0` | Pointers created during search |
| `records_scanned` | integer | `0` | Records scanned |
| `pointer_jumps` | integer | `0` | Pointer jumps made |

---

## Database Layer

### SQLite Schema

```sql
CREATE TABLE chat_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    embedding       BLOB,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata        TEXT
);

CREATE TABLE pointers (
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

CREATE TABLE schema_version (
    version     INTEGER PRIMARY KEY,
    dimension   INTEGER NOT NULL,
    applied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_records_session ON chat_records(session_id);
CREATE INDEX idx_chat_records_created ON chat_records(created_at DESC);
CREATE INDEX idx_pointers_source ON pointers(source_id);
CREATE INDEX idx_pointers_target ON pointers(target_id);
```

### PostgreSQL Schema

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chat_records (
    id              BIGSERIAL PRIMARY KEY,
    session_id      VARCHAR(64) NOT NULL,
    role            VARCHAR(16) NOT NULL,
    content         TEXT NOT NULL,
    embedding       VECTOR({dimension}),
    created_at      TIMESTAMP DEFAULT NOW(),
    metadata        JSONB
);

CREATE TABLE pointers (
    id              BIGSERIAL PRIMARY KEY,
    source_id       BIGINT NOT NULL REFERENCES chat_records(id) ON DELETE CASCADE,
    target_id       BIGINT NOT NULL REFERENCES chat_records(id) ON DELETE CASCADE,
    embedding       VECTOR({dimension}) NOT NULL,
    pointer_type    VARCHAR(32) DEFAULT 'embedding',
    summary         TEXT,
    relevance_score FLOAT,
    created_at      TIMESTAMP DEFAULT NOW(),
    access_count    INT DEFAULT 0,
    last_accessed   TIMESTAMP
);

CREATE TABLE schema_version (
    version     INT PRIMARY KEY,
    dimension   INT NOT NULL,
    applied_at  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_chat_records_session ON chat_records(session_id);
CREATE INDEX idx_chat_records_created ON chat_records(created_at DESC);
CREATE INDEX idx_pointers_source ON pointers(source_id);
CREATE INDEX idx_pointers_target ON pointers(target_id);
```

### Embedding Storage

**SQLite:**
- Store as BLOB (binary data)
- Convert: `Float32Array` → `Buffer`
- Size: `dimension * 4` bytes

**PostgreSQL:**
- Store as `VECTOR(dim)` type (pgvector extension)
- Pass as array of numbers

---

## Repository Layer

### ChatRecordRepository

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `create(record)` | ChatRecord | ChatRecord | Insert new record |
| `get_by_id(id)` | integer | ChatRecord \| null | Get by ID |
| `get_by_session(session_id, limit?, before_id?)` | string, int, int | ChatRecord[] | Get session records (newest first) |
| `get_latest(session_id)` | string | ChatRecord \| null | Get most recent |
| `count(session_id)` | string | integer | Count session records |

### PointerRepository

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `create(pointer)` | Pointer | Pointer | Create pointer |
| `get_pointers_at_source(source_id)` | integer | Pointer[] | Get pointers at record |
| `get_pointers_to_target(target_id)` | integer | Pointer[] | Get pointers to record |
| `find_similar_pointers(source_id, embedding, threshold, limit)` | int, number[], float, int | (Pointer, float)[] | Find similar pointers |
| `increment_access_count(id)` | integer | void | Increment access count |
| `delete(id)` | integer | boolean | Delete pointer |
| `count_at_source(source_id)` | integer | integer | Count pointers at source |

### MemoryRepository (Combined)

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `append_record(session_id, role, content, embedding?, metadata?)` | ... | ChatRecord | Append new record |
| `get_session_context(session_id, before_id?, limit?)` | ... | ChatRecord[] | Get session context |

---

## Service Layer

### EmbeddingProvider (Interface/Protocol)

```typescript
interface EmbeddingProvider {
  dimension: number;
  embed(text: string): Promise<number[]>;
}
```

### Utility Functions

#### cosine_similarity(a, b)

```
cosine_similarity(a, b) = dot(a, b) / (norm(a) * norm(b))
```

Returns: float between 0 and 1

### RetrievalService

#### Algorithm

```
1. Get latest record for session
2. While current_id exists and results < max_results:
   a. If current_id in visited_ids: break (cycle detection)
   b. Add current_id to visited_ids
   c. Get current record
   d. Increment records_scanned
   e. Compute similarity with query embedding
   f. If similarity >= threshold:
      - Add to results
      - If starting_record != current_record:
        - Create pointer from start to current
   g. Get pointers at current record
   h. For each pointer:
      - Compute pointer similarity
      - If >= threshold and target not visited:
        - Add target to results (via_pointer=true)
        - Increment pointer_jumps
        - Increment pointer access_count
   i. Get previous record (id < current_id)
   j. Set current_id to previous record's id
3. Sort results by score descending
4. Return top max_results
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `retrieve(query, session_id, query_embedding?, max_results?, min_similarity?)` | ... | RetrievalResult | Execute retrieval |

### MemoryService

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `remember(session_id, role, content, metadata?)` | ... | ChatRecord | Store memory |
| `recall(query, session_id, max_results?)` | ... | SearchResult[] | Recall memories |
| `get_context(session_id, limit?)` | ... | ChatRecord[] | Get recent context |

---

## API Layer

### Library API

```python
# Initialize
config = WalnutConfig()
await init_database(config)

# Use
memory = MemoryService.from_config(config)
record = await memory.remember("session-1", "user", "Hello")
results = await memory.recall("Hello", "session-1")
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `walnut-init` | Interactive configuration wizard |
| `walnut-init --verify` | Verify schema |
| `walnut-init --drop` | Drop and reinitialize |
| `walnut-server` | Start REST API |

### CLI Interactive Wizard Flow

```
1. Welcome message
2. Database Configuration:
   - Select backend (SQLite/PostgreSQL)
   - If SQLite: Enter path
   - If PostgreSQL: Enter host, port, database, user, password
3. Embedding Configuration:
   - Select provider (OpenAI/Cohere/Local/Custom)
   - Select model or enter dimension
   - Enter API key if needed
4. Retrieval Configuration:
   - Enter similarity threshold
   - Enter max pointers per node
5. Summary display
6. Confirm and save to .env
7. Initialize database
```

---

## Web API

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root info |
| GET | `/status` | System status |
| POST | `/init` | Initialize database |
| GET | `/config` | Get configuration |
| POST | `/remember` | Store memory |
| POST | `/recall` | Recall memories |
| GET | `/sessions/{id}/context` | Get session context |

### Request/Response Models

#### POST /init

**Request:**
```json
{
  "config": {
    "db_backend": "sqlite",
    "sqlite_path": "memory.db",
    "embedding_dimension": 1536,
    "embedding_provider": "openai"
  },
  "drop_existing": false
}
```

**Response:**
```json
{
  "status": "initialized",
  "backend": "sqlite",
  "tables_exist": true,
  "dimension_match": true,
  "recorded_dimension": 1536
}
```

#### POST /remember

**Request:**
```json
{
  "session_id": "user-123",
  "role": "user",
  "content": "I want to visit Paris",
  "embedding": [0.1, 0.2, ...],
  "metadata": {"key": "value"}
}
```

**Response:**
```json
{
  "id": 1,
  "session_id": "user-123",
  "role": "user",
  "content": "I want to visit Paris",
  "embedding": [0.1, 0.2, ...],
  "created_at": "2024-01-01T00:00:00",
  "metadata": {"key": "value"}
}
```

#### POST /recall

**Request:**
```json
{
  "session_id": "user-123",
  "query": "travel plans",
  "query_embedding": [0.1, 0.2, ...],
  "max_results": 10,
  "min_similarity": 0.7
}
```

**Response:**
```json
[
  {
    "record": {
      "id": 1,
      "session_id": "user-123",
      "role": "user",
      "content": "I want to visit Paris",
      "embedding": [0.1, 0.2, ...],
      "created_at": "2024-01-01T00:00:00",
      "metadata": {}
    },
    "score": 0.85,
    "via_pointer": false,
    "pointer_source_id": null
  }
]
```

---

## Implementation Notes

### Async/Await Pattern

All database operations must be async:
- SQLite: Use `better-sqlite3` (sync) or `sql.js` (async)
- PostgreSQL: Use `pg` with async

### Error Handling

- Configuration validation errors should be thrown early
- Database errors should be wrapped with context
- API errors should return appropriate HTTP status codes

### Testing

Unit tests should cover:
- Configuration validation
- Model serialization/deserialization
- Repository CRUD operations
- Retrieval algorithm correctness
- API endpoint responses

---

## Version Compatibility

| Feature | Python | Node.js |
|---------|--------|---------|
| SQLite | aiosqlite | better-sqlite3 / sql.js |
| PostgreSQL | asyncpg | pg |
| Validation | pydantic | zod |
| Config | pydantic-settings | dotenv + zod |
| Web API | FastAPI | Express / Fastify |
| CLI | argparse | commander / yargs |
