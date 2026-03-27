import Database from 'better-sqlite3';
import { Pool } from 'pg';
import { WalnutConfig, DatabaseConfig } from '../config';
import { ChatRecord, MessageRole, Pointer, PointerType } from '../models';

type SQLiteConnection = Database.Database;
type PostgreSQLConnection = Pool;

export class DatabaseInitializer {
  constructor(private config: WalnutConfig) {}

  async initialize(): Promise<void> {
    if (this.config.db.backend === 'sqlite') {
      await this.initializeSQLite();
    } else {
      await this.initializePostgreSQL();
    }
  }

  private async initializeSQLite(): Promise<void> {
    const db = new Database(this.config.db.sqlitePath);
    
    db.exec(`
      CREATE TABLE IF NOT EXISTS chat_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        embedding BLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        metadata TEXT
      );
      
      CREATE TABLE IF NOT EXISTS pointers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id INTEGER NOT NULL REFERENCES chat_records(id) ON DELETE CASCADE,
        target_id INTEGER NOT NULL REFERENCES chat_records(id) ON DELETE CASCADE,
        embedding BLOB NOT NULL,
        pointer_type TEXT DEFAULT 'embedding',
        summary TEXT,
        relevance_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        access_count INTEGER DEFAULT 0,
        last_accessed TIMESTAMP
      );
      
      CREATE INDEX IF NOT EXISTS idx_chat_records_session ON chat_records(session_id);
      CREATE INDEX IF NOT EXISTS idx_chat_records_created ON chat_records(created_at DESC);
      CREATE INDEX IF NOT EXISTS idx_pointers_source ON pointers(source_id);
      CREATE INDEX IF NOT EXISTS idx_pointers_target ON pointers(target_id);
      
      CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        dimension INTEGER NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);

    const stmt = db.prepare('INSERT OR IGNORE INTO schema_version (version, dimension) VALUES (1, ?)');
    stmt.run(this.config.embedding.dimension);
    
    db.close();
  }

  private async initializePostgreSQL(): Promise<void> {
    const pool = new Pool({
      host: this.config.db.host,
      port: this.config.db.port,
      database: this.config.db.database,
      user: this.config.db.user,
      password: this.config.db.password,
    });

    await pool.query('CREATE EXTENSION IF NOT EXISTS vector');
    
    await pool.query(`
      CREATE TABLE IF NOT EXISTS chat_records (
        id BIGSERIAL PRIMARY KEY,
        session_id VARCHAR(64) NOT NULL,
        role VARCHAR(16) NOT NULL,
        content TEXT NOT NULL,
        embedding VECTOR(${this.config.embedding.dimension}),
        created_at TIMESTAMP DEFAULT NOW(),
        metadata JSONB
      );
      
      CREATE TABLE IF NOT EXISTS pointers (
        id BIGSERIAL PRIMARY KEY,
        source_id BIGINT NOT NULL REFERENCES chat_records(id) ON DELETE CASCADE,
        target_id BIGINT NOT NULL REFERENCES chat_records(id) ON DELETE CASCADE,
        embedding VECTOR(${this.config.embedding.dimension}) NOT NULL,
        pointer_type VARCHAR(32) DEFAULT 'embedding',
        summary TEXT,
        relevance_score FLOAT,
        created_at TIMESTAMP DEFAULT NOW(),
        access_count INT DEFAULT 0,
        last_accessed TIMESTAMP
      );
      
      CREATE INDEX IF NOT EXISTS idx_chat_records_session ON chat_records(session_id);
      CREATE INDEX IF NOT EXISTS idx_chat_records_created ON chat_records(created_at DESC);
      CREATE INDEX IF NOT EXISTS idx_pointers_source ON pointers(source_id);
      CREATE INDEX IF NOT EXISTS idx_pointers_target ON pointers(target_id);
      
      CREATE TABLE IF NOT EXISTS schema_version (
        version INT PRIMARY KEY,
        dimension INT NOT NULL,
        applied_at TIMESTAMP DEFAULT NOW()
      );
    `);

    await pool.query(
      'INSERT INTO schema_version (version, dimension) VALUES (1, $1) ON CONFLICT DO NOTHING',
      [this.config.embedding.dimension]
    );

    await pool.end();
  }
}

export class ChatRecordRepository {
  constructor(
    private conn: SQLiteConnection | PostgreSQLConnection,
    private backend: 'sqlite' | 'postgresql'
  ) {}

  async create(record: ChatRecord): Promise<ChatRecord> {
    if (this.backend === 'sqlite') {
      return this.createSQLite(record);
    }
    return this.createPostgreSQL(record);
  }

  private async createSQLite(record: ChatRecord): Promise<ChatRecord> {
    const db = this.conn as SQLiteConnection;
    const stmt = db.prepare(`
      INSERT INTO chat_records (session_id, role, content, embedding, created_at, metadata)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    
    const embeddingBuffer = record.embedding 
      ? Buffer.from(new Float32Array(record.embedding).buffer)
      : null;
    
    const result = stmt.run(
      record.sessionId,
      record.role,
      record.content,
      embeddingBuffer,
      record.createdAt.toISOString(),
      JSON.stringify(record.metadata)
    );
    
    return { ...record, id: result.lastInsertRowid as number };
  }

  private async createPostgreSQL(record: ChatRecord): Promise<ChatRecord> {
    const pool = this.conn as PostgreSQLConnection;
    const result = await pool.query(
      `INSERT INTO chat_records (session_id, role, content, embedding, created_at, metadata)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING *`,
      [
        record.sessionId,
        record.role,
        record.content,
        record.embedding,
        record.createdAt,
        record.metadata
      ]
    );
    
    return this.rowToRecord(result.rows[0]);
  }

  async getById(id: number): Promise<ChatRecord | null> {
    if (this.backend === 'sqlite') {
      const db = this.conn as SQLiteConnection;
      const row = db.prepare('SELECT * FROM chat_records WHERE id = ?').get(id) as any;
      return row ? this.rowToRecordSQLite(row) : null;
    }
    
    const pool = this.conn as PostgreSQLConnection;
    const result = await pool.query('SELECT * FROM chat_records WHERE id = $1', [id]);
    return result.rows[0] ? this.rowToRecord(result.rows[0]) : null;
  }

  async getBySession(sessionId: string, limit: number = 100, beforeId?: number): Promise<ChatRecord[]> {
    if (this.backend === 'sqlite') {
      const db = this.conn as SQLiteConnection;
      let query = 'SELECT * FROM chat_records WHERE session_id = ?';
      const params: any[] = [sessionId];
      
      if (beforeId) {
        query += ' AND id < ?';
        params.push(beforeId);
      }
      
      query += ' ORDER BY created_at DESC LIMIT ?';
      params.push(limit);
      
      const rows = db.prepare(query).all(...params) as any[];
      return rows.map(r => this.rowToRecordSQLite(r));
    }
    
    const pool = this.conn as PostgreSQLConnection;
    let query = 'SELECT * FROM chat_records WHERE session_id = $1';
    const params: any[] = [sessionId];
    let paramIndex = 2;
    
    if (beforeId) {
      query += ` AND id < $${paramIndex++}`;
      params.push(beforeId);
    }
    
    query += ` ORDER BY created_at DESC LIMIT $${paramIndex}`;
    params.push(limit);
    
    const result = await pool.query(query, params);
    return result.rows.map(r => this.rowToRecord(r));
  }

  async getLatest(sessionId: string): Promise<ChatRecord | null> {
    const records = await this.getBySession(sessionId, 1);
    return records[0] || null;
  }

  private rowToRecordSQLite(row: any): ChatRecord {
    const embedding = row.embedding 
      ? Array.from(new Float32Array(row.embedding.buffer))
      : undefined;
    
    return {
      id: row.id,
      sessionId: row.session_id,
      role: row.role as MessageRole,
      content: row.content,
      embedding,
      createdAt: new Date(row.created_at),
      metadata: row.metadata ? JSON.parse(row.metadata) : {},
    };
  }

  private rowToRecord(row: any): ChatRecord {
    return {
      id: row.id,
      sessionId: row.session_id,
      role: row.role as MessageRole,
      content: row.content,
      embedding: row.embedding,
      createdAt: row.created_at,
      metadata: row.metadata || {},
    };
  }
}

export class PointerRepository {
  constructor(
    private conn: SQLiteConnection | PostgreSQLConnection,
    private backend: 'sqlite' | 'postgresql'
  ) {}

  async create(pointer: Pointer): Promise<Pointer> {
    if (this.backend === 'sqlite') {
      return this.createSQLite(pointer);
    }
    return this.createPostgreSQL(pointer);
  }

  private async createSQLite(pointer: Pointer): Promise<Pointer> {
    const db = this.conn as SQLiteConnection;
    const embeddingBuffer = Buffer.from(new Float32Array(pointer.embedding).buffer);
    
    const stmt = db.prepare(`
      INSERT INTO pointers (source_id, target_id, embedding, pointer_type, summary, relevance_score, created_at, access_count, last_accessed)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    
    const result = stmt.run(
      pointer.sourceId,
      pointer.targetId,
      embeddingBuffer,
      pointer.pointerType,
      pointer.summary,
      pointer.relevanceScore,
      pointer.createdAt.toISOString(),
      pointer.accessCount,
      pointer.lastAccessed?.toISOString()
    );
    
    return { ...pointer, id: result.lastInsertRowid as number };
  }

  private async createPostgreSQL(pointer: Pointer): Promise<Pointer> {
    const pool = this.conn as PostgreSQLConnection;
    const result = await pool.query(
      `INSERT INTO pointers (source_id, target_id, embedding, pointer_type, summary, relevance_score, created_at, access_count, last_accessed)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
       RETURNING *`,
      [
        pointer.sourceId,
        pointer.targetId,
        pointer.embedding,
        pointer.pointerType,
        pointer.summary,
        pointer.relevanceScore,
        pointer.createdAt,
        pointer.accessCount,
        pointer.lastAccessed
      ]
    );
    
    return this.rowToPointer(result.rows[0]);
  }

  async getPointersAtSource(sourceId: number): Promise<Pointer[]> {
    if (this.backend === 'sqlite') {
      const db = this.conn as SQLiteConnection;
      const rows = db.prepare('SELECT * FROM pointers WHERE source_id = ?').all(sourceId) as any[];
      return rows.map(r => this.rowToPointerSQLite(r));
    }
    
    const pool = this.conn as PostgreSQLConnection;
    const result = await pool.query('SELECT * FROM pointers WHERE source_id = $1', [sourceId]);
    return result.rows.map(r => this.rowToPointer(r));
  }

  async incrementAccessCount(pointerId: number): Promise<void> {
    const now = new Date();
    
    if (this.backend === 'sqlite') {
      const db = this.conn as SQLiteConnection;
      db.prepare('UPDATE pointers SET access_count = access_count + 1, last_accessed = ? WHERE id = ?')
        .run(now.toISOString(), pointerId);
    } else {
      const pool = this.conn as PostgreSQLConnection;
      await pool.query(
        'UPDATE pointers SET access_count = access_count + 1, last_accessed = $1 WHERE id = $2',
        [now, pointerId]
      );
    }
  }

  private rowToPointerSQLite(row: any): Pointer {
    const embedding = row.embedding 
      ? Array.from(new Float32Array(row.embedding.buffer))
      : [];
    
    return {
      id: row.id,
      sourceId: row.source_id,
      targetId: row.target_id,
      embedding,
      pointerType: row.pointer_type as PointerType,
      summary: row.summary,
      relevanceScore: row.relevance_score,
      createdAt: new Date(row.created_at),
      accessCount: row.access_count || 0,
      lastAccessed: row.last_accessed ? new Date(row.last_accessed) : undefined,
    };
  }

  private rowToPointer(row: any): Pointer {
    return {
      id: row.id,
      sourceId: row.source_id,
      targetId: row.target_id,
      embedding: row.embedding,
      pointerType: row.pointer_type as PointerType,
      summary: row.summary,
      relevanceScore: row.relevance_score,
      createdAt: row.created_at,
      accessCount: row.access_count || 0,
      lastAccessed: row.last_accessed,
    };
  }
}

export class MemoryRepository {
  public records: ChatRecordRepository;
  public pointers: PointerRepository;
  
  constructor(
    private conn: SQLiteConnection | PostgreSQLConnection,
    private config: WalnutConfig
  ) {
    this.records = new ChatRecordRepository(conn, config.db.backend);
    this.pointers = new PointerRepository(conn, config.db.backend);
  }

  async appendRecord(
    sessionId: string,
    role: string,
    content: string,
    embedding?: number[],
    metadata?: Record<string, unknown>
  ): Promise<ChatRecord> {
    return this.records.create({
      sessionId,
      role: role as MessageRole,
      content,
      embedding,
      createdAt: new Date(),
      metadata: metadata || {},
    });
  }

  async getSessionContext(
    sessionId: string,
    beforeId?: number,
    limit: number = 50
  ): Promise<ChatRecord[]> {
    return this.records.getBySession(sessionId, limit, beforeId);
  }
}
