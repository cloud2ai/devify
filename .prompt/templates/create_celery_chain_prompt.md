# Celery Chain Task 创建标准模板

这是一个通用的 Celery 任务链创建指导模板，适用于任何 Django + Celery 项目。基于最佳实践和成功实现经验，提供完整的任务链编排指导。

## 🎯 通用配置说明

### 占位符替换指南
在使用此模板时，请将以下占位符替换为实际值：

- `[功能]` → 具体功能名称（如：email_processing, data_analysis, file_conversion）
- `[primary_id]` → 主要实体的ID参数名（如：email_id, user_id, order_id）
- `[primary_entity]` → 主要实体的变量名（如：email, user, order）
- `[PrimaryEntity]` → 主要实体的类名（如：Email, User, Order）
- `[YourModel]` → 实际的数据模型类名
- `[your_app]` → 实际的Django应用名称
- `[module1]`, `[task1]` 等 → 实际的任务模块和任务名称
- `[步骤1描述]` 等 → 具体的处理步骤描述

### 项目适配检查清单
- [ ] 确认项目使用 Django + Celery 架构
- [ ] 确认有合适的数据模型用于状态管理
- [ ] 确认各个子任务已经实现
- [ ] 确认任务间的依赖关系
- [ ] 确认状态机的状态定义

## 📝 代码生成规范

**重要提示**：请严格遵循项目中的 Python 代码规范标准。详细规范请参考：`python_code_standards.md`

### 关键要求摘要
- 所有代码和注释必须使用英文
- 禁止行内注释，注释必须在代码上方
- 遵循 PEP 8 规范，每行不超过 79 字符
- 使用正确的导入顺序和文档字符串格式

## 🏗️ 核心架构设计原则

### 1. Chain Orchestrator 类结构设计
```python
"""
Chain Orchestrator for [具体功能] Workflow

This module orchestrates the complete [功能] processing chain:
1. [步骤1描述]
2. [步骤2描述]
3. [步骤3描述]
4. [步骤4描述]
5. [步骤5描述]

The chain ensures proper sequencing and error handling.
"""

import logging

from celery import shared_task, chain

# 根据项目结构调整导入路径
from [your_app].models import [YourModel]  # 替换为实际的数据模型
from [your_app].tasks.[module1] import [task1]
from [your_app].tasks.[module2] import [task2]
from [your_app].tasks.[module3] import [task3]
from [your_app].tasks.[module4] import [task4]
from [your_app].tasks.[module5] import [task5]

logger = logging.getLogger(__name__)
```

### 2. 主任务函数设计模式

#### process_[功能]_chain() - 主编排器
```python
@shared_task
def process_[功能]_chain(
    [primary_id]: str, force: bool = False, **kwargs
) -> str:
    """
    Main orchestrator task that creates the complete [功能] processing chain.

    This task creates a chain of all processing steps:
    1. [步骤1详细描述]
    2. [步骤2详细描述]
    3. [步骤3详细描述]
    4. [步骤4详细描述]
    5. [步骤5详细描述]

    STATE MACHINE FLOW
    ==================

    [前一步状态] → [当前步骤处理] → [当前步骤成功]
                        ↓
                [下一步处理] → [下一步成功]
                        ↓
                [再下一步处理] → [再下一步成功]
                        ↓
                [最后步骤处理] → [最后步骤成功] → [完成状态]

    TASK EXECUTION ORDER
    ====================

    1. [任务1名称]: [任务1功能描述]
    2. [任务2名称]: [任务2功能描述]
    3. [任务3名称]: [任务3功能描述]
    4. [任务4名称]: [任务4功能描述]
    5. [任务5名称]: [任务5功能描述]

    Args:
        [primary_id] (str): ID of the [primary_entity] to process
        force (bool): Whether to force processing regardless of current status.
                     When True, skips status checks and allows reprocessing
                     even if the content already exists.
        **kwargs: Additional parameters that can be passed to individual tasks

    Returns:
        str: The [primary_id] for the next task in the chain
    """
    try:
        # Validate that the [primary_entity] exists
        [primary_entity] = [YourModel].objects.get(id=[primary_id])
        if not [primary_entity]:
            raise Exception(
                f"[PrimaryEntity] with id {[primary_id]} not found")

        logger.info(f"[Chain] Starting processing chain for [primary_entity]: "
                    f"{[primary_id]}, force: {force}")

        # Create the processing chain with sequential execution
        # Note: Using .si() (immutable signature) to pass parameters
        processing_chain = chain(
            # Step 1: [步骤1描述] (required first)
            [task1].si([primary_id], force, **kwargs),

            # Step 2: [步骤2描述]
            [task2].si([primary_id], force, **kwargs),

            # Step 3: [步骤3描述]
            [task3].si([primary_id], force, **kwargs),

            # Step 4: [步骤4描述] (needs previous content)
            [task4].si([primary_id], force, **kwargs),

            # Step 5: [步骤5描述] (needs all content)
            [task5].si([primary_id], force, **kwargs)
        )

        # Execute the chain
        result = processing_chain.apply_async()
        logger.info(
            f"[Chain] Processing chain started for [primary_entity]: {[primary_id]}, "
            f"current status: {[primary_entity].status}, force: {force}, "
            f"chain_task_id: {result.id}"
        )

        # Log the chain composition for debugging
        logger.debug(
            f"[Chain] Chain composition for [primary_entity] {[primary_id]}: "
            f"[任务1] -> [任务2] -> [任务3] -> [任务4] -> [任务5]"
        )

        return [primary_id]

    except Exception as exc:
        logger.error(f"[Chain] Failed to start processing chain "
                     f"for {[primary_id]}: {exc}")
        raise
```

## 🔄 状态机流程设计

### 1. 状态流转图设计模式
```python
"""
STATE MACHINE FLOW
==================

[起始状态] → [步骤1处理] → [步骤1成功]
                ↓
        [步骤2处理] → [步骤2成功]
                ↓
        [步骤3处理] → [步骤3成功]
                ↓
        [步骤4处理] → [步骤4成功]
                ↓
        [步骤5处理] → [步骤5成功] → [完成状态]

关键设计原则：
- 每个步骤都有明确的输入状态和输出状态
- 相邻状态机之间允许 SUCCESS 状态直接转换到下一个 SUCCESS 状态
- 每个步骤失败时都有对应的 FAILED 状态用于重试
"""
```

### 2. 任务执行顺序设计
```python
"""
TASK EXECUTION ORDER
====================

1. [任务1名称]: [任务1功能描述] - [依赖关系说明]
2. [任务2名称]: [任务2功能描述] - [依赖关系说明]
3. [任务3名称]: [任务3功能描述] - [依赖关系说明]
4. [任务4名称]: [任务4功能描述] - [依赖关系说明]
5. [任务5名称]: [任务5功能描述] - [依赖关系说明]

依赖关系设计原则：
- 每个任务明确说明其前置依赖
- 使用 "needs previous content" 等描述依赖关系
- 确保任务链的逻辑顺序正确
"""
```

## 📝 日志输出标准化

### 1. 统一日志标签
```python
# 使用 [Chain] 作为统一标签
logger.info(f"[Chain] Starting processing chain for [primary_entity]: "
            f"{[primary_id]}, force: {force}")

logger.info(f"[Chain] Processing chain started for [primary_entity]: {[primary_id]}, "
            f"current status: {[primary_entity].status}, force: {force}, "
            f"chain_task_id: {result.id}")

logger.debug(f"[Chain] Chain composition for [primary_entity] {[primary_id]}: "
             f"[任务1] -> [任务2] -> [任务3] -> [任务4] -> [任务5]")

logger.error(f"[Chain] Failed to start processing chain "
             f"for {[primary_id]}: {exc}")
```

### 2. 行长度控制（≤79字符）
```python
# 正确的分行方式
logger.info(f"[Chain] Starting processing chain for [primary_entity]: "
            f"{[primary_id]}, force: {force}")

# 在逻辑断点处分行，保持语义完整
logger.info(f"[Chain] Processing chain started for [primary_entity]: {[primary_id]}, "
            f"current status: {[primary_entity].status}, force: {force}, "
            f"chain_task_id: {result.id}")
```

### 3. 日志级别使用
- **info**: 正常流程节点和重要状态变化
- **debug**: 详细的执行信息和链组合信息
- **error**: 错误情况和异常处理

## 🔧 Chain 构建最佳实践

### 1. 使用 .si() 不可变签名
```python
# 正确的方式：使用 .si() 传递参数
processing_chain = chain(
    task1.si([primary_id], force),
    task2.si([primary_id], force),
    task3.si([primary_id], force),
    task4.si([primary_id], force),
    task5.si([primary_id], force)
)

# 避免使用 .s() 可变签名，可能导致参数传递问题
```

### 2. 任务链注释模式
```python
processing_chain = chain(
    # Step 1: [步骤1描述] (required first)
    task1.si([primary_id], force),

    # Step 2: [步骤2描述]
    task2.si([primary_id], force),

    # Step 3: [步骤3描述]
    task3.si([primary_id], force),

    # Step 4: [步骤4描述] (needs previous content)
    task4.si([primary_id], force),

    # Step 5: [步骤5描述] (needs all content)
    task5.si([primary_id], force)
)
```

### 3. 链执行和结果处理
```python
# Execute the chain
result = processing_chain.apply_async()

# 记录执行结果
logger.info(
    f"[Chain] Processing chain started for [primary_entity]: {[primary_id]}, "
    f"current status: {[primary_entity].status}, force: {force}, "
    f"chain_task_id: {result.id}"
)
```

## 🛡️ 错误处理模式

### 1. 分层错误处理
```python
try:
    # [primary_entity] 验证
    [primary_entity] = [YourModel].objects.get(id=[primary_id])
    if not [primary_entity]:
        raise Exception(f"[PrimaryEntity] with id {[primary_id]} not found")

    # 链构建和执行
    processing_chain = chain(...)
    result = processing_chain.apply_async()

    return [primary_id]

except [YourModel].DoesNotExist:
    logger.error(f"[Chain] [PrimaryEntity] {[primary_id]} not found")
    raise
except Exception as exc:
    logger.error(f"[Chain] Failed to start processing chain "
                 f"for {[primary_id]}: {exc}")
    raise
```

### 2. 实体存在性验证
```python
# 验证 [primary_entity] 存在
try:
    [primary_entity] = [YourModel].objects.get(id=[primary_id])
    if not [primary_entity]:
        raise Exception(f"[PrimaryEntity] with id {[primary_id]} not found")
except [YourModel].DoesNotExist:
    logger.error(f"[Chain] [PrimaryEntity] {[primary_id]} not found")
    raise
```

### 3. 通用错误处理策略
```python
# 根据项目需求选择合适的错误处理策略
try:
    # 业务逻辑
    pass
except ValidationError as e:
    # 数据验证错误
    logger.warning(f"[Chain] Validation error: {e}")
    raise
except PermissionError as e:
    # 权限错误
    logger.error(f"[Chain] Permission denied: {e}")
    raise
except TimeoutError as e:
    # 超时错误
    logger.error(f"[Chain] Timeout error: {e}")
    raise
except Exception as e:
    # 其他未预期错误
    logger.error(f"[Chain] Unexpected error: {e}")
    raise
```

## 📊 调试和监控支持

### 1. 链组合日志
```python
# 记录链的组成结构，便于调试
logger.debug(
    f"[Chain] Chain composition for [primary_entity] {[primary_id]}: "
    f"[任务1] -> [任务2] -> [任务3] -> [任务4] -> [任务5]"
)
```

### 2. 执行状态日志
```python
# 记录链执行的详细信息
logger.info(
    f"[Chain] Processing chain started for [primary_entity]: {[primary_id]}, "
    f"current status: {[primary_entity].status}, force: {force}, "
    f"chain_task_id: {result.id}"
)
```

## 📋 具体实现检查清单

### ✅ 必须实现的结构
- [ ] 正确的模块文档字符串（包含功能描述和步骤说明）
- [ ] 正确的导入语句（celery, logging, models, tasks）
- [ ] 主任务函数 `process_[功能]_chain()`
- [ ] 状态机流程图文档
- [ ] 任务执行顺序文档
- [ ] 完整的错误处理

### ✅ Chain 构建检查
- [ ] 使用 `.si()` 不可变签名传递参数
- [ ] 正确的任务链顺序
- [ ] 每个步骤都有清晰的注释
- [ ] 依赖关系在注释中明确说明

### ✅ 日志标准化检查
- [ ] 所有 logger 使用 `[Chain]` 标签
- [ ] 每行 logger 输出 ≤79 字符
- [ ] 在逻辑断点处合理分行
- [ ] 保持语义完整性

### ✅ 错误处理检查
- [ ] 实体存在性验证
- [ ] 异常捕获和重新抛出
- [ ] 详细的错误日志记录
- [ ] 适当的异常类型处理

### ✅ 代码规范检查
- [ ] 所有代码使用英文
- [ ] 所有注释使用英文
- [ ] 禁止行内注释
- [ ] 遵循 PEP 8 规范
- [ ] 每行不超过 79 字符

## 🎯 关键实现细节

### 1. 参数传递模式
```python
# 使用 .si() 确保参数正确传递
processing_chain = chain(
    task1.si([primary_id], force),  # 传递 [primary_id] 和 force
    task2.si([primary_id], force),
    # ...
)
```

### 2. 任务链注释模式
```python
# 每个步骤都有清晰的注释说明
processing_chain = chain(
    # Step 1: OCR processing (required first)
    ocr_images_for_email.si([primary_id], force),

    # Step 2: Attachments OCR organization using LLM
    llm_ocr_task.si([primary_id], force),

    # Step 3: Email body organization using LLM
    llm_email_task.si([primary_id], force),

    # Step 4: Summarization (needs both email and attachment content)
    summarize_email_task.si([primary_id], force),

    # Step 5: Issue creation (needs all content)
    create_issue_task.si([primary_id], force)
)
```

### 3. 状态机文档模式
```python
"""
STATE MACHINE FLOW
==================

FETCHED → OCR_PROCESSING → OCR_SUCCESS
                ↓
        LLM_OCR_PROCESSING → LLM_OCR_SUCCESS
                ↓
        LLM_EMAIL_PROCESSING → LLM_EMAIL_SUCCESS
                ↓
        LLM_SUMMARY_PROCESSING → LLM_SUMMARY_SUCCESS
                ↓
        ISSUE_PROCESSING → ISSUE_SUCCESS → COMPLETED
"""
```

## 🚨 常见陷阱和避免方法

### ❌ 避免的反模式
1. **使用 .s() 可变签名** - 可能导致参数传递问题
2. **缺少实体存在性验证** - 可能导致运行时错误
3. **硬编码日志标签** - 应该使用 `[Chain]`
4. **缺少链组合调试日志** - 难以调试链执行问题
5. **任务顺序错误** - 可能导致依赖关系问题
6. **使用行内注释** - 应该将注释放在代码上方
7. **使用中文注释** - 所有注释必须使用英文

### ✅ 推荐的最佳实践
1. **使用 .si() 不可变签名** - 确保参数正确传递
2. **完整的文档字符串** - 包含状态机和执行顺序
3. **清晰的注释** - 每个步骤都有说明
4. **统一的日志格式** - 便于监控和调试
5. **适当的错误处理** - 确保异常正确传播
6. **英文代码和注释** - 保持代码国际化
7. **遵循 PEP 8 规范** - 保持代码一致性

## 📝 使用指南

### 快速开始
1. **复制此模板**作为新链编排器的起始点
2. **替换占位符**：根据占位符替换指南更新所有占位符
3. **调整任务链**：根据具体需求修改任务顺序和依赖关系
4. **更新状态机**：根据实际状态流转修改状态机文档
5. **测试链执行**：确保链能正确执行和传递参数
6. **验证日志格式**：确保所有日志使用 `[Chain]` 且 ≤79 字符

### 常见使用场景
- **数据处理管道**：数据清洗 → 转换 → 验证 → 存储
- **文件处理流程**：上传 → 解析 → 处理 → 生成 → 通知
- **订单处理系统**：创建 → 验证 → 支付 → 发货 → 完成
- **内容审核流程**：提交 → 预审 → 人工审核 → 发布 → 通知
- **邮件处理系统**：接收 → OCR → 分析 → 总结 → 创建工单

### 高级配置选项
- **条件执行**：根据参数决定是否执行某些任务
- **并行处理**：使用 `group` 或 `chord` 实现并行任务
- **错误重试**：配置任务重试策略和错误处理
- **监控集成**：添加任务执行监控和告警
- **性能优化**：使用 `select_related` 和 `prefetch_related` 优化查询

这个模板基于最佳实践和成功实现经验，包含了所有关键的设计模式和实现细节，适用于任何 Django + Celery 项目。