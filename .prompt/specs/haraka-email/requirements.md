# Haraka 邮件模式切换功能需求文档

## 需求介绍
在 SaaS 运营模式下，用户对于将敏感邮件发送到同一邮箱地址存在安全性和隐私方面的担忧。为了降低用户的这种焦虑并提高用户信任度，本功能旨在为 Devify 系统新增邮件模式选择功能：

1. **自动分配模式**：系统为用户分配独立的虚拟邮箱（`{username}@{system_domain}`），确保每个用户的邮件都有独立的接收地址
2. **自定义 IMAP 模式**：用户可以选择使用自己的邮箱服务器，完全控制邮件接收和处理

这种设计既满足了新用户简化配置的需求，又为对安全性有更高要求的用户提供了完全自主的解决方案，从而在 SaaS 环境中建立更强的用户信任。

## 需求

### 需求 1：重构邮件配置结构
**用户故事**：作为一个开发人员，我想要重构现有的邮件配置结构以支持新的邮件模式选择功能，这样系统可以同时支持自动分配和自定义IMAP两种模式。

#### 验收标准
1. WHEN 重构代码时 THEN 系统 SHALL 更新所有引用旧 email_config 结构的代码以使用新的配置格式
2. WHEN 重构代码时 THEN 系统 SHALL 更新所有引用 email_filter_config 的代码以使用新配置中的 filter_config 字段
3. WHEN 代码重构完成后 THEN 系统 SHALL 确保所有邮件处理功能能正常访问新的配置结构
4. WHEN 系统查询用户邮件配置时 THEN 系统 SHALL 支持新的配置结构（包含email_mode字段）
5. WHEN 系统处理自动分配模式时 THEN 系统 SHALL 支持 email_mode = "auto_assign" 的配置
6. WHEN 系统处理自定义IMAP模式时 THEN 系统 SHALL 支持 email_mode = "custom_imap" 的配置
7. WHEN 用户保存新格式的邮件配置时 THEN 系统 SHALL 验证配置完整性并正确处理新的配置结构

#### 配置结构变更
**现有结构**：
Settings表中的两条独立记录：
```json
// settings记录1: email_config
{
  "key": "email_config",
  "value": {
    "imap_host": "imap.example.com",
    "smtp_host": "smtp.example.com",
    "smtp_ssl_port": 465,
    "smtp_starttls_port": 587,
    "imap_ssl_port": 993,
    "username": "user@example.com",
    "password": "password",
    "use_ssl": true,
    "use_starttls": false
  }
}

// settings记录2: email_filter_config
{
  "key": "email_filter_config",
  "value": {
    "folder": "INBOX",
    "filters": ["unread"],
    "exclude_patterns": ["spam", "newsletter"],
    "max_age_days": 7
  }
}
```

**新结构**：
Settings表中的一条记录（合并email_filter_config）：
```json
// settings记录: email_config
{
  "key": "email_config",
  "value": {
    "email_mode": "custom_imap",
    "auto_assign_domain": "aimychats.com",
    "custom_imap_config": {
      "imap_host": "imap.example.com",
      "imap_port": 993,
      "username": "user@example.com",
      "password": "password",
      "use_ssl": true,
      "filter_config": {
        "folder": "INBOX",
        "filters": ["unread"],
        "exclude_patterns": ["spam", "newsletter"],
        "max_age_days": 7
      }
    }
  }
}
```

### 需求 2：文件系统邮件处理架构
**用户故事**：作为一个系统管理员，我想要系统支持文件系统邮件处理方式，这样可以确保自动分配模式下的邮件能够被及时处理，同时不影响现有自定义 IMAP 用户的邮件处理流程。

#### 验收标准
1. WHEN 系统启动时 THEN 系统 SHALL 支持多种邮件处理方式（文件系统、IMAP）
2. WHEN 处理自动分配模式邮件时 THEN 系统 SHALL 从文件系统获取邮件数据
3. WHEN 系统处理邮件数据时 THEN 系统 SHALL 支持标准的邮件数据格式（包含收件人、发件人、主题、内容、附件等字段）
4. WHEN 定时任务执行时 THEN 系统 SHALL 过滤出采用自动分配模式（email_mode = "auto_assign"）的用户
5. WHEN 处理邮件时 THEN 系统 SHALL 根据收件人地址解析用户名和域名
6. WHEN 收件人地址格式为 `{username}@{system_domain}` 时 THEN 系统 SHALL 在自动模式用户中查找对应的用户记录
7. WHEN 找到匹配的自动模式用户时 THEN 系统 SHALL 将邮件内容关联到该用户并调用现有的邮件解析和处理功能
8. WHEN 无法找到匹配的用户或用户不是自动模式时 THEN 系统 SHALL 记录警告日志并跳过该邮件
9. WHEN 邮件处理完成后 THEN 系统 SHALL 创建 EmailMessage 记录并触发现有的处理链路
10. WHEN 定时任务处理失败时 THEN 系统 SHALL 记录错误日志并支持重试机制
11. IF 文件系统中没有邮件 THEN 定时任务 SHALL 等待下一个执行周期
12. IF 系统支持邮件别名 THEN 系统 SHALL 支持用户配置和管理邮件别名
13. WHEN 用户配置邮件别名时 THEN 系统 SHALL 验证别名的唯一性确保不与其他用户冲突
14. WHEN 用户添加新的邮件别名时 THEN 系统 SHALL 检查别名格式为 `{alias}@{system_domain}` 且alias不与现有用户名重复
15. WHEN 用户修改或删除邮件别名时 THEN 系统 SHALL 允许用户管理自己的别名列表
16. WHEN 系统处理发送到别名地址的邮件时 THEN 系统 SHALL 将邮件正确路由到别名所属的用户
17. WHEN 多个用户尝试使用相同别名时 THEN 系统 SHALL 拒绝后续的重复别名注册并返回错误信息
18. WHEN 用户删除别名后 THEN 系统 SHALL 确保该别名可以被其他用户重新使用
19. IF 现有自定义 IMAP 用户 THEN 系统 SHALL 继续使用原有的邮件处理方式不受影响

### 需求 3：多语言配置模板管理系统
**用户故事**：作为一个系统管理员，我想要通过YAML配置文件管理多语言的邮件提示词模板和相关配置，这样可以方便地扩展新语言支持，同时避免将所有配置硬编码在数据库中。

#### 验收标准
1. WHEN 系统需要为用户初始化邮件配置时 THEN 系统 SHALL 读取 devify/devify/conf/threadline 目录下的prompts.yaml配置文件
2. WHEN 系统读取YAML配置时 THEN 系统 SHALL 支持场景化的多语言提示词配置结构（包含language_config, scene_config, scene_prompt_config等）
3. WHEN 用户注册或修改配置时 THEN 系统 SHALL 根据用户选择的语言和场景从YAML模板中匹配对应的配置内容
4. WHEN 前端需要显示语言选择时 THEN 系统 SHALL 从language_config中获取语言的显示名称和本地化名称
5. WHEN 前端需要显示场景信息时 THEN 系统 SHALL 从scene_config中获取场景名称和描述信息
6. WHEN 用户选择特定场景（如chat, product_issue等）时 THEN 系统 SHALL 从scene_prompt_config中获取对应场景的提示词配置
7. WHEN 用户语言为zh-CN时 THEN 系统 SHALL 使用YAML中对应的中文场景配置和提示词
8. WHEN 用户语言为en-US时 THEN 系统 SHALL 使用YAML中对应的英文场景配置和提示词
9. WHEN 用户选择的语言或场景在YAML中找不到对应配置时 THEN 系统 SHALL 抛出明确的错误信息
10. WHEN 系统需要OCR提示词时 THEN 系统 SHALL 使用对应场景和语言的ocr_prompt配置
11. WHEN YAML配置文件不存在或格式错误时 THEN 系统 SHALL 抛出明确的错误信息而不使用默认配置
12. WHEN 用户切换场景时 THEN 系统 SHALL 允许用户随时修改当前使用的场景配置
13. WHEN 用户切换场景后 THEN 系统 SHALL 根据新选择的场景和用户语言重新加载对应的提示词配置
14. WHEN 系统处理邮件时 THEN 系统 SHALL 使用用户当前设置的场景对应的提示词进行处理
15. WHEN 系统为用户生成邮件配置时 THEN 系统 SHALL 在用户的prompt_config中保存语言偏好和场景选择
16. WHEN 系统保存用户配置时 THEN 系统 SHALL 将从YAML模板匹配的场景化提示词内容保存到用户的prompt_config中
17. WHEN 用户未设置场景时 THEN 系统 SHALL 使用settings中配置的默认场景
18. WHEN management command需要初始化用户配置时 THEN 系统 SHALL 使用相同的YAML模板匹配逻辑支持场景选择
19. WHEN 需要扩展新语言或新场景时 THEN 系统 SHALL 支持通过在YAML文件中添加新的语言或场景配置来扩展
20. IF YAML配置文件缺失或无法访问 THEN 系统 SHALL 抛出错误而不是使用内置默认配置

#### 配置文件结构示例
YAML配置文件应包含以下结构（支持场景化的多语言提示词配置）：
```yaml
# devify/devify/conf/threadline/prompts.yaml
# 场景化多语言提示词配置模板

# 语言配置信息（用于前端显示）
language_config:
  zh-CN:
    name: 简体中文
    native_name: 简体中文
  en-US:
    name: English
    native_name: English

# 场景配置信息（用于前端显示）
scene_config:
  chat:
    zh-CN: 日常聊天
    en-US: Daily Chat
    description:
      zh-CN: 处理日常聊天记录和沟通内容
      en-US: Process daily chat records and communication content
  product_issue:
    zh-CN: 产品问题跟踪
    en-US: Product Issue Tracking
    description:
      zh-CN: 将聊天记录整理成产品问题格式，用于JIRA等问题管理系统
      en-US: Organize chat records into product issue format for JIRA and other issue management systems

# 场景化提示词配置
scene_prompt_config:
  chat:
    zh-CN:
      output_language: "zh-hans"
      email_content_prompt: "整理提供的聊天内容（可能包含聊天记录或消息正文）按时间顺序整理成对话文本，进行最小化润色，不改变任何原意并保留所有信息。输出格式：[日期 时间] 发言人：内容，图片占位符[IMAGE: filename.png]单独占行。对话文本必须为纯文本，结构清晰。始终保持对话的原始语言。"
      ocr_prompt: "将提供的OCR结果整理成纯文本输出，保持简洁易读的格式。完整保留所有内容，清楚标识任何重要信息。将不确定部分标记为[不清楚]。"
      summary_prompt: "根据提供的聊天内容，整理成简洁的聊天总结，包含：1）**参与者**：主要参与聊天的人员；2）**主要话题**：讨论的核心话题；3）**重要信息**：值得记录的关键信息；4）**后续事项**：需要跟进的事项（如有）。"
      summary_title_prompt: "根据聊天内容，提取聊天主题，格式简洁明了，准确表达聊天的核心内容，最大长度100字符。"
    en-US:
      output_language: "en"
      email_content_prompt: "Organize the provided chat content (which may include chat records or message bodies) in chronological order into conversation text with minimal polishing, without altering any original meaning and retaining all information. Output format: [Date Time] Speaker: Content, with image placeholders [IMAGE: filename.png] on separate lines. Conversation text must be plain text with clear structure. Always preserve the original language of the conversation."
      ocr_prompt: "Organize the provided OCR results into plain text output, maintaining a clean and readable format. Fully retain all content and clearly identify any important information. Mark any uncertain parts as [unclear]."
      summary_prompt: "Based on the provided chat content, organize into a concise chat summary, including: 1) **Participants**: main people involved in the chat; 2) **Main Topics**: core topics discussed; 3) **Important Information**: key information worth recording; 4) **Follow-up Items**: items that need follow-up (if any)."
      summary_title_prompt: "Based on the chat content, extract the chat topic, concise and accurately expressing the core content of the chat, maximum 100 characters."

  product_issue:
    zh-CN:
      output_language: "zh-hans"
      email_content_prompt: "整理提供的聊天内容（可能包含聊天记录或消息正文）按时间顺序整理成对话文本，进行最小化润色（明确标记任何假设），不改变任何原意并保留所有信息。输出格式：[日期 时间] 发言人：内容（单行显示，必要时可换行），图片占位符[IMAGE: filename.png]单独占行并放置在原始位置。对话文本必须为纯文本，结构清晰。始终保持对话的原始语言。"
      ocr_prompt: "将提供的OCR结果整理成纯文本输出，必要时使用Markdown格式处理代码或引用内容。完整保留和描述所有内容，不得遗漏。清楚突出任何正常、异常或有价值的信息。尝试纠正和标准化不完整、不清楚或可能错误的OCR内容，不改变其原意，并将任何不确定部分标记为[不清楚]。仅产生带有必要Markdown格式的结构化文本，不得包含任何附加解释、总结或无关内容。"
      summary_prompt: "根据提供的内容（包括按时间顺序的聊天记录和图像OCR识别的内容），按时间顺序整理聊天记录，保持每条记录的原始发言人和语言，完整保留所有信息。输出应包含四个部分：1）**主要内容**：列出当前对话的关键要点；2）**过程描述**：详细描述问题及其重现步骤，将任何不确定信息标记为\"未知\"；3）**解决方案**（如未解决，说明已尝试措施）：如问题已解决，列出解决方案；如未解决，列出已采取的措施及其结果；4）**解决状态**：说明问题是否已解决（是/否）。"
      summary_title_prompt: "根据聊天记录，提取单一结构化标题，格式为：[问题类别][参与者]标题内容；标题应使用动宾结构，简洁明了，准确表达核心问题或需求，避免模糊术语，最大长度300字符；如信息不清楚，添加[待确认]；如存在多个问题，仅提取最关键和核心的一个。"
    en-US:
      output_language: "en"
      email_content_prompt: "Organize the provided chat content (which may include chat records or message bodies) in chronological order into a conversation text with minimal polishing (clearly mark any assumptions), without altering any original meaning and retaining all information. Output format: [Date Time] Speaker: Content (on a single line, or wrapped across multiple lines if necessary), with image placeholders [IMAGE: filename.png] placed on separate lines in their original positions. Conversation text must be plain text with clear structure. Always preserve the original language of the conversation."
      ocr_prompt: "Organize the provided OCR results into plain text output, using Markdown formatting when necessary for code or quoted content. Fully retain and describe all content without omission. Clearly highlight any normal, abnormal, or valuable information. Attempt to correct and standardize incomplete, unclear, or potentially erroneous OCR content without altering its original meaning, and mark any uncertain parts as [unclear]. Produce only structured text with necessary Markdown formatting, without any additional explanations, summaries, or unrelated content."
      summary_prompt: "Based on the provided content (including chronological chat records and OCR-recognized content from images), organize the chat records in chronological order, preserving the original speaker and language for each entry, fully retaining all information. The output should include four sections: 1) **Main Content**: list the key points of the current conversation; 2) **Process Description**: provide a detailed description of the problem and its reproduction steps, marking any uncertain information as \"unknown\"; 3) **Solution** (if unresolved, indicate attempted measures): if the issue is resolved, list the solution; if unresolved, list measures already taken and their results; 4) **Resolution Status**: indicate whether the issue has been resolved (Yes/No)."
      summary_title_prompt: "Based on the chat records, extract a single structured title in the format: [Issue Category][Participant]Title Content; the title should use a verb-object structure, be concise, and accurately express the core problem or requirement, avoiding vague terms, with a maximum length of 300 characters; if the information is unclear, add [To Be Confirmed]; if multiple issues exist, extract only the most critical and central one."
```

### 需求 4：用户注册时的邮件配置初始化（低优先级）
**用户故事**：作为一个新注册用户，我想要在注册过程中选择我的偏好语言，并让系统根据我的语言偏好自动初始化邮件相关配置，这样我可以获得更好的本地化体验。

#### 验收标准
1. WHEN 用户注册时 THEN 系统 SHALL 支持接收和存储用户的语言偏好和默认场景选择
2. WHEN 用户选择语言偏好和场景后 THEN 系统 SHALL 将语言偏好和默认场景保存到用户的prompt_config中
3. WHEN 用户注册完成后 THEN 系统 SHALL 在数据库事务中原子性地完成邮件配置初始化
4. WHEN 系统初始化邮件配置时 THEN 系统 SHALL 在同一事务中创建用户记录和邮件配置记录
5. WHEN 系统初始化邮件配置时 THEN 系统 SHALL 使用需求3的YAML模板系统根据用户语言生成配置
6. WHEN 系统初始化邮件配置时 THEN 系统 SHALL 设置默认邮件模式为自动分配模式
7. WHEN 系统初始化邮件配置时 THEN 系统 SHALL 根据语言偏好从YAML模板设置相应的邮件过滤和处理参数
8. WHEN 系统初始化邮件配置时 THEN 系统 SHALL 根据用户语言从YAML模板加载对应的默认提示词
9. WHEN 邮件配置初始化过程中出现任何错误时 THEN 系统 SHALL 回滚整个事务以保证数据一致性
10. WHEN 事务回滚后 THEN 系统 SHALL 返回注册失败错误并记录详细错误日志
11. WHEN 系统查询用户配置时 THEN 系统 SHALL 根据用户语言从YAML模板返回本地化的提示词内容
12. WHEN 系统接收提示词更新请求时 THEN 系统 SHALL 允许用户编辑和保存自定义提示词
13. WHEN 系统查询用户邮件配置时 THEN 系统 SHALL 返回已初始化的配置（包括提示词）
14. IF 系统无法找到用户语言对应的YAML模板 THEN 系统 SHALL 使用默认英语YAML模板
15. IF 系统无法识别用户选择的语言 THEN 系统 SHALL 使用默认语言（英语）进行配置初始化
16. IF 初始化过程中数据库连接中断 THEN 系统 SHALL 确保事务完全回滚不留任何部分数据

### 需求 5：邮件模式配置后端支持（纯前端需求，后续实现）
**用户故事**：作为一个系统管理员，我想要系统能够支持两种邮件模式（自动分配和自定义IMAP），并提供相应的后端配置管理功能，这样可以满足不同用户的安全需求。

**注意**：此需求本质上是纯前端功能，后端只需要通过settings获取配置即可。由于前端代码不在本项目中，此需求标记为后续实现。

#### 验收标准
1. WHEN 系统初始化时 THEN 系统 SHALL 支持 email_mode 配置项（auto_assign 或 custom_imap）
2. WHEN 用户配置为自动分配模式时 THEN 系统 SHALL 为用户生成虚拟邮箱地址：`{username}@{system_domain}`
3. WHEN 用户配置为自定义IMAP模式时 THEN 系统 SHALL 支持完整的IMAP配置参数存储和验证
4. WHEN 系统保存邮件配置时 THEN 系统 SHALL 验证配置的有效性并保存到新的配置结构
5. WHEN 用户尝试修改语言或场景配置时 THEN 系统 SHALL 显示警告提示："修改语言或场景会导致提示词被覆盖，请谨慎修改"
6. WHEN 用户确认修改语言或场景后 THEN 系统 SHALL 从YAML模板重新生成对应的提示词配置
7. WHEN 用户取消修改语言或场景时 THEN 系统 SHALL 保持原有配置不变
8. WHEN 用户访问邮件别名管理界面时 THEN 系统 SHALL 显示用户当前的所有邮件别名列表
9. WHEN 用户添加新邮件别名时 THEN 系统 SHALL 提供别名输入界面并进行实时唯一性验证
10. WHEN 用户输入别名时 THEN 系统 SHALL 实时检查别名是否已被其他用户使用并显示验证结果
11. WHEN 别名验证失败时 THEN 系统 SHALL 显示具体的错误信息（如"别名已被使用"或"格式不正确"）
12. WHEN 用户保存有效的别名时 THEN 系统 SHALL 将别名添加到用户的别名列表中
13. WHEN 用户删除别名时 THEN 系统 SHALL 显示确认对话框并在确认后删除别名
14. WHEN 用户查看别名时 THEN 系统 SHALL 显示别名的完整邮箱地址格式 `{alias}@{system_domain}`
15. WHEN 邮件发送到虚拟邮箱时 THEN 系统 SHALL 通过 Haraka SMTP 服务器接收邮件
16. WHEN Haraka 接收到邮件时 THEN 系统 SHALL 自动推送邮件数据到 Redis 队列
17. WHEN 系统处理 Redis 队列中的邮件时 THEN 系统 SHALL 根据收件人地址映射到对应的用户
18. IF 系统域名未配置 THEN 系统 SHALL 使用默认域名 "aimychats.com"
