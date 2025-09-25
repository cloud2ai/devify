# Haraka 邮件模式切换功能实现任务列表

## 实现计划概述

本任务列表基于已确认的需求文档和设计文档，将功能实现分解为可执行的编码任务。任务按照依赖关系和优先级排序，确保每个步骤都可以独立测试和验证。

## 任务列表

### 当前优先实现（后端核心功能）

- [ ] 1. 环境变量配置和Django Settings更新
  - 在`settings/globals.py`中添加新的环境变量配置
  - 添加`AUTO_ASSIGN_EMAIL_DOMAIN`、`DEFAULT_LANGUAGE`、`DEFAULT_SCENE`、`THREADLINE_CONFIG_PATH`配置项
  - 创建示例`.env`配置文件更新
  - _要求: 需求1.4, 需求3.17_

- [ ] 2. 创建EmailAlias数据模型
  - 在`threadline/models.py`中创建EmailAlias模型
  - 实现字段定义、索引、Meta配置和模型方法
  - 添加`validate_alias_uniqueness`和`find_user_by_email`类方法
  - 实现`save`方法从settings读取默认domain
  - _要求: 需求2.12-18_

- [ ] 3. 创建EmailAlias数据库迁移
  - 生成EmailAlias模型的数据库迁移文件
  - 执行迁移创建相应的数据库表和索引
  - 验证数据库表结构和约束正确性
  - _要求: 需求2.12-18_

- [ ] 3.1 配置EmailAlias Django Admin管理界面
  - 在`threadline/admin.py`中添加EmailAlias的Admin配置
  - 配置列表显示字段、搜索字段、过滤选项
  - 添加只读字段和自定义显示方法
  - 实现用户数据隔离（管理员可查看所有，普通用户只能查看自己的）
  - _要求: 需求2.12-18_

- [ ] 4. 创建多语言配置管理工具
  - 在`threadline/utils/`目录下创建`prompt_config_manager.py`
  - 实现PromptConfigManager类，支持YAML配置文件加载
  - 实现语言降级机制和场景配置获取方法
  - 添加错误处理和默认配置fallback机制
  - _要求: 需求3.1-20_

- [ ] 5. 创建YAML配置文件和目录结构
  - 创建`/opt/devify/conf/threadline/`目录结构
  - 创建`prompts.yaml`配置文件，包含zh-CN和en-US的场景化提示词
  - 实现chat和product_issue两个场景的完整配置
  - 验证YAML文件格式和配置加载正确性
  - _要求: 需求3.1-20_

- [x] 6. 文件系统邮件处理架构实现 - ✅ 已完成
  - 实现了文件系统处理方式
  - 实现了统一的EmailProcessor类支持多种源
  - 实现了自动检测邮件源的逻辑
  - _要求: 需求2.1-19_

- [x] 7. 邮件配置结构重构 - ✅ 已完成
  - 更新了所有引用旧email_config结构的代码
  - 实现了新的配置结构支持email_mode字段
  - 实现了自动检测邮件源的逻辑
  - 确保现有邮件处理功能能正常访问新的配置结构
  - _要求: 需求1.1-7_

- [x] 8. 文件系统邮件处理定时任务 - ✅ 已完成
  - 实现了process_file_emails_task定时任务
  - 实现了schedule_user_email_scanning定时任务
  - 集成了EmailProcessor并添加错误处理和重试机制
  - 在threadline/tasks/__init__.py中添加了任务导入
  - _要求: 需求2.1-19_

- [x] 9. 实现EmailAlias管理API - ✅ 已完成
  - 在`threadline/views/`目录下创建`email_alias.py`
  - 实现EmailAliasAPIView、EmailAliasDetailAPIView和EmailAliasValidationAPIView
  - 添加用户数据隔离、权限控制和Swagger文档
  - 实现别名唯一性验证和CRUD操作
  - _要求: 需求2.12-18, 需求5.8-14_

- [x] 10. 创建EmailAlias序列化器 - ✅ 已完成
  - 在`threadline/serializers.py`中创建EmailAlias相关序列化器
  - 实现EmailAliasSerializer、EmailAliasCreateSerializer等
  - 添加字段验证和错误处理逻辑
  - _要求: 需求2.12-18_

- [ ] 11. 配置EmailAlias API路由 - ❌ 未完成
  - 在`threadline/urls.py`中添加邮件别名管理路由
  - 配置settings路由下的email-aliases相关端点
  - 验证路由配置和API访问正确性
  - _要求: 需求2.12-18, 需求5.8-14_

- [ ] 12. 扩展用户注册API - ❌ 未完成
  - 在`accounts/views.py`中创建CustomRegisterView
  - 继承dj_rest_auth的RegisterView并添加邮件配置初始化
  - 实现语言和场景参数支持，添加事务原子性保证
  - 更新`auth/urls.py`中的注册路由配置
  - _要求: 需求4.1-16_

- [ ] 13. 集成测试和验证 - ❌ 未完成
  - 编写EmailAlias模型的单元测试
  - 编写PromptConfigManager的单元测试
  - 编写EmailProcessor的单元测试
  - 编写API端点的集成测试
  - _要求: 所有需求的验证_

### 后续实现（低优先级）

- [ ] 14. 用户注册时的邮件配置初始化完整实现
  - 完善用户注册流程中的配置初始化逻辑
  - 添加更完整的错误处理和回滚机制
  - 实现配置初始化的详细日志记录
  - _要求: 需求4（低优先级）_

- [ ] 15. 邮件模式配置前端支持API
  - 实现邮件模式切换的后端API支持
  - 添加配置验证和保存逻辑
  - 实现语言/场景修改时的提示词覆盖警告
  - _要求: 需求5（纯前端需求，后续实现）_

## 实现注意事项

### 代码规范
- 所有代码注释使用英文
- 遵循项目的命名规范和代码风格
- 使用APIView而不是ViewSet实现API
- 每行代码最大73字符，适当换行

### 测试要求
- 每个组件都需要对应的单元测试
- API端点需要集成测试
- 错误场景需要专门的测试用例
- 使用pytest和Django TestCase

### 安全考虑
- 所有API都需要适当的权限控制
- 用户数据隔离（只能访问自己的数据）
- 输入验证和错误处理
- 敏感配置信息的安全存储

### 性能考虑
- 数据库查询优化（使用适当的索引）
- Redis队列处理的性能优化
- YAML配置文件的缓存机制
- 大量邮件处理时的性能测试

## 依赖关系

- 任务1（环境变量配置）必须首先完成
- 任务2-3（EmailAlias模型）为任务9-11的前置依赖
- 任务4-5（配置管理）为任务6、8、12的前置依赖
- 任务6（配置重构）为任务7-8的前置依赖
- 任务13（测试）应该在每个功能完成后立即进行
