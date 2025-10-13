# Celery to LangGraph Refactoring - Requirements Document

## Introduction

本需求文档描述了将现有基于 Celery task 链的工作流逻辑重构为 LangGraph 架构的需求。重构的核心目标是通过引入 LangGraph 的状态图机制，简化状态管理、解耦数据库操作、统一工作流编排，从而提供更好的控制逻辑、可维护性和可扩展性。

## Background

当前系统使用 Celery chain 机制实现工作流编排，存在以下问题：

1. **复杂的状态管理**：多个处理状态散落在不同任务中，状态机复杂且难以维护
2. **分散的任务逻辑**：多个独立的 Celery 任务，缺乏统一的编排视图
3. **数据库操作耦合**：每个任务都需要处理数据库状态更新，职责不清晰
4. **难以调试和追踪**：任务执行状态分散，完整流程追踪困难
5. **错误恢复复杂**：需要手动管理任务重试和状态恢复

LangGraph 提供了一种更现代的工作流编排方式，通过状态图和 checkpoint 机制，可以有效解决上述问题。

## Requirements

### Requirement 1: 架构重构规范

**User Story:** 作为开发者，我希望有清晰的架构重构指南，使得将 Celery 任务重构为 LangGraph 工作流时有明确的步骤和规范可遵循。

#### Acceptance Criteria

1. WHEN 开发者需要重构一个 Celery task chain THEN 系统应提供标准的架构转换模板
2. WHEN 开发者查看重构指南 THEN 应包含 State 定义、节点设计、工作流编排三个核心部分的详细规范
3. WHEN 开发者实施重构 THEN 应遵循"首尾数据库操作，中间纯 State 操作"的设计原则
4. IF 现有 Celery 任务有复杂的状态机 THEN 重构应简化状态机，将中间状态由 LangGraph State 管理
5. WHEN 重构完成 THEN 新架构应支持从任意节点恢复执行（通过 checkpoint 机制）

### Requirement 2: State 定义与管理

**User Story:** 作为开发者，我需要将现有的数据模型字段映射到 LangGraph State，使得工作流能够在内存中高效处理数据。

#### Acceptance Criteria

1. WHEN 创建 State 定义文件 THEN 应基于现有 Django 模型的字段结构
2. WHEN 定义 State 类型 THEN 应使用 TypedDict 并包含三类字段：
   - 核心字段：从 Django 模型映射的基础数据字段
   - 结果字段：工作流处理过程中产生的结果数据
   - 固定字段：error_message, node_errors, force 等控制字段
3. WHEN 实现 create_state 函数 THEN 应提供初始化 State 的标准接口
4. WHEN 节点处理 State THEN 应使用不可变更新模式 (`{**state, ...}`)
5. IF State 字段与数据库字段类型不同 THEN 应进行适当的类型转换（如 DateTime → ISO string）

### Requirement 3: 节点架构设计

**User Story:** 作为开发者，我需要将现有的 Celery Task 类重构为 LangGraph 节点，实现职责分离和代码复用。

#### Acceptance Criteria

1. WHEN 创建基础节点类 THEN 应继承 BaseLangGraphNode 抽象基类
2. WHEN 实现节点方法 THEN 应包含以下核心方法：
   - `can_enter_node()`: 节点准入条件检查
   - `execute_processing()`: 核心业务逻辑处理
   - `before_processing()` 和 `after_processing()`: 前后处理钩子
3. WHEN 实现首节点 (WorkflowPrepareNode) THEN 应：
   - 从数据库读取实体数据到 State
   - 将模型字段映射到 State
   - 更新数据库状态为 PROCESSING（非 force 模式）
4. WHEN 实现尾节点 (WorkflowFinalizeNode) THEN 应：
   - 从 State 提取所有处理结果
   - 批量写入数据库（使用事务和锁）
   - 更新数据库状态为 SUCCESS/FAILED
5. WHEN 实现业务节点 THEN 应：
   - 只操作 State，不直接访问数据库
   - 专注于业务逻辑处理
   - 返回更新后的 State
6. IF 节点处理失败 THEN 应使用 `add_node_error()` 记录错误到 State

### Requirement 4: 工作流编排实现

**User Story:** 作为开发者，我需要使用 LangGraph StateGraph 替代 Celery chain，实现统一的工作流编排和调度。

#### Acceptance Criteria

1. WHEN 创建工作流图 THEN 应定义 `create_[feature]_graph()` 函数：
   - 使用 `StateGraph(StateType)` 创建状态图
   - 添加所有业务节点
   - 定义节点之间的边（依赖关系）
   - 配置 Redis checkpoint 以支持状态持久化
   - 编译并返回可执行的图
2. WHEN 执行工作流 THEN 应定义 `execute_[feature]_workflow()` 函数：
   - 验证实体存在性
   - 创建初始 State（包含 force 参数）
   - 配置 checkpoint 参数（thread_id, checkpoint_ns）
   - 调用 graph.invoke() 执行工作流
   - 检查执行结果和错误状态
3. WHEN 节点顺序定义 THEN 应遵循：`START → WorkflowPrepare → 业务节点1 → ... → 业务节点N → WorkflowFinalize → END`
4. IF 工作流执行失败 THEN 应能够从 checkpoint 恢复并重新执行
5. WHEN 使用 force 模式 THEN 应：
   - 跳过状态检查和验证
   - 强制执行所有节点
   - 跳过数据库状态更新（避免状态机污染）

### Requirement 5: 状态机简化

**User Story:** 作为系统架构师，我希望简化复杂的数据库状态机，将中间处理状态由 LangGraph State 管理，减少状态机维护成本。

#### Acceptance Criteria

1. WHEN 重构状态机 THEN 应将数据库状态简化为核心状态：
   - 初始状态（如 CREATED, FETCHED）
   - 处理中状态（PROCESSING）
   - 成功状态（SUCCESS）
   - 失败状态（FAILED）
2. WHEN 定义状态转换 THEN 应简化为：
   - 初始状态 → PROCESSING
   - PROCESSING → SUCCESS（正常完成）
   - PROCESSING → FAILED（失败）
   - FAILED → PROCESSING（重试）
3. IF 原有状态机有多个中间状态（如 OCR_SUCCESS, LLM_SUCCESS 等）THEN 应移除这些状态，改为在 State 中跟踪
4. WHEN 节点需要检查前置条件 THEN 应检查 State 中的字段，而不是数据库状态
5. WHEN 工作流完成 THEN 只更新最终的 SUCCESS/FAILED 状态

### Requirement 6: 错误处理与恢复

**User Story:** 作为开发者，我需要统一的错误处理机制，使得节点失败时能够正确记录错误并支持恢复。

#### Acceptance Criteria

1. WHEN 节点执行失败 THEN 应使用 `add_node_error()` 将错误记录到 State
2. WHEN 工作流完成 THEN 应检查 `node_errors` 字段判断是否有节点失败
3. IF 任何节点有错误 THEN WorkflowFinalizeNode 应将数据库状态设置为 FAILED
4. WHEN 记录错误 THEN 应包含：
   - 错误类型
   - 错误消息
   - 错误发生的时间戳
   - 节点名称
5. WHEN 工作流失败后重试 THEN 应能够从 checkpoint 恢复到失败前的状态
6. IF 使用 force 模式 THEN 应忽略错误继续执行所有节点

### Requirement 7: Checkpoint 持久化

**User Story:** 作为系统管理员，我需要工作流状态能够持久化到 Redis，确保系统重启或故障后能够恢复执行。

#### Acceptance Criteria

1. WHEN 配置 checkpoint THEN 应使用 Redis 作为存储后端
2. WHEN 执行工作流 THEN 应配置唯一的 thread_id：`workflow_{entity_id}`
3. WHEN 节点执行完成 THEN 应自动保存 State 到 Redis checkpoint
4. IF 工作流中断 THEN 应能够使用相同的 thread_id 从上次中断点恢复
5. WHEN checkpoint 保存 THEN 应包含完整的 State 数据和执行历史
6. WHEN 查询 checkpoint THEN 应能够获取工作流的执行进度和状态

### Requirement 8: 与现有系统集成

**User Story:** 作为开发者，我需要重构后的 LangGraph 工作流能够与现有的 API、调度器等系统组件无缝集成。

#### Acceptance Criteria

1. WHEN 触发工作流 THEN 应提供与原 Celery 任务兼容的接口：
   - 接受相同的参数（entity_id, force）
   - 返回相同格式的结果
2. WHEN API 调用工作流 THEN 应能够直接调用 `execute_[feature]_workflow()` 函数
3. IF 需要异步执行 THEN 应能够在 Celery 任务中包装 LangGraph 工作流执行
4. WHEN 调度器触发工作流 THEN 应使用统一的入口函数
5. WHEN 工作流执行 THEN 应保持与原系统相同的日志格式和级别
6. IF 需要监控工作流状态 THEN 应能够通过 checkpoint 查询执行进度

### Requirement 9: 迁移和测试

**User Story:** 作为开发者，我需要有明确的迁移路径和测试策略，确保重构过程安全可控。

#### Acceptance Criteria

1. WHEN 开始重构 THEN 应先复制参考实现（如 speechtotext agents）到新位置
2. WHEN 修改代码 THEN 应按照模板提示词的步骤逐步进行：
   - 第一步：修改基础组件（State, base_node, checkpoint_manager）
   - 第二步：修改节点实现（prepare, finalize, 业务节点）
   - 第三步：修改工作流编排（workflow.py）
3. WHEN 完成重构 THEN 应保留原 Celery 任务代码（标记为 deprecated）
4. WHEN 测试重构结果 THEN 应：
   - 测试正常流程执行
   - 测试错误处理和恢复
   - 测试 force 模式
   - 测试 checkpoint 恢复
5. IF 测试通过 THEN 才能在生产环境切换到新实现
6. WHEN 切换完成 THEN 应更新文档和 API 说明

### Requirement 10: 文档和规范

**User Story:** 作为团队成员，我需要完整的文档和编码规范，使得新的 LangGraph 实现易于理解和维护。

#### Acceptance Criteria

1. WHEN 创建新文件 THEN 应添加完整的模块文档字符串（docstring）
2. WHEN 实现节点 THEN 应在文档中说明：
   - 节点的职责
   - 依赖的前置条件
   - 产生的结果字段
3. WHEN 定义 State THEN 应在文档中列出所有字段及其用途
4. WHEN 创建工作流 THEN 应在文档中包含：
   - 状态机流程图（使用 Mermaid）
   - 节点执行顺序
   - 依赖关系说明
5. IF 代码遵循项目规范 THEN 应：
   - 所有注释使用英文
   - 注释放在代码上方，禁止行内注释
   - 每行代码不超过 73 字符
   - 遵循 PEP 8 规范
6. WHEN 更新文档 THEN 应同步更新 `.prompt/docs/` 下的相关文档

## Success Criteria

重构完成后，系统应满足：

1. ✅ 代码结构清晰，职责分离明确（首尾数据库操作，中间纯 State 操作）
2. ✅ 状态机简化，维护成本降低
3. ✅ 工作流执行可追踪，支持从任意节点恢复
4. ✅ 错误处理统一，易于调试
5. ✅ 与现有系统无缝集成
6. ✅ 文档完整，易于新成员理解和维护
7. ✅ 性能不低于原 Celery 实现
8. ✅ 支持 force 模式用于调试和重新处理
