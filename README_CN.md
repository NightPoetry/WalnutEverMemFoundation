# WalnutEverMemFoundation

> ⚠️ **警告：本项目目前处于工程测试阶段。**
> 
> **请勿下载或使用，当前处于不可用状态。**
> 
> 本仓库正在积极开发中，待可用时会发布公告。

基于二元逻辑的 LLM 无限上下文记忆基础架构，作为 AI 记忆操作系统使用，需要配合 Skill 模块实现具体功能。

## 我为什么开源这个项目

我发现很多人可能做了很厉害的记忆机制。但是我需要的是世界快点实现 AGI，快一点，再快一点。我希望有生之年能见证全人类的飞跃。

我不知道我的这个思路有没有人做过，也不知道效果如何（因为我没有这么大体量的数据做测试）。但是我选择开源，将我思考了几年的最终结果进行开源，希望能给别人以启发。

如果有幸启发了你，我希望可以联系我，让我参与到你的项目中。我想要为 AGI 贡献一份力量，同时我需要更多的资源来验证我的假设和猜想。

有些人为了名誉和金钱而学习和研究 AGI，而我为了研究 AGI 而需要一定的名誉和金钱。

**联系方式**：
- 在 GitHub 提交 Issue（我会定期查看）
- 邮箱：mummyfox@foxmail.com

如果这个项目启发了你，或者你想合作，请联系我。我渴望与那些致力于 AGI 的人携手共进。

## 核心原理

### 记忆扫描算法（第二代）

WalnutEverMem 实现了**第二代**记忆扫描算法：

**第一代（基于文件）**：
- 存储：Markdown 文件
- 匹配：文本关键词匹配
- 索引：文件中的扫描记录
- 检索：O(n) 线性扫描

**第二代（基于数据库，当前）**：
- 存储：SQLite/PostgreSQL（支持向量）
- 匹配：向量嵌入相似度（RAG）
- 索引：指针数据结构（带元数据）
- 检索：O(1) 指针跳转 + 向量搜索

**核心洞察**：两代算法遵循**相同的核心原则**，第二代优化了实现方式：
- 按需检索 → 查询触发
- 两两比对 → 向量相似度
- 扫描记录 → 指针结构
- 避免重复 → 指针优化

### 关键机制

1. **按需检索** (On-Demand Retrieval)
   - 仅用户查询时触发（类似"提到概念时才扫描"）
   - 无预计算索引，避免索引膨胀
   - 查询驱动，而非预测驱动

2. **两两比对检索** (Pairwise Similarity Comparison)
   - 查询向量与每条记忆记录逐一比对
   - 使用 RAG 风格的向量相似度（余弦相似度）
   - 逐条计算相关性评分

3. **指针优化** (Pointer-Based Optimization)
   - 找到相关记忆时，在起始位置创建指针直达目标
   - 未来查询可通过指针直接跳转（O(1) 访问）
   - 随时间形成涌现树结构

4. **避免重复劳动** (Avoiding Repetition)
   - 指针作为缓存的检索路径
   - 访问计数追踪常用路径
   - 相似查询受益于已创建的指针

### 实现优化

与基于文件的记忆扫描相比：

| 方面 | 文件扫描 | WalnutEverMem |
|------|---------|---------------|
| **存储** | Markdown 文件 | SQLite/PostgreSQL + 向量支持 |
| **索引** | 文本匹配 | 向量嵌入（RAG） |
| **速度** | 线性扫描 | 向量相似度 + 指针跳转 |
| **智能** | 关键词匹配 | 语义理解 |
| **缓存** | 扫描结果记录 | 指针数据结构 |

**为什么选择数据库 + 向量？**
- **更快检索**：数据库索引 + 向量相似度搜索
- **更智能匹配**：语义理解 vs 文本匹配
- **可扩展**：高效处理大量记忆
- **结构化指针**：带元数据的显式指针记录

## 与 AI 系统集成

### WalnutEverMem 作为记忆查询基座

**核心概念**：WalnutEverMem 是上层 AI 系统的**工具/基础架构**——它提供高速记忆存储和检索，但需要 AI 应用**主动查询**。

**架构模式**：

```
┌─────────────────────────────────────────┐
│            AI 应用层                      │
│  (对话管理器、Agent、LLM 应用)            │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │  查询策略（你的选择）              │   │
│  │  - 按需查询                      │   │
│  │  - 每次回复查询                  │   │
│  │  - 上下文触发查询                │   │
│  └──────────────────────────────────┘   │
└─────────────┬───────────────────────────┘
              │ 主动查询
              ▼
┌─────────────────────────────────────────┐
│      WalnutEverMem 基础架构              │
│  (高速记忆查询引擎)                      │
│                                          │
│  - 顺序存储所有聊天记录                  │
│  - 提供基于向量的检索                    │
│  - 创建指针进行优化                      │
│  - 返回相关记忆                          │
└─────────────────────────────────────────┘
```

### 查询策略

#### 1. 按需查询（推荐）

仅当 AI 检测到未知概念或需要上下文时查询：

```python
# AI 接收用户消息
user_input = "还记得我们说过的话语映射系统吗？"

# AI 检测到未知概念 → 主动查询 WalnutEverMem
results = await memory.recall(
    query="话语映射系统",
    session_id=user_session,
    max_results=5
)

# 将检索到的记忆注入上下文
context = build_context(results)
response = await llm.generate(user_input, context)
```

**优势**：
- 高效（只在需要时查询）
- 成本效益（更少的 LLM token 消耗）
- 快速响应（无不必要的查询）

#### 2. 每次回复查询

每次回复前都查询以确保完整上下文：

```python
# 生成每个回复前
async def generate_response(user_input: str, session_id: str):
    # 总是查询最近上下文
    recent = await memory.get_context(session_id, limit=10)
    
    # 同时查询相关记忆
    relevant = await memory.recall(
        query=user_input,
        session_id=session_id,
        max_results=5
    )
    
    # 组合上下文
    full_context = build_context(recent, relevant)
    return await llm.generate(user_input, full_context)
```

**优势**：
- 从不错过相关上下文
- 行为一致
- 适合关键应用

**权衡**：
- 成本更高（更多查询）
- 响应时间更长

#### 3. 混合策略

基于触发器结合两种方法：

```python
async def process_user_message(user_input: str, session_id: str):
    # 总是获取最近上下文（轻量级）
    context = await memory.get_context(session_id, limit=5)
    
    # 检查是否需要查询（概念检测、置信度检查等）
    if needs_memory_query(user_input, context):
        relevant = await memory.recall(
            query=extract_query(user_input),
            session_id=session_id,
            max_results=5
        )
        context = merge_context(context, relevant)
    
    return await llm.generate(user_input, context)
```

### 实现示例

```python
from walnut_ever_mem import MemoryService

class AIAssistant:
    def __init__(self):
        self.memory = MemoryService.from_config(config)
        self.llm = LLMClient()
    
    async def process_message(self, user_input: str, session_id: str):
        # 步骤 1：获取最近上下文（总是）
        recent_context = await self.memory.get_context(
            session_id=session_id,
            limit=5
        )
        
        # 步骤 2：检测是否需要记忆查询
        concepts = self.extract_concepts(user_input)
        relevant_memories = []
        
        for concept in concepts:
            # 主动查询 WalnutEverMem
            results = await self.memory.recall(
                query=concept,
                session_id=session_id,
                max_results=3
            )
            relevant_memories.extend(results)
        
        # 步骤 3：构建丰富的上下文
        full_context = self.build_context(
            recent_context,
            relevant_memories
        )
        
        # 步骤 4：使用上下文生成回复
        response = await self.llm.generate(
            prompt=user_input,
            context=full_context
        )
        
        # 步骤 5：存储新记忆
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
