# LangGraph工作流编排创建标准模板

这是一个通用的LangGraph工作流编排创建指导模板，适用于任何Django + LangGraph项目。基于最佳实践和成功实现经验，提供完整的工作流编排开发指导。

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
- `[workflow_name]` → 工作流名称（如：speech_processing_workflow）

### 项目适配检查清单
- [ ] 确认项目使用Django + LangGraph架构
- [ ] 确认基础组件已实现（State、BaseNode、Checkpoint）
- [ ] 确认所有节点类已实现
- [ ] 确认Redis已配置用于checkpoint存储
- [ ] 确认工作流执行函数已定义

## 📝 代码生成规范

**重要提示**：请严格遵循项目中的Python代码规范标准。详细规范请参考：`python_code_standards.md`

### 关键要求摘要
- 所有代码和注释必须使用英文
- 禁止行内注释，注释必须在代码上方
- 遵循PEP 8规范，每行不超过79字符
- 使用正确的导入顺序和文档字符串格式

## 🏗️ 核心架构设计原则

### 1. StateGraph定义设计模式

#### 工作流图创建函数
```python
"""
LangGraph StateGraph definition for [功能] workflow.

This module defines the complete workflow graph with proper node
connections, checkpoint management, and execution flow.
"""

import logging
from functools import lru_cache
from typing import Dict, Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.redis import RedisSaver

from [your_app].agents.[功能]_state import [StateName]
from [your_app].agents.checkpoint_manager import create_checkpointer
from [your_app].agents.nodes.workflow_prepare import WorkflowPrepareNode
from [your_app].agents.nodes.[node1] import [Node1Class]
from [your_app].agents.nodes.[node2] import [Node2Class]
from [your_app].agents.nodes.[node3] import [Node3Class]
from [your_app].agents.nodes.workflow_finalize import WorkflowFinalizeNode

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def create_[功能]_graph():
    """
    Create and compile the [功能] processing graph.

    This function creates a StateGraph with the following structure:
    START → WorkflowPrepareNode → [Node1] → [Node2] → [Node3] → WorkflowFinalizeNode → END

    The graph is cached using lru_cache to avoid recreating it on each call.

    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Creating [功能] processing graph")

    # Create the StateGraph with [StateName] as the state type
    workflow = StateGraph([StateName])

    # Add nodes to the graph
    workflow.add_node("workflow_prepare_node", WorkflowPrepareNode())
    workflow.add_node("[node1_name]", [Node1Class]())
    workflow.add_node("[node2_name]", [Node2Class]())
    workflow.add_node("[node3_name]", [Node3Class]())
    workflow.add_node("workflow_finalize_node", WorkflowFinalizeNode())

    # Define the execution flow
    workflow.add_edge(START, "workflow_prepare_node")
    workflow.add_edge("workflow_prepare_node", "[node1_name]")
    workflow.add_edge("[node1_name]", "[node2_name]")
    workflow.add_edge("[node2_name]", "[node3_name]")
    workflow.add_edge("[node3_name]", "workflow_finalize_node")
    workflow.add_edge("workflow_finalize_node", END)

    # Compile the graph with Redis checkpointer
    graph = workflow.compile(checkpointer=create_checkpointer())

    logger.info("Successfully created [功能] processing graph")
    return graph
```

### 2. 工作流执行函数设计模式

#### 主编排器函数
```python
def execute_[功能]_workflow(
    [primary_id]: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Execute the complete [功能] processing workflow.

    This function orchestrates the entire [功能] processing workflow:
    1. WorkflowPrepareNode: Database pre-read + status update to PROCESSING
    2. [Node1]: [Node1功能描述]
    3. [Node2]: [Node2功能描述]
    4. [Node3]: [Node3功能描述]
    5. WorkflowFinalizeNode: Data batch write + status update to SUCCESS/FAILED

    WORKFLOW EXECUTION FLOW
    =======================

    [前一步状态] → [WorkflowPrepareNode] → [PROCESSING状态]
                        ↓
                [[Node1]] → [Node1结果]
                        ↓
                [[Node2]] → [Node2结果]
                        ↓
                [[Node3]] → [Node3结果]
                        ↓
                [WorkflowFinalizeNode] → [SUCCESS/FAILED状态]

    NODE EXECUTION ORDER
    ====================

    1. WorkflowPrepareNode: Database pre-read + status update
    2. [Node1]: [Node1功能描述] - [依赖关系说明]
    3. [Node2]: [Node2功能描述] - [依赖关系说明]
    4. [Node3]: [Node3功能描述] - [依赖关系说明]
    5. WorkflowFinalizeNode: Data batch write + status update

    Args:
        [primary_id] (str): ID of the [primary_entity] to process
        force (bool): Whether to force processing regardless of current status.
                     When True, skips status checks and allows reprocessing
                     even if the content already exists.

    Returns:
        Dict[str, Any]: Execution result containing:
            - success: bool - Whether the workflow completed successfully
            - [primary_id]: str - The processed [primary_entity] ID
            - error: str | None - Error message if failed
            - execution_time: float - Total execution time in seconds
    """
    import time
    start_time = time.time()

    try:
        # Validate that the [primary_entity] exists
        [primary_entity] = [YourModel].objects.get(id=[primary_id])
        if not [primary_entity]:
            raise Exception(
                f"[PrimaryEntity] with id {[primary_id]} not found")

        logger.info(f"[Workflow] Starting [功能] workflow for [primary_entity]: "
                    f"{[primary_id]}, force: {force}")

        # Create initial state
        initial_state = {
            "id": [primary_id],
            "user_id": [primary_entity].user_id,
            "display_name": [primary_entity].display_name,
            "file_size": [primary_entity].file_size,
            "file_md5": [primary_entity].file_md5,
            "duration": [primary_entity].duration,
            "format": [primary_entity].format,
            "storage_path": [primary_entity].storage_path,
            "storage_bucket": [primary_entity].storage_bucket,
            "sample_rate": [primary_entity].sample_rate,
            "channels": [primary_entity].channels,
            "bit_rate": [primary_entity].bit_rate,
            "asr_languages": [primary_entity].asr_languages,
            "llm_language": [primary_entity].llm_language,
            "scene": [primary_entity].scene,
            "force": force,
            "node_errors": {}
        }

        # Get the compiled graph
        graph = create_[功能]_graph()

        # Execute the workflow
        result = graph.invoke(initial_state)

        # Check final state
        if result.get("node_errors"):
            error_messages = []
            for node_name, error in result["node_errors"].items():
                error_messages.append(f"{node_name}: {error['error_message']}")

            execution_time = time.time() - start_time
            logger.error(f"[Workflow] [功能] workflow failed for {[primary_id]}: "
                        f"{'; '.join(error_messages)}")

            return {
                "success": False,
                "[primary_id]": [primary_id],
                "error": "; ".join(error_messages),
                "execution_time": execution_time
            }

        execution_time = time.time() - start_time
        logger.info(f"[Workflow] [功能] workflow completed successfully for "
                    f"{[primary_id]} in {execution_time:.2f}s")

        return {
            "success": True,
            "[primary_id]": [primary_id],
            "error": None,
            "execution_time": execution_time
        }

    except [YourModel].DoesNotExist:
        execution_time = time.time() - start_time
        logger.error(f"[Workflow] [PrimaryEntity] {[primary_id]} not found")
        return {
            "success": False,
            "[primary_id]": [primary_id],
            "error": f"[PrimaryEntity] {[primary_id]} not found",
            "execution_time": execution_time
        }
    except Exception as exc:
        execution_time = time.time() - start_time
        logger.error(f"[Workflow] Failed to execute [功能] workflow "
                     f"for {[primary_id]}: {exc}")
        return {
            "success": False,
            "[primary_id]": [primary_id],
            "error": str(exc),
            "execution_time": execution_time
        }
```

### 3. 工作流配置设计模式

#### 工作流配置管理
```python
"""
Workflow configuration management for [功能] processing.

This module provides configuration management for the [功能] workflow,
including node configurations, execution parameters, and monitoring settings.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class [功能]WorkflowConfig:
    """
    Configuration management for [功能] workflow.

    This class provides centralized configuration management for the
    [功能] workflow, including node settings, execution parameters,
    and monitoring configurations.
    """

    def __init__(self):
        """
        Initialize the workflow configuration.
        """
        self.node_configs = {
            "workflow_prepare_node": {
                "timeout": 30,
                "retry_count": 3,
                "log_level": "INFO"
            },
            "[node1_name]": {
                "timeout": 300,
                "retry_count": 2,
                "log_level": "INFO"
            },
            "[node2_name]": {
                "timeout": 300,
                "retry_count": 2,
                "log_level": "INFO"
            },
            "[node3_name]": {
                "timeout": 300,
                "retry_count": 2,
                "log_level": "INFO"
            },
            "workflow_finalize_node": {
                "timeout": 30,
                "retry_count": 3,
                "log_level": "INFO"
            }
        }

    def get_node_config(self, node_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific node.

        Args:
            node_name: Name of the node

        Returns:
            Dictionary containing node configuration
        """
        return self.node_configs.get(node_name, {})

    def update_node_config(
        self,
        node_name: str,
        config: Dict[str, Any]
    ) -> None:
        """
        Update configuration for a specific node.

        Args:
            node_name: Name of the node
            config: New configuration dictionary
        """
        if node_name in self.node_configs:
            self.node_configs[node_name].update(config)
            logger.info(f"Updated configuration for node: {node_name}")
        else:
            logger.warning(f"Node {node_name} not found in configuration")

    def get_execution_config(self) -> Dict[str, Any]:
        """
        Get execution configuration for the workflow.

        Returns:
            Dictionary containing execution configuration
        """
        return {
            "max_execution_time": 1800,  # 30 minutes
            "checkpoint_interval": 60,   # 1 minute
            "error_retry_delay": 5,      # 5 seconds
            "monitoring_enabled": True
        }


# Global workflow configuration instance
workflow_config = [功能]WorkflowConfig()
```

## 🔄 工作流编排设计原则

### 1. 节点连接设计

**核心原则**：
- 使用StateGraph进行节点编排
- 明确的节点连接关系
- 支持从任意节点重新开始
- 使用Redis checkpoint持久化状态

**节点连接模式**：
```python
# 定义执行流程
workflow.add_edge(START, "workflow_prepare_node")
workflow.add_edge("workflow_prepare_node", "[node1_name]")
workflow.add_edge("[node1_name]", "[node2_name]")
workflow.add_edge("[node2_name]", "[node3_name]")
workflow.add_edge("[node3_name]", "workflow_finalize_node")
workflow.add_edge("workflow_finalize_node", END)
```

### 2. 状态管理设计

**状态传递模式**：
- 使用[StateName]作为状态类型
- 状态在节点间自动传递
- 支持状态持久化和恢复
- 统一的错误处理机制

**初始状态创建**：
```python
# 创建初始状态
initial_state = {
    "id": [primary_id],
    "user_id": [primary_entity].user_id,
    # ... 其他字段
    "force": force,
    "node_errors": {}
}
```

### 3. 执行流程设计

**执行流程模式**：
1. **WorkflowPrepareNode**：数据库预读取 + 状态更新
2. **中间节点**：纯State操作，无数据库交互
3. **WorkflowFinalizeNode**：数据批量写入 + 状态更新

**Force支持**：
- 通过State传递force标志
- 首尾节点处理force状态
- 中间节点专注业务逻辑

## 📝 日志输出标准化

### 1. 统一日志标签
```python
# 使用 [Workflow] 作为统一标签
logger.info(f"[Workflow] Starting [功能] workflow for [primary_entity]: "
            f"{[primary_id]}, force: {force}")

logger.info(f"[Workflow] [功能] workflow completed successfully for "
            f"{[primary_id]} in {execution_time:.2f}s")

logger.error(f"[Workflow] [功能] workflow failed for {[primary_id]}: "
            f"{error_message}")
```

### 2. 行长度控制（≤79字符）
```python
# 正确的分行方式
logger.info(f"[Workflow] Starting [功能] workflow for [primary_entity]: "
            f"{[primary_id]}, force: {force}")

# 在逻辑断点处分行，保持语义完整
logger.info(f"[Workflow] [功能] workflow completed successfully for "
            f"{[primary_id]} in {execution_time:.2f}s")
```

### 3. 日志级别使用
- **info**: 正常流程节点和重要状态变化
- **error**: 错误情况和异常处理
- **debug**: 详细的执行信息和配置信息

## 🔧 工作流编排最佳实践

### 1. 图创建最佳实践
```python
# 使用lru_cache缓存编译后的图
@lru_cache(maxsize=1)
def create_[功能]_graph():
    workflow = StateGraph([StateName])
    # ... 添加节点和边
    return workflow.compile(checkpointer=create_checkpointer())
```

### 2. 节点连接最佳实践
```python
# 明确的节点连接关系
workflow.add_edge(START, "workflow_prepare_node")
workflow.add_edge("workflow_prepare_node", "[node1_name]")
# ... 其他连接
workflow.add_edge("workflow_finalize_node", END)
```

### 3. 状态管理最佳实践
```python
# 创建完整的初始状态
initial_state = {
    "id": [primary_id],
    "user_id": [primary_entity].user_id,
    # ... 所有必要字段
    "force": force,
    "node_errors": {}
}
```

## 🛡️ 错误处理模式

### 1. 工作流错误处理
```python
try:
    # 工作流执行
    result = graph.invoke(initial_state)

    # 检查最终状态
    if result.get("node_errors"):
        # 处理节点错误
        pass

except Exception as exc:
    # 处理执行错误
    logger.error(f"[Workflow] Failed to execute [功能] workflow: {exc}")
```

### 2. 节点错误检查
```python
# 检查节点错误
if result.get("node_errors"):
    error_messages = []
    for node_name, error in result["node_errors"].items():
        error_messages.append(f"{node_name}: {error['error_message']}")

    return {
        "success": False,
        "error": "; ".join(error_messages)
    }
```

### 3. 实体验证错误处理
```python
try:
    [primary_entity] = [YourModel].objects.get(id=[primary_id])
    if not [primary_entity]:
        raise Exception(f"[PrimaryEntity] with id {[primary_id]} not found")
except [YourModel].DoesNotExist:
    logger.error(f"[Workflow] [PrimaryEntity] {[primary_id]} not found")
    return {"success": False, "error": f"[PrimaryEntity] {[primary_id]} not found"}
```

## 📊 调试和监控支持

### 1. 工作流执行监控
```python
# 记录执行时间
start_time = time.time()
# ... 执行工作流
execution_time = time.time() - start_time

logger.info(f"[Workflow] [功能] workflow completed successfully for "
            f"{[primary_id]} in {execution_time:.2f}s")
```

### 2. 节点执行监控
```python
# 记录节点执行信息
logger.info(f"[Workflow] Starting [功能] workflow for [primary_entity]: "
            f"{[primary_id]}, force: {force}")
```

### 3. 错误监控
```python
# 记录错误信息
logger.error(f"[Workflow] [功能] workflow failed for {[primary_id]}: "
            f"{error_message}")
```

## 📋 具体实现检查清单

### ✅ 必须实现的结构
- [ ] 正确的StateGraph定义
- [ ] 正确的节点连接关系
- [ ] 正确的工作流执行函数
- [ ] 正确的配置管理
- [ ] 完整的文档字符串

### ✅ 图创建检查
- [ ] 使用lru_cache缓存编译后的图
- [ ] 正确的节点添加顺序
- [ ] 正确的边连接关系
- [ ] 正确的checkpointer配置

### ✅ 工作流执行检查
- [ ] 正确的初始状态创建
- [ ] 正确的实体验证
- [ ] 正确的错误处理
- [ ] 正确的执行结果检查

### ✅ 日志标准化检查
- [ ] 所有logger使用[Workflow]标签
- [ ] 每行logger输出≤79字符
- [ ] 在逻辑断点处合理分行
- [ ] 保持语义完整性

### ✅ 代码规范检查
- [ ] 所有代码使用英文
- [ ] 所有注释使用英文
- [ ] 禁止行内注释
- [ ] 遵循PEP 8规范
- [ ] 每行不超过79字符

## 🎯 关键实现细节

### 1. 图创建模式
```python
# 使用lru_cache缓存编译后的图
@lru_cache(maxsize=1)
def create_[功能]_graph():
    workflow = StateGraph([StateName])
    # ... 添加节点和边
    return workflow.compile(checkpointer=create_checkpointer())
```

### 2. 节点连接模式
```python
# 明确的节点连接关系
workflow.add_edge(START, "workflow_prepare_node")
workflow.add_edge("workflow_prepare_node", "[node1_name]")
# ... 其他连接
workflow.add_edge("workflow_finalize_node", END)
```

### 3. 状态管理模式
```python
# 创建完整的初始状态
initial_state = {
    "id": [primary_id],
    "user_id": [primary_entity].user_id,
    # ... 所有必要字段
    "force": force,
    "node_errors": {}
}
```

## 🚨 常见陷阱和避免方法

### ❌ 避免的反模式
1. **缺少图缓存** - 应该使用lru_cache缓存编译后的图
2. **缺少实体验证** - 应该验证[primary_entity]存在
3. **硬编码日志标签** - 应该使用[Workflow]
4. **缺少错误检查** - 应该检查最终状态中的错误
5. **使用行内注释** - 应该将注释放在代码上方
6. **使用中文注释** - 所有注释必须使用英文

### ✅ 推荐的最佳实践
1. **使用lru_cache** - 避免重复编译图
2. **完整的文档字符串** - 包含工作流和执行顺序
3. **清晰的节点连接** - 每个连接都有明确的目的
4. **统一的日志格式** - 便于监控和调试
5. **适当的错误处理** - 确保异常正确传播
6. **英文代码和注释** - 保持代码国际化
7. **遵循PEP 8规范** - 保持代码一致性

## 📝 使用指南

### 快速开始
1. **复制此模板**作为工作流编排的起始点
2. **替换占位符**：根据占位符替换指南更新所有占位符
3. **调整节点连接**：根据具体需求修改节点连接关系
4. **更新工作流执行**：根据实际需求修改执行逻辑
5. **测试工作流**：确保工作流能正确执行和传递状态
6. **验证日志格式**：确保所有日志使用[Workflow]且≤79字符

### 常见使用场景
- **语音处理工作流**：语音识别 → 分段处理 → 总结生成
- **邮件处理工作流**：邮件解析 → 内容分析 → 总结生成
- **数据分析工作流**：数据清洗 → 数据转换 → 结果生成
- **文件处理工作流**：文件上传 → 格式转换 → 结果存储

### 高级配置选项
- **条件执行**：根据参数决定是否执行某些节点
- **并行处理**：使用并行节点实现并行处理
- **错误重试**：配置节点重试策略和错误处理
- **监控集成**：添加工作流执行监控和告警
- **性能优化**：使用缓存和批量操作优化性能

这个模板基于LangGraph最佳实践和成功实现经验，包含了所有关键的工作流编排设计模式和实现细节，适用于任何Django + LangGraph项目。
