# WalnutEverMemFoundation

> ⚠️ **WARNING: This project is currently in the engineering testing phase.**
> 
> **Do NOT download or use it. It is NOT functional yet.**
> 
> This repository is under active development. An announcement will be made when it becomes available.

A binary-logic based infinite context memory foundation for LLMs, serving as an AI memory OS that requires Skill modules for practical use.

## Why I Open Source This Project

I've observed that many people may have developed impressive memory mechanisms. However, my goal is to accelerate the realization of AGI for the world—faster, and faster still. I hope to witness a transformative leap for all humanity within my lifetime.

I aim to solve the problems of AGI, and use AGI to solve all of humanity's problems: diseases and disasters, resource depletion, mental breakdowns, gentle companionship, and beyond.

I don't know if this approach has been explored before, or how effective it will be (I lack the large-scale data needed for thorough testing). Yet I choose to open source the final result of years of my thinking, hoping it may inspire others.

If this work happens to inspire you, I hope you'll reach out and let me participate in your project. I want to contribute to AGI, and I need more resources to validate my hypotheses and conjectures.

Some pursue AGI research for fame and money. I pursue AGI research, and for that, I need a certain amount of fame and money.

My ultimate goal is to solve AGI, and use AGI to solve all of humanity's problems: diseases and disasters, resource depletion, mental collapse, gentle companionship, and beyond.

**Contact**: 
- Submit an issue on GitHub (I check them regularly)
- Email: mummyfox@foxmail.com

If this project inspires you or you'd like to collaborate, please reach out. I'm eager to join forces with those working toward AGI.

## Core Principles

### Memory Scanning Algorithm (Generation 2)

WalnutEverMem implements the **second generation** of the memory scanning algorithm:

**Generation 1 (File-Based)**:
- Storage: Markdown files
- Matching: Text keyword matching
- Indexing: Scan result records in files
- Retrieval: O(n) linear scan

**Generation 2 (Database-Based, Current)**:
- Storage: SQLite/PostgreSQL with vector support
- Matching: Vector embedding similarity (RAG)
- Indexing: Pointer data structure with metadata
- Retrieval: O(1) pointer jumps + vector search

**Key Insight**: Both generations share the **same core principles**, but Gen 2 optimizes the implementation:
- On-demand retrieval → Query-triggered
- Pairwise comparison → Vector similarity
- Scan records → Pointer structure
- Avoid repetition → Pointer-based optimization

### Key Mechanisms

1. **On-Demand Retrieval** (按需检索)
   - Only triggers when user queries (similar to "scan when concept mentioned")
   - No pre-computed indexes, avoiding index bloat
   - Query-driven, not prediction-driven

2. **Pairwise Similarity Comparison** (两两比对检索)
   - Query embedding compared with each memory record
   - Uses RAG-style vector similarity (cosine similarity)
   - Computes relevance score for each record sequentially

3. **Pointer-Based Optimization** (指针优化)
   - When a relevant memory is found, creates a pointer at the starting position
   - Future queries can jump directly via pointers (O(1) access)
   - Pointers form an emergent tree structure over time

4. **Avoiding Repetition** (避免重复劳动)
   - Pointers serve as cached paths to relevant memories
   - Access count tracking identifies frequently used paths
   - Similar queries benefit from previously created pointers

### Implementation Optimizations

Compared to file-based memory scanning:

| Aspect | File-Based Scanning | WalnutEverMem |
|--------|-------------------|---------------|
| **Storage** | Markdown files | SQLite/PostgreSQL with vector support |
| **Indexing** | Text matching | Vector embeddings (RAG) |
| **Speed** | Linear scan | Vector similarity + pointer jumps |
| **Intelligence** | Keyword matching | Semantic similarity |
| **Caching** | Scan result records | Pointer data structure |

**Why Database + Vectors?**
- **Faster retrieval**: Database indexes + vector similarity search
- **Smarter matching**: Semantic understanding vs. text matching
- **Scalable**: Handles large memory volumes efficiently
- **Structured pointers**: Explicit pointer records with metadata

## Integration with AI Systems

### WalnutEverMem as a Memory Query Foundation

**Key Concept**: WalnutEverMem is a **tool/foundation** for upper-layer AI systems - it provides high-speed memory storage and retrieval, but requires **active queries** from the AI application.

**Architecture Pattern**:

```
┌─────────────────────────────────────────┐
│         AI Application Layer             │
│  (Dialogue Manager, Agent, LLM App)     │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │  Query Strategy (Your Choice)    │   │
│  │  - On-demand query               │   │
│  │  - Every-response query          │   │
│  │  - Context-triggered query       │   │
│  └──────────────────────────────────┘   │
└─────────────┬───────────────────────────┘
              │ Active Query
              ▼
┌─────────────────────────────────────────┐
│      WalnutEverMem Foundation           │
│  (High-Speed Memory Query Engine)       │
│                                          │
│  - Stores all chat records sequentially │
│  - Provides vector-based retrieval      │
│  - Creates pointers for optimization    │
│  - Returns relevant memories            │
└─────────────────────────────────────────┘
```

### Query Strategies

#### 1. On-Demand Query (Recommended)

Query only when AI detects unknown concepts or needs context:

```python
# AI receives user message
user_input = "还记得我们说过的话语映射系统吗？"

# AI detects unknown concept →主动 query WalnutEverMem
results = await memory.recall(
    query="话语映射系统",
    session_id=user_session,
    max_results=5
)

# Inject retrieved memories into context
context = build_context(results)
response = await llm.generate(user_input, context)
```

**Advantages**:
- Efficient (only query when needed)
- Cost-effective (fewer LLM tokens)
- Fast response (no unnecessary queries)

#### 2. Every-Response Query

Query before every response to ensure full context:

```python
# Before generating each response
async def generate_response(user_input: str, session_id: str):
    # Always query recent context
    recent = await memory.get_context(session_id, limit=10)
    
    # Also query relevant memories
    relevant = await memory.recall(
        query=user_input,
        session_id=session_id,
        max_results=5
    )
    
    # Combine context
    full_context = build_context(recent, relevant)
    return await llm.generate(user_input, full_context)
```

**Advantages**:
- Never misses relevant context
- Consistent behavior
- Good for critical applications

**Trade-offs**:
- Higher cost (more queries)
- Slower response time

#### 3. Hybrid Strategy

Combine both approaches based on triggers:

```python
async def process_user_message(user_input: str, session_id: str):
    # Always get recent context (lightweight)
    context = await memory.get_context(session_id, limit=5)
    
    # Check if query needed (concept detection, confidence check, etc.)
    if needs_memory_query(user_input, context):
        relevant = await memory.recall(
            query=extract_query(user_input),
            session_id=session_id,
            max_results=5
        )
        context = merge_context(context, relevant)
    
    return await llm.generate(user_input, context)
```

### Implementation Example

```python
from walnut_ever_mem import MemoryService

class AIAssistant:
    def __init__(self):
        self.memory = MemoryService.from_config(config)
        self.llm = LLMClient()
    
    async def process_message(self, user_input: str, session_id: str):
        # Step 1: Get recent context (always)
        recent_context = await self.memory.get_context(
            session_id=session_id,
            limit=5
        )
        
        # Step 2: Detect if memory query needed
        concepts = self.extract_concepts(user_input)
        relevant_memories = []
        
        for concept in concepts:
            # Active query to WalnutEverMem
            results = await self.memory.recall(
                query=concept,
                session_id=session_id,
                max_results=3
            )
            relevant_memories.extend(results)
        
        # Step 3: Build enriched context
        full_context = self.build_context(
            recent_context,
            relevant_memories
        )
        
        # Step 4: Generate response with context
        response = await self.llm.generate(
            prompt=user_input,
            context=full_context
        )
        
        # Step 5: Store new memory
        await self.memory.remember(
            session_id=session_id,
            role="user",
            content=user_input
        )
        await self.memory.remember(
            session_id=session_id,
            role="assistant",
            content=response
        )
        
        return response
```

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
