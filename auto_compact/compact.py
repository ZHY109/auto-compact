"""
Core compaction logic for auto-compact.
"""

import os
from pathlib import Path
from typing import Optional, TextIO

from auto_compact.filters import FileFilter
from auto_compact.config import load_ignore_patterns
from auto_compact.tokens import TokenCounter


def escape_xml(text: str) -> str:
    """
    Escape special characters for XML content.

    Args:
        text: Text to escape.

    Returns:
        Escaped text safe for XML content.
    """
    # Only escape characters that would break XML structure
    # We keep most content intact for readability
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def generate_file_entry(file_path: Path, base_path: Path) -> str:
    """
    Generate XML entry for a single file.

    Args:
        file_path: Path to the file.
        base_path: Base directory for relative path calculation.

    Returns:
        XML entry string for the file.
    """
    try:
        rel_path = file_path.relative_to(base_path)
        rel_path_str = str(rel_path).replace(os.sep, '/')

        content = file_path.read_text(encoding='utf-8')
        escaped_content = escape_xml(content)

        return f'<file path="{rel_path_str}">\n{escaped_content}\n</file>'
    except (IOError, OSError, UnicodeDecodeError) as e:
        rel_path = file_path.relative_to(base_path)
        rel_path_str = str(rel_path).replace(os.sep, '/')
        return f'<file path="{rel_path_str}">\n<!-- Error reading file: {e} -->\n</file>'


def compact_directory(
    base_path: Path,
    output: Optional[TextIO] = None,
    file_filter: Optional[FileFilter] = None,
    token_counter: Optional[TokenCounter] = None,
    include_header: bool = True,
) -> tuple[int, int]:
    """
    Compact a directory into XML format.

    Args:
        base_path: Directory to compact.
        output: Output stream to write to. If None, returns string.
        file_filter: FileFilter instance to use. If None, creates default.
        token_counter: TokenCounter to track token counts. If None, no counting.
        include_header: Whether to include XML header.

    Returns:
        Tuple of (number of files processed, total bytes written).
    """
    base_path = base_path.resolve()

    if file_filter is None:
        ignore_patterns = load_ignore_patterns(base_path)
        file_filter = FileFilter(ignore_patterns=ignore_patterns)

    # Get filtered files
    files = file_filter.filter_files(base_path)

    total_bytes = 0
    file_count = 0

    # Build output
    lines = []

    if include_header:
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append('<compact>')
        lines.append(f'<!-- Source: {base_path} -->')
        lines.append(f'<!-- Files: {len(files)} -->')
        lines.append('')

    for file_path in files:
        entry = generate_file_entry(file_path, base_path)
        lines.append(entry)
        lines.append('')

        file_count += 1

        if token_counter:
            token_counter.count_file(file_path)

    if include_header:
        lines.append('</compact>')

    output_text = '\n'.join(lines)
    total_bytes = len(output_text.encode('utf-8'))

    if output:
        output.write(output_text)
    else:
        return file_count, total_bytes

    return file_count, total_bytes


def compact_to_file(
    base_path: Path,
    output_path: Path,
    file_filter: Optional[FileFilter] = None,
    token_counter: Optional[TokenCounter] = None,
) -> tuple[int, int]:
    """
    Compact a directory to a file.

    Args:
        base_path: Directory to compact.
        output_path: Path to output file.
        file_filter: FileFilter instance to use.
        token_counter: TokenCounter to track token counts.

    Returns:
        Tuple of (number of files processed, total bytes written).
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        return compact_directory(
            base_path,
            output=f,
            file_filter=file_filter,
            token_counter=token_counter,
        )


def compact_to_string(
    base_path: Path,
    file_filter: Optional[FileFilter] = None,
    token_counter: Optional[TokenCounter] = None,
) -> str:
    """
    Compact a directory to a string.

    Args:
        base_path: Directory to compact.
        file_filter: FileFilter instance to use.
        token_counter: TokenCounter to track token counts.

    Returns:
        XML string representation of the compacted directory.
    """
    lines = []

    class StringOutput:
        def write(self, text: str):
            lines.append(text)

    output = StringOutput()
    compact_directory(
        base_path,
        output=output,
        file_filter=file_filter,
        token_counter=token_counter,
    )

    return ''.join(lines)


def estimate_output_size(base_path: Path, file_filter: Optional[FileFilter] = None) -> tuple[int, int]:
    """
    Estimate the size of the compacted output without generating it.

    Args:
        base_path: Directory to compact.
        file_filter: FileFilter instance to use.

    Returns:
        Tuple of (estimated file count, estimated byte size).
    """
    base_path = base_path.resolve()

    if file_filter is None:
        ignore_patterns = load_ignore_patterns(base_path)
        file_filter = FileFilter(ignore_patterns=ignore_patterns)

    files = file_filter.filter_files(base_path)

    total_bytes = 0

    # Estimate overhead for XML structure
    overhead_per_file = 50  # Rough estimate for <file path="...">\n and </file>\n
    header_size = 200  # XML header and compact tag

    for file_path in files:
        try:
            file_size = file_path.stat().st_size
            # Account for XML escaping (might add ~5% overhead)
            total_bytes += int(file_size * 1.05) + overhead_per_file
        except (IOError, OSError):
            pass

    total_bytes += header_size

    return len(files), total_bytes