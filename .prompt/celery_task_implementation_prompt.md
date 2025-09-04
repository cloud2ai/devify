# Django Celery任务实现标准模板

基于OCR任务的成功实现经验，以下是用于优化其他任务模块的详细指导模板。

## 🏗️ 核心架构设计原则

### 1. 类结构设计
```python
class XxxTask(Task):
    """任务类应继承Celery的Task基类"""

    def before_start(self, email_id: str, force: bool = False, **kwargs):
        """初始化层 - 所有初始化工作都在这里完成"""

    def run(self, email_id: str, force: bool = False) -> str:
        """主控制器 - 唯一处理force逻辑的地方"""

    # 辅助方法们...
```

### 2. 方法职责分离

#### before_start() - 初始化层
**职责范围：**
- 设置实例属性：`email_id`, `force`, `email`, `task_name`
- 获取EmailMessage对象：`select_related('user').get(id=email_id)`
- **关键操作**：`self.email.refresh_from_db()` - 强制刷新获取最新状态
- **状态缓存**：`self.current_status = self.email.status` - 缓存当前状态供全程使用
- 初始化状态机常量：`allowed_statuses`, `next_success_status`, `processing_status`, `next_failed_status`

**实现模板：**
```python
def before_start(self, email_id: str, force: bool = False, **kwargs):
    # 设置基础属性
    self.email_id = email_id
    self.force = force
    self.email = None
    self.task_name = "YOUR_TASK_NAME"  # 用于统一日志标签

    # 状态机配置 - 根据具体任务调整
    self.allowed_statuses = [
        EmailStatus.PREVIOUS_SUCCESS.value,  # 上一步成功状态
        EmailStatus.CURRENT_FAILED.value    # 当前步骤失败状态（用于重试）
    ]
    self.next_success_status = EmailStatus.CURRENT_SUCCESS.value
    self.processing_status = EmailStatus.CURRENT_PROCESSING.value
    self.next_failed_status = EmailStatus.CURRENT_FAILED.value

    # 获取并缓存邮件对象
    try:
        self.email = EmailMessage.objects.select_related('user').get(id=email_id)
        self.email.refresh_from_db()  # 强制刷新 - 关键操作！
        self.current_status = self.email.status  # 缓存状态 - 关键操作！

        logger.info(f"[{self.task_name}] Email object retrieved: "
                   f"{email_id}, current_status: {self.current_status}")
    except EmailMessage.DoesNotExist:
        logger.error(f"[{self.task_name}] EmailMessage {email_id} not found")
        raise
```

#### run() - 主控制器（Force逻辑集中处理）
**设计哲学：这是唯一处理force参数的地方**

**标准执行流程：**
```python
def run(self, email_id: str, force: bool = False) -> str:
    try:
        # 步骤1：初始化检查
        if not hasattr(self, 'email'):
            self.before_start(email_id, force)

        logger.info(f"[{self.task_name}] Start processing: "
                   f"{email_id}, force: {force}")

        # 步骤2：前置检查（force模式跳过）
        if not self.force and not self._pre_execution_check():
            logger.info(f"[{self.task_name}] Pre-execution check failed, "
                       f"skipping to next task: {email_id}")
            return email_id

        # 步骤3：完成状态检查（force模式跳过）
        if not self.force and self._is_already_complete():
            logger.info(f"[{self.task_name}] Email {email_id} already "
                       f"complete, skipping to next task")
            return email_id

        # 步骤4：设置处理状态（force模式跳过）
        if not self.force:
            logger.info(f"[{self.task_name}] Setting processing status "
                       f"for email {email_id}")
            self._set_processing_status()

        # 步骤5：核心业务逻辑（总是执行，传递force_mode参数）
        results = self._execute_core_processing(force_mode=self.force)

        # 步骤6：更新状态（force模式跳过）
        if not self.force:
            logger.info(f"[{self.task_name}] Updating email status "
                       f"for email {email_id}")
            self._update_email_status(results)
        else:
            logger.info(f"[{self.task_name}] Force mode: skipping "
                       f"status updates for {email_id}")

        logger.info(f"[{self.task_name}] Processing completed: {email_id}")
        return email_id

    except EmailMessage.DoesNotExist:
        logger.error(f"[{self.task_name}] EmailMessage {email_id} not found")
        raise
    except Exception as exc:
        logger.error(f"[{self.task_name}] Fatal error for {email_id}: {exc}")
        if not self.force:
            self._handle_error(exc)
        else:
            logger.warning(f"[{self.task_name}] Force mode: skipping "
                          f"error handling for {email_id}")
        raise
```

### 3. 辅助方法设计模式

#### _pre_execution_check() - 状态验证
```python
def _pre_execution_check(self) -> bool:
    """只检查状态机，不处理force逻辑"""
    if self.current_status not in self.allowed_statuses:
        logger.warning(f"[{self.task_name}] Email {self.email_id} cannot be "
                      f"processed in status: {self.current_status}. "
                      f"Allowed: {self.allowed_statuses}")
        return False

    logger.debug(f"[{self.task_name}] Pre-execution check passed "
                f"for email {self.email_id}")
    return True
```

#### _is_already_complete() - 完成状态检查
```python
def _is_already_complete(self) -> bool:
    """检查是否已完成，不处理force逻辑"""
    if self.current_status == self.next_success_status:
        logger.info(f"[{self.task_name}] Email {self.email_id} already in "
                   f"{self.next_success_status} state, skipping to next task")
        return True
    return False
```

#### _execute_core_processing() - 纯业务逻辑
```python
def _execute_core_processing(self, force_mode: bool = False) -> Dict:
    """
    核心业务逻辑，接收force_mode参数但专注于业务处理

    关键设计点：
    - 不直接检查self.force，而是接收force_mode参数
    - 专注于业务逻辑，不处理状态转换
    - 返回处理结果供上层决策使用
    """
    # 具体业务逻辑实现...
    pass
```

## 🔄 状态机集成最佳实践

### 1. 状态定义模式
```python
# 在before_start()中定义状态机配置
self.allowed_statuses = [
    EmailStatus.PREVIOUS_SUCCESS.value,    # 上一步成功状态
    EmailStatus.CURRENT_FAILED.value      # 当前步骤失败状态（重试用）
]
self.next_success_status = EmailStatus.CURRENT_SUCCESS.value
self.processing_status = EmailStatus.CURRENT_PROCESSING.value
self.next_failed_status = EmailStatus.CURRENT_FAILED.value
```

### 2. 状态缓存策略
```python
# 关键操作：强制刷新并缓存状态
self.email.refresh_from_db()
self.current_status = self.email.status

# 全程使用缓存的状态，确保一致性
if self.current_status not in self.allowed_statuses:
    # 使用缓存的状态进行检查
```

### 3. Force模式处理原则
- **集中处理**：只在run()方法中处理force逻辑
- **状态跳过**：force模式跳过所有状态检查和更新
- **业务执行**：force模式仍然执行核心业务逻辑
- **参数传递**：通过force_mode参数传递给业务方法

## 📝 日志输出标准化

### 1. 统一日志标签
```python
# 使用动态task_name，避免硬编码
logger.info(f"[{self.task_name}] Your log message here")

# 而不是硬编码：
logger.info(f"[OCR] Your log message here")  # ❌ 避免这样做
```

### 2. 行长度控制（≤73字符）
```python
# 正确的分行方式
logger.info(f"[{self.task_name}] Processing {count} attachments, "
           f"force: {self.force}")

# 在逻辑断点处分行，保持语义完整
logger.error(f"[{self.task_name}] Failed to process attachment "
            f"{attachment.id}: {error}")
```

### 3. 日志级别使用
- **info**: 正常流程节点和重要状态变化
- **debug**: 详细的执行信息和内部状态
- **warning**: 非致命问题和跳过操作
- **error**: 错误情况和异常处理

## 🛡️ 错误处理模式

### 1. 分层错误处理
```python
# run()方法中的顶层错误处理
except Exception as exc:
    logger.error(f"[{self.task_name}] Fatal error for {email_id}: {exc}")
    if not self.force:
        self._handle_error(exc)  # 只在非force模式下处理错误
    else:
        logger.warning(f"[{self.task_name}] Force mode: skipping "
                      f"error handling for {email_id}")
    raise
```

### 2. 业务逻辑中的错误处理
```python
# 在核心业务方法中处理具体错误
try:
    # 具体业务操作
    result = some_business_operation()
except SpecificException as e:
    logger.error(f"Specific operation failed: {e}")
    # 返回错误结果，让上层决定状态转换
    return {'success': False, 'error': str(e)}
```

## 📊 结果统计模式

### 1. 统一的结果格式
```python
return {
    'attachment_results': [],      # 详细的每个项目结果
    'success_count': 0,           # 成功处理的数量
    'fail_count': 0,              # 失败的数量
    'skipped_count': 0,           # 跳过的数量（已有内容）
    'no_attachments': False       # 是否没有待处理项目
}
```

### 2. 状态决策逻辑
```python
def _update_email_status(self, results: Dict) -> None:
    if results['no_attachments']:
        # 没有待处理项目 -> 成功
        self._save_email(status=self.next_success_status)
        return

    if results['fail_count'] == 0:
        # 所有项目都成功（包括跳过的）-> 成功
        self._save_email(status=self.next_success_status)
    else:
        # 有失败项目 -> 失败
        error_message = f"Processing failed for {results['fail_count']} items"
        self._save_email(status=self.next_failed_status, error_message=error_message)
```

## 🔧 工具方法设计

### 1. 数据保存方法
```python
def _save_email(self, status: str = "", error_message: str = "") -> None:
    """纯工具方法：只负责保存，不处理业务逻辑"""
    update_fields = []

    if status:
        self.email.status = status
        update_fields.append('status')

    if error_message:
        self.email.error_message = error_message
        update_fields.append('error_message')
    elif status:  # 设置新状态时清空错误信息
        self.email.error_message = ""
        update_fields.append('error_message')

    if update_fields:
        self.email.save(update_fields=update_fields)
        logger.info(f"[{self.task_name}] Saved email {self.email_id} to {status}")
```

### 2. 状态设置方法
```python
def _set_processing_status(self) -> None:
    """设置处理中状态 - 简单委托"""
    self._save_email(status=self.processing_status)
```

## 📋 具体实现检查清单

### ✅ 必须实现的方法
- [ ] `before_start()` - 初始化和状态缓存
- [ ] `run()` - 主控制流程和force逻辑
- [ ] `_pre_execution_check()` - 状态验证
- [ ] `_is_already_complete()` - 完成检查
- [ ] `_set_processing_status()` - 状态设置
- [ ] `_execute_core_processing()` - 核心业务逻辑
- [ ] `_update_email_status()` - 结果状态更新
- [ ] `_save_email()` - 邮件保存工具
- [ ] `_handle_error()` - 错误处理

### ✅ Force模式处理检查
- [ ] run()方法中集中处理所有force逻辑
- [ ] force=True时跳过状态检查：`if not self.force and not self._pre_execution_check()`
- [ ] force=True时跳过完成检查：`if not self.force and self._is_already_complete()`
- [ ] force=True时跳过状态设置：`if not self.force: self._set_processing_status()`
- [ ] force=True时跳过状态更新：`if not self.force: self._update_email_status()`
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
- [ ] 每行logger输出≤73字符
- [ ] 在逻辑断点处合理分行
- [ ] 保持语义完整性

### ✅ 错误处理检查
- [ ] 分层错误处理（run()顶层 + 业务方法具体处理）
- [ ] force模式下跳过错误状态更新
- [ ] 适当的异常重新抛出
- [ ] 错误信息的详细记录

## 🎯 关键实现细节

### 1. 状态刷新和缓存（防止并发问题）
```python
# 关键操作序列
self.email = EmailMessage.objects.select_related('user').get(id=email_id)
self.email.refresh_from_db()  # 必须刷新！
self.current_status = self.email.status  # 必须缓存！

# 全程使用缓存的状态
if self.current_status not in self.allowed_statuses:
    return False
```

### 2. Force模式的完整隔离
```python
# Force检查模式：在每个需要状态操作的地方
if not self.force and condition:
    # 正常模式的操作
elif self.force:
    # Force模式的日志说明
    logger.info(f"[{self.task_name}] Force mode: skipping xxx")
```

### 3. 业务逻辑的纯净性
```python
def _execute_core_processing(self, force_mode: bool = False):
    """
    核心业务逻辑保持纯净：
    - 接收force_mode参数而不是直接访问self.force
    - 专注于业务处理，不处理状态转换
    - 返回结构化结果供上层使用
    """
    # 根据force_mode决定处理策略
    if not force_mode and existing_content:
        # 跳过已有内容
        pass
    else:
        # 执行处理逻辑
        pass
```

### 4. 结果驱动的状态更新
```python
def _update_email_status(self, results: Dict) -> None:
    """根据业务结果决定状态，不包含业务逻辑"""
    if results['fail_count'] == 0:
        self._save_email(status=self.next_success_status)
    else:
        error_msg = f"Failed: {results['fail_count']} items"
        self._save_email(status=self.next_failed_status, error_message=error_msg)
```

## 🚨 常见陷阱和避免方法

### ❌ 避免的反模式
1. **在辅助方法中处理force逻辑** - 应该集中在run()方法
2. **硬编码日志标签** - 应该使用`self.task_name`
3. **不刷新数据库状态** - 可能导致并发问题
4. **在业务方法中直接访问self.force** - 应该传递参数
5. **状态检查和业务逻辑混合** - 应该分离关注点

### ✅ 推荐的最佳实践
1. **单一职责原则** - 每个方法只做一件事
2. **依赖注入** - 通过参数传递依赖，而不是直接访问实例变量
3. **状态缓存** - 避免重复数据库查询和并发问题
4. **集中控制** - Force逻辑集中在一个地方
5. **结构化返回** - 使用字典返回详细的处理结果

## 📝 任务包装器模板

```python
# 创建任务实例
xxx_task = XxxTask()

@shared_task
def xxx_processing_task(email_id: str, force: bool = False, *args, **kwargs) -> str:
    """
    Celery任务包装器 - 兼容性接口

    Args:
        email_id: 邮件ID
        force: 是否强制处理

    Returns:
        str: 邮件ID（用于任务链）
    """
    return xxx_task.run(email_id, force)
```

## 🎯 使用指南

1. **复制此模板**作为新任务的起始点
2. **替换占位符**：`Xxx`, `YOUR_TASK_NAME`, `CURRENT_XXX`等
3. **实现核心业务逻辑**：`_execute_core_processing()`方法
4. **调整状态机配置**：根据具体任务修改allowed_statuses
5. **测试force模式**：确保force=True时正确跳过状态操作
6. **验证日志格式**：确保所有日志使用`[{self.task_name}]`且≤73字符

这个模板基于OCR任务的成功实现，包含了所有关键的设计模式和实现细节。
