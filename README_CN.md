# WalnutEverMemFoundation

> ⚠️ **警告：本项目目前处于工程测试阶段。**
> 
> **请勿下载或使用，当前处于不可用状态。**
> 
> 本仓库正在积极开发中，待可用时会发布公告。

基于二元逻辑的 LLM 无限上下文记忆基础架构，作为 AI 记忆操作系统使用，需要配合 Skill 模块实现具体功能。

## 项目结构

本仓库包含同一规范的多个实现版本：

```
Core/
├── implementations/
│   ├── python/          # Python 实现
│   │   ├── src/
│   │   │   └── walnut_ever_mem/
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── nodejs/          # Node.js/TypeScript 实现
│       ├── walnut_ever_mem/
│       │   └── src/
│       ├── package.json
│       └── tsconfig.json
├── SPEC.md              # 系统规范（唯一真实来源）
├── README.md            # 本文件
└── README_CN.md         # 中文版
```

## 实现版本

### Python 版本

- **位置**: `implementations/python/`
- **包名**: `walnut-ever-mem`
- **要求**: Python 3.10+
- **依赖**: pydantic, aiosqlite, asyncpg, numpy, fastapi

**安装:**
```bash
cd implementations/python
pip install -e .
```

**快速开始:**
```bash
# 交互式 CLI
walnut-init

# Web API
walnut-server

# 库引入
from walnut_ever_mem import WalnutConfig, MemoryService
```

### Node.js/TypeScript 版本

- **位置**: `implementations/nodejs/`
- **包名**: `walnut-ever-mem`
- **要求**: Node.js 18+
- **依赖**: zod, better-sqlite3, pg, express, commander

**安装:**
```bash
cd implementations/nodejs
npm install
npm run build
```

**快速开始:**
```bash
# 交互式 CLI
npx walnut-init

# Web API
npx walnut-server

# 库引入
import { createConfig, MemoryService } from 'walnut-ever-mem';
```

## 规范文档

两个实现版本都遵循 `SPEC.md` 中定义的同一系统规范，确保：

- 完全相同的 API 接口
- 相同的数据模型
- 一致的行为
- 跨语言兼容性

## 选择哪个实现？

**选择 Python 如果：**
- 你在 AI/ML 生态系统中工作
- 需要丰富的数据科学库
- 喜欢动态类型

**选择 Node.js 如果：**
- 你在构建 Web 应用
- 需要高并发
- 喜欢 TypeScript 的类型安全

## 开发

### 添加新实现

1. 仔细阅读 `SPEC.md`
2. 在 `implementations/` 下创建新目录
3. 遵循相同的 API 结构
4. 添加与 Python/Node.js 测试模式匹配的测试

### 更新所有实现

修改规范时：

1. 首先更新 `SPEC.md`
2. 更新所有实现以匹配规范
3. 确保所有实现的测试都通过

## 许可证

Apache License 2.0
