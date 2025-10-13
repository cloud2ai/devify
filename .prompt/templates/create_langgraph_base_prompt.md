# LangGraph基础组件创建标准模板

## 📂 前提条件

用户应该已经将 `speechtotext/agents/` 目录整体复制到新位置.

## 🎯 AI的任务

在用户提供的agents目录中，修改以下文件以适配新业务。

---

## 第一步：自动查找agents目录和模型文件

**AI执行步骤**：

1. **查找agents目录**
   - 搜索包含 `speechtotext_state.py` 的目录
   - 排除 `speechtotext/agents/`（这是参考实现）
   - 如果找到，确认该目录包含：`nodes/base_node.py`, `checkpoint_manager.py`, `speechtotext_state.py`

2. **查找Django模型文件**
   - 在agents目录的同级或上级查找 `models.py`
   - 例如：如果agents在 `emailprocessing/agents/`，则查找 `emailprocessing/models.py`

3. **如果找不到，询问用户**：
   ```
   未找到agents目录或模型文件，请提供：
   1. agents目录路径（如：emailprocessing/agents/）
   2. Django模型文件路径（如：emailprocessing/models.py）
   ```

4. **确认找到的目录结构**：
   ```
   找到agents目录：[your_app]/agents/
   包含文件：
   ├── nodes/base_node.py ✓
   ├── checkpoint_manager.py ✓
   ├── speechtotext_state.py ✓
   └── workflow.py ✓

   找到模型文件：[your_app]/models.py ✓

   继续？
   ```

---

## 第二步：分析Django模型（独立任务）

**AI执行步骤**：

1. 读取用户提供的模型文件
2. 识别主实体模型类
3. 提取模型字段及类型
4. 向用户确认

**AI输出示例**：

```
我读取了你的模型文件，找到以下模型：

模型类名：Email
主键：id (UUID)
字段列表：
  - subject: CharField (可为空)
  - sender: EmailField
  - recipient: EmailField
  - body: TextField (可为空)
  - received_at: DateTimeField
  - status: CharField (choices)

请确认：
1. 这是否是工作流的主实体模型？
2. 以上哪些字段需要在State中使用？
3. 工作流会产生哪些结果字段？（如：sentiment, classification, entities）
```

**如果无法读取模型**，AI应该询问：
```
请提供以下信息：
1. Django模型类名（如：Email）
2. 主键字段名和类型（如：id: UUID）
3. 需要在State中使用的模型字段列表（字段名和类型）
4. 工作流会产生的结果字段列表（字段名和类型）
```

---

## 第三步：收集命名信息

**AI询问用户**：

| 信息项 | 用途 | 示例 |
|--------|------|------|
| 功能名称 | 文件命名 | `email_processing` |
| State类名 | 类命名 | `EmailState` |
| 主实体变量名 | 函数参数命名 | `email_id` |

---

## 第四步：逐个修改文件

### 任务1：重命名并修改 `speechtotext_state.py`

**步骤1.1：重命名文件**
- 从：`speechtotext_state.py`
- 到：`[feature]_state.py`（如 `email_processing_state.py`）

**步骤1.2：修改内容**

| 位置 | 修改说明 |
|------|---------|
| **State类名** | `AudioFileState` → 用户提供的State类名 |
| **核心字段部分** | 删除所有AudioFile模型字段，替换为用户模型字段（基于第二步分析） |
| **结果字段部分** | 删除所有audio结果字段，替换为用户提供的结果字段 |
| **固定字段** | `error_message`, `node_errors`, `force` **保持不变** |
| **create函数名** | `create_audio_file_state` → `create_[feature]_state` |
| **create函数参数** | `audio_file_id: str` → `[entity]_id: str` |
| **create函数体** | 根据新的State字段调整初始化 |
| **辅助函数类型注解** | 所有 `AudioFileState` → 新的State类名 |

**字段替换对照**：

```python
# === 原State结构 ===
class AudioFileState(TypedDict, total=False):
    # 核心字段（删除这部分）
    id: str
    user_id: str
    display_name: str | None
    file_size: int
    duration: float | None
    format: str
    storage_path: str | None

    # 结果字段（删除这部分）
    segments: List[Dict[str, Any]] | None
    transcription: str | None
    summary: str | None
    translation: str | None

    # 固定字段（保持不变）
    error_message: str | None
    node_errors: Dict[str, List[NodeError]] | None
    force: bool | None

# === 新State结构（示例：EmailState）===
class EmailState(TypedDict, total=False):
    # 核心字段（基于Django模型）
    id: str
    user_id: str
    subject: str | None
    sender: str | None
    recipient: str | None
    body: str | None
    received_at: str | None
    status: str | None

    # 结果字段（用户提供）
    sentiment: str | None
    classification: str | None
    entities: List[Dict[str, Any]] | None

    # 固定字段（保持不变）
    error_message: str | None
    node_errors: Dict[str, List[NodeError]] | None
    force: bool | None
```

**create函数修改**：

```python
# 原函数
def create_audio_file_state(
    audio_file_id: str,
    user_id: str,
    force: bool = False
) -> AudioFileState:
    return {
        "id": audio_file_id,
        "user_id": user_id,
        "display_name": None,
        "file_size": 0,
        # ... 其他AudioFile字段

        "segments": None,
        "transcription": None,
        # ... 其他结果字段

        "error_message": None,
        "node_errors": {},
        "force": force,
    }

# 新函数（基于模型字段调整）
def create_email_processing_state(
    email_id: str,
    user_id: str,
    force: bool = False
) -> EmailState:
    return {
        "id": email_id,
        "user_id": user_id,
        "subject": None,
        "sender": None,
        # ... 基于Django模型的字段

        "sentiment": None,
        "classification": None,
        # ... 用户提供的结果字段

        "error_message": None,
        "node_errors": {},
        "force": force,
    }
```

**不修改的内容**：
- `NodeError` 类定义
- 以下8个辅助函数的**实现逻辑**（只改类型注解）：
  - `set_global_error`
  - `clear_global_error`
  - `add_node_error`
  - `get_node_errors_by_name`
  - `has_node_errors`
  - `clear_node_errors`
  - `clear_node_errors_by_name`
  - `get_all_node_names_with_errors`

**验证**：
- [ ] 文件已重命名
- [ ] State类名已替换
- [ ] 核心字段匹配Django模型
- [ ] 结果字段已添加
- [ ] 固定字段未被修改
- [ ] create函数名和参数已更新
- [ ] create函数体字段初始化正确
- [ ] 所有辅助函数类型注解已更新
- [ ] 辅助函数实现逻辑未改变

---

### 任务2：修改 `nodes/base_node.py`

**修改导入语句**：

```python
# 原导入
from speechtotext.agents.speechtotext_state import (
    AudioFileState,
    add_node_error,
    get_node_errors_by_name,
    has_node_errors
)

# 新导入
from [your_app].agents.[feature]_state import (
    [StateName],
    add_node_error,
    get_node_errors_by_name,
    has_node_errors
)
```

**修改类型注解**：

在以下6个方法中，将所有 `AudioFileState` 替换为新的State类名：
- `__call__(self, state: [StateName]) -> [StateName]:`
- `can_enter_node(self, state: [StateName]) -> bool:`
- `before_processing(self, state: [StateName]) -> [StateName]:`
- `execute_processing(self, state: [StateName]) -> [StateName]:`
- `after_processing(self, state: [StateName]) -> [StateName]:`
- `_handle_error(self, error: Exception, state: [StateName]) -> [StateName]:`

**不修改**：
- `BaseLangGraphNode` 类的所有实现逻辑
- 所有方法的代码内容
- 文档字符串

**验证**：
- [ ] 导入语句已更新
- [ ] 所有类型注解已替换为新State类名
- [ ] 类实现逻辑完全未改动

---

### 任务3：确认 `checkpoint_manager.py`

**无需修改**，确认文件存在即可。

**验证**：
- [ ] 文件存在且内容完整

---

## 第五步：完成检查

**文件检查**：
- [ ] `[feature]_state.py` 已创建
- [ ] `nodes/base_node.py` 已修改
- [ ] `checkpoint_manager.py` 存在

**代码质量检查**：
- [ ] 所有类名、函数名一致
- [ ] 类型注解统一
- [ ] 导入语句正确
- [ ] State字段与Django模型匹配
- [ ] 固定字段（error_message, node_errors, force）未被修改
- [ ] 遵循PEP 8规范（每行≤73字符）
- [ ] 注释使用英文且在代码上方

---

## 📋 AI工作流程

```
1. 自动查找agents目录和模型文件
   - 搜索包含 speechtotext_state.py 的目录（排除参考实现）
   - 查找对应的 models.py
   - 找不到时询问用户
2. 读取并分析Django模型（独立任务）
   - 提取模型类名、字段、类型
   - 向用户确认需要的字段
3. 收集命名信息（功能名、State类名等）
4. 展示修改计划（列出所有替换点）
5. 用户确认后，执行3个任务：
   - 任务1：重命名并修改 speechtotext_state.py
   - 任务2：修改 nodes/base_node.py
   - 任务3：确认 checkpoint_manager.py
6. 执行完成检查
7. 提示后续步骤
```

---

## 🔄 完成后提示

```
✅ 基础组件修改完成！

已修改文件：
- [your_app]/agents/[feature]_state.py
- [your_app]/agents/nodes/base_node.py
- [your_app]/agents/checkpoint_manager.py（已确认）

接下来使用：create_langgraph_node_prompt.md
需要修改：
1. nodes/workflow_prepare.py（首节点）
2. nodes/workflow_finalize.py（尾节点）
3. 创建业务节点（可选）

需要继续修改节点吗？
```

---

## 📌 关键原则

1. **基于模型定义**：State字段必须基于实际的Django模型，不要猜测
2. **独立任务**：如果无法读取模型，将"提供模型信息"作为独立任务交给用户
3. **精确替换**：按照模型字段精确替换，不改变逻辑
4. **保护固定字段**：error_message, node_errors, force 绝对不能修改
5. **验证严格**：每个任务后执行验证清单
