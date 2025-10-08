# 邮件收取架构统一优化需求

## 项目概述

统一和优化邮件收取架构，将现有的两种邮件收取方式（IMAP 用户模式和 Haraka 文件模式）整合到统一的调度和处理流程中，消除重复代码，提高代码复用性和维护性。

## 需求

### 需求 1：改造 EmailTask 模型

**用户故事：** 作为系统管理员，我希望 EmailTask 模型能够支持统一邮件收取架构，以便能够追踪和监控 IMAP 和 Haraka 两种邮件收取方式。

#### 1.1 模型字段扩展

**用户故事：** 作为开发者，我希望扩展 EmailTask 模型字段，以便能够区分不同的邮件源。

##### 验收标准

1. WHEN 扩展 EmailTask 模型时 THEN 系统 SHALL 添加 email_source 字段区分 IMAP 和 Haraka
2. WHEN 扩展 EmailTask 模型时 THEN 系统 SHALL 添加 details 字段记录完整执行过程

#### 1.2 任务执行记录

**用户故事：** 作为系统管理员，我希望能够记录任务的完整执行过程，以便能够追踪和监控任务状态。

##### 验收标准

1. WHEN 统一调度器运行时 THEN 系统 SHALL 创建全局 EmailTask 记录
2. WHEN 各 Handler 运行时 THEN 系统 SHALL 更新对应的 EmailTask 统计信息
3. WHEN 任务执行过程中 THEN 系统 SHALL 实时记录执行步骤和状态变化
4. WHEN 任务完成时 THEN 系统 SHALL 记录处理邮件数量和错误信息
5. WHEN 查看任务详情时 THEN 系统 SHALL 提供完整的执行记录，无需查看日志文件

#### 1.3 状态机闭环管理

**用户故事：** 作为系统管理员，我希望 EmailTask 有完整的状态机闭环管理，以便能够准确追踪任务状态，自动处理异常情况。

##### 验收标准

1. WHEN 调度器初始化任务时 THEN 系统 SHALL 创建任务并设置状态为 PENDING
2. WHEN 任务开始执行时 THEN 系统 SHALL 自动设置状态为 RUNNING 并记录开始时间
3. WHEN 任务正常完成时 THEN 系统 SHALL 自动设置状态为 COMPLETED 并记录完成时间
4. WHEN 任务发生错误时 THEN 系统 SHALL 自动设置状态为 FAILED 并记录错误详情
5. WHEN 任务超时时（超过10分钟）THEN 系统 SHALL 自动设置状态为 FAILED 并记录超时原因
6. WHEN 任务被取消时 THEN 系统 SHALL 自动设置状态为 CANCELLED 并记录取消原因
7. WHEN 状态转换时 THEN 系统 SHALL 记录状态转换时间和原因到 details
8. WHEN 状态异常时 THEN 系统 SHALL 提供状态修复和重置机制
9. WHEN 查看任务状态时 THEN 系统 SHALL 显示完整的状态转换历史

#### 1.4 任务状态检测和自动清理

**用户故事：** 作为系统管理员，我希望系统能够自动检测未完成的任务状态，以便能够智能处理无人管理的任务。

##### 验收标准

1. WHEN 服务启动时 THEN 系统 SHALL 查询上一次任务执行情况
2. WHEN 检测到 RUNNING 状态任务时 THEN 系统 SHALL 判断任务是否有人管理
3. WHEN 任务超过设定时间（10分钟）未更新时 THEN 系统 SHALL 将任务状态设置为 CANCELLED
4. WHEN 将任务设置为 CANCELLED 时 THEN 系统 SHALL 记录取消原因到 details
5. WHEN 任务被自动取消时 THEN 系统 SHALL 不触发重试机制，等待下次调度
6. WHEN 检测到 PENDING 状态任务时 THEN 系统 SHALL 将任务状态设置为 CANCELLED
7. WHEN 自动清理任务时 THEN 系统 SHALL 记录清理统计信息
8. WHEN 任务被跳过时 THEN 系统 SHALL 设置状态为 SKIPPED 并记录跳过原因

### 需求 2：统一邮件收取架构

**用户故事：** 作为系统管理员，我希望有一个统一的邮件收取架构，以便能够同时管理 IMAP 和 Haraka 两种邮件收取方式，减少重复代码并提高维护效率。

#### 2.1 统一调度器

**用户故事：** 作为系统管理员，我希望有一个统一的调度器，以便能够同时管理 IMAP 和 Haraka 两种邮件收取方式。

##### 验收标准

1. WHEN 系统启动时 THEN 系统 SHALL 同时启动 IMAP 邮件收取任务和 Haraka 邮件收取任务
2. WHEN 两个任务运行时 THEN 系统 SHALL 确保它们独立运行且互不影响
3. WHEN 启动新任务前 THEN 系统 SHALL 检查是否存在任务锁
4. WHEN 发现任务锁存在时 THEN 系统 SHALL 跳过任务执行并设置状态为 SKIPPED
5. WHEN 没有任务锁时 THEN 系统 SHALL 获取锁并检查是否有未闭环的状态机
6. WHEN 发现未闭环状态机时 THEN 系统 SHALL 将旧任务设置为 CANCELLED 状态
7. WHEN 任务执行时 THEN 系统 SHALL 记录完整的日志和监控信息
8. WHEN 任务完成时 THEN 系统 SHALL 释放锁
9. WHEN 任务超时时（超过10分钟）THEN 系统 SHALL 自动标记任务为超时状态并释放锁

#### 2.2 统一邮件保存服务

**用户故事：** 作为开发者，我希望有一个统一的邮件保存服务，以便 IMAP 和 Haraka Handler 都能使用相同的邮件保存逻辑。

##### 验收标准

1. WHEN 保存邮件时 THEN 系统 SHALL 提供统一的邮件保存接口
2. WHEN 处理附件时 THEN 系统 SHALL 提供统一的附件处理接口
3. WHEN 分配用户时 THEN 系统 SHALL 提供统一的用户分配逻辑
4. WHEN 发生错误时 THEN 系统 SHALL 提供统一的错误处理机制

#### 2.3 IMAP 邮件收取任务

**用户故事：** 作为系统管理员，我希望有一个专门的 IMAP 邮件收取任务，以便能够高效地处理所有用户的 IMAP 邮件收取。

##### 验收标准

1. WHEN IMAP 邮件收取任务启动时 THEN 系统 SHALL 遍历所有活跃用户的 IMAP 配置
2. WHEN 处理 IMAP 用户邮件时 THEN 系统 SHALL 为每个用户独立收取邮件
3. WHEN 保存 IMAP 邮件时 THEN 系统 SHALL 使用统一的邮件保存服务
4. WHEN IMAP 发生错误时 THEN 系统 SHALL 提供独立的错误处理和重试机制
5. WHEN IMAP 处理完成时 THEN 系统 SHALL 记录完整的日志和监控信息

#### 2.4 Haraka 邮件收取任务

**用户故事：** 作为系统管理员，我希望有一个专门的 Haraka 邮件收取任务，以便能够处理所有 Haraka 邮件并根据内容分配给相应用户。

##### 验收标准

1. WHEN Haraka 邮件收取任务启动时 THEN 系统 SHALL 收取所有 Haraka 邮件
2. WHEN 处理 Haraka 邮件时 THEN 系统 SHALL 根据邮件内容过滤和分配给用户
3. WHEN 保存 Haraka 邮件时 THEN 系统 SHALL 使用统一的邮件保存服务
4. WHEN Haraka 发生错误时 THEN 系统 SHALL 提供独立的错误处理和重试机制
5. WHEN Haraka 处理完成时 THEN 系统 SHALL 记录完整的日志和监控信息

### 需求 3：定期任务清理机制

**用户故事：** 作为系统管理员，我希望有定期任务清理机制，以便能够自动清理过期的任务记录，保持系统性能。

#### 验收标准

1. WHEN 定期清理时 THEN 系统 SHALL 自动清理超过1天的已完成任务
2. WHEN 清理任务时 THEN 系统 SHALL 保留必要的审计日志和统计信息
3. WHEN 清理失败任务时 THEN 系统 SHALL 保留错误信息和 details 用于分析
4. WHEN 清理超时任务时 THEN 系统 SHALL 释放相关锁和资源
5. WHEN 清理过程中 THEN 系统 SHALL 记录清理统计信息
6. WHEN 清理异常时 THEN 系统 SHALL 提供手动清理接口
7. WHEN 服务启动时 THEN 系统 SHALL 自动清理因服务重启导致的未完成任务
8. WHEN 清理重启导致的任务时 THEN 系统 SHALL 记录清理原因到系统日志
