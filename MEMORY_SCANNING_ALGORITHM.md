# 记忆扫描算法实现说明

**版本**: 2.0  
**创建时间**: 2026-04-01  
**算法版本**: 第二代（v2）  
**实现**: WalnutEverMem Foundation

---

## 一、算法演进

### 1.1 第一代：基于文件的记忆扫描算法

**核心思想**：按需扫描 + 客观索引

**实现方式**：
- 存储：Markdown 文件（`memory/YYYY-MM-DD.md`）
- 匹配：文本关键词匹配
- 索引：扫描结果记录在文件中
- 检索：线性扫描历史文件

**历史地位**：
- 验证了"按需检索"和"两两比对"的核心思路
- 证明了避免预构建索引的可行性
- 为第二代算法奠定了理论基础

**局限性**：
- 性能：O(n) 线性扫描，数据量大时慢
- 智能：表面文本匹配，缺乏语义理解
- 扩展：文件格式难以支持大规模应用

### 1.2 第二代：基于数据库的记忆扫描算法（当前）

**核心思想**：继承第一代的思路，优化实现方式

**实现方式**：
- 存储：SQLite/PostgreSQL（支持向量）
- 匹配：向量嵌入相似度（RAG 技术）
- 索引：指针数据结构（带元数据）
- 检索：O(1) 指针跳转 + 向量搜索

**关键改进**：
- 性能提升：从 O(n) 到 O(1) 的跨越
- 智能提升：从文本匹配到语义理解
- 结构化提升：从文件记录到数据库指针

**本质传承**：
> **核心思路与第一代完全一致**，只是实现载体从文件升级为数据库：
> - 按需检索 → 查询时触发
> - 两两比对 → 向量相似度计算
> - 扫描记录 → 指针数据结构
> - 避免重复 → 指针跳转优化

---

## 二、算法原理（第二代）

### 1.1 核心思想

WalnutEverMem 实现的记忆扫描算法基于以下核心原则：

> **如无必要，勿建索引** - 按需检索，而非预先构建

**关键机制**：

1. **按需检索** (On-Demand Retrieval)
   - 用户查询时才触发检索
   - 不预先构建大量索引
   - 避免索引膨胀和维护成本

2. **两两比对** (Pairwise Comparison)
   - 查询向量与每条记忆记录逐一比对
   - 计算余弦相似度作为相关性评分
   - 基于 RAG 的语义理解，而非表面文本匹配

3. **指针优化** (Pointer Optimization)
   - 找到相关记忆时，创建指针从起点直达目标
   - 后续相似查询可直接跳转（O(1) 访问）
   - 随时间形成高效的树状检索路径

4. **避免重复** (Avoiding Repetition)
   - 指针作为缓存的检索路径
   - 访问计数追踪常用路径
   - 相似查询受益于已创建的指针

### 1.2 算法流程

```
┌─────────────────────────────────────────────────────────┐
│ 用户提交查询 (带上下文)                                   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 1. 提取查询向量 (语义表示)                                 │
│    query_embedding = embed(query + context)             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. 从最新记录开始，向后扫描                                │
│    current_record = get_latest(session_id)              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
         ┌───────────────┐
         │ 扫描循环开始   │
         └───────┬───────┘
                 │
                 ▼
    ┌────────────────────────┐
    │ a. 两两比对             │
    │    similarity =        │
    │    cosine_similarity(  │
    │      query_embedding,  │
    │      record_embedding  │
    │    )                   │
    └────────┬───────────────┘
             │
             ▼
    ┌────────────────┐
    │ b. 相似度>=阈值？│
    └────┬───────────┘
         │
    ┌────┴────┐
    │  是     │  否
    ▼         │
┌─────────┐   │
│ 添加到  │   │
│ 结果集  │   │
│         │   │
│ 创建指  │   │
│ 针 (如  │   │
│ 果不是  │   │
│ 起点)   │   │
└────┬────┘   │
     │        │
     └────────┘
              │
              ▼
    ┌────────────────────────┐
    │ c. 检查当前位置的指针   │
    │    for pointer in      │
    │      pointers_at_current│
    └────────┬───────────────┘
             │
             ▼
    ┌────────────────┐
    │ d. 指针匹配？   │
    └────┬───────────┘
         │
    ┌────┴────┐
    │  是     │  否
    ▼         │
┌─────────┐   │
│ 跳转到  │   │
│ 目标    │   │
│ (O(1))  │   │
└────┬────┘   │
     │        │
     └────────┘
              │
              ▼
    ┌────────────────────────┐
    │ e. 移动到前一条记录     │
    │    current_id =        │
    │    get_previous(current)│
    └────────┬───────────────┘
             │
             ▼
         ┌───┴───┐
         │还有记 │
         │录？   │
         └───┬───┘
             │
      ┌──────┴──────┐
      │  是         │  否
      ▼             │
  继续循环          │
                    │
                    ▼
         ┌──────────────────┐
         │ 3. 按相似度排序  │
         │    返回 top-k    │
         └──────────────────┘
```

### 1.3 伪代码

```python
async def retrieve(query, session_id, query_embedding, max_results=10, threshold=0.7):
    results = []
    starting_record = await get_latest(session_id)
    current_id = starting_record.id
    visited = set()
    
    while current_id and len(results) < max_results:
        if current_id in visited:
            break  # 防止循环
        visited.add(current_id)
        
        record = await get_by_id(current_id)
        
        # 两两比对：查询向量 ↔ 记录向量
        similarity = cosine_similarity(query_embedding, record.embedding)
        
        if similarity >= threshold:
            results.append(SearchResult(record, similarity))
            
            # 创建指针（记忆优化）
            if starting_record.id != current_id:
                await create_pointer(
                    source_id=starting_record.id,
                    target_id=current_id,
                    embedding=query_embedding,
                    relevance=similarity
                )
        
        # 检查现有指针（快速跳转）
        pointers = await get_pointers_at_source(current_id)
        for pointer in pointers:
            pointer_sim = cosine_similarity(query_embedding, pointer.embedding)
            if pointer_sim >= threshold:
                target = await get_by_id(pointer.target_id)
                if target and target.id not in visited:
                    results.append(SearchResult(target, pointer_sim, via_pointer=True))
                    await increment_access_count(pointer.id)
        
        # 移动到前一条记录
        current_id = await get_previous_id(current_id)
    
    return sorted(results, by=similarity, descending=True)[:max_results]
```

---

## 三、与第一代算法的对比

### 3.1 核心思路传承

**两代算法的共同原则**：

| 原则 | 第一代（文件） | 第二代（数据库） | 状态 |
|------|---------------|-----------------|------|
| **按需检索** | ✅ 用户提到才扫描 | ✅ 用户查询才检索 | ✅ 完全一致 |
| **两两比对** | ✅ 查询词 vs 文本 | ✅ 查询向量 vs 记录向量 | ✅ 思路一致，实现升级 |
| **扫描记录** | ✅ 记录到文件"扫描结果"部分 | ✅ 创建指针数据结构 | ✅ 思路一致，载体升级 |
| **避免重复** | ✅ 避免重复扫描 | ✅ 指针 O(1) 跳转 | ✅ 思路一致，优化升级 |
| **客观索引** | ✅ 不预构建索引 | ✅ 只为真实查询创建指针 | ✅ 完全一致 |

**核心思想一脉相承**：
> 两代算法都遵循"**如无必要，勿建索引**"的设计原则，采用**按需检索 + 两两比对 + 记录优化**的核心思路。

### 3.2 实现方式演进

| 方面 | 第一代（文件扫描） | 第二代（数据库） | 提升幅度 |
|------|------------------|-----------------|---------|
| **存储介质** | Markdown 文件 | SQLite/PostgreSQL | ⭐⭐⭐⭐⭐ |
| **匹配方式** | 文本关键词匹配 | 向量相似度（RAG） | ⭐⭐⭐⭐⭐ |
| **检索速度** | O(n) 线性扫描 | O(1) 指针跳转 + 向量搜索 | ⭐⭐⭐⭐⭐ |
| **智能程度** | 表面文本匹配 | 深层语义理解 | ⭐⭐⭐⭐⭐ |
| **索引结构** | 文件中的扫描记录 | 数据库指针表（带元数据） | ⭐⭐⭐⭐⭐ |
| **可扩展性** | 适合小规模 | 支持百万级记录 | ⭐⭐⭐⭐⭐ |

### 3.3 为什么演进到第二代？

**第一代的贡献**：
- ✅ 验证了核心思路的可行性
- ✅ 证明了按需检索的有效性
- ✅ 提供了算法设计的理论基础

**第一代的局限**（推动演进的动力）：
- ❌ 性能瓶颈：文件线性扫描慢
- ❌ 智能不足：文本匹配缺乏语义理解
- ❌ 扩展困难：文件格式难以支持大规模应用

**第二代的解决方案**：
- ✅ 数据库 + 向量 → 性能提升
- ✅ RAG 技术 → 智能提升
- ✅ 结构化指针 → 可扩展性提升

**本质**：
> 第二代不是对第一代的否定，而是**核心思路的延续和实现方式的优化**。

---

## 四、实现细节

### 4.1 两两比对机制

```python
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """计算两个向量的余弦相似度"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# 在检索中应用
similarity = cosine_similarity(query_embedding, record.embedding)
if similarity >= threshold:  # 例如 0.7
    # 找到相关记忆
    results.append(record)
```

**关键点**：
- 归一化点积，范围 [0, 1]
- 1 表示完全相同，0 表示完全无关
- 阈值过滤（默认 0.7）平衡召回率和精确率

### 4.2 指针创建机制

```python
async def _create_pointer(
    source_id: int,      # 查询起始位置
    target_id: int,      # 找到的相关记忆
    query_embedding,     # 查询向量（用于未来匹配）
    relevance_score: float,
) -> Pointer | None:
    # 检查是否已存在相似指针（避免重复）
    existing = await find_similar_pointers(
        source_id, query_embedding, threshold=0.95
    )
    if existing:
        return None  # 已有高度相似指针
    
    # 创建新指针
    pointer = Pointer(
        source_id=source_id,
        target_id=target_id,
        embedding=query_embedding,  # 保存查询向量
        relevance_score=relevance_score,
    )
    return await repo.create(pointer)
```

**指针数据结构**：
```typescript
interface Pointer {
  id: number;
  source_id: number;     // 指针所在位置
  target_id: number;     // 指向的目标
  embedding: number[];   // 创建时的查询向量
  pointer_type: 'embedding' | 'summary';
  relevance_score: number;  // 相关性评分
  access_count: number;  // 访问次数（用于优化）
  last_accessed: Date;   // 最后访问时间
}
```

### 3.3 指针跳转机制

```python
# 检查当前位置的所有指针
pointers = await get_pointers_at_source(current_id)

for pointer in pointers:
    # 计算当前查询与指针的相似度
    pointer_similarity = cosine_similarity(query_embedding, pointer.embedding)
    
    if pointer_similarity >= threshold:
        # 匹配成功，直接跳转到目标
        target_record = await get_by_id(pointer.target_id)
        results.append(SearchResult(
            record=target_record,
            score=pointer_similarity,
            via_pointer=True,  # 标记为指针跳转
        ))
        pointer_jumps += 1
        
        # 更新访问统计
        await increment_access_count(pointer.id)
```

**优势**：
- O(1) 时间复杂度直达目标
- 随时间积累，常用路径被优化
- 访问计数帮助识别重要指针

---

## 五、日志输出示例

### 5.1 典型检索日志

```
[INFO] Starting memory scan for session user-123, query: '话语映射系统...' (embedding dim: 1536)
[DEBUG] Match found at record 42: similarity=0.852 (threshold: 0.7)
[INFO] Created pointer 15: 50 -> 42 (relevance: 0.852)
[DEBUG] Pointer jump: 30 -> 25 (similarity: 0.789)
[DEBUG] Pointer jump: 20 -> 10 (similarity: 0.812)
[INFO] Memory scan complete: scanned=50, found=5, pointer_jumps=2, pointers_created=1
```

**解读**：
- 扫描了 50 条记录
- 找到 5 条相关记忆
- 2 次指针跳转（快速访问历史）
- 创建 1 个新指针（为未来优化）

### 5.2 调试信息

启用详细日志后：

```python
# Python: 设置 logging level 为 DEBUG
import logging
logging.basicConfig(level=logging.DEBUG)

# Node.js: 设置 NODE_DEBUG=memory
NODE_DEBUG=memory node app.js
```

---

## 六、性能优化

### 6.1 懒加载策略

```python
class LazyMemoryScanner:
    def __init__(self):
        self.loaded_files = {}  # 缓存已加载文件
        self.max_cache_size = 10
    
    async def _scan_file(self, file_path, concept):
        # 检查缓存
        if file_path not in self.loaded_files:
            if len(self.loaded_files) >= self.max_cache_size:
                # 移除最旧的
                oldest_key = next(iter(self.loaded_files))
                del self.loaded_files[oldest_key]
            
            # 加载文件
            with open(file_path, 'r') as f:
                self.loaded_files[file_path] = f.read()
        
        content = self.loaded_files[file_path]
        # ... 继续扫描
```

### 6.2 批量扫描

```python
async def scan_multiple(self, concepts: list, current_date: str) -> dict:
    """批量扫描多个概念"""
    results = {}
    
    # 先检查缓存
    cached = [c for c in concepts if c in self.index_cache]
    uncached = [c for c in concepts if c not in self.index_cache]
    
    # 处理缓存概念
    for concept in cached:
        results[concept] = self.scan(concept, current_date)
    
    # 处理未缓存概念（一次性加载文件）
    if uncached:
        today_content = await load_today_file()
        for concept in uncached:
            if concept in today_content:
                result = await _scan_file(today_file, concept)
                results[concept] = result
    
    return results
```

### 6.3 指针清理

```python
async def cleanup_unused_pointers(max_age_days=30):
    """清理长时间未使用的指针"""
    cutoff = datetime.now() - timedelta(days=max_age_days)
    
    unused = await find_pointers(
        last_accessed < cutoff,
        access_count == 0
    )
    
    for pointer in unused:
        await delete_pointer(pointer.id)
    
    return len(unused)
```

---

## 七、使用示例

### 7.1 Python 示例

```python
from walnut_ever_mem import WalnutConfig, MemoryService, init_database

# 初始化
config = WalnutConfig()
await init_database(config)

memory = MemoryService.from_config(config)

# 存储记忆
await memory.remember("session-1", "user", "我想学习话语映射系统")

# 检索记忆（触发记忆扫描）
results = await memory.recall(
    query="话语映射系统是什么？",
    session_id="session-1",
    max_results=5
)

for result in results:
    print(f"Score: {result.score:.3f}")
    print(f"Content: {result.record.content}")
    print(f"Via pointer: {result.via_pointer}")
    print("---")});
```

### 7.2 Node.js 示例

```typescript
import { createConfig, MemoryService, initDatabase } from 'walnut-ever-mem';

// 初始化
const config = createConfig();
await initDatabase(config);

const memory = new MemoryService(config);

// 存储记忆
await memory.remember("session-1", "user", "我想学习话语映射系统");

// 检索记忆（触发记忆扫描）
const results = await memory.recall(
  "话语映射系统是什么？",
  "session-1",
  5
);

results.forEach(result => {
  console.log(`Score: ${result.score.toFixed(3)}`);
  console.log(`Content: ${result.record.content}`);
  console.log(`Via pointer: ${result.viaPointer}`);
  console.log('---');
});
```

---

## 八、总结

### 8.1 核心优势

1. **按需检索** - 不预先扫描，只在查询时触发
2. **两两比对** - 查询与记忆逐一比对，确保准确性
3. **指针优化** - 成功检索创建捷径，未来查询更快
4. **语义理解** - 向量相似度超越表面文本匹配
5. **高效性能** - 数据库 + 向量 + 指针，三重优化

### 8.2 适用场景

- AI 助手长期记忆
- 对话上下文管理
- 个性化知识积累
- 智能检索系统

### 8.3 与记忆扫描算法的关系

**WalnutEverMem = 记忆扫描算法（第一代思路） + 数据库优化 + RAG 技术**

- 继承了记忆扫描的核心思想（按需、比对、记录）
- 使用数据库替代文件存储（性能提升）
- 使用向量相似度替代文本匹配（智能提升）
- 使用指针数据结构替代扫描记录（结构化提升）

**两代算法的关系**：
> 第二代是第一代思路的自然演进和优化，两者都是本项目原创的记忆管理解决方案。

---

**文档状态**: ✅ 完成  
**最后更新**: 2026-04-01  
**维护者**: WalnutEverMem Team
