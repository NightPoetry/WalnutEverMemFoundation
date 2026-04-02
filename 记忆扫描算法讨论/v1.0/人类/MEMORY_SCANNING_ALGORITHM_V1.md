# 记忆扫描算法与客观索引 - 实现指南

**版本**：1.0  
**创建时间**：2026-04-01  
**时区**：UTC+8（本地时间）  
**设计来源**：记忆管理系统实践总结

---

## 一、系统概述

### 1.1 问题定义

**核心问题**：AI 助手重启后丢失对话上下文，用户提到历史概念时无法快速定位相关信息。

**传统方案缺陷**：
- 预先构建大量索引 → 索引膨胀、维护成本高
- 每次查询全量扫描 → 性能差、响应慢
- 无扫描记录 → 重复扫描相同内容

### 1.2 解决方案

**记忆扫描算法 + 客观索引机制**：
- **按需扫描**：用户提到未知概念时才触发扫描
- **扫描记录**：记录扫描结果，避免重复扫描
- **客观索引**：基于实际查询需求建立索引，不主观构建

### 1.3 设计原则

**设计原则**：
> 如无必要，勿建索引

**核心原则**：
1. **不主观构建索引** - 不预先猜测什么需要索引
2. **客观需求驱动** - 只有当用户实际提到时才建立索引
3. **扫描结果即索引** - 扫描发现的位置信息就是最自然的索引
4. **避免索引膨胀** - 只索引真正被查询过的内容

---

## 二、数据结构设计

### 2.1 记忆文件结构

**文件路径**：`memory/YYYY-MM-DD.md`

```markdown
# 2026-04-01 记忆文件

**日期**：2026-04-01  
**时区**：UTC+8（本地时间）  
**创建时间**：2026-04-01 13:19 (UTC+8)

---

## 对话记录

### 13:19 (UTC+8) - 话题标签
**内容**：对话内容摘要...

### 13:47 (UTC+8) - 话题标签
**内容**：对话内容摘要...

---

## 扫描结果

**本次扫描内容**：无（新对话开始）
或
**本次扫描内容**：
- 示例概念A：在 2026-04-01 中发现（首次提及）
- 示例概念B：在 2026-03-25 中发现（历史概念）

---

**记录人**：艾米（小狐狸助手）🦊  
**记录时间**：2026-04-01 13:47 (UTC+8)
```

### 2.2 扫描结果索引结构

**存储位置**：记忆文件的"扫描结果"部分

```json
{
  "concept": "概念名称",
  "foundIn": "YYYY-MM-DD",
  "foundAt": "文件中的具体位置（章节标题或行号）",
  "summary": "概念简要说明",
  "relatedFiles": ["相关文件路径列表"],
  "scanTime": "2026-04-01T13:55:00+08:00",
  "isFirstMention": false,
  "previousScans": [
    {
      "date": "2026-03-25",
      "result": "found"
    }
  ]
}
```

### 2.3 客观索引缓存

**存储位置**：`memory/index-cache.json`（可选，内存缓存亦可）

```json
{
  "version": "1.0",
  "updatedAt": "2026-04-01T13:55:00+08:00",
  "indexedConcepts": {
    "示例概念A": {
      "firstFound": "2026-04-01",
      "lastAccessed": "2026-04-01T13:55:00+08:00",
      "locations": [
        {
          "date": "2026-04-01",
          "section": "13:47 (UTC+8) - 示例话题"
        }
      ],
      "summary": "示例概念的简要说明",
      "relatedConcepts": ["相关概念1", "相关概念2"]
    },
    "示例概念B": {
      "firstFound": "2026-03-25",
      "lastAccessed": "2026-04-01T14:00:00+08:00",
      "locations": [
        {
          "date": "2026-03-25",
          "section": "示例章节"
        }
      ],
      "summary": "示例项目的简要说明",
      "relatedConcepts": ["相关概念1", "相关概念2"]
    }
  }
}
```

---

## 三、核心算法实现

### 3.1 记忆扫描算法（完整流程）

```python
class MemoryScanner:
    def __init__(self, memory_dir: str, index_cache: dict = None):
        self.memory_dir = memory_dir
        self.index_cache = index_cache or {}
        self.scan_history = []  # 记录本次会话的扫描历史
    
    def scan(self, concept: str, current_date: str) -> ScanResult:
        """
        扫描记忆系统，查找概念相关信息
        
        Args:
            concept: 要查找的概念名称
            current_date: 当前日期（YYYY-MM-DD）
        
        Returns:
            ScanResult: 扫描结果对象
        """
        # 步骤 1：检查客观索引缓存
        if concept in self.index_cache:
            cached = self.index_cache[concept]
            return ScanResult(
                found=True,
                concept=concept,
                locations=cached['locations'],
                summary=cached['summary'],
                from_cache=True,
                scan_date=current_date
            )
        
        # 步骤 2：检查当前对话记忆（今天文件）
        today_file = f"{self.memory_dir}/{current_date}.md"
        if os.path.exists(today_file):
            result = self._scan_file(today_file, concept, current_date)
            if result.found:
                self._update_index(concept, result)
                return result
        
        # 步骤 3：向前扫描历史记忆文件
        result = self._scan_history_files(concept, current_date)
        
        # 步骤 4：记录扫描结果
        self._record_scan_result(concept, result, current_date)
        
        # 步骤 5：更新客观索引
        if result.found:
            self._update_index(concept, result)
        
        return result
    
    def _scan_history_files(self, concept: str, current_date: str) -> ScanResult:
        """向前扫描历史记忆文件"""
        # 获取所有记忆文件列表（按日期倒序）
        memory_files = self._get_memory_files_sorted()
        
        for file_date in memory_files:
            if file_date >= current_date:
                continue  # 跳过今天及以后的文件
            
            file_path = f"{self.memory_dir}/{file_date}.md"
            result = self._scan_file(file_path, concept, file_date)
            
            if result.found:
                result.found_in = file_date
                return result
        
        # 未找到
        return ScanResult(
            found=False,
            concept=concept,
            locations=[],
            summary=None,
            from_cache=False,
            scan_date=current_date,
            message=f"未在历史记忆中找到 '{concept}'"
        )
    
    def _scan_file(self, file_path: str, concept: str, file_date: str) -> ScanResult:
        """扫描单个记忆文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 简单实现：检查概念是否在文件中
        if concept in content:
            # 提取相关段落（可扩展为更智能的提取）
            locations = self._extract_locations(content, concept)
            summary = self._extract_summary(content, concept)
            
            return ScanResult(
                found=True,
                concept=concept,
                locations=locations,
                summary=summary,
                from_cache=False,
                scan_date=file_date,
                found_in=file_date
            )
        
        return ScanResult(
            found=False,
            concept=concept,
            locations=[],
            summary=None,
            from_cache=False,
            scan_date=file_date
        )
    
    def _extract_locations(self, content: str, concept: str) -> list:
        """提取概念在文件中的位置"""
        locations = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if concept in line:
                # 找到最近的章节标题
                section = self._find_nearest_section(lines, i)
                locations.append({
                    'line': i + 1,
                    'section': section,
                    'context': line.strip()
                })
        
        return locations
    
    def _find_nearest_section(self, lines: list, current_line: int) -> str:
        """找到最近的章节标题"""
        for i in range(current_line, -1, -1):
            if lines[i].startswith('### ') or lines[i].startswith('## '):
                return lines[i].strip('# ').strip()
        return "未知章节"
    
    def _extract_summary(self, content: str, concept: str) -> str:
        """提取概念简要说明（可扩展为 AI 摘要）"""
        # 简单实现：返回包含概念的第一段话
        lines = content.split('\n')
        for line in lines:
            if concept in line and len(line) > 10:
                return line.strip()
        return None
    
    def _update_index(self, concept: str, result: ScanResult):
        """更新客观索引缓存"""
        if concept not in self.index_cache:
            self.index_cache[concept] = {
                'firstFound': result.found_in,
                'lastAccessed': result.scan_date,
                'locations': result.locations,
                'summary': result.summary,
                'relatedConcepts': []
            }
        else:
            self.index_cache[concept]['lastAccessed'] = result.scan_date
            # 合并位置信息
            existing_locations = self.index_cache[concept]['locations']
            for loc in result.locations:
                if loc not in existing_locations:
                    existing_locations.append(loc)
    
    def _record_scan_result(self, concept: str, result: ScanResult, current_date: str):
        """记录扫描结果到当前记忆文件"""
        today_file = f"{self.memory_dir}/{current_date}.md"
        
        # 读取当前记忆文件
        if os.path.exists(today_file):
            with open(today_file, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = f"# {current_date} 记忆文件\n\n## 扫描结果\n\n**本次扫描内容**：无\n"
        
        # 更新扫描结果部分
        scan_record = f"- **{concept}**: {'在 ' + result.found_in + ' 中发现' if result.found else '未在历史记忆中找到'}"
        
        # 插入到"## 扫描结果"部分
        if "## 扫描结果" in content:
            # 找到扫描结果部分并追加
            parts = content.split("## 扫描结果")
            if "**本次扫描内容**：无" in parts[1]:
                # 替换"无"为实际记录
                parts[1] = parts[1].replace(
                    "**本次扫描内容**：无",
                    f"**本次扫描内容**：\n{scan_record}"
                )
            else:
                # 追加到现有扫描记录
                parts[1] = parts[1] + f"\n{scan_record}"
            content = "## 扫描结果".join(parts)
        
        # 写回文件
        with open(today_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _get_memory_files_sorted(self) -> list:
        """获取所有记忆文件列表（按日期倒序）"""
        files = []
        for f in os.listdir(self.memory_dir):
            if f.endswith('.md') and f[0:4].isdigit():  # YYYY-MM-DD.md
                date_str = f.replace('.md', '')
                files.append(date_str)
        return sorted(files, reverse=True)
```

### 3.2 扫描结果数据类

```python
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class ScanResult:
    """扫描结果"""
    found: bool                    # 是否找到
    concept: str                   # 概念名称
    locations: List[dict]          # 位置列表
    summary: Optional[str]         # 简要说明
    from_cache: bool               # 是否来自缓存
    scan_date: str                 # 扫描日期
    found_in: Optional[str] = None # 在哪个文件中找到
    message: Optional[str] = None  # 附加消息
    
    def to_dict(self) -> dict:
        return {
            'found': self.found,
            'concept': self.concept,
            'locations': self.locations,
            'summary': self.summary,
            'from_cache': self.from_cache,
            'scan_date': self.scan_date,
            'found_in': self.found_in,
            'message': self.message
        }
```

### 3.3 使用示例

```python
# 初始化扫描器
scanner = MemoryScanner(
    memory_dir="/path/to/memory",
    index_cache=load_index_cache()  # 加载现有索引
)

# 示例 1：用户提到未知概念
concept = "示例概念"
current_date = "2026-04-01"

result = scanner.scan(concept, current_date)

if result.found:
    print(f"找到 '{concept}' 在 {result.found_in}")
    print(f"位置：{result.locations}")
    print(f"说明：{result.summary}")
else:
    print(f"未找到 '{concept}'：{result.message}")

# 示例 2：用户再次提到同一概念（使用缓存）
result2 = scanner.scan(concept, current_date)
print(f"来自缓存：{result2.from_cache}")  # True

# 示例 3：获取索引缓存状态
print(f"已索引概念数：{len(scanner.index_cache)}")
```

---

## 四、与对话系统集成

### 4.1 对话中触发扫描的时机

```python
class DialogueSystem:
    def __init__(self):
        self.scanner = MemoryScanner(memory_dir="memory")
        self.unknown_concepts = set()  # 本次会话遇到的未知概念
    
    def process_user_input(self, user_input: str, current_date: str) -> str:
        """处理用户输入"""
        # 步骤 1：提取潜在概念
        concepts = self._extract_concepts(user_input)
        
        # 步骤 2：检查每个概念是否已知
        for concept in concepts:
            if concept not in self.known_concepts:
                # 未知概念，触发扫描
                result = self.scanner.scan(concept, current_date)
                
                if result.found:
                    # 找到相关信息，更新已知概念
                    self.known_concepts[concept] = result.summary
                    self._add_to_context(concept, result)
                else:
                    # 未找到，记录为真正未知
                    self.unknown_concepts.add(concept)
        
        # 步骤 3：生成回复
        response = self._generate_response(user_input)
        
        return response
    
    def _extract_concepts(self, text: str) -> list:
        """从文本中提取潜在概念"""
        # 简单实现：提取名词短语
        # 实际应用中可使用 NLP 库（如 spaCy、jieba）
        concepts = []
        
        # 示例规则：提取引号、书名号中的内容
        import re
        patterns = [
            r'"([^"]+)"',           # 双引号
            r'"([^"]+)"',           # 中文引号
            r'《([^》]+)》',         # 书名号
            r'那个 (\S+)',           # "那个 XXX"
            r'之前说的 (\S+)',       # "之前说的 XXX"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            concepts.extend(matches)
        
        return concepts
```

### 4.2 回复中融入扫描结果

```python
def _add_to_context(self, concept: str, result: ScanResult):
    """将扫描结果添加到对话上下文"""
    
    # 构建上下文信息
    context = f"""
    [系统提示：找到 '{concept}' 的历史信息]
    首次发现：{result.found_in}
    位置：{result.locations[0]['section'] if result.locations else '未知'}
    说明：{result.summary}
    """
    
    # 添加到对话上下文（供 AI 模型使用）
    self.conversation_history.append({
        'role': 'system',
        'content': context
    })
```

---

## 五、性能优化

### 5.1 懒加载策略

```python
class LazyMemoryScanner(MemoryScanner):
    """懒加载扫描器"""
    
    def __init__(self, memory_dir: str):
        super().__init__(memory_dir)
        self.loaded_files = {}  # 缓存已加载的文件内容
        self.max_cache_size = 10  # 最多缓存 10 个文件
    
    def _scan_file(self, file_path: str, concept: str, file_date: str) -> ScanResult:
        """懒加载文件内容"""
        # 检查缓存
        if file_path not in self.loaded_files:
            # 缓存已满，移除最旧的
            if len(self.loaded_files) >= self.max_cache_size:
                oldest_key = next(iter(self.loaded_files))
                del self.loaded_files[oldest_key]
            
            # 加载文件
            with open(file_path, 'r', encoding='utf-8') as f:
                self.loaded_files[file_path] = f.read()
        
        content = self.loaded_files[file_path]
        # ... 继续扫描逻辑
```

### 5.2 批量扫描优化

```python
def scan_multiple(self, concepts: list, current_date: str) -> dict:
    """批量扫描多个概念"""
    results = {}
    
    # 步骤 1：先检查缓存
    cached_concepts = [c for c in concepts if c in self.index_cache]
    uncached_concepts = [c for c in concepts if c not in self.index_cache]
    
    # 处理缓存概念
    for concept in cached_concepts:
        results[concept] = self.scan(concept, current_date)
    
    # 处理未缓存概念（一次性加载文件）
    if uncached_concepts:
        # 预加载今天文件
        today_file = f"{self.memory_dir}/{current_date}.md"
        if os.path.exists(today_file):
            with open(today_file, 'r', encoding='utf-8') as f:
                today_content = f.read()
            
            for concept in uncached_concepts:
                if concept in today_content:
                    result = self._scan_file(today_file, concept, current_date)
                    results[concept] = result
                    self._update_index(concept, result)
    
    return results
```

### 5.3 索引持久化

```python
import json

def save_index_cache(self, cache_path: str):
    """保存索引缓存到文件"""
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(self.index_cache, f, ensure_ascii=False, indent=2)

def load_index_cache(cache_path: str) -> dict:
    """从文件加载索引缓存"""
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}
```

---

## 六、测试用例

### 6.1 单元测试

```python
import unittest

class TestMemoryScanner(unittest.TestCase):
    
    def setUp(self):
        self.scanner = MemoryScanner(memory_dir="test_memory")
        # 创建测试记忆文件
        self._create_test_files()
    
    def test_scan_found_in_today(self):
        """测试在今天文件中找到概念"""
        result = self.scanner.scan("测试概念", "2026-04-01")
        self.assertTrue(result.found)
        self.assertEqual(result.found_in, "2026-04-01")
    
    def test_scan_found_in_history(self):
        """测试在历史文件中找到概念"""
        result = self.scanner.scan("历史概念", "2026-04-01")
        self.assertTrue(result.found)
        self.assertEqual(result.found_in, "2026-03-30")
    
    def test_scan_not_found(self):
        """测试未找到概念"""
        result = self.scanner.scan("不存在的概念", "2026-04-01")
        self.assertFalse(result.found)
        self.assertIn("未找到", result.message)
    
    def test_cache_hit(self):
        """测试缓存命中"""
        # 第一次扫描
        result1 = self.scanner.scan("缓存概念", "2026-04-01")
        self.assertFalse(result1.from_cache)
        
        # 第二次扫描（应命中缓存）
        result2 = self.scanner.scan("缓存概念", "2026-04-01")
        self.assertTrue(result2.from_cache)
    
    def test_index_update(self):
        """测试索引更新"""
        self.scanner.scan("新概念", "2026-04-01")
        self.assertIn("新概念", self.scanner.index_cache)
    
    def _create_test_files(self):
        """创建测试记忆文件"""
        # 创建今天文件
        with open("test_memory/2026-04-01.md", 'w') as f:
            f.write("# 2026-04-01 记忆文件\n\n## 对话记录\n\n### 13:00 - 测试概念\n测试概念的内容...\n")
        
        # 创建历史文件
        with open("test_memory/2026-03-30.md", 'w') as f:
            f.write("# 2026-03-30 记忆文件\n\n## 对话记录\n\n### 10:00 - 历史概念\n历史概念的内容...\n")
```

### 6.2 集成测试

```python
def test_full_workflow():
    """测试完整工作流程"""
    scanner = MemoryScanner(memory_dir="memory")
    
    # 场景 1：用户首次提到概念
    result1 = scanner.scan("示例概念", "2026-04-01")
    assert result1.found == True
    assert result1.from_cache == False
    
    # 场景 2：用户再次提到同一概念
    result2 = scanner.scan("示例概念", "2026-04-01")
    assert result2.from_cache == True
    
    # 场景 3：检查索引缓存
    assert "示例概念" in scanner.index_cache
    
    # 场景 4：保存索引缓存
    scanner.save_index_cache("memory/index-cache.json")
    
    # 场景 5：重新加载索引缓存
    new_scanner = MemoryScanner(
        memory_dir="memory",
        index_cache=load_index_cache("memory/index-cache.json")
    )
    assert "示例概念" in new_scanner.index_cache
```

---

## 七、部署与监控

### 7.1 部署配置

```yaml
# config/memory-scanner.yaml
memory_scanner:
  memory_dir: "/path/to/memory"
  index_cache_path: "/path/to/memory/index-cache.json"
  
  # 性能配置
  max_cache_size: 10          # 最多缓存的文件数
  cache_ttl_hours: 24         # 缓存存活时间（小时）
  
  # 扫描配置
  max_scan_depth: 30          # 最多向前扫描 30 天
  scan_timeout_seconds: 5     # 单次扫描超时时间
  
  # 日志配置
  log_level: "INFO"
  log_file: "/path/to/logs/memory-scanner.log"
  
  # 监控配置
  enable_metrics: true
  metrics_port: 9090
```

### 7.2 监控指标

```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
SCAN_REQUESTS = Counter('memory_scan_requests_total', 'Total scan requests')
SCAN_DURATION = Histogram('memory_scan_duration_seconds', 'Scan duration')
CACHE_HITS = Counter('memory_cache_hits_total', 'Total cache hits')
INDEX_SIZE = Gauge('memory_index_size', 'Current index size')

class MonitoredMemoryScanner(MemoryScanner):
    """带监控的扫描器"""
    
    @SCAN_DURATION.time()
    def scan(self, concept: str, current_date: str) -> ScanResult:
        SCAN_REQUESTS.inc()
        
        # 检查缓存
        if concept in self.index_cache:
            CACHE_HITS.inc()
        
        result = super().scan(concept, current_date)
        
        # 更新索引大小指标
        INDEX_SIZE.set(len(self.index_cache))
        
        return result
```

---

## 八、常见问题与解决方案

### 8.1 性能问题

**问题**：扫描大量历史文件时响应慢

**解决方案**：
1. 增加缓存大小
2. 实现懒加载
3. 限制最大扫描深度（如只扫描最近 30 天）
4. 使用更高效的文本搜索算法（如 Aho-Corasick）

### 8.2 索引膨胀问题

**问题**：索引缓存文件过大

**解决方案**：
1. 定期清理长时间未访问的索引
2. 限制索引缓存大小（如最多 1000 个概念）
3. 使用 LRU 淘汰策略

```python
def cleanup_index_cache(self, max_size: int = 1000):
    """清理索引缓存"""
    if len(self.index_cache) > max_size:
        # 按最后访问时间排序
        sorted_items = sorted(
            self.index_cache.items(),
            key=lambda x: x[1]['lastAccessed']
        )
        # 移除最旧的 50%
        remove_count = len(sorted_items) // 2
        for i in range(remove_count):
            del self.index_cache[sorted_items[i][0]]
```

### 8.3 扫描准确性问题

**问题**：简单文本匹配误报率高

**解决方案**：
1. 使用 NLP 技术提取实体和概念
2. 增加上下文窗口
3. 使用语义相似度匹配
4. 引入用户反馈机制

---

## 九、扩展功能

### 9.1 多模态记忆扫描

```python
class MultiModalScanner(MemoryScanner):
    """支持多模态记忆的扫描器"""
    
    def scan(self, concept: str, current_date: str) -> ScanResult:
        # 扫描文本记忆
        text_result = super().scan(concept, current_date)
        
        # 扫描灵感系统
        inspiration_result = self._scan_inspirations(concept)
        
        # 扫描知识系统
        knowledge_result = self._scan_knowledge(concept)
        
        # 扫描原则系统
        principle_result = self._scan_principles(concept)
        
        # 合并结果
        return self._merge_results([
            text_result,
            inspiration_result,
            knowledge_result,
            principle_result
        ])
```

### 9.2 智能概念提取

```python
import spacy

class SmartConceptExtractor:
    """使用 NLP 智能提取概念"""
    
    def __init__(self):
        self.nlp = spacy.load("zh_core_web_sm")
    
    def extract(self, text: str) -> list:
        """从文本中提取概念"""
        doc = self.nlp(text)
        concepts = []
        
        # 提取命名实体
        for ent in doc.ents:
            concepts.append(ent.text)
        
        # 提取名词短语
        for chunk in doc.noun_chunks:
            if len(chunk.text) > 2:  # 过滤太短的
                concepts.append(chunk.text)
        
        return list(set(concepts))  # 去重
```

### 9.3 概念关系图

```python
class ConceptGraph:
    """概念关系图"""
    
    def __init__(self):
        self.graph = nx.Graph()
    
    def add_concept(self, concept: str, related: list):
        """添加概念及其关联"""
        self.graph.add_node(concept)
        for rel in related:
            self.graph.add_edge(concept, rel)
    
    def find_related(self, concept: str, depth: int = 2) -> list:
        """查找相关概念"""
        if concept not in self.graph:
            return []
        
        return list(nx.ego_graph(self.graph, concept, radius=depth).nodes())
```

---

## 十、总结

### 10.1 核心优势

1. **按需扫描** - 不预先扫描，只在用户提到时触发
2. **扫描记录** - 记录扫描结果，避免重复劳动
3. **客观索引** - 基于实际需求建立，不主观构建
4. **高效性能** - 缓存 + 懒加载，响应迅速
5. **易于实现** - 算法简单，代码量少

### 10.2 适用场景

- AI 助手记忆系统
- 对话上下文管理
- 个人知识管理
- 笔记检索系统

### 10.3 后续优化方向

1. 引入语义搜索
2. 支持多模态记忆
3. 智能概念提取
4. 概念关系图谱

---

**文档状态**：✅ 完成  
**最后更新**：2026-04-01 22:48 (UTC+8)  
**维护者**：艾米（小狐狸助手）🦊
