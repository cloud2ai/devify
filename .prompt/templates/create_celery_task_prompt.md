# Celery任务实现标准模板

这是一个通用的 Celery 任务实现指导模板，适用于任何 Django + Celery 项目。基于最佳实践和成功实现经验，提供完整的任务开发指导。

## 🎯 通用配置说明

### 占位符替换指南
在使用此模板时，请将以下占位符替换为实际值：

- `[功能]` → 具体功能名称（如：ocr_processing, data_analysis, file_conversion）
- `[primary_id]` → 主要实体的ID参数名（如：email_id, user_id, order_id）
- `[primary_entity]` → 主要实体的变量名（如：email, user, order）
- `[PrimaryEntity]` → 主要实体的类名（如：Email, User, Order）
- `[YourModel]` → 实际的数据模型类名
- `[your_app]` → 实际的Django应用名称
- `[StatusEnum]` → 实际的状态枚举类名
- `[YOUR_TASK_NAME]` → 任务名称（用于日志标签）

### 项目适配检查清单
- [ ] 确认项目使用 Django + Celery 架构
- [ ] 确认有合适的数据模型用于状态管理
- [ ] 确认状态枚举已定义
- [ ] 确认任务间的依赖关系
- [ ] 确认错误处理策略

## 📝 代码生成规范

**重要提示**：请严格遵循项目中的 Python 代码规范标准。详细规范请参考：`python_code_standards.md`

### 关键要求摘要
- 所有代码和注释必须使用英文
- 禁止行内注释，注释必须在代码上方
- 遵循 PEP 8 规范，每行不超过 79 字符
- 使用正确的导入顺序和文档字符串格式

## 🏗️ 核心架构设计原则

### 1. 类结构设计
```python
class [功能]Task(Task):
    """
    Task class for [功能] processing.

    This class handles the complete [功能] processing workflow
    with proper state management and error handling.
    """

    def before_start(self, [primary_id]: str, force: bool = False, **kwargs):
        """
        Initialize the task with required parameters.

        This method sets up all necessary instance variables
        and validates the input data.
        """

    def run(self, [primary_id]: str, force: bool = False) -> str:
        """
        Main controller method that handles force logic.

        This is the only place where force parameter is processed.
        """

    # Additional helper methods...
```

### 2. 方法职责分离

#### before_start() - 初始化层
**职责范围：**
- 设置实例属性：`[primary_id]`, `force`, `[primary_entity]`, `task_name`
- 获取[PrimaryEntity]对象：`select_related('[related_field]').get(id=[primary_id])`
- **关键操作**：`self.[primary_entity].refresh_from_db()` - 强制刷新获取最新状态
- **状态缓存**：`self.current_status = self.[primary_entity].status` - 缓存当前状态供全程使用
- 初始化状态机常量：`allowed_statuses`, `next_success_status`, `processing_status`, `next_failed_status`

**实现模板：**
```python
def before_start(self, [primary_id]: str, force: bool = False, **kwargs):
    """
    Initialize task with required parameters and state management.

    Args:
        [primary_id]: ID of the [primary_entity] to process
        force: Whether to force processing regardless of current status
        **kwargs: Additional parameters
    """
    # Set basic attributes
    self.[primary_id] = [primary_id]
    self.force = force
    self.[primary_entity] = None
    self.task_name = "[YOUR_TASK_NAME]"  # For unified logging

    # State machine configuration - adjust based on specific task
    self.allowed_statuses = [
        [StatusEnum].PREVIOUS_SUCCESS.value,  # Previous step success status
        [StatusEnum].CURRENT_FAILED.value    # Current step failed status (for retry)
    ]
    self.next_success_status = [StatusEnum].CURRENT_SUCCESS.value
    self.processing_status = [StatusEnum].CURRENT_PROCESSING.value
    self.next_failed_status = [StatusEnum].CURRENT_FAILED.value

    # Get and cache [primary_entity] object
    try:
        self.[primary_entity] = [YourModel].objects.select_related('[related_field]').get(id=[primary_id])
        self.[primary_entity].refresh_from_db()  # Force refresh - critical operation!
        self.current_status = self.[primary_entity].status  # Cache status - critical operation!

        logger.info(f"[{self.task_name}] [PrimaryEntity] object retrieved: "
                   f"{[primary_id]}, current_status: {self.current_status}")
    except [YourModel].DoesNotExist:
        logger.error(f"[{self.task_name}] [PrimaryEntity] {[primary_id]} not found")
        raise
```

#### run() - 主控制器（Force逻辑集中处理）
**设计哲学：这是唯一处理force参数的地方**

**标准执行流程：**
```python
def run(self, [primary_id]: str, force: bool = False) -> str:
    """
    Main controller method that handles the complete processing workflow.

    This method is the only place where force parameter is processed.
    All force logic is centralized here for better maintainability.

    Args:
        [primary_id]: ID of the [primary_entity] to process
        force: Whether to force processing regardless of current status

    Returns:
        str: [primary_id] for the next task in the chain
    """
    try:
        # Step 1: Initialize check
        if not hasattr(self, '[primary_entity]'):
            self.before_start([primary_id], force)

        logger.info(f"[{self.task_name}] Start processing: "
                   f"{[primary_id]}, force: {force}")

        # Step 2: Pre-execution check (skip in force mode)
        if not self.force and not self._pre_execution_check():
            logger.info(f"[{self.task_name}] Pre-execution check failed, "
                       f"skipping to next task: {[primary_id]}")
            return [primary_id]

        # Step 3: Completion status check (skip in force mode)
        if not self.force and self._is_already_complete():
            logger.info(f"[{self.task_name}] [PrimaryEntity] {[primary_id]} already "
                       f"complete, skipping to next task")
            return [primary_id]

        # Step 4: Set processing status (skip in force mode)
        if not self.force:
            logger.info(f"[{self.task_name}] Setting processing status "
                       f"for [primary_entity] {[primary_id]}")
            self._set_processing_status()

        # Step 5: Core business logic (always execute, pass force_mode parameter)
        results = self._execute_core_processing(force_mode=self.force)

        # Step 6: Update status (skip in force mode)
        if not self.force:
            logger.info(f"[{self.task_name}] Updating [primary_entity] status "
                       f"for [primary_entity] {[primary_id]}")
            self._update_[primary_entity]_status(results)
        else:
            logger.info(f"[{self.task_name}] Force mode: skipping "
                       f"status updates for {[primary_id]}")

        logger.info(f"[{self.task_name}] Processing completed: {[primary_id]}")
        return [primary_id]

    except [YourModel].DoesNotExist:
        logger.error(f"[{self.task_name}] [PrimaryEntity] {[primary_id]} not found")
        raise
    except Exception as exc:
        logger.error(f"[{self.task_name}] Fatal error for {[primary_id]}: {exc}")
        if not self.force:
            self._handle_error(exc)
        else:
            logger.warning(f"[{self.task_name}] Force mode: skipping "
                          f"error handling for {[primary_id]}")
        raise
```

### 3. 辅助方法设计模式

#### _pre_execution_check() - 状态验证
```python
def _pre_execution_check(self) -> bool:
    """
    Check state machine without handling force logic.

    Returns:
        bool: True if pre-execution check passes, False otherwise
    """
    if self.current_status not in self.allowed_statuses:
        logger.warning(f"[{self.task_name}] [PrimaryEntity] {self.[primary_id]} cannot be "
                      f"processed in status: {self.current_status}. "
                      f"Allowed: {self.allowed_statuses}")
        return False

    logger.debug(f"[{self.task_name}] Pre-execution check passed "
                f"for [primary_entity] {self.[primary_id]}")
    return True
```

#### _is_already_complete() - 完成状态检查
```python
def _is_already_complete(self) -> bool:
    """
    Check if already completed without handling force logic.

    Returns:
        bool: True if already complete, False otherwise
    """
    if self.current_status == self.next_success_status:
        logger.info(f"[{self.task_name}] [PrimaryEntity] {self.[primary_id]} already in "
                   f"{self.next_success_status} state, skipping to next task")
        return True
    return False
```

#### _execute_core_processing() - 纯业务逻辑
```python
def _execute_core_processing(self, force_mode: bool = False) -> Dict:
    """
    Core business logic that receives force_mode parameter but focuses on business processing.

    Key design points:
    - Does not directly check self.force, but receives force_mode parameter
    - Focuses on business logic, does not handle state transitions
    - Returns processing results for upper layer decision making

    Args:
        force_mode: Whether to force processing regardless of existing content

    Returns:
        Dict: Processing results with detailed statistics
    """
    # Implement specific business logic here
    pass
```

## 🔄 状态机集成最佳实践

### 1. 状态定义模式
```python
# Define state machine configuration in before_start()
self.allowed_statuses = [
    [StatusEnum].PREVIOUS_SUCCESS.value,    # Previous step success status
    [StatusEnum].CURRENT_FAILED.value      # Current step failed status (for retry)
]
self.next_success_status = [StatusEnum].CURRENT_SUCCESS.value
self.processing_status = [StatusEnum].CURRENT_PROCESSING.value
self.next_failed_status = [StatusEnum].CURRENT_FAILED.value
```

### 2. 状态缓存策略
```python
# Critical operations: force refresh and cache status
self.[primary_entity].refresh_from_db()
self.current_status = self.[primary_entity].status

# Use cached status throughout to ensure consistency
if self.current_status not in self.allowed_statuses:
    # Use cached status for checks
```

### 3. Force模式处理原则
- **集中处理**：只在run()方法中处理force逻辑
- **状态跳过**：force模式跳过所有状态检查和更新
- **业务执行**：force模式仍然执行核心业务逻辑
- **参数传递**：通过force_mode参数传递给业务方法

## 📝 日志输出标准化

### 1. 统一日志标签
```python
# Use dynamic task_name to avoid hardcoding
logger.info(f"[{self.task_name}] Your log message here")

# Instead of hardcoding:
logger.info(f"[OCR] Your log message here")  # ❌ Avoid this
```

### 2. 行长度控制（≤79字符）
```python
# Correct line breaking
logger.info(f"[{self.task_name}] Processing {count} items, "
           f"force: {self.force}")

# Break at logical points while maintaining semantic integrity
logger.error(f"[{self.task_name}] Failed to process item "
            f"{item.id}: {error}")
```

### 3. 日志级别使用
- **info**: 正常流程节点和重要状态变化
- **debug**: 详细的执行信息和内部状态
- **warning**: 非致命问题和跳过操作
- **error**: 错误情况和异常处理

## 🛡️ 错误处理模式

### 1. 分层错误处理
```python
# Top-level error handling in run() method
except Exception as exc:
    logger.error(f"[{self.task_name}] Fatal error for {[primary_id]}: {exc}")
    if not self.force:
        self._handle_error(exc)  # Only handle errors in non-force mode
    else:
        logger.warning(f"[{self.task_name}] Force mode: skipping "
                      f"error handling for {[primary_id]}")
    raise
```

### 2. 业务逻辑中的错误处理
```python
# Handle specific errors in core business methods
try:
    # Specific business operation
    result = some_business_operation()
except SpecificException as e:
    logger.error(f"Specific operation failed: {e}")
    # Return error result for upper layer to decide state transition
    return {'success': False, 'error': str(e)}
```

## 📊 结果统计模式

### 1. 统一的结果格式
```python
return {
    'item_results': [],      # Detailed results for each item
    'success_count': 0,      # Number of successful processing
    'fail_count': 0,         # Number of failures
    'skipped_count': 0,      # Number of skipped items (existing content)
    'no_items': False       # Whether there are no items to process
}
```

### 2. 状态决策逻辑
```python
def _update_[primary_entity]_status(self, results: Dict) -> None:
    """
    Update [primary_entity] status based on business results.

    Args:
        results: Processing results dictionary
    """
    if results['no_items']:
        # No items to process -> success
        self._save_[primary_entity](status=self.next_success_status)
        return

    if results['fail_count'] == 0:
        # All items successful (including skipped) -> success
        self._save_[primary_entity](status=self.next_success_status)
    else:
        # Some items failed -> failure
        error_message = f"Processing failed for {results['fail_count']} items"
        self._save_[primary_entity](status=self.next_failed_status, error_message=error_message)
```

## 🔧 工具方法设计

### 1. 数据保存方法
```python
def _save_[primary_entity](self, status: str = "", error_message: str = "") -> None:
    """
    Pure utility method: only responsible for saving, no business logic.

    Args:
        status: Status to set
        error_message: Error message to set
    """
    update_fields = []

    if status:
        self.[primary_entity].status = status
        update_fields.append('status')

    if error_message:
        self.[primary_entity].error_message = error_message
        update_fields.append('error_message')
    elif status:  # Clear error message when setting new status
        self.[primary_entity].error_message = ""
        update_fields.append('error_message')

    if update_fields:
        self.[primary_entity].save(update_fields=update_fields)
        logger.info(f"[{self.task_name}] Saved [primary_entity] {self.[primary_id]} to {status}")
```

### 2. 状态设置方法
```python
def _set_processing_status(self) -> None:
    """
    Set processing status - simple delegation.
    """
    self._save_[primary_entity](status=self.processing_status)
```

## 📋 具体实现检查清单

### ✅ 必须实现的方法
- [ ] `before_start()` - 初始化和状态缓存
- [ ] `run()` - 主控制流程和force逻辑
- [ ] `_pre_execution_check()` - 状态验证
- [ ] `_is_already_complete()` - 完成检查
- [ ] `_set_processing_status()` - 状态设置
- [ ] `_execute_core_processing()` - 核心业务逻辑
- [ ] `_update_[primary_entity]_status()` - 结果状态更新
- [ ] `_save_[primary_entity]()` - [primary_entity]保存工具
- [ ] `_handle_error()` - 错误处理

### ✅ Force模式处理检查
- [ ] run()方法中集中处理所有force逻辑
- [ ] force=True时跳过状态检查：`if not self.force and not self._pre_execution_check()`
- [ ] force=True时跳过完成检查：`if not self.force and self._is_already_complete()`
- [ ] force=True时跳过状态设置：`if not self.force: self._set_processing_status()`
- [ ] force=True时跳过状态更新：`if not self.force: self._update_[primary_entity]_status()`
- [ ] force=True时跳过错误处理：`if not self.force: self._handle_error()`
- [ ] 核心业务逻辑传递force_mode参数：`self._execute_core_processing(force_mode=self.force)`

### ✅ 状态机集成检查
- [ ] 正确定义allowed_statuses（包含前一步成功状态和当前失败状态）
- [ ] 实现refresh_from_db()状态刷新
- [ ] 实现current_status状态缓存
- [ ] 正确的状态转换序列
- [ ] 错误状态的正确处理

### ✅ 日志标准化检查
- [ ] 所有logger使用`f"[{self.task_name}]"`标签
- [ ] 每行logger输出≤79字符
- [ ] 在逻辑断点处合理分行
- [ ] 保持语义完整性

### ✅ 错误处理检查
- [ ] 分层错误处理（run()顶层 + 业务方法具体处理）
- [ ] force模式下跳过错误状态更新
- [ ] 适当的异常重新抛出
- [ ] 错误信息的详细记录

### ✅ 代码规范检查
- [ ] 所有代码使用英文
- [ ] 所有注释使用英文
- [ ] 禁止行内注释
- [ ] 遵循 PEP 8 规范
- [ ] 每行不超过 79 字符

## 🎯 关键实现细节

### 1. 状态刷新和缓存（防止并发问题）
```python
# Critical operation sequence
self.[primary_entity] = [YourModel].objects.select_related('[related_field]').get(id=[primary_id])
self.[primary_entity].refresh_from_db()  # Must refresh!
self.current_status = self.[primary_entity].status  # Must cache!

# Use cached status throughout
if self.current_status not in self.allowed_statuses:
    return False
```

### 2. Force模式的完整隔离
```python
# Force check pattern: at each place where state operations are needed
if not self.force and condition:
    # Normal mode operation
elif self.force:
    # Force mode log explanation
    logger.info(f"[{self.task_name}] Force mode: skipping xxx")
```

### 3. 业务逻辑的纯净性
```python
def _execute_core_processing(self, force_mode: bool = False):
    """
    Keep core business logic pure:
    - Receive force_mode parameter instead of directly accessing self.force
    - Focus on business processing, do not handle state transitions
    - Return structured results for upper layer use
    """
    # Decide processing strategy based on force_mode
    if not force_mode and existing_content:
        # Skip existing content
        pass
    else:
        # Execute processing logic
        pass
```

### 4. 结果驱动的状态更新
```python
def _update_[primary_entity]_status(self, results: Dict) -> None:
    """
    Decide status based on business results, no business logic included.
    """
    if results['fail_count'] == 0:
        self._save_[primary_entity](status=self.next_success_status)
    else:
        error_msg = f"Failed: {results['fail_count']} items"
        self._save_[primary_entity](status=self.next_failed_status, error_message=error_msg)
```

## 🚨 常见陷阱和避免方法

### ❌ 避免的反模式
1. **在辅助方法中处理force逻辑** - 应该集中在run()方法
2. **硬编码日志标签** - 应该使用`self.task_name`
3. **不刷新数据库状态** - 可能导致并发问题
4. **在业务方法中直接访问self.force** - 应该传递参数
5. **状态检查和业务逻辑混合** - 应该分离关注点
6. **使用行内注释** - 应该将注释放在代码上方
7. **使用中文注释** - 所有注释必须使用英文

### ✅ 推荐的最佳实践
1. **单一职责原则** - 每个方法只做一件事
2. **依赖注入** - 通过参数传递依赖，而不是直接访问实例变量
3. **状态缓存** - 避免重复数据库查询和并发问题
4. **集中控制** - Force逻辑集中在一个地方
5. **结构化返回** - 使用字典返回详细的处理结果
6. **英文代码和注释** - 保持代码国际化
7. **遵循 PEP 8 规范** - 保持代码一致性

## 📝 任务包装器模板

```python
# Create task instance
[功能]_task = [功能]Task()

@shared_task
def [功能]_processing_task([primary_id]: str, force: bool = False, *args, **kwargs) -> str:
    """
    Celery task wrapper - compatibility interface.

    Args:
        [primary_id]: [PrimaryEntity] ID
        force: Whether to force processing

    Returns:
        str: [primary_id] (for task chain)
    """
    return [功能]_task.run([primary_id], force)
```

## 🎯 使用指南

### 快速开始
1. **复制此模板**作为新任务的起始点
2. **替换占位符**：根据占位符替换指南更新所有占位符
3. **实现核心业务逻辑**：`_execute_core_processing()`方法
4. **调整状态机配置**：根据具体任务修改allowed_statuses
5. **测试force模式**：确保force=True时正确跳过状态操作
6. **验证日志格式**：确保所有日志使用`[{self.task_name}]`且≤79字符

### 常见使用场景
- **数据处理任务**：数据清洗、转换、验证
- **文件处理任务**：上传、解析、转换、生成
- **邮件处理任务**：OCR、分析、总结、分类
- **订单处理任务**：验证、支付、发货、通知
- **内容审核任务**：预审、人工审核、发布

### 高级配置选项
- **条件执行**：根据参数决定是否执行某些操作
- **批量处理**：处理多个项目并统计结果
- **错误重试**：配置重试策略和错误处理
- **性能优化**：使用数据库查询优化
- **监控集成**：添加任务执行监控

这个模板基于最佳实践和成功实现经验，包含了所有关键的设计模式和实现细节，适用于任何 Django + Celery 项目。