# LangGraph Email Workflow - 手动测试指南

## 🎯 测试目标

验证 LangGraph email processing workflow 的核心功能是否正常工作。

## 📋 准备工作

### 1. 确保服务运行

```bash
# Redis (用于 checkpointer)
redis-cli ping  # 应该返回 PONG

# Django
cd /home/ubuntu/workspace/devify_workspace/devify
python manage.py check
```

### 2. 进入 Django Shell

```bash
python manage.py shell
```

## 🧪 测试步骤

### 方式 1: 快速测试（推荐首次使用）

```python
from threadline.agents.manual_test import quick_test

# 运行快速测试（不包含实际 workflow 执行）
quick_test()
```

**包含的测试：**
- ✅ Workflow graph 创建
- ✅ EmailState 创建
- ✅ 所有节点实例化
- ✅ Celery task 导入

### 方式 2: 完整测试

```python
from threadline.agents.manual_test import full_test

# 运行完整测试（包含实际 workflow 执行）
full_test()
```

**额外包含：**
- ✅ 使用真实邮件执行 workflow

### 方式 3: 单独测试

```python
from threadline.agents.manual_test import *

# 测试 1: Graph 创建
test_workflow_graph_creation()

# 测试 2: State 创建
test_email_state_creation()

# 测试 3: 节点实例化
test_node_instantiation()

# 测试 4: 使用指定邮件执行 workflow
test_workflow_with_real_email('email-id-here')

# 测试 5: Celery task 导入
test_celery_task_import()
```

## 🔍 预期输出示例

### 成功的测试输出

```
======================================================================
TEST 1: Workflow Graph Creation
======================================================================
✅ Workflow graph created successfully
   Graph type: <class 'langgraph.graph.state.CompiledStateGraph'>
   Graph has nodes: True

======================================================================
TEST 2: EmailState Creation
======================================================================
✅ EmailState created successfully
   Email ID: test-email-123
   User ID: test-user-456
   Force mode: False
   Node errors: {}
   Issue fields present: issue_id=None, issue_url=None, issue_metadata=None
   Issue prepare data: None

======================================================================
TEST 3: Node Instantiation
======================================================================
✅ WorkflowPrepareNode: instantiated successfully
   - node_name: workflow_prepare
   - has can_enter_node: True
   - has execute_processing: True
✅ OCRNode: instantiated successfully
   - node_name: ocr_node
   - has can_enter_node: True
   - has execute_processing: True
...

======================================================================
TEST SUMMARY
======================================================================
✅ PASS: graph_creation
✅ PASS: state_creation
✅ PASS: node_instantiation
✅ PASS: celery_import

Total: 4/4 tests passed

🎉 All tests passed!
```

## 🐛 常见问题排查

### 问题 1: Redis 连接失败

**症状：**
```
ConnectionError: Error connecting to Redis
```

**解决：**
```bash
# 检查 Redis 是否运行
redis-cli ping

# 启动 Redis
sudo systemctl start redis
# 或
redis-server
```

### 问题 2: 模型导入错误

**症状：**
```
ImportError: cannot import name 'EmailMessage'
```

**解决：**
```bash
# 检查数据库迁移
python manage.py showmigrations threadline

# 运行迁移
python manage.py migrate
```

### 问题 3: EmailMessage 不存在

**症状：**
```
EmailMessage.DoesNotExist: EmailMessage matching query does not exist
```

**解决：**
```python
# 创建测试邮件或使用现有邮件
from threadline.models import EmailMessage
emails = EmailMessage.objects.all()[:5]
for email in emails:
    print(f"ID: {email.id}, Status: {email.status}, Subject: {email.subject}")
```

## 🚀 使用 Celery 执行 Workflow

### 1. 确保 Celery Worker 运行

```bash
# 在新终端中
cd /home/ubuntu/workspace/devify_workspace/devify
celery -A devify worker -l info
```

### 2. 执行 Workflow Task

```python
from threadline.tasks import process_email_workflow

# 方式 1: 异步执行
result = process_email_workflow.delay('email-id-here')
print(f"Task ID: {result.id}")

# 方式 2: 同步执行（用于测试）
result = process_email_workflow.apply(args=['email-id-here'], kwargs={'force': False})
print(f"Result: {result}")

# 方式 3: 强制重新处理
result = process_email_workflow.delay('email-id-here', force=True)
```

### 3. 检查执行结果

```python
from threadline.models import EmailMessage

email = EmailMessage.objects.get(id='email-id-here')
print(f"Status: {email.status}")
print(f"Summary: {email.summary_content}")
print(f"LLM Content: {email.llm_content}")

# 检查附件
for att in email.attachments.all():
    print(f"Attachment: {att.filename}")
    print(f"  OCR: {att.ocr_content[:100] if att.ocr_content else 'None'}...")
    print(f"  LLM: {att.llm_content[:100] if att.llm_content else 'None'}...")

# 检查 Issue
from threadline.models import Issue
issues = Issue.objects.filter(email_message=email)
for issue in issues:
    print(f"Issue: {issue.external_id} - {issue.issue_url}")
```

## 📊 性能测试

### 测试 Workflow 执行时间

```python
import time
from threadline.agents.email_workflow import execute_email_processing_workflow

email_id = 'your-email-id'

start_time = time.time()
result = execute_email_processing_workflow(email_id, force=False)
end_time = time.time()

print(f"Execution time: {end_time - start_time:.2f} seconds")
print(f"Success: {result['success']}")
```

### 测试批量处理

```python
from threadline.models import EmailMessage
from threadline.state_machine import EmailStatus
from threadline.tasks import process_email_workflow

# 获取待处理邮件
emails = EmailMessage.objects.filter(status=EmailStatus.FETCHED.value)[:10]

print(f"Processing {len(emails)} emails...")

for email in emails:
    result = process_email_workflow.delay(str(email.id))
    print(f"Scheduled: {email.id} -> Task: {result.id}")
```

## ✅ 验证清单

在部署到生产环境之前，请确认：

- [ ] 所有快速测试通过 (`quick_test()`)
- [ ] 完整测试通过 (`full_test()`)
- [ ] Celery worker 可以成功执行任务
- [ ] 数据库正确更新（EmailMessage, Issue）
- [ ] Redis checkpoint 正常工作
- [ ] 错误处理正常（测试 force mode）
- [ ] 日志输出清晰完整

## 🔄 对比测试：Chain vs Workflow

### 测试相同邮件使用两种方法

```python
from threadline.tasks import process_email_chain, process_email_workflow
from threadline.models import EmailMessage

email_id = 'test-email-id'

# 重置邮件状态
email = EmailMessage.objects.get(id=email_id)
email.status = 'FETCHED'
email.save()

# 方法 1: Chain (旧)
import time
start = time.time()
process_email_chain.delay(email_id)
chain_time = time.time() - start

# 重置
email.refresh_from_db()
email.status = 'FETCHED'
email.save()

# 方法 2: Workflow (新)
start = time.time()
process_email_workflow.delay(email_id)
workflow_time = time.time() - start

print(f"Chain execution time: {chain_time:.2f}s")
print(f"Workflow execution time: {workflow_time:.2f}s")
```

## 📝 记录测试结果

创建测试记录：

```python
test_results = {
    'date': '2025-10-09',
    'tests_run': ['graph_creation', 'state_creation', 'node_instantiation', 'celery_import'],
    'passed': 4,
    'failed': 0,
    'notes': 'All basic tests passed successfully'
}

# 保存到文件
import json
with open('/tmp/workflow_test_results.json', 'w') as f:
    json.dump(test_results, f, indent=2)
```

