# E2E Tests for Subscription Billing

端到端测试套件，用于验证订阅和支付流程的完整性。

## 📋 测试场景

测试用例对应 `docs/SUBSCRIPTION_SCENARIOS.md` 中的场景：

- ✅ **场景0**: 新用户初始状态（Free Plan）
- 🚧 **场景1**: 新用户订阅（Free → Basic/Pro）- 需要Stripe集成
- 🚧 **场景2**: 升级订阅（Basic → Pro）
- 🚧 **场景3**: 降级订阅（Pro → Basic）
- 🚧 **场景4**: 取消订阅
- 🚧 **场景5**: 恢复订阅
- 🚧 **场景6**: 已取消时升级
- 🚧 **场景7**: 自动续订（模拟）

## 🛠️ 环境准备

### 1. 安装依赖

```bash
cd /home/ubuntu/workspace/devify_workspace/devify

# 安装Python依赖
pip install pytest pytest-django playwright pytest-playwright

# 安装Playwright浏览器
playwright install chromium
```

### 2. 确保服务运行

```bash
# 确保Django开发服务器运行在 localhost:8000
docker ps | grep devify-api-dev

# 如果未运行，启动服务
docker-compose up -d
```

### 3. 数据库准备

测试会自动创建和清理测试用户，不影响现有数据。

## 🚀 运行测试

### 基础测试（不需要Stripe）

```bash
# 运行所有非Stripe测试
pytest tests/e2e/ -m "not stripe" -v

# 运行特定测试类
pytest tests/e2e/test_subscription_flow.py::TestScenario0FreePlan -v

# 运行特定测试方法
pytest tests/e2e/test_subscription_flow.py::TestScenario0FreePlan::test_new_user_has_free_plan -v
```

### Stripe集成测试

```bash
# 运行Stripe相关测试（需要配置）
pytest tests/e2e/ -m stripe -v
```

### 查看浏览器运行

```bash
# 显示浏览器窗口（用于调试）
pytest tests/e2e/ --headed -v

# 慢速执行（便于观察）
pytest tests/e2e/ --headed --slowmo 1000 -v
```

### 生成测试报告

```bash
# HTML报告
pytest tests/e2e/ --html=report.html --self-contained-html

# 覆盖率报告
pytest tests/e2e/ --cov=billing --cov-report=html
```

## 📊 测试结果验证

每个测试会进行**双重验证**：

1. **前端验证**：检查页面显示是否正确
   - 计划名称
   - 积分数量
   - 按钮状态

2. **数据库验证**：检查数据库状态是否正确
   - `billing_subscription` 表
   - `billing_usercredits` 表
   - 关联关系

## 🔧 测试隔离

- ✅ 每个测试创建独立的测试用户
- ✅ 测试完成后自动清理
- ✅ 不影响现有用户数据
- ✅ 使用独立的浏览器上下文

## 📝 编写新测试

### Page Object模式

```python
from .pages.billing_page import BillingPage
from .pages.login_page import LoginPage

def test_my_scenario(page, base_url, test_user):
    # 1. Login
    login_page = LoginPage(page, base_url)
    login_page.goto()
    login_page.login(test_user.username, test_user.raw_password)

    # 2. Navigate to billing
    billing_page = BillingPage(page, base_url)
    billing_page.goto()

    # 3. Perform actions
    billing_page.click_upgrade_to_basic()

    # 4. Verify
    assert billing_page.is_plan_current("Basic")
```

### 数据库验证

```python
from .helpers.db_helper import DBHelper

def test_database_state(test_user):
    # 简单断言
    DBHelper.assert_subscription_state(
        test_user.id,
        expected_plan_slug='standard',
        expected_status='active'
    )

    DBHelper.assert_credits_state(
        test_user.id,
        expected_base_credits=100
    )
```

## ⚠️ 注意事项

### Stripe测试

1. 使用测试模式和测试卡号
2. Webhook需要正确配置
3. 支付回调有延迟（1-5秒）

### 超时设置

- 页面加载：10秒
- Stripe回调：30秒
- Webhook处理：5秒

### 测试卡号

```
成功：4242 4242 4242 4242
失败：4000 0000 0000 0002
需要3D验证：4000 0027 6000 3184
```

## 🐛 调试技巧

### 1. 截图调试

```python
def test_something(page):
    # 截图保存
    page.screenshot(path="debug.png")
```

### 2. 查看页面HTML

```python
def test_something(page):
    print(page.content())
```

### 3. 暂停执行

```python
def test_something(page):
    page.pause()  # 打开Playwright Inspector
```

### 4. 查看数据库

```bash
# 测试执行时连接数据库
docker exec -it devify-mysql-dev mysql -u root -p devify
```

## 📈 持续集成

可以将测试集成到CI/CD流程：

```yaml
# .github/workflows/test.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run E2E tests
        run: |
          docker-compose up -d
          pytest tests/e2e/ -m "not stripe"
```

## 📚 参考文档

- [SUBSCRIPTION_SCENARIOS.md](../../docs/SUBSCRIPTION_SCENARIOS.md) - 完整场景文档
- [Playwright文档](https://playwright.dev/python/)
- [Pytest-Django文档](https://pytest-django.readthedocs.io/)
