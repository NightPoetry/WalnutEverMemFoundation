# WalnutEverMemFoundation

> ⚠️ **WARNING: This project is currently in the engineering testing phase.**
> 
> **Do NOT download or use it. It is NOT functional yet.**
> 
> This repository is under active development. An announcement will be made when it becomes available.

A binary-logic based infinite context memory foundation for LLMs, serving as an AI memory OS that requires Skill modules for practical use.

## Project Structure

This repository contains multiple implementations of the same specification:

```
Core/
├── implementations/
│   ├── python/          # Python implementation
│   │   ├── src/
│   │   │   └── walnut_ever_mem/
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── nodejs/          # Node.js/TypeScript implementation
│       ├── walnut_ever_mem/
│       │   └── src/
│       ├── package.json
│       └── tsconfig.json
├── SPEC.md              # System specification (single source of truth)
├── README.md            # This file
└── README_CN.md         # Chinese version
```

## Implementations

### Python Version

- **Location**: `implementations/python/`
- **Package**: `walnut-ever-mem`
- **Requirements**: Python 3.10+
- **Dependencies**: pydantic, aiosqlite, asyncpg, numpy, fastapi

**Installation:**
```bash
cd implementations/python
pip install -e .
```

**Quick Start:**
```bash
# Interactive CLI
walnut-init

# Web API
walnut-server

# Library
from walnut_ever_mem import WalnutConfig, MemoryService
```

### Node.js/TypeScript Version

- **Location**: `implementations/nodejs/`
- **Package**: `walnut-ever-mem`
- **Requirements**: Node.js 18+
- **Dependencies**: zod, better-sqlite3, pg, express, commander

**Installation:**
```bash
cd implementations/nodejs
npm install
npm run build
```

**Quick Start:**
```bash
# Interactive CLI
npx walnut-init

# Web API
npx walnut-server

# Library
import { createConfig, MemoryService } from 'walnut-ever-mem';
```

## Specification

Both implementations follow the same system specification defined in `SPEC.md`. This ensures:

- Identical API interfaces
- Same data models
- Consistent behavior
- Cross-language compatibility

## Which Implementation to Choose?

**Choose Python if:**
- You're working in AI/ML ecosystem
- Need rich data science libraries
- Prefer dynamic typing

**Choose Node.js if:**
- You're building web applications
- Need high concurrency
- Prefer TypeScript for type safety

## Development

### Adding a New Implementation

1. Read `SPEC.md` thoroughly
2. Create new directory under `implementations/`
3. Follow the same API structure
4. Add tests matching Python/Node.js test patterns

### Updating All Implementations

When making changes to the specification:

1. Update `SPEC.md` first
2. Update all implementations to match
3. Ensure tests pass in all implementations

## License

Apache License 2.0
