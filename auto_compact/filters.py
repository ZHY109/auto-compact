"""
File filtering logic for auto-compact.
"""

import os
import mimetypes
from pathlib import Path
from typing import Optional, Set

import pathspec

# Binary file signatures (magic bytes)
BINARY_SIGNATURES = {
    b'\x00',  # Null bytes (common in binaries)
    b'\xff\xd8\xff',  # JPEG
    b'\x89PNG',  # PNG
    b'GIF87a',  # GIF
    b'GIF89a',  # GIF
    b'PK\x03\x04',  # ZIP
    b'Rar!',  # RAR
    b'\x1f\x8b',  # GZIP
    b'BZh',  # BZIP2
    b'\xfd7zXZ\x00',  # XZ
}

# Text file extensions to always include
TEXT_EXTENSIONS = {
    '.txt', '.md', '.rst', '.json', '.yaml', '.yml', '.toml',
    '.xml', '.html', '.css', '.js', '.ts', '.jsx', '.tsx',
    '.py', '.rb', '.go', '.rs', '.java', '.kt', '.scala',
    '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',
    '.cs', '.swift', '.m', '.mm', '.sh', '.bash', '.zsh',
    '.ps1', '.bat', '.cmd', '.sql', '.csv', '.tsv',
    '.ini', '.cfg', '.conf', '.env', '.gitignore', '.dockerignore',
    '.dockerfile', '.makefile', '.rakefile', '.gemfile',
    '.vue', '.svelte', '.astro', '.scss', '.sass', '.less',
    '.graphql', '.gql', '.proto', '.thrift', '.dart',
    '.lua', '.php', '.pl', '.pm', '.r', '.ex', '.exs',
    '.erl', '.hrl', '.clj', '.cljs', '.edn', '.lisp', '.lsp',
    '.scm', '.rkt', '.ml', '.mli', '.hs', '.lhs', '.elm',
    '.nim', '.cr', '.d', '.di', '.zig', '.v', '.sv', '.svh',
    '.vhdl', '.vhd', '.verilog', '.vlog',
}


def get_default_ignore_patterns() -> str:
    """
    Get the default ignore patterns from the bundled .compactignore file.

    Returns:
        String content of the default ignore patterns.
    """
    # Try to load from package directory first
    package_dir = Path(__file__).parent.parent
    default_file = package_dir / ".compactignore"

    if default_file.exists():
        return default_file.read_text(encoding='utf-8')

    # Fallback to minimal defaults if file not found
    return """
# Dependencies
node_modules/
__pycache__/
*.pyc
venv/
.venv/

# Version control
.git/

# Binary files
*.so
*.dll
*.exe
*.png
*.jpg
*.jpeg
*.gif
*.zip
*.tar
*.tar.gz

# Lock files
package-lock.json
yarn.lock
poetry.lock
"""


def is_binary_file(file_path: Path, sample_size: int = 8192) -> bool:
    """
    Check if a file is binary by examining its content.

    Args:
        file_path: Path to the file to check.
        sample_size: Number of bytes to sample for binary detection.

    Returns:
        True if the file appears to be binary, False otherwise.
    """
    # Check extension first
    ext = file_path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return False

    # Check MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type:
        if mime_type.startswith('text/'):
            return False
        if mime_type.startswith('application/'):
            # Some application types are text-based
            text_app_types = {
                'application/json', 'application/xml', 'application/javascript',
                'application/xhtml+xml', 'application/typescript',
                'application/x-yaml', 'application/toml',
            }
            if mime_type in text_app_types:
                return False

    # Read sample and check for binary signatures
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(sample_size)

        # Check for known binary signatures
        for sig in BINARY_SIGNATURES:
            if sample.startswith(sig):
                return True

        # Check for null bytes (strong indicator of binary)
        if b'\x00' in sample:
            return True

        # Check ratio of non-printable characters
        # If more than 30% non-printable, consider it binary
        non_printable = sum(1 for b in sample if b < 32 and b not in (9, 10, 13))
        if sample and (non_printable / len(sample)) > 0.3:
            return True

        return False
    except (IOError, OSError):
        return True


class FileFilter:
    """
    File filter that applies ignore patterns and other filtering rules.
    """

    def __init__(
        self,
        ignore_patterns: Optional[str] = None,
        include_hidden: bool = False,
        max_file_size: Optional[int] = None,
    ):
        """
        Initialize the file filter.

        Args:
            ignore_patterns: Gitignore-style patterns to ignore.
                           If None, uses default patterns.
            include_hidden: Whether to include hidden files/directories.
            max_file_size: Maximum file size in bytes. Files larger than
                          this are excluded. None means no limit.
        """
        if ignore_patterns is None:
            ignore_patterns = get_default_ignore_patterns()

        self.spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern,
            ignore_patterns.splitlines()
        )
        self.include_hidden = include_hidden
        self.max_file_size = max_file_size

    def should_ignore(self, file_path: Path, base_path: Path) -> bool:
        """
        Check if a file should be ignored.

        Args:
            file_path: Path to the file to check.
            base_path: Base directory for relative path calculation.

        Returns:
            True if the file should be ignored, False otherwise.
        """
        # Get relative path for pattern matching
        try:
            rel_path = file_path.relative_to(base_path)
        except ValueError:
            return True

        rel_path_str = str(rel_path).replace(os.sep, '/')

        # Check against ignore patterns
        if self.spec.match_file(rel_path_str):
            return True

        # Check for hidden files
        if not self.include_hidden:
            # Check if any part of the path is hidden
            for part in rel_path.parts:
                if part.startswith('.') and part not in ('.', '..'):
                    return True

        # Check file size
        if self.max_file_size is not None and file_path.is_file():
            try:
                if file_path.stat().st_size > self.max_file_size:
                    return True
            except (IOError, OSError):
                return True

        # Check if binary
        if file_path.is_file() and is_binary_file(file_path):
            return True

        return False

    def filter_files(self, base_path: Path) -> list[Path]:
        """
        Get all non-ignored files under the base path.

        Args:
            base_path: Base directory to search.

        Returns:
            List of file paths that pass all filters.
        """
        result = []
        base_path = base_path.resolve()

        for file_path in base_path.rglob('*'):
            if not file_path.is_file():
                continue

            if not self.should_ignore(file_path, base_path):
                result.append(file_path)

        # Sort for consistent output
        return sorted(result)