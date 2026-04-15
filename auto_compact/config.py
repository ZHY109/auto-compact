"""
Configuration file handling for auto-compact.
"""

import os
from pathlib import Path
from typing import Optional


CONFIG_FILENAMES = ['.compactignore', '.compactignore.global']


def find_config_files(start_path: Optional[Path] = None) -> list[Path]:
    """
    Find all applicable config files, ordered by precedence (lowest to highest).

    Searches for:
    1. User home directory .compactignore
    2. .compactignore files in parent directories (from root to start_path)
    3. .compactignore in start_path (highest precedence)

    Args:
        start_path: Directory to start searching from. Defaults to current directory.

    Returns:
        List of config file paths, ordered by precedence (lowest first).
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path).resolve()

    config_files = []

    # Check user home directory
    home_config = Path.home() / '.compactignore'
    if home_config.exists():
        config_files.append(home_config)

    # Walk up the directory tree from start_path to root
    current = start_path
    parent_configs = []

    while True:
        for filename in CONFIG_FILENAMES:
            config_path = current / filename
            if config_path.exists() and config_path not in config_files:
                # Add at beginning (lower precedence)
                parent_configs.insert(0, config_path)

        parent = current.parent
        if parent == current:  # Reached root
            break
        current = parent

    # Add parent configs (lower precedence first)
    config_files.extend(parent_configs)

    # Check start_path itself (highest precedence)
    for filename in CONFIG_FILENAMES:
        config_path = start_path / filename
        if config_path.exists() and config_path not in config_files:
            config_files.append(config_path)

    return config_files


def load_config_file(config_path: Path) -> str:
    """
    Load a single config file.

    Args:
        config_path: Path to the config file.

    Returns:
        Content of the config file as string.

    Raises:
        IOError: If the file cannot be read.
    """
    return config_path.read_text(encoding='utf-8')


def merge_configs(config_paths: list[Path]) -> str:
    """
    Merge multiple config files into a single set of patterns.

    Later files override earlier files. Each file's patterns are
    concatenated with newlines.

    Args:
        config_paths: List of config file paths (ordered by precedence).

    Returns:
        Merged config content as a single string.
    """
    if not config_paths:
        return ''

    sections = []
    for path in config_paths:
        content = load_config_file(path)
        if content.strip():
            sections.append(content)

    return '\n\n'.join(sections)


def load_ignore_patterns(
    start_path: Optional[Path] = None,
    custom_config: Optional[Path] = None,
) -> str:
    """
    Load ignore patterns from config files.

    Loads and merges patterns from:
    1. User home .compactignore
    2. Parent directory .compactignore files
    3. Current directory .compactignore
    4. Custom config file (if provided)

    Args:
        start_path: Directory to start searching from. Defaults to current directory.
        custom_config: Path to a custom config file (highest precedence).

    Returns:
        Merged ignore patterns as a string.
    """
    config_files = find_config_files(start_path)

    # Add custom config if provided
    if custom_config:
        custom_path = Path(custom_config).resolve()
        if custom_path.exists():
            if custom_path not in config_files:
                config_files.append(custom_path)
        else:
            raise FileNotFoundError(f"Config file not found: {custom_config}")

    return merge_configs(config_files)


def get_effective_config(
    start_path: Optional[Path] = None,
    custom_config: Optional[Path] = None,
    include_default: bool = True,
) -> tuple[str, list[Path]]:
    """
    Get the effective ignore configuration with all sources.

    Args:
        start_path: Directory to start searching from.
        custom_config: Path to a custom config file.
        include_default: Whether to include built-in default patterns.

    Returns:
        Tuple of (merged patterns string, list of config file paths used).
    """
    from auto_compact.filters import get_default_ignore_patterns

    config_files = find_config_files(start_path)

    # Add custom config if provided
    if custom_config:
        custom_path = Path(custom_config).resolve()
        if custom_path.exists():
            if custom_path not in config_files:
                config_files.append(custom_path)

    merged = merge_configs(config_files)

    if include_default:
        # Prepend default patterns
        defaults = get_default_ignore_patterns()
        if merged.strip():
            merged = f"{defaults}\n\n# User patterns:\n{merged}"
        else:
            merged = defaults

    return merged, config_files