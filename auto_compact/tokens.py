"""
Token counting utilities for auto-compact.
"""

from pathlib import Path
from typing import Optional

# tiktoken is optional dependency for token counting
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

# Default encoding for most models (GPT-4, GPT-3.5-turbo, Claude)
DEFAULT_ENCODING = "cl100k_base"

# Token counts for different models (approximate context windows)
MODEL_CONTEXT_WINDOWS = {
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-16k": 16384,
    "claude-2": 100000,
    "claude-2.1": 200000,
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "claude-3.5-sonnet": 200000,
}


def get_encoding(encoding_name: Optional[str] = None) -> Optional[tiktoken.Encoding]:
    """
    Get tiktoken encoding for token counting.

    Args:
        encoding_name: Name of the encoding to use. Defaults to cl100k_base.

    Returns:
        tiktoken Encoding object, or None if tiktoken is not available.
    """
    if not HAS_TIKTOKEN:
        return None

    try:
        return tiktoken.get_encoding(encoding_name or DEFAULT_ENCODING)
    except Exception:
        # Try to get by model name
        try:
            return tiktoken.encoding_for_model(encoding_name)
        except Exception:
            return None


def count_tokens(text: str, encoding: Optional[tiktoken.Encoding] = None) -> int:
    """
    Count the number of tokens in a text string.

    Args:
        text: Text to count tokens for.
        encoding: tiktoken encoding to use. If None, uses default.

    Returns:
        Number of tokens. Returns -1 if tiktoken is not available.
    """
    if not HAS_TIKTOKEN:
        # Fallback: estimate ~4 characters per token
        return len(text) // 4

    if encoding is None:
        encoding = get_encoding()

    if encoding is None:
        return len(text) // 4

    return len(encoding.encode(text))


def count_file_tokens(
    file_path: Path,
    encoding: Optional[tiktoken.Encoding] = None
) -> int:
    """
    Count the number of tokens in a file.

    Args:
        file_path: Path to the file to count tokens for.
        encoding: tiktoken encoding to use.

    Returns:
        Number of tokens. Returns -1 if file cannot be read.
    """
    try:
        content = file_path.read_text(encoding='utf-8')
        return count_tokens(content, encoding)
    except (IOError, OSError, UnicodeDecodeError):
        return -1


class TokenCounter:
    """
    Token counter for tracking token counts across multiple files.
    """

    def __init__(self, encoding_name: Optional[str] = None):
        """
        Initialize the token counter.

        Args:
            encoding_name: Name of the encoding to use.
        """
        self.encoding = get_encoding(encoding_name)
        self.total_tokens = 0
        self.file_counts: dict[str, int] = {}

    def count_file(self, file_path: Path) -> int:
        """
        Count tokens in a file and add to totals.

        Args:
            file_path: Path to the file.

        Returns:
            Token count for this file.
        """
        count = count_file_tokens(file_path, self.encoding)

        if count > 0:
            self.total_tokens += count
            self.file_counts[str(file_path)] = count

        return count

    def count_text(self, text: str) -> int:
        """
        Count tokens in a text string and add to totals.

        Args:
            text: Text to count.

        Returns:
            Token count for this text.
        """
        count = count_tokens(text, self.encoding)
        self.total_tokens += count
        return count

    def get_report(self) -> str:
        """
        Get a report of token counts.

        Returns:
            Formatted report string.
        """
        lines = ["Token Count Report", "=" * 40, ""]

        if not HAS_TIKTOKEN:
            lines.append("Note: tiktoken not available, using rough estimate (~4 chars/token)")
            lines.append("")

        lines.append(f"Total tokens: {self.total_tokens}")
        lines.append(f"Files counted: {len(self.file_counts)}")
        lines.append("")

        # Add per-file breakdown
        if self.file_counts:
            lines.append("Per-file breakdown:")
            lines.append("-" * 40)

            # Sort by token count (descending)
            sorted_files = sorted(
                self.file_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )

            for path, count in sorted_files[:20]:  # Show top 20
                # Truncate long paths
                display_path = path if len(path) <= 40 else "..." + path[-37:]
                lines.append(f"{display_path}: {count}")

            if len(sorted_files) > 20:
                remaining = len(sorted_files) - 20
                lines.append(f"... and {remaining} more files")

        lines.append("")
        lines.append("Context window fit:")
        lines.append("-" * 40)

        for model, window in MODEL_CONTEXT_WINDOWS.items():
            percent = (self.total_tokens / window) * 100
            status = "OK" if percent <= 80 else "WARN" if percent <= 95 else "OVER"
            lines.append(f"{model}: {percent:.1f}% [{status}]")

        return "\n".join(lines)

    def get_summary_dict(self) -> dict:
        """
        Get a summary of token counts as a dictionary.

        Returns:
            Dictionary with token count summary.
        """
        return {
            "total_tokens": self.total_tokens,
            "file_count": len(self.file_counts),
            "tiktoken_available": HAS_TIKTOKEN,
            "top_files": sorted(
                self.file_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
        }