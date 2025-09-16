# 基于 Models.py 生成 Views.py CRUD 方法的提示词模板

这个模板用于根据 `models.py` 中的特定模型对象，生成对应的 `views.py` 中的 CRUD 方法。

## 使用说明

1. 提供 `models.py` 文件路径和具体的模型类名
2. 系统会分析该模型的结构、字段类型、关系等
3. 生成对应的 APIView 类，包含完整的 CRUD 方法
4. 自动适配现有的项目结构和代码风格

## 提示词模板

```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

要求：
1. 生成完整的 APIView 类，包含 get、post、put、patch、delete 方法
2. 包含适当的权限控制、分页、搜索、过滤功能
3. 添加完整的 Swagger 文档注解
4. 包含错误处理和日志记录
5. 遵循项目的代码风格和命名规范（使用 APIView 而不是 ViewSet）
6. 如果需要，同时生成对应的 serializers.py 文件

请分析模型结构并生成相应的代码。
```

## 1. 基础提示词模板

### 简单版本
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

要求：
1. 生成完整的 APIView 类，包含 get、post、put、patch、delete 方法
2. 包含适当的权限控制、分页、搜索、过滤功能
3. 添加完整的 Swagger 文档注解
4. 包含错误处理和日志记录
5. 遵循项目的代码风格和命名规范

请分析模型结构并生成相应的代码。
```

### 详细版本
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

具体要求：
1. **APIView 结构**：
   - 生成完整的 APIView 类
   - 包含 get、post、put、patch、delete 方法
   - 添加适当的权限控制（IsAuthenticated）
   - 配置分页、搜索、过滤功能

2. **Swagger 文档**：
   - 使用 @extend_schema 装饰器
   - 包含详细的参数说明和响应格式
   - 添加适当的错误响应文档

3. **错误处理**：
   - 统一的错误响应格式
   - 适当的 HTTP 状态码
   - 详细的错误日志记录

4. **代码风格**：
   - 遵循项目的代码风格
   - 使用适当的注释
   - 遵循 Django REST Framework 最佳实践

5. **如果需要**：
   - 同时生成对应的 serializers.py 文件
   - 包含创建、更新、完整显示等不同用途的序列化器

请分析模型结构并生成相应的代码。
```

## 2. 针对特定场景的提示词模板

### 场景1：生成 APIView + Serializers
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 和 serializers.py 文件。

模型文件路径: {models_file_path}
模型类名: {ModelName}

要求：
1. **views.py**：
   - 生成完整的 APIView 类，包含所有 CRUD 方法
   - 添加适当的权限控制、分页、搜索、过滤功能
   - 包含完整的 Swagger 文档注解
   - 添加错误处理和日志记录

2. **serializers.py**：
   - 生成主序列化器（用于显示）
   - 生成创建序列化器（用于创建）
   - 生成更新序列化器（用于更新）
   - 包含适当的验证规则
   - 处理关联字段和选择字段

请分析模型结构并生成相应的代码。
```

### 场景2：只生成 APIView
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 APIView 类。

模型文件路径: {models_file_path}
模型类名: {ModelName}

要求：
1. 生成完整的 APIView 类
2. 包含 get、post、put、patch、delete 方法
3. 添加适当的权限控制（IsAuthenticated）
4. 配置分页、搜索、过滤功能
5. 包含完整的 Swagger 文档注解
6. 添加错误处理和日志记录
7. 遵循项目的代码风格和命名规范

请分析模型结构并生成相应的代码。
```

### 场景3：生成 APIView + 自定义方法
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 APIView 类。

模型文件路径: {models_file_path}
模型类名: {ModelName}

要求：
1. 生成完整的 APIView 类，包含所有 CRUD 方法
2. 添加以下自定义方法：
   - bulk_update: 批量更新
   - bulk_delete: 批量删除
   - custom_action: 根据模型特点添加的自定义动作
3. 包含适当的权限控制、分页、搜索、过滤功能
4. 添加完整的 Swagger 文档注解
5. 包含错误处理和日志记录

请分析模型结构并生成相应的代码。
```

## 3. 针对特定字段类型的提示词模板

### 包含外键关系的模型
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

特别注意：
- 该模型包含外键关系，请正确处理关联字段
- 在序列化器中包含关联对象的详细信息
- 在 APIView 中添加适当的 select_related 优化
- 考虑关联对象的权限控制

要求：
1. 生成完整的 APIView 类，包含所有 CRUD 方法
2. 正确处理外键字段的序列化和反序列化
3. 添加适当的数据库查询优化
4. 包含完整的 Swagger 文档注解
5. 添加错误处理和日志记录

请分析模型结构并生成相应的代码。
```

### 包含选择字段的模型
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

特别注意：
- 该模型包含选择字段（choices），请正确处理
- 在序列化器中添加选择字段的显示方法
- 在 Swagger 文档中正确描述选择字段的选项

要求：
1. 生成完整的 APIView 类，包含所有 CRUD 方法
2. 正确处理选择字段的验证和显示
3. 在序列化器中添加 get_{field}_display 方法
4. 包含完整的 Swagger 文档注解
5. 添加错误处理和日志记录

请分析模型结构并生成相应的代码。
```

### 包含 JSON 字段的模型
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

特别注意：
- 该模型包含 JSON 字段，请正确处理
- 添加适当的 JSON 字段验证
- 考虑 JSON 字段的搜索和过滤功能

要求：
1. 生成完整的 APIView 类，包含所有 CRUD 方法
2. 正确处理 JSON 字段的序列化和验证
3. 添加 JSON 字段的搜索和过滤功能
4. 包含完整的 Swagger 文档注解
5. 添加错误处理和日志记录

请分析模型结构并生成相应的代码。
```

## 4. 针对特定业务场景的提示词模板

### 用户相关模型
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

特别注意：
- 该模型与用户相关，请添加用户数据隔离
- 在查询中自动过滤当前用户的数据
- 在创建时自动设置当前用户
- 考虑用户权限控制

要求：
1. 生成完整的 APIView 类，包含所有 CRUD 方法
2. 添加用户数据隔离（只显示当前用户的数据）
3. 在创建时自动设置 user 字段
4. 添加适当的权限控制
5. 包含完整的 Swagger 文档注解
6. 添加错误处理和日志记录

请分析模型结构并生成相应的代码。
```

### 状态机模型
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

特别注意：
- 该模型包含状态字段，请正确处理状态转换
- 添加状态验证和状态转换逻辑
- 考虑状态相关的业务规则

要求：
1. 生成完整的 APIView 类，包含所有 CRUD 方法
2. 添加状态转换的自定义方法
3. 添加状态验证逻辑
4. 包含状态相关的 Swagger 文档
5. 添加错误处理和日志记录

请分析模型结构并生成相应的代码。
```

## 5. 完整的代码生成提示词模板

### 标准 CRUD 生成
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成完整的 CRUD 代码。

模型文件路径: {models_file_path}
模型类名: {ModelName}

请生成以下文件：

1. **serializers.py**：
   - {ModelName}Serializer（主序列化器，用于显示）
   - {ModelName}CreateSerializer（创建序列化器）
   - {ModelName}UpdateSerializer（更新序列化器）
   - 包含适当的验证规则和字段处理

2. **views.py**：
   - {ModelName}APIView（完整的 APIView）
   - 包含 get、post、put、patch、delete 方法
   - 添加适当的权限控制、分页、搜索、过滤功能
   - 包含完整的 Swagger 文档注解
   - 添加错误处理和日志记录

3. **urls.py**：
   - 配置 APIView 的路由
   - 使用 Django 的 path 函数

4. **admin.py**：
   - 配置 Django 管理后台
   - 添加适当的显示字段和过滤选项

要求：
- 遵循项目的代码风格和命名规范
- 包含完整的错误处理
- 添加适当的注释和文档
- 考虑性能优化（如 select_related、prefetch_related）
- 包含适当的权限控制

请分析模型结构并生成相应的代码。
```

## 6. 使用示例

### 示例1：生成 AudioFile 模型的 CRUD
```
请根据以下 models.py 文件中的 AudioFile 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: /home/ubuntu/workspace/liangyi_workspace/liangyi/liangyi/speechtotext/models.py
模型类名: AudioFile

要求：
1. 生成完整的 APIView 类，包含 get、post、put、patch、delete 方法
2. 包含适当的权限控制、分页、搜索、过滤功能
3. 添加完整的 Swagger 文档注解
4. 包含错误处理和日志记录
5. 遵循项目的代码风格和命名规范

请分析模型结构并生成相应的代码。
```

### 示例2：生成带序列化器的完整 CRUD
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成完整的 CRUD 代码。

模型文件路径: {models_file_path}
模型类名: {ModelName}

请生成：
1. serializers.py - 包含所有必要的序列化器
2. views.py - 包含完整的 APIView
3. urls.py - 配置路由
4. admin.py - 配置管理后台

要求：
- 遵循 Django REST Framework 最佳实践
- 包含完整的 Swagger 文档
- 添加适当的错误处理
- 考虑性能优化

请分析模型结构并生成相应的代码。
```

## 7. 高级功能和最佳实践

### 验证和错误处理
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

特别注意：
- 实现完整的验证和错误处理机制
- 使用 serializer.is_valid(raise_exception=True) 进行验证
- 实现字段级验证和对象级验证
- 添加适当的 ValidationError 处理
- 考虑嵌套序列化器的验证

要求：
1. 生成完整的 APIView 类，包含所有 CRUD 方法
2. 实现完整的验证机制（字段级和对象级）
3. 添加详细的错误处理和响应
4. 包含完整的 Swagger 文档注解
5. 添加错误处理和日志记录

请分析模型结构并生成相应的代码。
```

### 分页和过滤
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

特别注意：
- 实现完整的分页功能
- 添加搜索和过滤功能
- 使用 DjangoFilterBackend 进行复杂过滤
- 实现排序功能
- 考虑性能优化

要求：
1. 生成完整的 APIView 类，包含所有 CRUD 方法
2. 实现分页、搜索、过滤、排序功能
3. 添加适当的性能优化
4. 包含完整的 Swagger 文档注解
5. 添加错误处理和日志记录

请分析模型结构并生成相应的代码。
```

### 权限和认证
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

特别注意：
- 实现细粒度的权限控制
- 添加对象级权限检查
- 实现自定义权限类
- 考虑不同用户角色的访问控制
- 添加适当的认证机制

要求：
1. 生成完整的 APIView 类，包含所有 CRUD 方法
2. 实现完整的权限控制机制
3. 添加对象级权限检查
4. 包含完整的 Swagger 文档注解
5. 添加错误处理和日志记录

请分析模型结构并生成相应的代码。
```

### 缓存和性能优化
```
请根据以下 models.py 文件中的 {ModelName} 模型，生成对应的 views.py 中的 CRUD 方法。

模型文件路径: {models_file_path}
模型类名: {ModelName}

特别注意：
- 实现适当的缓存策略
- 使用 select_related 和 prefetch_related 优化查询
- 添加数据库查询优化
- 考虑分页性能
- 实现适当的缓存失效机制

要求：
1. 生成完整的 APIView 类，包含所有 CRUD 方法
2. 实现性能优化和缓存策略
3. 添加数据库查询优化
4. 包含完整的 Swagger 文档注解
5. 添加错误处理和日志记录

请分析模型结构并生成相应的代码。
```

## 8. 注意事项

### 代码风格要求
- 代码内注释使用英文
- 遵循项目的命名规范
- 保持代码简洁和可读性
- 添加适当的类型提示
- 使用 DRF 最佳实践

### 功能要求
- 包含完整的 CRUD 操作
- 添加适当的权限控制
- 包含分页、搜索、过滤功能
- 添加完整的 Swagger 文档
- 包含错误处理和日志记录
- 实现验证和错误处理机制

### 性能优化
- 使用 select_related 和 prefetch_related
- 添加适当的数据库索引
- 考虑查询优化
- 添加适当的缓存策略
- 实现分页性能优化

### 安全考虑
- 实现适当的权限控制
- 添加输入验证和清理
- 防止 SQL 注入和 XSS 攻击
- 实现适当的认证机制
- 添加对象级权限检查

### 错误处理最佳实践
- 使用 `serializer.is_valid(raise_exception=True)` 进行验证
- 实现字段级和对象级验证
- 添加适当的 ValidationError 处理
- 使用统一的错误响应格式
- 添加详细的错误日志记录

### 验证最佳实践
- 实现字段级验证方法（如 `validate_field_name`）
- 实现对象级验证方法（`validate`）
- 使用自定义验证器
- 添加适当的错误消息
- 考虑嵌套序列化器的验证

这个模板提供了多种场景下的提示词模板，可以根据具体的模型特点和业务需求选择合适的模板使用。