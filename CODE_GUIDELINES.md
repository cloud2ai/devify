# Code Guidelines

This document outlines the coding guidelines for the project to ensure code readability, maintainability, and consistency.

## 1. General Principles

- **PEP 8 Compliance**: Follow [PEP 8](https://peps.python.org/pep-0008/) for general Python code style.
- **PEP 257 Docstring**: Adhere to [PEP 257](https://peps.python.org/pep-0257/) for writing docstrings.
- **Consistent Naming**: Use meaningful, descriptive names for variables, functions, and classes.
- **No Hardcoding**: Avoid hardcoding values that can be configured (e.g., URLs, file paths, database credentials).
- **Commenting**: Use comments to explain "why" something is done, not "what" is done. Keep comments up to date and relevant.

## 2. File Structure

- **Module Docstring**: Each Python file (module) should start with a docstring that briefly explains the module’s purpose and any important details.
  - **Location**: The module-level docstring should be placed directly at the top of the file, before `import` statements.
  - **Example**:
    ```python
    """
    This module provides utilities for interacting with the Celery task queue.
    It includes configurations for the broker and result backend using Redis or RabbitMQ.
    """
    import redis
    import celery
    ```

- **Imports**: Group imports in the following order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library imports
  - **Example**:
    ```python
    import os
    import sys

    import requests

    from my_project import utils
    ```

## 3. Docstrings

- **Style**: Use triple double quotes `"""docstring"""` for all docstrings.
- **Module Docstring**: Should provide a brief summary of the module's functionality, followed by a more detailed explanation if necessary.
- **Class Docstring**: Should describe the purpose of the class and, if applicable, any important methods or attributes.
- **Function/Method Docstring**: Should describe the function’s purpose, parameters, and return values. For functions with side effects, mention those as well.

  - **Function Docstring Example**:
    ```python
    def add(a, b):
        """
        Adds two numbers and returns the result.

        Parameters:
        a (int or float): The first number to add.
        b (int or float): The second number to add.

        Returns:
        int or float: The sum of `a` and `b`.
        """
        return a + b
    ```

  - **Class Docstring Example**:
    ```python
    class TaskManager:
        """
        A class to manage and schedule Celery tasks.

        Attributes:
        broker_url (str): The URL of the message broker.
        backend_url (str): The URL of the result backend.
        """
        def __init__(self, broker_url, backend_url):
            self.broker_url = broker_url
            self.backend_url = backend_url
    ```

## 4. Naming Conventions

- **Variable Names**: Use lowercase with words separated by underscores (e.g., `user_name`, `task_queue`).
- **Function Names**: Use lowercase with words separated by underscores (e.g., `calculate_sum()`, `send_request()`).
- **Class Names**: Use CapitalizedWords (CamelCase) (e.g., `TaskManager`, `UserProfile`).
- **Constants**: Use all uppercase with words separated by underscores (e.g., `MAX_RETRIES`, `API_KEY`).

## 5. Code Formatting

- **Indentation**: Use 4 spaces per indentation level. Do not use tabs.
- **Line Length**: Limit all lines to a maximum of 79 characters. For docstrings, use 72 characters per line.
- **Blank Lines**:
  - Surround top-level function and class definitions with two blank lines.
  - Method definitions inside a class should be surrounded by one blank line.
  - Use blank lines to separate logical sections of code for readability.

## 6. Error Handling

- **Exceptions**: Use `try-except` blocks for handling exceptions. Be specific about the exceptions you catch and avoid using a generic `except` clause.
- **Logging**: Use the `logging` module to log errors, warnings, and information. Avoid using `print()` for logging purposes.

  - **Example**:
    ```python
    try:
        result = some_function()
    except SomeSpecificError as e:
        logging.error("Error occurred: %s", e)
    ```

## 7. Testing

- **Test Files**: All unit test files should be placed in a `tests/` directory.
- **Naming Test Functions**: Use `test_` as a prefix for all test function names (e.g., `test_addition()`).
- **Test Coverage**: Ensure high test coverage, particularly for critical code paths. Use tools like `pytest` and `coverage.py` to check coverage.

## 8. Version Control

- **Commit Messages**: Use clear and descriptive commit messages. Follow the format:
