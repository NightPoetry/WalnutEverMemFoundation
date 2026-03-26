import { z } from 'zod';

export const DatabaseBackendSchema = z.enum(['sqlite', 'postgresql']);
export type DatabaseBackend = z.infer<typeof DatabaseBackendSchema>;

export const DatabaseConfigSchema = z.object({
  backend: DatabaseBackendSchema.default('sqlite'),
  sqlitePath: z.string().default('walnut_memory.db'),
  host: z.string().default('localhost'),
  port: z.number().int().positive().default(5432),
  database: z.string().default('walnut_memory'),
  user: z.string().default('postgres'),
  password: z.string().default(''),
});

export type DatabaseConfig = z.infer<typeof DatabaseConfigSchema>;

export const EmbeddingProviderSchema = z.enum(['openai', 'cohere', 'local', 'custom']);
export type EmbeddingProvider = z.infer<typeof EmbeddingProviderSchema>;

export const EmbeddingConfigSchema = z.object({
  dimension: z.number().int().min(64).max(4096).default(1536),
  provider: EmbeddingProviderSchema.default('openai'),
  modelName: z.string().default('text-embedding-3-small'),
  apiKey: z.string().optional(),
  apiBase: z.string().optional(),
});

export type EmbeddingConfig = z.infer<typeof EmbeddingConfigSchema>;

export const RetrievalConfigSchema = z.object({
  similarityThreshold: z.number().min(0).max(1).default(0.7),
  maxPointersPerNode: z.number().int().min(1).max(1000).default(100),
  pointerCleanupThreshold: z.number().int().positive().default(1000),
});

export type RetrievalConfig = z.infer<typeof RetrievalConfigSchema>;

export const WalnutConfigSchema = z.object({
  db: DatabaseConfigSchema.default({}),
  embedding: EmbeddingConfigSchema.default({}),
  retrieval: RetrievalConfigSchema.default({}),
  debug: z.boolean().default(false),
});

export type WalnutConfig = z.infer<typeof WalnutConfigSchema>;

export function createConfig(overrides?: Partial<WalnutConfig>): WalnutConfig {
  return WalnutConfigSchema.parse(overrides ?? {});
}

export function configFromEnv(): WalnutConfig {
  return createConfig({
    db: {
      backend: process.env.WALNUT_DB_BACKEND as DatabaseBackend || 'sqlite',
      sqlitePath: process.env.WALNUT_DB_SQLITE_PATH || 'walnut_memory.db',
      host: process.env.WALNUT_DB_HOST || 'localhost',
      port: parseInt(process.env.WALNUT_DB_PORT || '5432'),
      database: process.env.WALNUT_DB_DATABASE || 'walnut_memory',
      user: process.env.WALNUT_DB_USER || 'postgres',
      password: process.env.WALNUT_DB_PASSWORD || '',
    },
    embedding: {
      dimension: parseInt(process.env.WALNUT_EMBED_DIMENSION || '1536'),
      provider: (process.env.WALNUT_EMBED_PROVIDER as EmbeddingProvider) || 'openai',
      modelName: process.env.WALNUT_EMBED_MODEL_NAME || 'text-embedding-3-small',
      apiKey: process.env.WALNUT_EMBED_API_KEY,
      apiBase: process.env.WALNUT_EMBED_API_BASE,
    },
    retrieval: {
      similarityThreshold: parseFloat(process.env.WALNUT_RETRIEVE_SIMILARITY_THRESHOLD || '0.7'),
      maxPointersPerNode: parseInt(process.env.WALNUT_RETRIEVE_MAX_POINTERS_PER_NODE || '100'),
      pointerCleanupThreshold: parseInt(process.env.WALNUT_RETRIEVE_POINTER_CLEANUP_THRESHOLD || '1000'),
    },
    debug: process.env.WALNUT_DEBUG === 'true',
  });
}

export function getConnectionUrl(config: DatabaseConfig): string {
  if (config.backend === 'sqlite') {
    return `sqlite://${config.sqlitePath}`;
  }
  return `postgresql://${config.user}:${config.password}@${config.host}:${config.port}/${config.database}`;
}
