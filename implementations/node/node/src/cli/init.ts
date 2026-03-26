#!/usr/bin/env node

import { Command } from 'commander';
import { createInterface } from 'readline';
import { createConfig, DatabaseConfig, EmbeddingConfig } from '../config';
import { DatabaseInitializer } from '../repository';

const rl = createInterface({
  input: process.stdin,
  output: process.stdout,
});

function prompt(question: string, defaultValue?: string): Promise<string> {
  return new Promise((resolve) => {
    const hint = defaultValue ? ` [${defaultValue}]` : '';
    rl.question(`${question}${hint}: `, (answer) => {
      resolve(answer || defaultValue || '');
    });
  });
}

function promptChoice(question: string, choices: string[], defaultIndex: number = 0): Promise<number> {
  return new Promise((resolve) => {
    console.log(`\n${question}`);
    choices.forEach((choice, i) => {
      const marker = i === defaultIndex ? '>' : ' ';
      console.log(`  ${marker} ${i + 1}. ${choice}`);
    });

    rl.question(`Select [1-${choices.length}] (default ${defaultIndex + 1}): `, (answer) => {
      const idx = parseInt(answer) - 1;
      if (isNaN(idx) || idx < 0 || idx >= choices.length) {
        resolve(defaultIndex);
      } else {
        resolve(idx);
      }
    });
  });
}

function promptYesNo(question: string, defaultValue: boolean = true): Promise<boolean> {
  return new Promise((resolve) => {
    const hint = defaultValue ? '[Y/n]' : '[y/N]';
    rl.question(`${question} ${hint}: `, (answer) => {
      const a = answer.toLowerCase().trim();
      if (a === '') resolve(defaultValue);
      else if (['y', 'yes', 'true', '1'].includes(a)) resolve(true);
      else resolve(false);
    });
  });
}

async function interactiveConfig() {
  console.log('\n' + '='.repeat(50));
  console.log('  WalnutEverMem Configuration Wizard');
  console.log('='.repeat(50) + '\n');

  console.log('[Database Configuration]');
  console.log('-'.repeat(30));

  const backendIdx = await promptChoice(
    'Select database backend:',
    ['SQLite (recommended, zero-config)', 'PostgreSQL (for production)'],
    0
  );
  const backend = backendIdx === 0 ? 'sqlite' : 'postgresql';

  const dbConfig: Partial<DatabaseConfig> = { backend };

  if (backend === 'sqlite') {
    dbConfig.sqlitePath = await prompt('SQLite database path', 'walnut_memory.db');
  } else {
    console.log('\nPostgreSQL Configuration:');
    dbConfig.host = await prompt('Host', 'localhost');
    dbConfig.port = parseInt(await prompt('Port', '5432'));
    dbConfig.database = await prompt('Database name', 'walnut_memory');
    dbConfig.user = await prompt('User', 'postgres');
    dbConfig.password = await prompt('Password', '');
  }

  console.log('\n[Embedding Configuration]');
  console.log('-'.repeat(30));

  const providerIdx = await promptChoice(
    'Select embedding provider:',
    ['OpenAI', 'Cohere', 'Local (sentence-transformers)', 'Custom'],
    0
  );
  const providers = ['openai', 'cohere', 'local', 'custom'] as const;

  const embedConfig: Partial<EmbeddingConfig> = {
    provider: providers[providerIdx]
  };

  if (embedConfig.provider === 'openai') {
    const modelIdx = await promptChoice(
      'Select OpenAI embedding model:',
      ['text-embedding-3-small (1536 dim)', 'text-embedding-3-large (3072 dim)'],
      0
    );
    embedConfig.dimension = modelIdx === 0 ? 1536 : 3072;
    embedConfig.modelName = modelIdx === 0 ? 'text-embedding-3-small' : 'text-embedding-3-large';
    
    const apiKey = await prompt('OpenAI API Key (leave empty to use env var)', '');
    if (apiKey) embedConfig.apiKey = apiKey;
  } else if (embedConfig.provider === 'cohere') {
    embedConfig.dimension = 1024;
    embedConfig.modelName = 'embed-v3';
    const apiKey = await prompt('Cohere API Key', '');
    if (apiKey) embedConfig.apiKey = apiKey;
  } else if (embedConfig.provider === 'local') {
    embedConfig.dimension = parseInt(await prompt('Embedding dimension', '384'));
    embedConfig.modelName = await prompt('Model name', 'all-MiniLM-L6-v2');
  } else {
    embedConfig.dimension = parseInt(await prompt('Embedding dimension', '1536'));
    embedConfig.modelName = await prompt('Model name', 'custom');
  }

  console.log('\n[Summary]');
  console.log('-'.repeat(30));
  console.log(`Database: ${backend}`);
  if (backend === 'sqlite') {
    console.log(`  Path: ${dbConfig.sqlitePath}`);
  } else {
    console.log(`  Host: ${dbConfig.host}:${dbConfig.port}`);
    console.log(`  Database: ${dbConfig.database}`);
  }
  console.log(`Embedding: ${embedConfig.provider}`);
  console.log(`  Model: ${embedConfig.modelName}`);
  console.log(`  Dimension: ${embedConfig.dimension}`);

  if (!await promptYesNo('\nProceed with this configuration?', true)) {
    console.log('Configuration cancelled.');
    process.exit(0);
  }

  return createConfig({
    db: dbConfig as DatabaseConfig,
    embedding: embedConfig as EmbeddingConfig,
  });
}

async function saveConfig(config: any, path: string = '.env') {
  const lines = [
    '# WalnutEverMem Configuration',
    '# Generated by walnut-init',
    '',
    '# Database Configuration',
    `WALNUT_DB__BACKEND=${config.db.backend}`,
  ];

  if (config.db.backend === 'sqlite') {
    lines.push(`WALNUT_DB__SQLITE_PATH=${config.db.sqlitePath}`);
  } else {
    lines.push(
      `WALNUT_DB__HOST=${config.db.host}`,
      `WALNUT_DB__PORT=${config.db.port}`,
      `WALNUT_DB__DATABASE=${config.db.database}`,
      `WALNUT_DB__USER=${config.db.user}`,
      `WALNUT_DB__PASSWORD=${config.db.password}`
    );
  }

  lines.push(
    '',
    '# Embedding Configuration',
    `WALNUT_EMBED__DIMENSION=${config.embedding.dimension}`,
    `WALNUT_EMBED__PROVIDER=${config.embedding.provider}`,
    `WALNUT_EMBED__MODEL_NAME=${config.embedding.modelName}`
  );

  if (config.embedding.apiKey) {
    lines.push(`WALNUT_EMBED__API_KEY=${config.embedding.apiKey}`);
  }

  lines.push(
    '',
    '# Retrieval Configuration',
    `WALNUT_RETRIEVE__SIMILARITY_THRESHOLD=${config.retrieval.similarityThreshold}`,
    `WALNUT_RETRIEVE__MAX_POINTERS_PER_NODE=${config.retrieval.maxPointersPerNode}`,
    '',
    '# Debug Mode',
    `WALNUT_DEBUG=${config.debug}`
  );

  await require('fs').promises.writeFile(path, lines.join('\n') + '\n');
  console.log(`\nConfiguration saved to: ${path}`);
}

async function main() {
  console.log('\nWelcome to WalnutEverMem!');
  console.log('This wizard will help you set up your infinite context memory.\n');

  const config = await interactiveConfig();

  if (await promptYesNo('\nSave configuration to .env file?', true)) {
    await saveConfig(config);
  }

  if (await promptYesNo('\nInitialize database now?', true)) {
    console.log('\nInitializing database...');
    const initializer = new DatabaseInitializer(config);
    await initializer.initialize();
    console.log('Database initialized successfully!');
  }

  console.log('\n' + '='.repeat(50));
  console.log('  Setup Complete!');
  console.log('='.repeat(50));
  console.log('\nQuick Start:');
  console.log('  import { createConfig, MemoryService, DatabaseInitializer } from "walnut-ever-mem";');
  console.log('  const config = createConfig();');
  console.log('  await new DatabaseInitializer(config).initialize();');
  console.log('  const memory = new MemoryService(repo, config);');
  console.log('  await memory.remember("session-1", "user", "Hello!");');
  console.log();

  rl.close();
}

main().catch(console.error);
