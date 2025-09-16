# LangGraph基础组件创建标准模板

这是一个通用的LangGraph基础组件创建指导模板，适用于任何Django + LangGraph项目。基于最佳实践和成功实现经验，提供完整的基础组件开发指导。

## 🎯 通用配置说明

### 占位符替换指南
在使用此模板时，请将以下占位符替换为实际值：

- `[功能]` → 具体功能名称（如：speech_to_text, email_processing, data_analysis）
- `[primary_id]` → 主要实体的ID参数名（如：audio_file_id, email_id, user_id）
- `[primary_entity]` → 主要实体的变量名（如：audio_file, email, user）
- `[PrimaryEntity]` → 主要实体的类名（如：AudioFile, Email, User）
- `[YourModel]` → 实际的数据模型类名
- `[your_app]` → 实际的Django应用名称
- `[StateName]` → 状态类名（如：AudioFileState, EmailState）
- `[node_name]` → 节点名称（如：speech_recognition_node, email_processing_node）

### 项目适配检查清单
- [ ] 确认项目使用Django + LangGraph架构
- [ ] 确认有合适的数据模型用于状态管理
- [ ] 确认Redis已配置用于checkpoint存储
- [ ] 确认LangGraph依赖已安装
- [ ] 确认状态枚举已定义

## 📝 代码生成规范

**重要提示**：请严格遵循项目中的Python代码规范标准。详细规范请参考：`python_code_standards.md`

### 关键要求摘要
- 所有代码和注释必须使用英文
- 禁止行内注释，注释必须在代码上方
- 遵循PEP 8规范，每行不超过79字符
- 使用正确的导入顺序和文档字符串格式

## 🏗️ 核心架构设计原则

### 1. State定义设计模式

#### [StateName] (TypedDict) 设计
```python
"""
[功能] State definitions for LangGraph workflow management.

This module defines the simplified state structure based on [PrimaryEntity] model,
focusing on storing results rather than complex workflow state management.
"""

from datetime import datetime
from typing import TypedDict, List, Dict, Any


class NodeError(TypedDict):
    """
    Error information for a specific node failure.
    """
    error_message: str
    timestamp: str


class [StateName](TypedDict, total=False):
    """
    Simplified state structure based on [PrimaryEntity] model.

    Focuses on storing results and processing data, excludes workflow
    execution fields. Uses segments array and counters for workflow control.
    """
    # Core [PrimaryEntity] fields (excluding status, timestamps, etc.)
    id: str
    user_id: str
    display_name: str | None
    file_size: int
    file_md5: str
    duration: float | None
    format: str
    storage_path: str | None
    storage_bucket: str | None
    sample_rate: int | None
    channels: int
    bit_rate: int | None
    asr_languages: List[str] | None
    llm_language: str | None
    scene: str | None

    # Processing results
    segments: List[Dict[str, Any]] | None
    segments_total_count: int | None

    # Final results
    summary: str | None
    translation: str | None

    # Workflow control
    force: bool
    node_errors: Dict[str, NodeError]


def add_node_error(
    state: [StateName],
    node_name: str,
    error_message: str
) -> [StateName]:
    """
    Add error information to the state for a specific node.

    Args:
        state: Current state
        node_name: Name of the node that encountered the error
        error_message: Error message to store

    Returns:
        Updated state with error information
    """
    if "node_errors" not in state:
        state["node_errors"] = {}

    state["node_errors"][node_name] = {
        "error_message": error_message,
        "timestamp": datetime.now().isoformat()
    }
    return state


def get_node_errors_by_name(
    state: [StateName],
    node_name: str
) -> List[NodeError]:
    """
    Get all errors for a specific node.

    Args:
        state: Current state
        node_name: Name of the node

    Returns:
        List of errors for the node
    """
    if "node_errors" not in state:
        return []

    node_errors = state["node_errors"].get(node_name, [])
    if isinstance(node_errors, list):
        return node_errors
    return [node_errors] if node_errors else []


def has_node_errors(state: [StateName]) -> bool:
    """
    Check if there are any node errors in the state.

    Args:
        state: Current state

    Returns:
        True if there are errors, False otherwise
    """
    return bool(state.get("node_errors"))
```

### 2. BaseLangGraphNode设计模式

#### 基础节点类设计
```python
"""
Base LangGraph Node implementation.

This module provides the base class for all LangGraph nodes in the
[功能] workflow, ensuring consistent structure, error handling,
and logging.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from [your_app].agents.[功能]_state import (
    [StateName],
    add_node_error,
    get_node_errors_by_name,
    has_node_errors
)

logger = logging.getLogger(__name__)


class BaseLangGraphNode(ABC):
    """
    Base class for all LangGraph nodes in the [功能] workflow.

    This class provides a standardized structure for LangGraph nodes with:
    - Three-phase processing: before_processing, execute_processing, after_processing
    - Consistent error handling and logging based on node_errors
    - Automatic node entry validation based on error states

    Subclasses can implement:
    - before_processing(): Pre-processing validation and setup
    - execute_processing(): Core business logic (required)
    - after_processing(): Post-processing cleanup and finalization
    """

    def __init__(self, node_name: str):
        """
        Initialize the base node.

        Args:
            node_name (str): Name of the node for logging and identification
        """
        self.node_name = node_name
        self.logger = logging.getLogger(f"[{node_name}]")

    def __call__(self, state: [StateName]) -> [StateName]:
        """
        LangGraph Node standard call interface.

        This method orchestrates the three-phase processing:
        1. before_processing: Validation and setup
        2. execute_processing: Core business logic
        3. after_processing: Cleanup and finalization

        Args:
            state: Current workflow state

        Returns:
            Updated state after processing
        """
        try:
            self.logger.info(f"Starting {self.node_name} processing")

            # Phase 1: Pre-processing validation and setup
            state = self.before_processing(state)

            # Phase 2: Core business logic
            state = self.execute_processing(state)

            # Phase 3: Post-processing cleanup and finalization
            state = self.after_processing(state)

            self.logger.info(f"Completed {self.node_name} processing")
            return state

        except Exception as e:
            self.logger.error(f"Error in {self.node_name}: {str(e)}")
            state = add_node_error(state, self.node_name, str(e))
            return state

    def before_processing(self, state: [StateName]) -> [StateName]:
        """
        Pre-processing validation and setup.

        This method is called before execute_processing and should:
        - Validate input state
        - Check for required dependencies
        - Perform any necessary setup

        Args:
            state: Current workflow state

        Returns:
            Updated state after pre-processing
        """
        # Check if there are any previous errors
        if has_node_errors(state):
            self.logger.warning(f"Skipping {self.node_name} due to previous errors")
            return state

        # Check if already completed (for idempotency)
        if self.is_already_completed(state):
            self.logger.info(f"{self.node_name} already completed, skipping")
            return state

        return state

    @abstractmethod
    def execute_processing(self, state: [StateName]) -> [StateName]:
        """
        Core business logic processing.

        This method must be implemented by subclasses and should contain
        the main processing logic for the node.

        Args:
            state: Current workflow state

        Returns:
            Updated state after processing
        """
        pass

    def after_processing(self, state: [StateName]) -> [StateName]:
        """
        Post-processing cleanup and finalization.

        This method is called after execute_processing and should:
        - Clean up any temporary resources
        - Perform any necessary finalization
        - Update state with results

        Args:
            state: Current workflow state

        Returns:
            Updated state after post-processing
        """
        return state

    def is_already_completed(self, state: [StateName]) -> bool:
        """
        Check if the node has already completed its processing.

        This method should be overridden by subclasses to implement
        their specific completion logic.

        Args:
            state: Current workflow state

        Returns:
            True if already completed, False otherwise
        """
        return False
```

### 3. CheckpointManager设计模式

#### Redis Checkpoint管理
```python
"""
Redis Checkpoint Manager for LangGraph workflows.

This module provides checkpoint management functionality for LangGraph
workflows using Redis as the storage backend.
"""

import logging
from typing import Optional, Dict, Any

from langgraph.checkpoint.redis import RedisSaver
from django.conf import settings

logger = logging.getLogger(__name__)


class CheckpointManager:
    """
    Manages Redis checkpoints for LangGraph workflows.

    This class provides a centralized way to create and manage
    Redis checkpoints for LangGraph workflows.
    """

    def __init__(self):
        """
        Initialize the checkpoint manager.
        """
        self.redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
        self.checkpointer = None

    def get_checkpointer(self) -> RedisSaver:
        """
        Get or create a Redis checkpointer.

        Returns:
            RedisSaver instance for checkpoint management
        """
        if self.checkpointer is None:
            try:
                self.checkpointer = RedisSaver.from_url(self.redis_url)
                logger.info("Redis checkpointer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Redis checkpointer: {e}")
                raise

        return self.checkpointer

    def create_checkpoint_config(self) -> Dict[str, Any]:
        """
        Create checkpoint configuration for LangGraph workflows.

        Returns:
            Dictionary containing checkpoint configuration
        """
        return {
            "checkpointer": self.get_checkpointer(),
            "checkpoint_id": "workflow_checkpoint"
        }


# Global checkpoint manager instance
checkpoint_manager = CheckpointManager()


def create_checkpointer() -> RedisSaver:
    """
    Create a Redis checkpointer instance.

    This function provides a convenient way to create checkpointer
    instances for LangGraph workflows.

    Returns:
        RedisSaver instance
    """
    return checkpoint_manager.get_checkpointer()
```

## 🔄 状态管理设计原则

### 1. 状态结构设计

**核心原则**：
- 直接映射数据库模型字段，方便数据加载和存储
- 包含处理结果字段：segments、summary等
- 包含工作流控制字段：force、node_errors等
- 避免过度通用化，按实际需求设计

**状态字段分类**：
```python
# 核心实体字段
id: str
user_id: str
display_name: str | None
# ... 其他模型字段

# 处理结果字段
segments: List[Dict[str, Any]] | None
summary: str | None
# ... 其他结果字段

# 工作流控制字段
force: bool
node_errors: Dict[str, NodeError]
```

### 2. 错误处理设计

**错误信息结构**：
```python
class NodeError(TypedDict):
    error_message: str
    timestamp: str
```

**错误管理函数**：
- `add_node_error()`: 添加节点错误
- `get_node_errors_by_name()`: 获取特定节点错误
- `has_node_errors()`: 检查是否有错误

### 3. 节点基类设计

**三阶段处理模式**：
1. **before_processing()**: 预处理验证和设置
2. **execute_processing()**: 核心业务逻辑（必须实现）
3. **after_processing()**: 后处理清理和完成

**关键特性**：
- 统一的错误处理和日志记录
- 基于node_errors的自动节点入口验证
- 支持幂等性检查
- 标准化的LangGraph节点接口

## 📝 日志输出标准化

### 1. 统一日志标签
```python
# 使用节点名称作为日志标签
self.logger = logging.getLogger(f"[{node_name}]")

# 日志输出示例
self.logger.info(f"Starting {self.node_name} processing")
self.logger.info(f"Completed {self.node_name} processing")
self.logger.error(f"Error in {self.node_name}: {str(e)}")
```

### 2. 行长度控制（≤79字符）
```python
# 正确的分行方式
self.logger.info(f"Starting {self.node_name} processing")

# 在逻辑断点处分行，保持语义完整
self.logger.error(f"Error in {self.node_name}: {str(e)}")
```

### 3. 日志级别使用
- **info**: 正常流程节点和重要状态变化
- **warning**: 跳过处理的情况
- **error**: 错误情况和异常处理

## 🔧 基础组件构建最佳实践

### 1. State定义最佳实践
```python
# 按数据库模型抽象，避免过度通用化
class [StateName](TypedDict, total=False):
    # 直接映射模型字段
    id: str
    user_id: str
    # ... 其他字段

# 包含处理结果字段
segments: List[Dict[str, Any]] | None
summary: str | None

# 包含工作流控制字段
force: bool
node_errors: Dict[str, NodeError]
```

### 2. 节点基类最佳实践
```python
# 三阶段处理模式
def __call__(self, state: [StateName]) -> [StateName]:
    try:
        # Phase 1: Pre-processing
        state = self.before_processing(state)

        # Phase 2: Core business logic
        state = self.execute_processing(state)

        # Phase 3: Post-processing
        state = self.after_processing(state)

        return state
    except Exception as e:
        # 统一错误处理
        state = add_node_error(state, self.node_name, str(e))
        return state
```

### 3. Checkpoint管理最佳实践
```python
# 使用单例模式管理checkpointer
checkpoint_manager = CheckpointManager()

# 提供便捷的创建函数
def create_checkpointer() -> RedisSaver:
    return checkpoint_manager.get_checkpointer()
```

## 🛡️ 错误处理模式

### 1. 节点错误处理
```python
def __call__(self, state: [StateName]) -> [StateName]:
    try:
        # 处理逻辑
        pass
    except Exception as e:
        self.logger.error(f"Error in {self.node_name}: {str(e)}")
        state = add_node_error(state, self.node_name, str(e))
        return state
```

### 2. 状态验证
```python
def before_processing(self, state: [StateName]) -> [StateName]:
    # 检查是否有之前的错误
    if has_node_errors(state):
        self.logger.warning(f"Skipping {self.node_name} due to previous errors")
        return state

    # 检查是否已完成
    if self.is_already_completed(state):
        self.logger.info(f"{self.node_name} already completed, skipping")
        return state

    return state
```

### 3. Checkpoint错误处理
```python
def get_checkpointer(self) -> RedisSaver:
    if self.checkpointer is None:
        try:
            self.checkpointer = RedisSaver.from_url(self.redis_url)
            logger.info("Redis checkpointer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis checkpointer: {e}")
            raise

    return self.checkpointer
```

## 📊 调试和监控支持

### 1. 状态调试
```python
# 记录状态信息
self.logger.debug(f"Current state: {state}")

# 记录处理结果
self.logger.info(f"Processing completed for {self.node_name}")
```

### 2. 错误监控
```python
# 记录错误信息
self.logger.error(f"Error in {self.node_name}: {str(e)}")

# 记录跳过原因
self.logger.warning(f"Skipping {self.node_name} due to previous errors")
```

## 📋 具体实现检查清单

### ✅ 必须实现的结构
- [ ] 正确的State定义（TypedDict）
- [ ] 正确的NodeError定义
- [ ] 完整的错误管理函数
- [ ] 正确的BaseLangGraphNode基类
- [ ] 正确的CheckpointManager类
- [ ] 完整的文档字符串

### ✅ State定义检查
- [ ] 直接映射数据库模型字段
- [ ] 包含处理结果字段
- [ ] 包含工作流控制字段
- [ ] 使用正确的类型注解
- [ ] 避免过度通用化

### ✅ 节点基类检查
- [ ] 三阶段处理模式
- [ ] 统一的错误处理
- [ ] 正确的日志记录
- [ ] 支持幂等性检查
- [ ] 标准化的接口

### ✅ Checkpoint管理检查
- [ ] 正确的Redis配置
- [ ] 单例模式实现
- [ ] 错误处理机制
- [ ] 便捷的创建函数

### ✅ 代码规范检查
- [ ] 所有代码使用英文
- [ ] 所有注释使用英文
- [ ] 禁止行内注释
- [ ] 遵循PEP 8规范
- [ ] 每行不超过79字符

## 🎯 关键实现细节

### 1. State设计模式
```python
# 按数据库模型抽象，避免过度通用化
class [StateName](TypedDict, total=False):
    # 核心字段
    id: str
    user_id: str
    # 处理结果
    segments: List[Dict[str, Any]] | None
    summary: str | None
    # 工作流控制
    force: bool
    node_errors: Dict[str, NodeError]
```

### 2. 节点基类模式
```python
# 三阶段处理模式
def __call__(self, state: [StateName]) -> [StateName]:
    try:
        state = self.before_processing(state)
        state = self.execute_processing(state)
        state = self.after_processing(state)
        return state
    except Exception as e:
        state = add_node_error(state, self.node_name, str(e))
        return state
```

### 3. Checkpoint管理模式
```python
# 单例模式管理checkpointer
class CheckpointManager:
    def __init__(self):
        self.checkpointer = None

    def get_checkpointer(self) -> RedisSaver:
        if self.checkpointer is None:
            self.checkpointer = RedisSaver.from_url(self.redis_url)
        return self.checkpointer
```

## 🚨 常见陷阱和避免方法

### ❌ 避免的反模式
1. **过度通用化的State** - 应该按数据库模型抽象
2. **缺少错误处理** - 应该统一处理异常
3. **硬编码日志标签** - 应该使用节点名称
4. **缺少幂等性检查** - 应该支持重复执行
5. **使用行内注释** - 应该将注释放在代码上方
6. **使用中文注释** - 所有注释必须使用英文

### ✅ 推荐的最佳实践
1. **按模型抽象State** - 避免过度通用化
2. **三阶段处理模式** - 确保处理逻辑清晰
3. **统一的错误处理** - 确保异常正确传播
4. **完整的文档字符串** - 便于理解和维护
5. **英文代码和注释** - 保持代码国际化
6. **遵循PEP 8规范** - 保持代码一致性

## 📝 使用指南

### 快速开始
1. **复制此模板**作为基础组件的起始点
2. **替换占位符**：根据占位符替换指南更新所有占位符
3. **调整State定义**：根据实际数据模型修改State结构
4. **实现节点基类**：根据具体需求实现BaseLangGraphNode
5. **配置Checkpoint**：根据Redis配置调整CheckpointManager
6. **测试基础组件**：确保State、BaseNode、Checkpoint正常工作

### 常见使用场景
- **语音处理工作流**：AudioFileState + 语音识别节点
- **邮件处理工作流**：EmailState + 邮件分析节点
- **数据分析工作流**：DataState + 数据处理节点
- **文件处理工作流**：FileState + 文件转换节点

### 高级配置选项
- **自定义State字段**：根据业务需求添加特定字段
- **自定义错误处理**：实现特定的错误处理逻辑
- **自定义Checkpoint配置**：配置特定的Redis参数
- **性能优化**：使用缓存和批量操作优化性能

这个模板基于LangGraph最佳实践和成功实现经验，包含了所有关键的基础组件设计模式和实现细节，适用于任何Django + LangGraph项目。
