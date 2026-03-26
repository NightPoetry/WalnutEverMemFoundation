# WalnutEverMem - Node.js/TypeScript Version

> ⚠️ **WARNING: This project is currently in the engineering testing phase.**
> 
> **Do NOT download or use it. It is NOT functional yet.**

A binary-logic based infinite context memory foundation for LLMs.

## Installation

```bash
npm install walnut-ever-mem
```

## Quick Start

### Interactive CLI

```bash
npx walnut-init
```

### Web API

```bash
npx walnut-server
# or
npx walnut-server 8080  # custom port
```

### Library API

```typescript
import { createConfig, DatabaseInitializer, MemoryService, MemoryRepository } from 'walnut-ever-mem';
import Database from 'better-sqlite3';

// Initialize
const config = createConfig();
await new DatabaseInitializer(config).initialize();

// Use
const db = new Database('walnut_memory.db');
const repo = new MemoryRepository(db, config);
const memory = new MemoryService(repo, config);

// Remember
await memory.remember('session-1', 'user', 'Hello!');

// Recall
const results = await memory.recall('greeting', 'session-1');
```

## Configuration

### Environment Variables

```bash
WALNUT_DB__BACKEND=sqlite
WALNUT_DB__SQLITE_PATH=walnut_memory.db
WALNUT_EMBED__DIMENSION=1536
WALNUT_EMBED__PROVIDER=openai
WALNUT_EMBED__API_KEY=sk-xxx
WALNUT_RETRIEVE__SIMILARITY_THRESHOLD=0.7
```

### Programmatic Configuration

```typescript
import { createConfig } from 'walnut-ever-mem';

const config = createConfig({
  db: {
    backend: 'sqlite',
    sqlitePath: './data/memory.db',
  },
  embedding: {
    dimension: 1536,
    provider: 'openai',
    modelName: 'text-embedding-3-small',
  },
});
```

## API Reference

### MemoryService

```typescript
// Store a memory
await memory.remember(sessionId: string, role: string, content: string, metadata?: object);

// Recall memories
await memory.recall(query: string, sessionId: string, maxResults?: number);

// Get context
await memory.getContext(sessionId: string, limit?: number);
```

### Web API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root info |
| GET | `/status` | System status |
| POST | `/init` | Initialize database |
| GET | `/config` | Get configuration |
| POST | `/remember` | Store memory |
| POST | `/recall` | Recall memories |
| GET | `/sessions/:id/context` | Get session context |

## License

Apache License 2.0
