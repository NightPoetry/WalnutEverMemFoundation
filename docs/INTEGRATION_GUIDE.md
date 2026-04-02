# WalnutEverMem 系统集成指南

**版本**: 1.0  
**创建时间**: 2026-04-01  
**目标读者**: AI 应用开发者

---

## 一、WalnutEverMem 的定位

### 1.1 高速记忆查询基座

**WalnutEverMem 是什么？**

> WalnutEverMem 是一个**工具/基础架构**，为上层 AI 系统提供高速记忆存储和检索能力。

**关键特性**：
- ✅ **被动查询**：等待上层 AI 主动调用
- ✅ **高速检索**：数据库 + 向量 + 指针三重优化
- ✅ **按需响应**：查询时触发，无预计算开销
- ✅ **记忆优化**：自动创建指针，越用越快

**不是什么**：
- ❌ 不是完整的 AI 应用
- ❌ 不主动决定何时查询
- ❌ 不处理业务逻辑
- ❌ 不生成回复内容

### 1.2 架构层次

```
┌─────────────────────────────────────────────┐
│  业务逻辑层                                   │
│  (AI 应用、对话系统、Agent)                   │
│  - 决定何时查询                              │
│  - 处理查询结果                              │
│  - 生成回复                                  │
└─────────────┬───────────────────────────────┘
              │ 调用 API
              ▼
┌─────────────────────────────────────────────┐
│  WalnutEverMem 基础架构层                     │
│  (记忆存储与检索引擎)                         │
│  - 存储记忆                                  │
│  - 执行检索                                  │
│  - 创建指针                                  │
│  - 返回结果                                  │
└─────────────────────────────────────────────┘
```

---

## 二、查询策略设计

### 2.1 策略选择矩阵

| 策略 | 适用场景 | 成本 | 性能 | 推荐度 |
|------|---------|------|------|--------|
| **按需查询** | 概念驱动对话、知识问答 | 低 | 高 | ⭐⭐⭐⭐⭐ |
| **每次回复查询** | 心理咨询、法律咨询等关键场景 | 高 | 中 | ⭐⭐⭐ |
| **混合策略** | 通用对话助手 | 中 | 高 | ⭐⭐⭐⭐ |

### 2.2 按需查询（推荐）

**何时使用**：
- 用户提到历史概念（"还记得 XXX 吗？"）
- 检测到未知术语
- 需要上下文补充

**实现模式**：

```python
class ConceptDrivenAI:
    def __init__(self):
        self.memory = MemoryService.from_config(config)
        self.llm = LLMClient()
    
    async def process(self, user_input: str, session_id: str):
        # 步骤 1：提取概念
        concepts = self.extract_concepts(user_input)
        
        # 步骤 2：按需查询
        context_parts = []
        for concept in concepts:
            results = await self.memory.recall(
                query=concept,
                session_id=session_id,
                max_results=3
            )
            if results:
                context_parts.extend([r.record.content for r in results])
        
        # 步骤 3：生成回复
        context = "\n".join(context_parts) if context_parts else "无相关记忆"
        return await self.llm.generate(
            prompt=user_input,
            context=context
        )
    
    def extract_concepts(self, text: str) -> list:
        """提取文本中的关键概念"""
        # 可以使用 NLP 库、关键词提取等
        import re
        patterns = [
            r'"([^"]+)"',           # 引号内容
            r'那个 (\S+)',           # "那个 XXX"
            r'之前说的 (\S+)',       # "之前说的 XXX"
        ]
        concepts = []
        for pattern in patterns:
            concepts.extend(re.findall(pattern, text))
        return concepts
```

**优点**：
- 🎯 精准：只查询需要的内容
- 💰 经济：减少 LLM token 消耗
- ⚡ 快速：无多余查询

### 2.3 每次回复查询

**何时使用**：
- 高风险场景（医疗、法律、心理咨询）
- 需要完整上下文的场景
- 用户可能随时提及历史的场景

**实现模式**：

```python
class AlwaysQueryAI:
    def __init__(self):
        self.memory = MemoryService.from_config(config)
        self.llm = LLMClient()
    
    async def generate_response(self, user_input: str, session_id: str):
        # 总是查询最近上下文
        recent = await self.memory.get_context(
            session_id=session_id,
            limit=10
        )
        
        # 总是查询相关记忆
        relevant = await self.memory.recall(
            query=user_input,
            session_id=session_id,
            max_results=5
        )
        
        # 组合上下文
        context = self.build_context(recent, relevant)
        return await self.llm.generate(user_input, context)
    
    def build_context(self, recent: list, relevant: list) -> str:
        """构建完整上下文"""
        parts = ["[最近对话]:"]
        for record in recent:
            parts.append(f"{record.role}: {record.content}")
        
        if relevant:
            parts.append("\n[相关记忆]:")
            for result in relevant:
                parts.append(f"- {result.record.content} (相似度：{result.score:.2f})")
        
        return "\n".join(parts)
```

**优点**：
- 🔍 全面：从不错过相关信息
- 🛡️ 安全：适合关键应用
- 📊 一致：行为可预测

**缺点**：
- 💸 成本高：每次都查询
- 🐌 速度慢：增加延迟

### 2.4 混合策略

**何时使用**：
- 通用对话助手
- 需要平衡成本和性能的场景

**实现模式**：

```python
class HybridAI:
    def __init__(self):
        self.memory = MemoryService.from_config(config)
        self.llm = LLMClient()
    
    async def process_message(self, user_input: str, session_id: str):
        # 总是获取轻量级上下文（便宜）
        context = await self.memory.get_context(
            session_id=session_id,
            limit=5
        )
        
        # 判断是否需要深度查询
        if self.needs_deep_query(user_input, context):
            # 提取查询词
            query = self.extract_query(user_input)
            relevant = await self.memory.recall(
                query=query,
                session_id=session_id,
                max_results=5
            )
            context = self.merge_context(context, relevant)
        
        return await self.llm.generate(user_input, context)
    
    def needs_deep_query(self, user_input: str, context: list) -> bool:
        """判断是否需要深度记忆查询"""
        # 触发条件示例：
        
        # 1. 包含历史引用词
        history_keywords = ['记得', '之前', '说过', '提到', '那个']
        if any(kw in user_input for kw in history_keywords):
            return True
        
        # 2. 包含疑问词（询问已知概念）
        question_words = ['是什么', '怎么用', '为什么']
        if any(kw in user_input for kw in question_words):
            return True
        
        # 3. 概念检测（使用 NLP 或关键词）
        concepts = self.extract_concepts(user_input)
        if len(concepts) > 0:
            return True
        
        return False
    
    def extract_query(self, user_input: str) -> str:
        """从用户输入中提取查询词"""
        # 简单实现：直接使用用户输入
        # 可以优化为提取关键词
        return user_input
```

---

## 三、实战示例

### 3.1 对话助手（推荐方案）

```python
from walnut_ever_mem import MemoryService, WalnutConfig
from typing import List

class SmartAssistant:
    """智能对话助手 - 混合策略实现"""
    
    def __init__(self):
        config = WalnutConfig()
        self.memory = MemoryService.from_config(config)
        self.llm = self.init_llm()
    
    async def chat(self, user_input: str, session_id: str) -> str:
        """处理用户对话"""
        
        # 1. 获取基础上下文（总是执行）
        base_context = await self.memory.get_context(
            session_id=session_id,
            limit=5
        )
        
        # 2. 检测是否需要记忆检索
        memory_context = []
        if self._should_query_memory(user_input):
            concepts = self._extract_key_concepts(user_input)
            for concept in concepts:
                results = await self.memory.recall(
                    query=concept,
                    session_id=session_id,
                    max_results=3
                )
                memory_context.extend([
                    r.record.content for r in results
                ])
        
        # 3. 构建提示词
        prompt = self._build_prompt(
            user_input=user_input,
            recent_context=base_context,
            memory_context=memory_context
        )
        
        # 4. 生成回复
        response = await self.llm.generate(prompt)
        
        # 5. 存储对话记录
        await self._store_conversation(
            session_id=session_id,
            user_input=user_input,
            response=response
        )
        
        return response
    
    def _should_query_memory(self, text: str) -> bool:
        """判断是否需要查询记忆"""
        # 历史引用检测
        history_markers = [
            '还记得', '之前说', '提到过', '那个',
            '上次', '以前', '曾经'
        ]
        if any(marker in text for marker in history_markers):
            return True
        
        # 问题检测（询问概念）
        if any(q in text for q in ['是什么', '怎么用', '为什么', '怎么做']):
            return True
        
        return False
    
    def _extract_key_concepts(self, text: str) -> List[str]:
        """提取关键概念"""
        import re
        concepts = []
        
        # 提取引号内容
        concepts.extend(re.findall(r'"([^"]+)"', text))
        
        # 提取特定模式
        patterns = [
            r'那个 (\S+)',
            r'关于 (\S+)',
            r'之前说的 (\S+)',
        ]
        for pattern in patterns:
            concepts.extend(re.findall(pattern, text))
        
        # 去重
        return list(set(concepts))
    
    def _build_prompt(
        self,
        user_input: str,
        recent_context: list,
        memory_context: list
    ) -> str:
        """构建 LLM 提示词"""
        prompt_parts = []
        
        # 添加系统指令
        prompt_parts.append("你是一个智能助手。")
        
        # 添加最近对话
        if recent_context:
            prompt_parts.append("\n[最近对话]:")
            for record in recent_context[-5:]:
                prompt_parts.append(
                    f"{record.role}: {record.content}"
                )
        
        # 添加检索到的记忆
        if memory_context:
            prompt_parts.append("\n[相关背景信息]:")
            for memory in memory_context:
                prompt_parts.append(f"- {memory}")
        
        # 添加用户问题
        prompt_parts.append(f"\n用户：{user_input}")
        prompt_parts.append("\n助手：")
        
        return "\n".join(prompt_parts)
    
    async def _store_conversation(
        self,
        session_id: str,
        user_input: str,
        response: str
    ):
        """存储对话到记忆"""
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
```

### 3.2 心理咨询助手（每次查询）

```python
class TherapyAssistant:
    """心理咨询助手 - 每次回复都查询"""
    
    def __init__(self):
        config = WalnutConfig()
        self.memory = MemoryService.from_config(config)
        self.llm = self.init_llm()
    
    async def counsel(self, user_input: str, session_id: str) -> str:
        """提供心理咨询"""
        
        # 总是获取完整上下文（安全优先）
        recent = await self.memory.get_context(
            session_id=session_id,
            limit=20  # 更多历史
        )
        
        relevant = await self.memory.recall(
            query=user_input,
            session_id=session_id,
            max_results=10  # 更多相关记忆
        )
        
        # 构建详细上下文
        context = self._build_therapy_context(recent, relevant)
        
        # 生成回复
        prompt = f"""
你是一位专业的心理咨询师。基于以下对话历史和相关信息，
以温暖、专业的方式回应用户。

{context}

用户：{user_input}
咨询师："""
        
        response = await self.llm.generate(prompt)
        
        # 存储记录
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
    
    def _build_therapy_context(
        self,
        recent: list,
        relevant: list
    ) -> str:
        """构建咨询上下文"""
        parts = []
        
        parts.append("【对话历史】")
        for record in recent:
            emoji = "👤" if record.role == "user" else "💬"
            parts.append(f"{emoji} {record.content}")
        
        if relevant:
            parts.append("\n【相关背景】")
            for result in relevant:
                parts.append(f"• {result.record.content}")
        
        return "\n".join(parts)
```

### 3.3 知识问答助手（概念驱动）

```python
class KnowledgeQA:
    """知识问答助手 - 纯按需查询"""
    
    def __init__(self):
        config = WalnutConfig()
        self.memory = MemoryService.from_config(config)
        self.llm = self.init_llm()
    
    async def answer(self, question: str, session_id: str) -> str:
        """回答知识性问题"""
        
        # 提取问题中的关键概念
        concepts = self._extract_question_concepts(question)
        
        # 为每个概念查询记忆
        knowledge_base = []
        for concept in concepts:
            results = await self.memory.recall(
                query=concept,
                session_id=session_id,
                max_results=5
            )
            knowledge_base.extend([
                r.record.content for r in results
                if r.score > 0.7  # 只使用高相关度
            ])
        
        # 构建答案
        if knowledge_base:
            context = "\n\n".join(knowledge_base)
            prompt = f"""
基于以下已知信息回答问题。如果信息不足，请诚实说明。

已知信息：
{context}

问题：{question}
回答："""
        else:
            prompt = f"""
我没有相关的背景信息。

问题：{question}
回答："""
        
        return await self.llm.generate(prompt)
    
    def _extract_question_concepts(self, question: str) -> list:
        """从问题中提取概念"""
        # 移除疑问词
        question_words = ['什么', '怎么', '为什么', '哪些', '如何']
        for word in question_words:
            question = question.replace(word, '')
        
        # 提取名词短语（简单实现）
        import jieba
        words = jieba.lcut(question)
        
        # 过滤停用词
        stopwords = {'的', '了', '是', '在', '我', '有', '和'}
        concepts = [w for w in words if w not in stopwords and len(w) > 1]
        
        return concepts
```

---

## 四、性能优化建议

### 4.1 查询优化

```python
# ✅ 好的做法
async def optimized_query(memory_service, query, session_id):
    # 限制结果数量
    results = await memory_service.recall(
        query=query,
        session_id=session_id,
        max_results=5  # 不要太多
    )
    return results

# ❌ 避免的做法
async def bad_query(memory_service, query, session_id):
    # 查询太多结果，浪费资源
    results = await memory_service.recall(
        query=query,
        session_id=session_id,
        max_results=100  # 太多了！
    )
    return results
```

### 4.2 上下文构建

```python
# ✅ 智能合并
def smart_context_merge(recent, relevant):
    """智能合并上下文，去重"""
    seen_ids = set()
    merged = []
    
    # 先添加相关记忆
    for result in relevant:
        if result.record.id not in seen_ids:
            merged.append(result.record.content)
            seen_ids.add(result.record.id)
    
    # 再添加最近对话（去重）
    for record in recent:
        if record.id not in seen_ids:
            merged.append(record.content)
            seen_ids.add(record.id)
    
    # 限制总长度
    return merged[:10]  # 最多 10 条
```

### 4.3 缓存策略

```python
class CachedAI:
    """带缓存的 AI 助手"""
    
    def __init__(self):
        self.memory = MemoryService.from_config(config)
        self.query_cache = {}  # 简单内存缓存
    
    async def query_with_cache(self, query, session_id):
        """带缓存的查询"""
        cache_key = f"{session_id}:{query}"
        
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]
        
        # 执行查询
        results = await self.memory.recall(
            query=query,
            session_id=session_id,
            max_results=5
        )
        
        # 缓存结果（TTL: 5 分钟）
        self.query_cache[cache_key] = {
            'results': results,
            'timestamp': time.time()
        }
        
        return results
    
    def cleanup_cache(self):
        """清理过期缓存"""
        now = time.time()
        expired = [
            k for k, v in self.query_cache.items()
            if now - v['timestamp'] > 300  # 5 分钟
        ]
        for key in expired:
            del self.query_cache[key]
```

---

## 五、调试与监控

### 5.1 启用详细日志

```python
# Python: 设置 logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 在查询时记录日志
async def query_with_logging(query, session_id):
    logger.info(f"Querying memory: '{query[:50]}...'")
    
    results = await memory.recall(
        query=query,
        session_id=session_id,
        max_results=5
    )
    
    logger.info(f"Found {len(results)} results")
    for i, result in enumerate(results):
        logger.debug(f"  [{i}] Score: {result.score:.3f}, "
                    f"Content: {result.record.content[:50]}...")
    
    return results
```

### 5.2 性能监控

```python
class MonitoredAI:
    """带监控的 AI 助手"""
    
    def __init__(self):
        self.stats = {
            'queries': 0,
            'avg_results': 0,
            'avg_response_time': 0,
        }
    
    async def process_with_stats(self, user_input, session_id):
        start_time = time.time()
        
        # 执行查询
        results = await self.memory.recall(
            query=user_input,
            session_id=session_id
        )
        
        # 更新统计
        self.stats['queries'] += 1
        self.stats['avg_results'] = (
            (self.stats['avg_results'] * (self.stats['queries'] - 1) +
             len(results)) / self.stats['queries']
        )
        
        response_time = time.time() - start_time
        self.stats['avg_response_time'] = (
            (self.stats['avg_response_time'] * (self.stats['queries'] - 1) +
             response_time) / self.stats['queries']
        )
        
        return results
    
    def print_stats(self):
        """打印统计信息"""
        print(f"查询次数：{self.stats['queries']}")
        print(f"平均结果数：{self.stats['avg_results']:.1f}")
        print(f"平均响应时间：{self.stats['avg_response_time']*1000:.1f}ms")
```

---

## 六、最佳实践总结

### 6.1 DO ✅

- 按需查询，减少不必要调用
- 限制查询结果数量（5-10 条）
- 使用混合策略平衡成本和性能
- 为查询结果设置相关性阈值
- 记录查询日志用于优化
- 定期清理无用缓存

### 6.2 DON'T ❌

- 不要每次都查询大量数据
- 不要查询不限制 max_results
- 不要忽略查询结果的相关性分数
- 不要在循环中频繁查询
- 不要忘记存储新的对话记录
- 不要在不需要的场景使用"每次查询"策略

---

## 七、常见问题

### Q1: 应该选择哪种查询策略？

**A**: 根据你的应用场景：
- **对话助手** → 混合策略（推荐）
- **知识问答** → 按需查询
- **心理咨询** → 每次查询
- **不确定** → 从按需查询开始，根据效果调整

### Q2: max_results 设置多少合适？

**A**: 
- 按需查询：3-5 条
- 每次查询：5-10 条
- 混合策略：基础 5 条 + 深度 5 条

### Q3: 如何提高查询准确性？

**A**:
1. 优化查询词提取（使用 NLP）
2. 设置合适的相似度阈值（0.7-0.8）
3. 结合多个概念查询
4. 使用过滤条件（时间范围、角色等）

### Q4: WalnutEverMem 会自动学习吗？

**A**: 是的！通过指针机制：
- 每次成功查询都会创建指针
- 指针加速未来相似查询
- 系统越用越快

---

**文档状态**: ✅ 完成  
**最后更新**: 2026-04-01  
**维护者**: WalnutEverMem Team
