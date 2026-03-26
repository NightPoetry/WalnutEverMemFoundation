#!/usr/bin/env node

import express from 'express';
import cors from 'cors';
import { createConfig, DatabaseInitializer, MemoryRepository, MemoryService } from '../index';
import { ChatRecord, Pointer } from '../models';
import Database from 'better-sqlite3';
import { Pool } from 'pg';

const app = express();
app.use(cors());
app.use(express.json());

let config: any = null;
let initialized = false;

interface ConfigRequest {
  dbBackend: string;
  sqlitePath: string;
  dbHost: string;
  dbPort: number;
  dbDatabase: string;
  dbUser: string;
  dbPassword: string;
  embeddingDimension: number;
  embeddingProvider: string;
  embeddingModelName: string;
  embeddingApiKey?: string;
  similarityThreshold: number;
}

interface InitRequest {
  config: ConfigRequest;
  dropExisting: boolean;
}

interface RememberRequest {
  sessionId: string;
  role: string;
  content: string;
  embedding?: number[];
  metadata?: Record<string, unknown>;
}

interface RecallRequest {
  sessionId: string;
  query: string;
  queryEmbedding?: number[];
  maxResults?: number;
  minSimilarity?: number;
}

app.get('/', (req, res) => {
  res.json({
    name: 'WalnutEverMem',
    version: '0.1.0',
    status: initialized ? 'initialized' : 'not_initialized',
  });
});

app.get('/status', async (req, res) => {
  if (!initialized) {
    return res.json({
      status: 'not_initialized',
      backend: 'none',
      tablesExist: false,
      dimensionMatch: null,
      recordedDimension: null,
    });
  }

  try {
    res.json({
      status: 'initialized',
      backend: config.db.backend,
      tablesExist: true,
      dimensionMatch: true,
      recordedDimension: config.embedding.dimension,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/init', async (req, res) => {
  try {
    const { config: cfg, dropExisting }: InitRequest = req.body;

    const newConfig = createConfig({
      db: {
        backend: cfg.dbBackend as any,
        sqlitePath: cfg.sqlitePath,
        host: cfg.dbHost,
        port: cfg.dbPort,
        database: cfg.dbDatabase,
        user: cfg.dbUser,
        password: cfg.dbPassword,
      },
      embedding: {
        dimension: cfg.embeddingDimension,
        provider: cfg.embeddingProvider as any,
        modelName: cfg.embeddingModelName,
        apiKey: cfg.embeddingApiKey,
      },
    });

    const initializer = new DatabaseInitializer(newConfig);

    if (dropExisting) {
      console.log('Dropping existing schema...');
    }

    await initializer.initialize();
    config = newConfig;
    initialized = true;

    res.json({
      status: 'initialized',
      backend: newConfig.db.backend,
      tablesExist: true,
      dimensionMatch: true,
      recordedDimension: newConfig.embedding.dimension,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/config', (req, res) => {
  if (!initialized) {
    return res.status(503).json({ error: 'Database not initialized' });
  }

  res.json({
    dbBackend: config.db.backend,
    dbPathOrHost: config.db.backend === 'sqlite' ? config.db.sqlitePath : config.db.host,
    embeddingDimension: config.embedding.dimension,
    embeddingProvider: config.embedding.provider,
    embeddingModelName: config.embedding.modelName,
  });
});

app.post('/remember', async (req, res) => {
  if (!initialized) {
    return res.status(503).json({ error: 'Database not initialized' });
  }

  try {
    const { sessionId, role, content, embedding, metadata }: RememberRequest = req.body;

    let conn: any;
    if (config.db.backend === 'sqlite') {
      conn = new Database(config.db.sqlitePath);
    } else {
      conn = new Pool({
        host: config.db.host,
        port: config.db.port,
        database: config.db.database,
        user: config.db.user,
        password: config.db.password,
      });
    }

    const repo = new MemoryRepository(conn, config);
    const record = await repo.appendRecord(sessionId, role, content, embedding, metadata);

    if (config.db.backend === 'sqlite') {
      conn.close();
    } else {
      await conn.end();
    }

    res.json({
      id: record.id,
      sessionId: record.sessionId,
      role: record.role,
      content: record.content,
      embedding: record.embedding,
      createdAt: record.createdAt.toISOString(),
      metadata: record.metadata,
    });
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/recall', async (req, res) => {
  if (!initialized) {
    return res.status(503).json({ error: 'Database not initialized' });
  }

  try {
    const { sessionId, query, queryEmbedding, maxResults = 10, minSimilarity }: RecallRequest = req.body;

    let conn: any;
    if (config.db.backend === 'sqlite') {
      conn = new Database(config.db.sqlitePath);
    } else {
      conn = new Pool({
        host: config.db.host,
        port: config.db.port,
        database: config.db.database,
        user: config.db.user,
        password: config.db.password,
      });
    }

    const repo = new MemoryRepository(conn, config);
    const service = new MemoryService(repo, config);
    const results = await service.recall(query, sessionId, maxResults);

    if (config.db.backend === 'sqlite') {
      conn.close();
    } else {
      await conn.end();
    }

    res.json(results.map(r => ({
      record: {
        id: r.record.id,
        sessionId: r.record.sessionId,
        role: r.record.role,
        content: r.record.content,
        embedding: r.record.embedding,
        createdAt: r.record.createdAt.toISOString(),
        metadata: r.record.metadata,
      },
      score: r.score,
      viaPointer: r.viaPointer,
      pointerSourceId: r.pointerSourceId,
    })));
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/sessions/:sessionId/context', async (req, res) => {
  if (!initialized) {
    return res.status(503).json({ error: 'Database not initialized' });
  }

  try {
    const { sessionId } = req.params;
    const limit = parseInt(req.query.limit as string) || 50;

    let conn: any;
    if (config.db.backend === 'sqlite') {
      conn = new Database(config.db.sqlitePath);
    } else {
      conn = new Pool({
        host: config.db.host,
        port: config.db.port,
        database: config.db.database,
        user: config.db.user,
        password: config.db.password,
      });
    }

    const repo = new MemoryRepository(conn, config);
    const records = await repo.getSessionContext(sessionId, undefined, limit);

    if (config.db.backend === 'sqlite') {
      conn.close();
    } else {
      await conn.end();
    }

    res.json(records.map(r => ({
      id: r.id,
      sessionId: r.sessionId,
      role: r.role,
      content: r.content,
      embedding: r.embedding,
      createdAt: r.createdAt.toISOString(),
      metadata: r.metadata,
    })));
  } catch (error: any) {
    res.status(500).json({ error: error.message });
  }
});

function runServer(port: number = 8000) {
  app.listen(port, '0.0.0.0', () => {
    console.log(`WalnutEverMem API server running at http://localhost:${port}`);
  });
}

if (require.main === module) {
  const port = parseInt(process.argv[2]) || 8000;
  runServer(port);
}

export { app, runServer };
