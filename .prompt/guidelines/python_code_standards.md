# Python 代码规范标准

这是一个通用的 Python 代码规范标准，适用于所有 Python 项目。基于 PEP 8 和最佳实践，提供统一的代码风格指导。

## 📝 代码生成规范

### 重要代码规范要求
1. **语言要求**：所有生成的代码必须使用英文
2. **注释要求**：所有代码注释必须使用英文
3. **注释位置**：禁止使用行内注释，所有注释必须在代码上方
4. **代码格式**：遵循 PEP 8 规范，每行不超过 79 字符
5. **导入顺序**：标准库 → 第三方库 → 本地应用，每组之间空一行
6. **文档字符串**：使用英文 docstring 格式

### 代码示例规范
```python
# Correct comment format - above the code
def process_data(data):
    """
    Process the input data and return results.

    Args:
        data: Input data to process

    Returns:
        Processed data result
    """
    # Process the data
    result = perform_processing(data)
    return result

# Incorrect comment format - inline comments
def process_data(data):
    result = perform_processing(data)  # Process data  # ❌ Avoid
    return result
```

## 🏗️ 导入规范

### 导入顺序
```python
import os
import sys
from typing import Dict, List, Optional

import requests
from celery import shared_task, Task
from django.db import models

from myapp.models import MyModel
from myapp.utils import helper_function
```

### 导入格式
```python
# Correct: one import per line
import os
import sys
from typing import Dict, List

# Incorrect: multiple imports on one line
import os, sys  # ❌ Avoid
from typing import Dict, List, Optional  # ✅ Acceptable, but prefer separate lines
```

## 📖 文档字符串规范

### 函数文档字符串
```python
def process_data(data: str, force: bool = False) -> Dict:
    """
    Process the input data and return results.

    This function performs data processing with optional force mode.
    When force is True, it will reprocess even if data already exists.

    Args:
        data (str): Input data to process
        force (bool, optional): Whether to force processing. Defaults to False.

    Returns:
        Dict: Processing results with the following keys:
            - success (bool): Whether processing was successful
            - result (str): Processed data
            - error (str, optional): Error message if failed

    Raises:
        ValueError: If input data is invalid
        ProcessingError: If processing fails

    Example:
        >>> result = process_data("test data", force=True)
        >>> print(result['success'])
        True
    """
    pass
```

### 类文档字符串
```python
class DataProcessor:
    """
    A class for processing various types of data.

    This class provides methods for processing different data formats
    with proper error handling and state management.

    Attributes:
        processor_name (str): Name of the processor
        is_active (bool): Whether the processor is active

    Example:
        >>> processor = DataProcessor("my_processor")
        >>> result = processor.process("data")
    """

    def __init__(self, name: str):
        """
        Initialize the data processor.

        Args:
            name (str): Name of the processor
        """
        self.processor_name = name
        self.is_active = True
```

## 🔤 命名规范

### 变量和函数命名
```python
# Correct: use lowercase with underscores
user_id = "12345"
email_address = "user@example.com"
def process_email_data():
    pass

# Incorrect: use camelCase
userId = "12345"  # ❌ Avoid
emailAddress = "user@example.com"  # ❌ Avoid
def processEmailData():  # ❌ Avoid
    pass
```

### 类命名
```python
# Correct: use PascalCase
class EmailProcessor:
    pass

class DataValidator:
    pass

# Incorrect: use underscores
class email_processor:  # ❌ Avoid
    pass
```

### 常量命名
```python
# Correct: use UPPERCASE with underscores
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30
API_BASE_URL = "https://api.example.com"

# Incorrect: use lowercase
max_retry_count = 3  # ❌ Avoid
```

## 📏 行长度和格式

### 行长度限制
```python
# Correct: lines under 79 characters
logger.info(f"[{self.task_name}] Processing {count} items, "
           f"force: {self.force}")

# Incorrect: lines too long
logger.info(f"[{self.task_name}] Processing {count} items, force: {self.force}, status: {status}, error: {error}")  # ❌ Too long
```

### 函数参数换行
```python
# Correct: break parameters across lines
def process_data(
    data: str,
    force: bool = False,
    timeout: int = 30,
    retry_count: int = 3
) -> Dict:
    pass

# Incorrect: parameters too long
def process_data(data: str, force: bool = False, timeout: int = 30, retry_count: int = 3) -> Dict:  # ❌ Too long
    pass
```

## 💬 注释规范

### 单行注释
```python
# Correct: comments above the code
# Process the data with force mode
result = process_data(data, force=True)

# Incorrect: inline comments
result = process_data(data, force=True)  # Process the data  # ❌ Avoid
```

### 多行注释
```python
# Correct: use multiple single-line comments
# This is a complex operation that requires multiple steps:
# 1. Validate input data
# 2. Process the data
# 3. Save results
result = complex_operation(data)

# Or use docstring
def complex_operation(data):
    """
    This is a complex operation that requires multiple steps:
    1. Validate input data
    2. Process the data
    3. Save results
    """
    pass
```

## 🚫 禁止的反模式

### 1. 行内注释
```python
# ❌ Avoid: inline comments
result = process_data(data)  # Process data
status = get_status()  # Get status
```

### 2. 中文注释
```python
# ❌ Avoid: Chinese comments
def process_data(data):
    # 处理数据
    result = perform_processing(data)
    return result
```

### 3. 过长的行
```python
# ❌ Avoid: lines too long
logger.info(f"[{self.task_name}] Processing {count} items, force: {self.force}, status: {status}, error: {error}, retry: {retry_count}")
```

### 4. 不规范的导入
```python
# ❌ Avoid: incorrect import order
from myapp.models import MyModel
import os
from celery import shared_task
import sys
```

## ✅ 推荐的最佳实践

### 1. 清晰的注释
```python
# Correct: clear English comments
def process_email_attachments(email_id: str) -> List[Dict]:
    """
    Process all attachments for the given email.

    Args:
        email_id: ID of the email to process

    Returns:
        List of processed attachment results
    """
    # Get all attachments for the email
    attachments = get_attachments(email_id)

    # Process each attachment
    results = []
    for attachment in attachments:
        # Skip if already processed
        if attachment.is_processed:
            continue

        # Process the attachment
        result = process_single_attachment(attachment)
        results.append(result)

    return results
```

### 2. 合理的函数长度
```python
# Correct: functions keep reasonable length
def validate_email_data(email_data: Dict) -> bool:
    """
    Validate email data before processing.

    Args:
        email_data: Email data to validate

    Returns:
        True if valid, False otherwise
    """
    # Check required fields
    if not email_data.get('subject'):
        return False

    if not email_data.get('body'):
        return False

    # Check email format
    if not is_valid_email(email_data.get('from_email')):
        return False

    return True
```

### 3. 清晰的变量命名
```python
# Correct: clear variable naming
def process_user_orders(user_id: str) -> Dict:
    """
    Process all orders for a specific user.

    Args:
        user_id: ID of the user

    Returns:
        Processing results dictionary
    """
    # Get user's orders
    user_orders = Order.objects.filter(user_id=user_id)

    # Process each order
    processed_orders = []
    failed_orders = []

    for order in user_orders:
        try:
            # Process the order
            result = process_single_order(order)
            processed_orders.append(result)
        except Exception as e:
            # Log the error
            logger.error(f"Failed to process order {order.id}: {e}")
            failed_orders.append(order.id)

    return {
        'processed_count': len(processed_orders),
        'failed_count': len(failed_orders),
        'processed_orders': processed_orders,
        'failed_orders': failed_orders
    }
```

## 📋 代码规范检查清单

### ✅ 基本规范检查
- [ ] 所有代码使用英文
- [ ] 所有注释使用英文
- [ ] 禁止行内注释
- [ ] 遵循 PEP 8 规范
- [ ] 每行不超过 79 字符

### ✅ 导入规范检查
- [ ] 导入顺序正确（标准库 → 第三方库 → 本地应用）
- [ ] 每组导入之间空一行
- [ ] 每行一个导入（或合理分组）
- [ ] 使用绝对导入

### ✅ 文档字符串检查
- [ ] 所有公共函数都有文档字符串
- [ ] 所有类都有文档字符串
- [ ] 文档字符串包含参数说明
- [ ] 文档字符串包含返回值说明
- [ ] 文档字符串包含异常说明（如适用）

### ✅ 命名规范检查
- [ ] 变量和函数使用小写字母和下划线
- [ ] 类使用驼峰命名
- [ ] 常量使用大写字母和下划线
- [ ] 名称具有描述性

### ✅ 注释规范检查
- [ ] 注释在代码上方
- [ ] 注释使用英文
- [ ] 注释清晰易懂
- [ ] 复杂逻辑有注释说明

这个规范文件可以作为所有 Python 项目的通用标准，确保代码质量和一致性。
