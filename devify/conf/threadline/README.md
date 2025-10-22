# Threadline Prompts Configuration

## Overview

This directory contains the refactored multi-file prompt configuration system for Threadline. The configuration has been split from a single `prompts.yaml` file into multiple files for better maintainability and extensibility.

## File Structure

```
threadline/
├── languages.yaml           # Supported languages configuration
├── scenarios.yaml          # Scenarios metadata and prompt file paths
├── prompts/                # Prompt templates directory
│   ├── default.yaml       # Default prompts and shared snippets
│   ├── chat.yaml          # Chat scenario prompts
│   └── product_issue.yaml # Product issue tracking prompts
└── prompts.yaml.bak       # Backup of original configuration
```

## Configuration Files

### 1. languages.yaml

Defines the list of supported languages with their display names.

**Structure:**
```yaml
languages:
  - code: zh-CN
    name: 简体中文
    native_name: 简体中文
  - code: en-US
    name: English
    native_name: English
```

### 2. scenarios.yaml

Defines available scenarios with their metadata, descriptions, and prompt file paths.

**Structure:**
```yaml
default_prompt_file: prompts/default.yaml

scenarios:
  chat:
    zh-CN: 日常聊天
    en-US: Daily Chat
    description:
      zh-CN: 处理日常聊天记录和沟通内容
      en-US: Handle daily chat records and communication content
    prompt_file: prompts/chat.yaml
```

**Fields:**
- `default_prompt_file`: Path to the default prompts file (relative to this directory)
- `scenarios`: Dictionary of scenario definitions
  - Each scenario contains:
    - Language-specific names (e.g., `zh-CN`, `en-US`)
    - `description`: Language-specific descriptions
    - `prompt_file`: Path to the scenario's prompt file

### 3. prompts/default.yaml

Contains default prompts and shared snippets that can be referenced in other prompts.

**Structure:**
```yaml
# Shared snippets (can be referenced using {variable_name})
shared:
  zh-CN:
    output_language: "请按照中文输出。"
    no_explanation: "不应提供任何解释或附加内容。"
    # ... more shared snippets

  en-US:
    output_language: "Please output in English."
    # ... more shared snippets

# Common prompts (language-agnostic)
# These prompts are identical for all languages
common:
  email_content_prompt: |
    Prompt text here (always in English, uses en-US shared snippets)
  ocr_prompt: |
    ...

# Language-specific prompts
# Only summary_prompt and summary_title_prompt are customizable per language
zh-CN:
  output_language: 中文
  summary_prompt: |
    ...
  summary_title_prompt: |
    ...

en-US:
  output_language: English
  summary_prompt: |
    ...
  summary_title_prompt: |
    ...
```

**Prompt Types:**
- `email_content_prompt`: Email content organization (COMMON - same for all languages)
- `ocr_prompt`: OCR result processing (COMMON - same for all languages)
- `summary_prompt`: Content summarization (LANGUAGE-SPECIFIC - customizable per language)
- `summary_title_prompt`: Title generation (LANGUAGE-SPECIFIC - customizable per language)

**Shared Snippets:**
Shared snippets are language-specific text fragments that can be referenced in prompts using `{variable_name}` syntax. The system uses **3 optimized shared variables**:

1. **`image_placeholder`**: Image placeholder format
   - Example: `[IMAGE: filename.png]`
   - Usage: Standardized format for representing images in text output

2. **`output_requirements`**: Combined output constraints
   - Includes: Plain text requirement, preserve original meaning, structured output format, no extra explanations
   - Purpose: Ensures consistent output quality and format

3. **`content_processing`**: Combined content handling rules
   - Includes: Content retention requirements, Markdown formatting guidelines
   - Purpose: Defines how to handle and format various content types

**Optimization:** Reduced from 8 variables to 3 variables per language (62.5% reduction), making configuration more maintainable while preserving all functionality.

### 4. prompts/{scenario}.yaml

Scenario-specific prompts. Only define prompts that differ from the defaults.

**Example (prompts/chat.yaml):**
```yaml
zh-CN:
  output_language: 中文
  email_content_prompt: |
    Custom prompt for chat scenario
    Can reference shared snippets: {no_explanation}

en-US:
  output_language: English
```

**Fallback Mechanism:**
- Common prompts (`email_content_prompt`, `ocr_prompt`) are always used from `common` section
- Language-specific prompts can be overridden in scenario files
- If a prompt is not defined in the scenario file, it falls back to the language-specific section in `default.yaml`
- Shared snippets are always loaded from `default.yaml`

**Common Prompts vs Language-Specific Prompts:**
- **Common prompts** (`email_content_prompt`, `ocr_prompt`):
  - Defined once in the `common` section of `default.yaml`
  - Always rendered using English (`en-US`) shared snippets for consistency
  - Identical for all languages and scenarios
  - Cannot be overridden by language-specific or scenario-specific configurations
  - This ensures universal formatting and processing logic

- **Language-specific prompts** (`summary_prompt`, `summary_title_prompt`):
  - Defined per language in language sections of `default.yaml`
  - Rendered using their respective language's shared snippets
  - Can be customized in scenario files per language
  - Allow for culturally appropriate summarization and title generation

## Variable Rendering

Prompts support variable references using `{variable_name}` syntax. Variables are replaced with shared snippets during prompt loading.

**Example:**
```yaml
# In default.yaml shared section:
shared:
  zh-CN:
    no_explanation: "不应提供任何解释或附加内容。"

# In a prompt:
email_content_prompt: |
  Process the email content.
  {no_explanation}

# Rendered result:
# Process the email content.
# 不应提供任何解释或附加内容。
```

**Features:**
- Supports nested references (shared snippets can reference other snippets)
- Language-specific snippets (each language has its own shared section)
- Automatic rendering during prompt loading

## Usage

### Getting Available Languages

```python
from devify.threadline.utils.prompt_config_manager import (
    PromptConfigManager
)

manager = PromptConfigManager()
languages = manager.get_available_languages()
# Returns: {'zh-CN': {'name': '简体中文', 'native_name': '简体中文'}, ...}
```

### Getting Available Scenarios

```python
scenes = manager.get_available_scenes()
# Returns: ['chat', 'product_issue']
```

### Getting Prompt Configuration

```python
prompts = manager.get_prompt_config('chat', 'zh-CN')
# Returns: {
#   'output_language': '中文',
#   'email_content_prompt': '...',
#   'ocr_prompt': '...',
#   'summary_prompt': '...',
#   'summary_title_prompt': '...'
# }
```

### Generating User Configuration

```python
user_config = manager.generate_user_config('zh-CN', 'chat')
# Returns: {
#   'language': 'zh-CN',
#   'scene': 'chat',
#   'output_language': '中文',
#   'email_content_prompt': '...',
#   ...
# }
```

## Adding New Scenarios

1. **Create a new prompt file** in `prompts/` directory (e.g., `prompts/custom_scenario.yaml`)

2. **Define prompts** (only define what differs from defaults):
```yaml
zh-CN:
  output_language: 中文
  email_content_prompt: |
    Custom prompt with {shared_snippets}

en-US:
  output_language: English
```

3. **Register the scenario** in `scenarios.yaml`:
```yaml
scenarios:
  custom_scenario:
    zh-CN: 自定义场景
    en-US: Custom Scenario
    description:
      zh-CN: 场景描述
      en-US: Scenario description
    prompt_file: prompts/custom_scenario.yaml
```

## Adding New Languages

1. **Add language to `languages.yaml`**:
```yaml
languages:
  - code: fr-FR
    name: Français
    native_name: Français
```

2. **Add language sections** to `prompts/default.yaml`:
```yaml
shared:
  fr-FR:
    output_language: "Veuillez produire en français."
    # ... other snippets

fr-FR:
  output_language: Français
  email_content_prompt: |
    ...
```

3. **Add language to scenarios** in `scenarios.yaml`:
```yaml
scenarios:
  chat:
    fr-FR: Chat quotidien
    description:
      fr-FR: Description en français
```

## Migration from Old Configuration

The old `prompts.yaml` has been backed up to `prompts.yaml.bak`. The new system maintains backward compatibility with the same API:

- `get_language_config(language)`: Unchanged
- `get_scene_config(scene, language)`: Unchanged
- `get_prompt_config(scene, language)`: Unchanged
- `generate_user_config(language, scene)`: Unchanged
- `get_available_languages()`: Unchanged
- `get_available_scenes()`: Unchanged

## Benefits of the New Structure

1. **Better Organization**: Each scenario has its own file
2. **Easier Maintenance**: Only define what differs from defaults
3. **Reusability**: Shared snippets reduce duplication
4. **Extensibility**: Easy to add new scenarios and languages
5. **Clarity**: Separation of concerns (metadata, prompts, shared content)
6. **Version Control**: Easier to track changes to individual scenarios
7. **Consistency**: Common prompts ensure identical processing logic across all languages
8. **Flexibility**: Language-specific prompts allow cultural customization where needed

## Notes

- All prompt files use YAML format with UTF-8 encoding
- Shared snippets are rendered recursively (up to 10 iterations to prevent infinite loops)
- Language fallback: If a language is not found, it falls back to `settings.DEFAULT_LANGUAGE`
- Chinese language variants (zh-*) automatically fall back to `zh-CN`

## Recent Optimizations

### Common Prompts (v2.0)

To improve consistency and reduce redundancy, the prompt system now supports **common prompts** that are shared across all languages:

**What Changed:**
- `email_content_prompt` and `ocr_prompt` moved to a `common` section in `default.yaml`
- These prompts are now identical for all languages (written in English)
- They use English shared snippets for consistent formatting
- Cannot be overridden by language or scenario configurations

**Why This Matters:**
- **Consistency**: Email and OCR processing use the same logic regardless of user language
- **Maintainability**: Only one version to update instead of multiple language versions
- **Reliability**: Reduces risk of inconsistencies between language versions
- **Simplicity**: Scenario files no longer need to define these prompts

**What Remains Language-Specific:**
- `summary_prompt`: Different cultures may have different expectations for summaries
- `summary_title_prompt`: Title formats and conventions vary by language
- `output_language`: Used by the system to specify desired output language

**Impact on Existing Scenarios:**
- `chat.yaml` and `product_issue.yaml` have been updated to remove common prompts
- They now only define language-specific summary prompts
- All common prompts automatically use the universal definitions

### Shared Variables Optimization (v2.1)

To further improve maintainability and usability, the shared variables have been consolidated:

**Before (v2.0):** 8 shared variables per language
- `output_language`
- `no_explanation`
- `image_placeholder`
- `plain_text_requirement`
- `preserve_original`
- `markdown_formatting`
- `retain_all_content`
- `structured_output`

**After (v2.1):** 3 optimized shared variables per language
- `image_placeholder` - Image placeholder format
- `output_requirements` - Combined output constraints
- `content_processing` - Combined content handling rules

**Benefits:**
- **Simpler**: 62.5% reduction in variable count
- **Cleaner**: Related constraints grouped logically
- **Easier**: Fewer variables to remember and reference
- **Maintainable**: Updates affect fewer locations
- **Powerful**: Same functionality with better organization

**What Changed:**
Multiple related constraints were intelligently combined into logical groups:
- Output-related constraints → `output_requirements`
- Content handling rules → `content_processing`
- Format definitions remain separate → `image_placeholder`

**Migration Impact:**
All prompts have been updated to use the new optimized variables. No action required for existing code.
