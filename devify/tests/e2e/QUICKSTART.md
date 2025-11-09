# 快速开始：E2E测试

## ✅ 框架已完成

测试框架已经完全实现，包括：

- ✅ **Playwright测试框架**：完整的Page Object模式
- ✅ **数据库验证辅助类**：DBHelper for double verification
- ✅ **测试隔离**：每个测试独立用户，自动清理
- ✅ **场景0测试**：新用户Free Plan验证

## 🚀 立即运行测试

### 方式1：在Docker容器内运行（推荐）

测试需要在Django容器内运行，因为需要访问数据库。

```bash
# 进入容器
docker exec -it devify-api-dev bash

# 运行所有测试
cd /opt/devify
pytest tests/e2e/ -v

# 运行单个测试
pytest tests/e2e/test_subscription_flow.py::TestScenario0FreePlan -v

# 显示浏览器（需要X11支持）
pytest tests/e2e/ --headed -v
```

**注意**：容器内运行测试需要确保`/opt/devify/tests`目录存在且包含测试文件。

### 方式2：在主机上运行（开发模式）

如果您在主机上设置了Python环境：

```bash
cd /home/ubuntu/workspace/devify_workspace/devify

# 安装依赖
pip install pytest pytest-django playwright pytest-playwright
playwright install chromium

# 设置Django settings
export DJANGO_SETTINGS_MODULE=devify.settings.base

# 运行测试
pytest tests/e2e/ -v
```

### 方式3：使用快捷脚本

```bash
cd /home/ubuntu/workspace/devify_workspace/devify/tests/e2e

# 基础测试（无Stripe）
./run_tests.sh basic

# 显示浏览器
./run_tests.sh headed

# 调试模式（慢速+可见）
./run_tests.sh debug

# 运行单个测试
./run_tests.sh single test_new_user_has_free_plan
```

## 📋 已实现的测试

### ✅ 场景0：新用户初始状态

```python
class TestScenario0FreePlan:
    def test_new_user_has_free_plan(self, page, base_url, test_user):
        """
        验证新用户:
        - 前端显示Free Plan
        - 积分显示10/10
        - 数据库无订阅记录
        - UserCredits.base_credits = 10
        """

    def test_new_user_can_see_upgrade_buttons(self, page, base_url, test_user):
        """
        验证可以看到升级按钮
        """
```

### ✅ 数据库一致性测试

```python
class TestDatabaseConsistency:
    def test_user_has_at_most_one_active_subscription(self, test_user):
        """
        验证：用户最多只有1个active订阅
        """

    def test_user_has_credits_record(self, test_user):
        """
        验证：每个用户都有UserCredits记录
        """
```

### ✅ 页面元素测试

```python
class TestBillingPageElements:
    def test_billing_page_loads_successfully(self, page, base_url, test_user):
        """
        验证billing页面正常加载
        """

    def test_all_plans_are_displayed(self, page, base_url, test_user):
        """
        验证所有套餐都显示
        """
```

## 🚧 待实现的场景

以下场景框架已就绪，需要Stripe集成：

- [ ] **场景1**：Free → Basic/Pro（需要Stripe Checkout交互）
- [ ] **场景2**：Basic → Pro升级
- [ ] **场景3**：Pro → Basic降级
- [ ] **场景4**：取消订阅
- [ ] **场景5**：恢复订阅
- [ ] **场景6**：已取消时升级
- [ ] **场景7**：自动续订（模拟）

## 🎯 核心架构

### Page Object模式

```
tests/e2e/pages/
├── login_page.py      # 登录页面操作
└── billing_page.py    # Billing页面操作（核心）
```

**BillingPage支持的操作**：
- `get_current_plan_name()` - 获取当前计划
- `get_credits_display()` - 获取积分显示
- `click_upgrade_to_basic()` - 点击升级到Basic
- `click_cancel_subscription()` - 点击取消订阅
- `click_resume_subscription()` - 点击恢复订阅
- `confirm_dialog()` - 确认对话框

### 数据库验证

```
tests/e2e/helpers/db_helper.py
```

**DBHelper支持的方法**：
- `get_active_subscription(user_id)` - 获取活跃订阅
- `get_credits(user_id)` - 获取积分
- `assert_subscription_state()` - 断言订阅状态
- `assert_credits_state()` - 断言积分状态
- `count_active_subscriptions()` - 统计活跃订阅数

## 🔧 调试技巧

### 1. 查看浏览器操作

```bash
pytest tests/e2e/ --headed --slowmo 1000
```

### 2. 暂停在特定位置

在测试中添加：
```python
page.pause()  # 打开Playwright Inspector
```

### 3. 截图保存

```python
page.screenshot(path="/opt/devify/test-screenshot.png")
```

### 4. 查看测试用户

测试会自动创建`test_xxxxxxxx`格式的用户，测试完成后自动删除。

可以在测试运行时查看：
```sql
SELECT * FROM auth_user WHERE username LIKE 'test_%';
```

## 📊 测试流程示意

```
1. Fixture创建测试用户
    ↓
2. 登录系统
    ↓
3. 访问/billing页面
    ↓
4. 前端操作（点击、填写）
    ↓
5. 前端验证（检查显示）
    ↓
6. 数据库验证（检查数据）
    ↓
7. 自动清理测试用户
```

## 🎉 接下来

1. **运行现有测试**：验证框架工作正常
2. **添加Stripe测试**：需要配置Stripe Checkout交互
3. **CI/CD集成**：将测试加入自动化流程
4. **测试覆盖率**：扩展到所有7个场景

## 💡 使用AI内置浏览器演示

AI可以使用内置浏览器工具进行**实时演示和验证**：

```
示例：验证Free Plan页面
1. 导航到 http://localhost:8000/login
2. 使用测试用户登录
3. 访问 /billing
4. 检查页面元素
5. 验证数据库状态
```

这对于调试特定场景非常有用！

## ❓ 常见问题

**Q: 测试会影响现有用户吗？**
A: 不会。每个测试使用独立的`test_xxx`用户，完成后自动删除。

**Q: 如何跳过Stripe测试？**
A: 使用 `pytest tests/e2e/ -m "not stripe"`

**Q: 测试失败后如何调试？**
A:
1. 使用`--headed`查看浏览器
2. 添加`page.screenshot()`截图
3. 使用`page.pause()`暂停调试
4. 查看数据库状态

**Q: 可以在生产环境运行吗？**
A: **不要**在生产环境运行！测试会创建和删除用户。
