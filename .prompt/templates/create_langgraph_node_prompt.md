# LangGraph节点实现创建标准模板

这是一个通用的LangGraph节点实现创建指导模板，适用于任何Django + LangGraph项目。基于最佳实践和成功实现经验，提供完整的节点开发指导。

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
- `[NodeClass]` → 节点类名（如：SpeechRecognitionNode, EmailProcessingNode）

### 项目适配检查清单
- [ ] 确认项目使用Django + LangGraph架构
- [ ] 确认基础组件已实现（State、BaseNode、Checkpoint）
- [ ] 确认工作流编排已实现
- [ ] 确认节点基类已定义
- [ ] 确认状态枚举已定义

## 📝 代码生成规范

**重要提示**：请严格遵循项目中的Python代码规范标准。详细规范请参考：`python_code_standards.md`

### 关键要求摘要
- 所有代码和注释必须使用英文
- 禁止行内注释，注释必须在代码上方
- 遵循PEP 8规范，每行不超过79字符
- 使用正确的导入顺序和文档字符串格式

## 🏗️ 核心架构设计原则

### 1. 首尾节点设计模式

#### WorkflowPrepareNode（第一个节点）
```python
"""
Workflow Prepare Node for [功能] processing.

This node is responsible for database pre-read and status update to PROCESSING.
It implements the first-and-last node database operations pattern.
"""

import logging
from typing import Dict, Any

from [your_app].agents.base_node import BaseLangGraphNode
from [your_app].agents.[功能]_state import [StateName]
from [your_app].models import [YourModel]

logger = logging.getLogger(__name__)


class WorkflowPrepareNode(BaseLangGraphNode):
    """
    Workflow Prepare Node for [功能] processing.

    This node is responsible for:
    1. Database pre-read of [PrimaryEntity] data
    2. Status update to PROCESSING
    3. Initial state preparation for workflow execution

    This node implements the first-and-last node database operations pattern,
    where only the first and last nodes interact with the database.
    """

    def __init__(self):
        """
        Initialize the WorkflowPrepareNode.
        """
        super().__init__("workflow_prepare_node")

    def before_processing(self, state: [StateName]) -> [StateName]:
        """
        Pre-processing validation and setup.

        This method validates the input state and checks for required
        dependencies before processing begins.

        Args:
            state: Current workflow state

        Returns:
            Updated state after pre-processing
        """
        # Check if there are any previous errors
        if self.has_node_errors(state):
            self.logger.warning("Skipping workflow prepare due to previous errors")
            return state

        # Check if already completed (for idempotency)
        if self.is_already_completed(state):
            self.logger.info("Workflow prepare already completed, skipping")
            return state

        return state

    def execute_processing(self, state: [StateName]) -> [StateName]:
        """
        Core processing logic for workflow preparation.

        This method performs:
        1. Database pre-read of [PrimaryEntity] data
        2. Status update to PROCESSING
        3. State preparation for workflow execution

        Args:
            state: Current workflow state

        Returns:
            Updated state after processing
        """
        try:
            [primary_id] = state["id"]
            force = state.get("force", False)

            self.logger.info(f"Starting workflow prepare for {[primary_id]}, force: {force}")

            # Database pre-read
            [primary_entity] = [YourModel].objects.get(id=[primary_id])

            # Update status to PROCESSING (unless force mode)
            if not force:
                [primary_entity].status = [YourModel].ProcessingStatus.PROCESSING
                [primary_entity].save(update_fields=['status'])

            # Prepare state for workflow execution
            state.update({
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
            })

            self.logger.info(f"Successfully prepared workflow for {[primary_id]}")
            return state

        except [YourModel].DoesNotExist:
            error_msg = f"[PrimaryEntity] {[primary_id]} not found"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Failed to prepare workflow for {[primary_id]}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def after_processing(self, state: [StateName]) -> [StateName]:
        """
        Post-processing cleanup and finalization.

        This method performs any necessary cleanup after processing.

        Args:
            state: Current workflow state

        Returns:
            Updated state after post-processing
        """
        return state

    def is_already_completed(self, state: [StateName]) -> bool:
        """
        Check if the workflow prepare has already completed.

        Args:
            state: Current workflow state

        Returns:
            True if already completed, False otherwise
        """
        # Check if all required fields are already in state
        required_fields = ["user_id", "display_name", "file_size"]
        return all(field in state for field in required_fields)
```

#### WorkflowFinalizeNode（最后一个节点）
```python
"""
Workflow Finalize Node for [功能] processing.

This node is responsible for data batch write and status update to SUCCESS/FAILED.
It implements the first-and-last node database operations pattern.
"""

import logging
from typing import Dict, Any

from [your_app].agents.base_node import BaseLangGraphNode
from [your_app].agents.[功能]_state import [StateName]
from [your_app].models import [YourModel]

logger = logging.getLogger(__name__)


class WorkflowFinalizeNode(BaseLangGraphNode):
    """
    Workflow Finalize Node for [功能] processing.

    This node is responsible for:
    1. Data batch write to database
    2. Status update to SUCCESS/FAILED
    3. Final state cleanup and completion

    This node implements the first-and-last node database operations pattern,
    where only the first and last nodes interact with the database.
    """

    def __init__(self):
        """
        Initialize the WorkflowFinalizeNode.
        """
        super().__init__("workflow_finalize_node")

    def before_processing(self, state: [StateName]) -> [StateName]:
        """
        Pre-processing validation and setup.

        This method validates the input state and checks for required
        dependencies before processing begins.

        Args:
            state: Current workflow state

        Returns:
            Updated state after pre-processing
        """
        # Check if there are any previous errors
        if self.has_node_errors(state):
            self.logger.warning("Skipping workflow finalize due to previous errors")
            return state

        # Check if already completed (for idempotency)
        if self.is_already_completed(state):
            self.logger.info("Workflow finalize already completed, skipping")
            return state

        return state

    def execute_processing(self, state: [StateName]) -> [StateName]:
        """
        Core processing logic for workflow finalization.

        This method performs:
        1. Data batch write to database
        2. Status update to SUCCESS/FAILED
        3. Final state cleanup and completion

        Args:
            state: Current workflow state

        Returns:
            Updated state after processing
        """
        try:
            [primary_id] = state["id"]
            force = state.get("force", False)

            self.logger.info(f"Starting workflow finalize for {[primary_id]}, force: {force}")

            # Get the [primary_entity] from database
            [primary_entity] = [YourModel].objects.get(id=[primary_id])

            # Check if there are any node errors
            if self.has_node_errors(state):
                # Update status to FAILED
                [primary_entity].status = [YourModel].ProcessingStatus.FAILED
                [primary_entity].save(update_fields=['status'])

                self.logger.error(f"Workflow failed for {[primary_id]} due to node errors")
                return state

            # Batch write processing results to database
            self._batch_write_results([primary_entity], state)

            # Update status to SUCCESS
            [primary_entity].status = [YourModel].ProcessingStatus.SUCCESS
            [primary_entity].save(update_fields=['status'])

            self.logger.info(f"Successfully finalized workflow for {[primary_id]}")
            return state

        except [YourModel].DoesNotExist:
            error_msg = f"[PrimaryEntity] {[primary_id]} not found"
            self.logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Failed to finalize workflow for {[primary_id]}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def after_processing(self, state: [StateName]) -> [StateName]:
        """
        Post-processing cleanup and finalization.

        This method performs any necessary cleanup after processing.

        Args:
            state: Current workflow state

        Returns:
            Updated state after post-processing
        """
        return state

    def is_already_completed(self, state: [StateName]) -> bool:
        """
        Check if the workflow finalize has already completed.

        Args:
            state: Current workflow state

        Returns:
            True if already completed, False otherwise
        """
        # Check if the [primary_entity] status is already SUCCESS or FAILED
        try:
            [primary_id] = state["id"]
            [primary_entity] = [YourModel].objects.get(id=[primary_id])
            return [primary_entity].status in [
                [YourModel].ProcessingStatus.SUCCESS,
                [YourModel].ProcessingStatus.FAILED
            ]
        except [YourModel].DoesNotExist:
            return False

    def _batch_write_results(
        self,
        [primary_entity]: [YourModel],
        state: [StateName]
    ) -> None:
        """
        Batch write processing results to database.

        Args:
            [primary_entity]: The [PrimaryEntity] instance to update
            state: Current workflow state
        """
        # Update [primary_entity] with processing results
        update_fields = []

        if "segments" in state and state["segments"] is not None:
            [primary_entity].segments = state["segments"]
            update_fields.append("segments")

        if "segments_total_count" in state and state["segments_total_count"] is not None:
            [primary_entity].segments_total_count = state["segments_total_count"]
            update_fields.append("segments_total_count")

        if "summary" in state and state["summary"] is not None:
            [primary_entity].summary = state["summary"]
            update_fields.append("summary")

        if "translation" in state and state["translation"] is not None:
            [primary_entity].translation = state["translation"]
            update_fields.append("translation")

        # Save the updated [primary_entity]
        if update_fields:
            [primary_entity].save(update_fields=update_fields)
            self.logger.info(f"Updated [primary_entity] {[primary_entity].id} with fields: {update_fields}")
```

### 2. 中间节点设计模式

#### [NodeClass]（中间节点）
```python
"""
[NodeClass] for [功能] processing.

This node is responsible for [节点功能描述].
It implements the middle node pattern with pure State operations.
"""

import logging
from typing import Dict, Any

from [your_app].agents.base_node import BaseLangGraphNode
from [your_app].agents.[功能]_state import [StateName]

logger = logging.getLogger(__name__)


class [NodeClass](BaseLangGraphNode):
    """
    [NodeClass] for [功能] processing.

    This node is responsible for:
    1. [节点功能描述1]
    2. [节点功能描述2]
    3. [节点功能描述3]

    This node implements the middle node pattern, where only pure State
    operations are performed without database interactions.
    """

    def __init__(self):
        """
        Initialize the [NodeClass].
        """
        super().__init__("[node_name]")

    def before_processing(self, state: [StateName]) -> [StateName]:
        """
        Pre-processing validation and setup.

        This method validates the input state and checks for required
        dependencies before processing begins.

        Args:
            state: Current workflow state

        Returns:
            Updated state after pre-processing
        """
        # Check if there are any previous errors
        if self.has_node_errors(state):
            self.logger.warning("Skipping [node_name] due to previous errors")
            return state

        # Check if already completed (for idempotency)
        if self.is_already_completed(state):
            self.logger.info("[node_name] already completed, skipping")
            return state

        # Check for required dependencies
        if not self._check_dependencies(state):
            error_msg = "Missing required dependencies for [node_name]"
            self.logger.error(error_msg)
            raise Exception(error_msg)

        return state

    def execute_processing(self, state: [StateName]) -> [StateName]:
        """
        Core processing logic for [节点功能描述].

        This method performs:
        1. [处理步骤1]
        2. [处理步骤2]
        3. [处理步骤3]

        Args:
            state: Current workflow state

        Returns:
            Updated state after processing
        """
        try:
            [primary_id] = state["id"]
            force = state.get("force", False)

            self.logger.info(f"Starting [node_name] for {[primary_id]}, force: {force}")

            # [处理步骤1]
            result1 = self._process_step1(state)
            state.update(result1)

            # [处理步骤2]
            result2 = self._process_step2(state)
            state.update(result2)

            # [处理步骤3]
            result3 = self._process_step3(state)
            state.update(result3)

            self.logger.info(f"Successfully completed [node_name] for {[primary_id]}")
            return state

        except Exception as e:
            error_msg = f"Failed to process [node_name] for {[primary_id]}: {str(e)}"
            self.logger.error(error_msg)
            raise Exception(error_msg)

    def after_processing(self, state: [StateName]) -> [StateName]:
        """
        Post-processing cleanup and finalization.

        This method performs any necessary cleanup after processing.

        Args:
            state: Current workflow state

        Returns:
            Updated state after post-processing
        """
        return state

    def is_already_completed(self, state: [StateName]) -> bool:
        """
        Check if the [node_name] has already completed.

        Args:
            state: Current workflow state

        Returns:
            True if already completed, False otherwise
        """
        # Check if the expected result is already in state
        return "[expected_result_field]" in state and state["[expected_result_field]"] is not None

    def _check_dependencies(self, state: [StateName]) -> bool:
        """
        Check if all required dependencies are present in state.

        Args:
            state: Current workflow state

        Returns:
            True if all dependencies are present, False otherwise
        """
        required_fields = ["[dependency_field1]", "[dependency_field2]"]
        return all(field in state for field in required_fields)

    def _process_step1(self, state: [StateName]) -> Dict[str, Any]:
        """
        Process step 1: [处理步骤1描述].

        Args:
            state: Current workflow state

        Returns:
            Dictionary containing step 1 results
        """
        # [处理步骤1的具体实现]
        return {
            "[result_field1]": "[result_value1]",
            "[result_field2]": "[result_value2]"
        }

    def _process_step2(self, state: [StateName]) -> Dict[str, Any]:
        """
        Process step 2: [处理步骤2描述].

        Args:
            state: Current workflow state

        Returns:
            Dictionary containing step 2 results
        """
        # [处理步骤2的具体实现]
        return {
            "[result_field3]": "[result_value3]",
            "[result_field4]": "[result_value4]"
        }

    def _process_step3(self, state: [StateName]) -> Dict[str, Any]:
        """
        Process step 3: [处理步骤3描述].

        Args:
            state: Current workflow state

        Returns:
            Dictionary containing step 3 results
        """
        # [处理步骤3的具体实现]
        return {
            "[result_field5]": "[result_value5]",
            "[result_field6]": "[result_value6]"
        }
```

## 🔄 节点设计原则

### 1. 首尾节点设计原则

**核心职责**：
- **WorkflowPrepareNode**：数据库预读取 + 状态更新到PROCESSING
- **WorkflowFinalizeNode**：数据批量写入 + 状态更新到SUCCESS/FAILED

**设计特点**：
- 实现首尾数据库操作模式
- 处理force参数的状态更新
- 负责数据库状态机管理
- 支持幂等性检查

### 2. 中间节点设计原则

**核心职责**：
- 纯LangGraph State操作
- 无数据库交互
- 专注业务逻辑处理
- 支持依赖检查

**设计特点**：
- 实现中间节点模式
- 不关心force参数的状态更新
- 只操作LangGraph State
- 支持幂等性检查

### 3. 节点基类设计原则

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
self.logger.info(f"Starting [node_name] for {[primary_id]}, force: {force}")
self.logger.info(f"Successfully completed [node_name] for {[primary_id]}")
self.logger.error(f"Failed to process [node_name] for {[primary_id]}: {str(e)}")
```

### 2. 行长度控制（≤79字符）
```python
# 正确的分行方式
self.logger.info(f"Starting [node_name] for {[primary_id]}, force: {force}")

# 在逻辑断点处分行，保持语义完整
self.logger.error(f"Failed to process [node_name] for {[primary_id]}: "
                 f"{str(e)}")
```

### 3. 日志级别使用
- **info**: 正常流程节点和重要状态变化
- **warning**: 跳过处理的情况
- **error**: 错误情况和异常处理

## 🔧 节点实现最佳实践

### 1. 首尾节点最佳实践
```python
# 数据库操作集中在首尾节点
def execute_processing(self, state: [StateName]) -> [StateName]:
    # 数据库预读取或批量写入
    [primary_entity] = [YourModel].objects.get(id=[primary_id])

    # 状态更新
    if not force:
        [primary_entity].status = [YourModel].ProcessingStatus.PROCESSING
        [primary_entity].save(update_fields=['status'])
```

### 2. 中间节点最佳实践
```python
# 纯State操作，无数据库交互
def execute_processing(self, state: [StateName]) -> [StateName]:
    # 处理业务逻辑
    result = self._process_business_logic(state)

    # 更新State
    state.update(result)
    return state
```

### 3. 依赖检查最佳实践
```python
# 检查依赖字段
def _check_dependencies(self, state: [StateName]) -> bool:
    required_fields = ["[dependency_field1]", "[dependency_field2]"]
    return all(field in state for field in required_fields)
```

## 🛡️ 错误处理模式

### 1. 节点错误处理
```python
def execute_processing(self, state: [StateName]) -> [StateName]:
    try:
        # 处理逻辑
        pass
    except Exception as e:
        error_msg = f"Failed to process [node_name] for {[primary_id]}: {str(e)}"
        self.logger.error(error_msg)
        raise Exception(error_msg)
```

### 2. 依赖检查错误处理
```python
def before_processing(self, state: [StateName]) -> [StateName]:
    if not self._check_dependencies(state):
        error_msg = "Missing required dependencies for [node_name]"
        self.logger.error(error_msg)
        raise Exception(error_msg)
```

### 3. 幂等性检查
```python
def is_already_completed(self, state: [StateName]) -> bool:
    # 检查是否已完成
    return "[expected_result_field]" in state and state["[expected_result_field]"] is not None
```

## 📊 调试和监控支持

### 1. 节点执行监控
```python
# 记录节点执行信息
self.logger.info(f"Starting [node_name] for {[primary_id]}, force: {force}")

# 记录完成信息
self.logger.info(f"Successfully completed [node_name] for {[primary_id]}")
```

### 2. 错误监控
```python
# 记录错误信息
self.logger.error(f"Failed to process [node_name] for {[primary_id]}: {str(e)}")

# 记录跳过原因
self.logger.warning("Skipping [node_name] due to previous errors")
```

## 📋 具体实现检查清单

### ✅ 必须实现的结构
- [ ] 正确的节点类定义
- [ ] 正确的三阶段处理模式
- [ ] 正确的依赖检查
- [ ] 正确的幂等性检查
- [ ] 完整的文档字符串

### ✅ 首尾节点检查
- [ ] 数据库操作逻辑
- [ ] 状态更新逻辑
- [ ] Force参数处理
- [ ] 批量写入逻辑
- [ ] 错误处理机制

### ✅ 中间节点检查
- [ ] 纯State操作
- [ ] 依赖检查逻辑
- [ ] 业务逻辑处理
- [ ] 结果更新逻辑
- [ ] 错误处理机制

### ✅ 日志标准化检查
- [ ] 所有logger使用节点名称标签
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

### 1. 首尾节点模式
```python
# 数据库操作集中在首尾节点
def execute_processing(self, state: [StateName]) -> [StateName]:
    # 数据库预读取或批量写入
    [primary_entity] = [YourModel].objects.get(id=[primary_id])

    # 状态更新
    if not force:
        [primary_entity].status = [YourModel].ProcessingStatus.PROCESSING
        [primary_entity].save(update_fields=['status'])
```

### 2. 中间节点模式
```python
# 纯State操作，无数据库交互
def execute_processing(self, state: [StateName]) -> [StateName]:
    # 处理业务逻辑
    result = self._process_business_logic(state)
t
    # 更新State
    state.update(result)
    return state
```

### 3. 依赖检查模式
```python
# 检查依赖字段
def _check_dependencies(self, state: [StateName]) -> bool:
    required_fields = ["[dependency_field1]", "[dependency_field2]"]
    return all(field in state for field in required_fields)
```

## 🚨 常见陷阱和避免方法

### ❌ 避免的反模式
1. **中间节点进行数据库操作** - 应该只在首尾节点进行
2. **缺少依赖检查** - 应该检查所有必需的依赖
3. **硬编码日志标签** - 应该使用节点名称
4. **缺少幂等性检查** - 应该支持重复执行
5. **使用行内注释** - 应该将注释放在代码上方
6. **使用中文注释** - 所有注释必须使用英文

### ✅ 推荐的最佳实践
1. **首尾数据库操作模式** - 数据库操作集中在首尾节点
2. **中间纯State操作** - 中间节点只操作State
3. **完整的依赖检查** - 确保所有依赖都存在
4. **统一的错误处理** - 确保异常正确传播
5. **完整的文档字符串** - 便于理解和维护
6. **英文代码和注释** - 保持代码国际化
7. **遵循PEP 8规范** - 保持代码一致性

## 📝 使用指南

### 快速开始
1. **复制此模板**作为节点实现的起始点
2. **替换占位符**：根据占位符替换指南更新所有占位符
3. **选择节点类型**：首尾节点或中间节点
4. **实现业务逻辑**：根据具体需求实现处理逻辑
5. **测试节点**：确保节点能正确执行和更新状态
6. **验证日志格式**：确保所有日志使用节点名称且≤79字符

### 常见使用场景
- **语音识别节点**：语音转文字处理
- **分段处理节点**：文本分段和整理
- **总结生成节点**：内容总结和摘要
- **邮件处理节点**：邮件内容分析
- **数据分析节点**：数据清洗和转换

### 高级配置选项
- **自定义依赖检查**：实现特定的依赖验证逻辑
- **自定义幂等性检查**：实现特定的完成状态检查
- **自定义错误处理**：实现特定的错误处理逻辑
- **性能优化**：使用缓存和批量操作优化性能

这个模板基于LangGraph最佳实践和成功实现经验，包含了所有关键的节点实现设计模式和实现细节，适用于任何Django + LangGraph项目。
