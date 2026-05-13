# Threadline 工作流进度上报打点逻辑

## 概述

Threadline 工作流使用基于百分比的进度跟踪系统，将整个工作流分为 7 个主要阶段（stage），每个阶段根据实际工作量动态分配进度百分比。

## 工作流阶段（WORKFLOW_STAGES）

当前工作流包含以下 7 个阶段：

```python
WORKFLOW_STAGES = (
    "prepare",    # 准备阶段
    "credits",    # 积分检查
    "images",     # 图片处理
    "llm",        # LLM 文本处理
    "summary",    # 摘要生成
    "metadata",   # 元数据提取
    "finalize",   # 最终化
)
```

**注意：** `"issue"` 阶段已被移除（2026-05-11），issue 处理已迁移到 relay 项目。

## 进度计算机制

### 1. 单位（Units）分配

每个阶段根据实际需要处理的内容分配"单位"：

- **prepare**: 固定 1 单位
- **credits**: 固定 1 单位
- **images**: 根据需要处理的图片数量（每张图片 1 单位）
- **llm**: 如果有文本内容需要处理则 1 单位，否则 0
- **summary**: 根据需要生成的内容（title + data，最多 2 单位）
- **metadata**: 如果需要提取元数据则 1 单位，否则 0
- **finalize**: 固定 1 单位

### 2. 百分比计算

总进度 0-100% 根据各阶段的单位比例动态分配：

```python
# 例如：如果有 3 张图片需要处理
units = {
    "prepare": 1,
    "credits": 1,
    "images": 3,    # 3 张图片
    "llm": 1,
    "summary": 2,   # title + data
    "metadata": 1,
    "finalize": 1,
}
# 总单位 = 10

# 百分比分配（大约）：
# prepare:  10%  (1/10)
# credits:  10%  (1/10)
# images:   30%  (3/10)
# llm:      10%  (1/10)
# summary:  20%  (2/10)
# metadata: 10%  (1/10)
# finalize: 10%  (1/10)
```

### 3. 阶段内进度（ratio）

每个阶段内部可以上报多个进度点，使用 `ratio` (0.0-1.0) 表示阶段内的完成度：

- `ratio=0.0`: 阶段开始
- `ratio=0.5`: 阶段进行到一半
- `ratio=1.0`: 阶段完成

## 各阶段详细打点

### Stage 1: prepare (准备阶段)

**节点**: `WorkflowPrepareNode`  
**progress_stage**: `"prepare"`

**打点位置**:
1. `ratio=0.2` - PREPARE_STATUS: 邮件状态设置为 PROCESSING
2. `ratio=0.45` - PREPARE_PROMPT_CONFIG: Prompt 配置加载完成
3. `ratio=0.6` - PREPARE_ISSUE_CONFIG: Issue 配置加载完成
4. `ratio=0.8` - PREPARE_ATTACHMENTS: 附件数据加载完成
5. `ratio=1.0` - PREPARE_COMPLETE: 准备阶段完成

**前端可见**: 
- 如果总进度 10%，则这个阶段占 0-10%
- ratio=0.2 时显示 2%
- ratio=0.45 时显示 4.5%
- ratio=0.6 时显示 6%
- ratio=0.8 时显示 8%
- ratio=1.0 时显示 10%

---

### Stage 2: credits (积分检查)

**节点**: `CreditsCheckNode`  
**progress_stage**: `"credits"`

**打点位置**:
- 节点开始和结束时自动上报（由 base_node 处理）

**前端可见**: 
- 如果总进度 10%，则这个阶段占 10-20%
- 通常很快完成，用户可能看到进度从 10% 跳到 20%

---

### Stage 3: images (图片处理)

**节点**: `ImageIntentNode`  
**progress_stage**: `"images"`

**打点位置**:
1. 开始处理图片时
2. 每处理完一张图片后上报：`step_index=i, step_total=total_images`
3. 所有图片处理完成

**前端可见**: 
- 如果有 3 张图片，这个阶段可能占 20-50%（30%）
- 第 1 张图片完成：约 30%
- 第 2 张图片完成：约 40%
- 第 3 张图片完成：约 50%

**示例代码**:
```python
self._record_progress_step(
    self.workflow_stage,
    "IMAGE_PROCESSED",
    f"Processed image {i+1}/{total}",
    state=state,
    step_index=i+1,
    step_total=total,
)
```

---

### Stage 4: llm (LLM 文本处理)

**节点**: `LLMEmailNode`  
**progress_stage**: `"llm"`

**打点位置**:
- 节点开始和结束时自动上报（由 base_node 处理）
- LLM 调用前后可能有额外的进度点

**前端可见**: 
- 如果总进度 10%，则这个阶段占 50-60%
- 通常是一次 LLM 调用，进度从 50% 跳到 60%

---

### Stage 5: summary (摘要生成)

**节点**: `SummaryNode`  
**progress_stage**: `"summary"`

**打点位置**:
1. 生成 summary_title 时
2. 生成 summary_data 时
3. 处理 TODOs 时（如果有）
4. 摘要生成完成

**前端可见**: 
- 如果总进度 20%（title + data），则这个阶段占 60-80%
- 生成 title 完成：约 70%
- 生成 data 完成：约 80%

---

### Stage 6: metadata (元数据提取)

**节点**: `MetadataNode`  
**progress_stage**: `"metadata"`

**打点位置**:
- 节点开始和结束时自动上报（由 base_node 处理）

**前端可见**: 
- 如果总进度 10%，则这个阶段占 80-90%
- 通常很快完成，进度从 80% 跳到 90%

---

### Stage 7: finalize (最终化)

**节点**: `WorkflowFinalizeNode`  
**progress_stage**: `"finalize"`

**打点位置**:
- 节点开始和结束时自动上报（由 base_node 处理）
- 数据库同步完成后
- Relay 事件发布后

**前端可见**: 
- 固定占 90-100%
- 完成后进度显示 100%

---

## 进度上报 API

### _record_progress_step()

```python
def _record_progress_step(
    self,
    stage: str,              # 阶段名称（如 "images"）
    action: str,             # 动作名称（如 "IMAGE_PROCESSED"）
    message: str,            # 描述信息
    *,
    state: EmailState,       # 当前状态（包含 progress_plan）
    ratio: float = None,     # 阶段内进度 0.0-1.0
    step_index: int = None,  # 当前步骤索引（从 1 开始）
    step_total: int = None,  # 总步骤数
    level: str = "INFO",     # 日志级别
    **data: Any,            # 额外数据
) -> None:
```

### 使用方式

**方式 1: 使用 ratio**
```python
self._record_progress_step(
    "prepare",
    "PREPARE_STATUS",
    "Email marked as processing",
    state=state,
    ratio=0.2,  # 阶段内 20% 完成
)
```

**方式 2: 使用 step_index/step_total**
```python
self._record_progress_step(
    "images",
    "IMAGE_PROCESSED",
    f"Processed image {i+1}/{total}",
    state=state,
    step_index=i+1,    # 当前是第几张
    step_total=total,  # 总共几张
)
```

---

## 前端进度显示示例

假设一个典型的邮件处理场景：
- 3 张图片需要处理
- 有文本内容需要 LLM 处理
- 需要生成 title 和 data

**单位分配**:
```
prepare:  1 单位
credits:  1 单位
images:   3 单位
llm:      1 单位
summary:  2 单位
metadata: 1 单位
finalize: 1 单位
总计:     10 单位
```

**百分比分配**:
```
prepare:   0% -  10%  (10%)
credits:  10% -  20%  (10%)
images:   20% -  50%  (30%)
llm:      50% -  60%  (10%)
summary:  60% -  80%  (20%)
metadata: 80% -  90%  (10%)
finalize: 90% - 100%  (10%)
```

**前端看到的进度变化**:
```
0%   → 开始
2%   → prepare: 状态设置
4%   → prepare: 配置加载
10%  → prepare 完成
20%  → credits 完成
30%  → images: 第 1 张图片完成
40%  → images: 第 2 张图片完成
50%  → images: 第 3 张图片完成
60%  → llm 完成
70%  → summary: title 生成完成
80%  → summary: data 生成完成
90%  → metadata 完成
100% → finalize 完成，工作流结束
```

---

## 注意事项

1. **动态分配**: 进度百分比是动态计算的，根据实际工作量自动调整
2. **跳过阶段**: 如果某个阶段没有工作（如没有图片），该阶段的单位为 0，不占用进度
3. **错误处理**: 如果某个节点出错，进度会停在当前位置，不会继续增长
4. **并发处理**: 图片处理可能并发进行，但进度上报是顺序的
5. **Issue 阶段已移除**: 从 2026-05-11 开始，issue 阶段不再占用进度

---

## 相关文件

- `agents/progress.py` - 进度计算核心逻辑
- `agents/nodes/base_node.py` - 进度上报基类
- `agents/nodes/workflow_prepare.py` - prepare 阶段实现
- `agents/nodes/image_intent_node.py` - images 阶段实现
- `agents/nodes/llm_email_node.py` - llm 阶段实现
- `agents/nodes/summary_node.py` - summary 阶段实现
- `agents/nodes/metadata_node.py` - metadata 阶段实现
- `agents/nodes/workflow_finalize.py` - finalize 阶段实现

---

## 更新历史

- **2026-05-11**: 移除 `"issue"` 阶段，issue 处理迁移到 relay 项目
- **2026-05-11**: 修复进度计算逻辑，确保百分比准确
