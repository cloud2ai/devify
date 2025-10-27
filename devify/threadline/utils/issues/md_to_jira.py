"""
Markdown to JIRA Wiki Converter.

This module provides conversion from Markdown to JIRA Wiki format.
Designed as a standalone utility that can be used independently.

Key features:
- Converts Markdown syntax to JIRA Wiki markup
- Reduces header sizes (h1-h4 -> h4, h5/h6 keep levels) for
  visual harmony
- Handles headers, bold, italic, inline code
- Converts lists (unordered and ordered)
- Processes code blocks with language support
- Converts links and blockquotes
- Preserves existing JIRA syntax

Inspired by: https://github.com/eshack94/md-to-jira
"""
import re


def to_jira_wiki(markdown_text: str) -> str:
    """
    Convert Markdown to JIRA Wiki format.

    This function performs syntax mapping from Markdown to JIRA Wiki
    format. Key transformations include:
    - Headers: h1-h4 -> h4., h5 -> h5., h6 -> h6. (reduced for
      visual coordination)
    - Bold: **text** -> *text*
    - Italic: *text* -> _text_
    - Inline code: `text` -> {{text}}
    - Lists: - -> *, 1. -> #
    - Horizontal rules: --- -> ----
    - Code blocks: ``` -> {code:}

    Args:
        markdown_text: Markdown formatted text to convert

    Returns:
        JIRA Wiki formatted text

    Example:
        >>> text = '# Header\nThis is a paragraph.'
        >>> to_jira_wiki(text)
        'h4. Header\\nThis is a paragraph.'
    """
    if not markdown_text:
        return ""

    """
    First pass: Process code blocks before line-by-line processing.
    This prevents code blocks from being converted to bq. blocks.
    """
    code_block_pattern = r"```(\w+)?\n([\s\S]*?)```"

    code_blocks = []
    def replace_code(match):
        idx = len(code_blocks)
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{idx}__"

    markdown_text = re.sub(code_block_pattern, replace_code, markdown_text)

    lines = markdown_text.split('\n')
    jira_lines = []

    for i, line in enumerate(lines):
        is_empty = not line.strip()

        if is_empty:
            jira_lines.append('')
            continue

        jira_line = line

        if line.startswith('# '):
            """
            Reduce header sizes for better visual coordination in JIRA.
            h1-h4 become h4, h5 and h6 keep their actual sizes.
            """
            jira_line = re.sub(r"^# (.+)$", r"h4. \1", line)
        elif line.startswith('## '):
            jira_line = re.sub(r"^## (.+)$", r"h4. \1", line)
        elif line.startswith('### '):
            jira_line = re.sub(r"^### (.+)$", r"h4. \1", line)
        elif line.startswith('#### '):
            jira_line = re.sub(r"^#### (.+)$", r"h4. \1", line)
        elif line.startswith('##### '):
            jira_line = re.sub(r"^##### (.+)$", r"h5. \1", line)
        elif line.startswith('###### '):
            jira_line = re.sub(r"^###### (.+)$", r"h6. \1", line)

        jira_line = re.sub(r"\*\*(.+?)\*\*", r"*\1*", jira_line)
        jira_line = re.sub(
            r"(?<!\*)\*([^*]+?)\*(?!\*)", r"_\1_", jira_line
        )
        jira_line = re.sub(r"`([^`]+)`", r"{{\1}}", jira_line)

        if re.match(r"^[\s]*[-]\s+", line):
            jira_line = re.sub(r"^[\s]*[-]\s+", "* ", line)
        elif re.match(r"^[\s]*\d+\s*\.\s+", line):
            jira_line = re.sub(r"^[\s]*\d+\s*\.\s+", "# ", line)
        elif line.strip().startswith('>'):
            jira_line = re.sub(r"^> (.+)$", r"bq. \1", line)
        elif line.strip() == '---':
            jira_line = "----"

        jira_line = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)", r"[\1|\2]", jira_line
        )

        jira_lines.append(jira_line)

    jira_text = '\n'.join(jira_lines)

    """
    Second pass: Restore and convert the code blocks.
    """
    for idx, original_code in enumerate(code_blocks):
        placeholder = f"__CODE_BLOCK_{idx}__"

        match = re.match(r"```(\w+)?\n([\s\S]*?)\n```", original_code)
        if match:
            lang = match.group(1) or ""
            code_content = match.group(2)
            converted = f"{{code:{lang}}}\n{code_content}\n{{code}}"
            jira_text = jira_text.replace(placeholder, converted)

    return jira_text


def convert_file_to_jira(markdown_file: str) -> str:
    """
    Convert a Markdown file to JIRA Wiki format.

    Args:
        markdown_file: Path to the Markdown file

    Returns:
        str: JIRA Wiki formatted text

    Raises:
        FileNotFoundError: If the file doesn't exist
    """
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_text = f.read()

    return to_jira_wiki(markdown_text)


def main():
    """
    Command line interface for md-to-jira conversion.

    Usage:
        python md_to_jira.py <input_file>
        python md_to_jira.py <input_file> > <output_file>
    """
    import sys

    if len(sys.argv) < 2:
        print("Usage: python md_to_jira.py <markdown_file>")
        print("Example: python md_to_jira.py README.md")
        sys.exit(1)

    markdown_file = sys.argv[1]

    try:
        jira_text = convert_file_to_jira(markdown_file)
        print(jira_text)
    except FileNotFoundError:
        print(f"Error: File '{markdown_file}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
