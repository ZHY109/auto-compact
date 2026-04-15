"""
CLI interface for auto-compact.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from auto_compact import __version__
from auto_compact.filters import FileFilter
from auto_compact.config import load_ignore_patterns, get_effective_config
from auto_compact.compact import compact_directory, compact_to_file, estimate_output_size
from auto_compact.tokens import TokenCounter


def create_parser() -> argparse.ArgumentParser:
    """
    Create the argument parser for auto-compact CLI.

    Returns:
        ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog='auto-compact',
        description='Compact local files into a single text file for AI consumption.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  auto-compact                          Compact current directory, output to stdout
  auto-compact . -o output.txt           Compact current directory to output.txt
  auto-compact src -o src.txt            Compact src/ directory to src.txt
  auto-compact . --count-tokens          Compact and show token count estimate
  auto-compact . --include-hidden        Include hidden files in output
  auto-compact . --max-size 100000       Skip files larger than 100KB

Config files:
  .compactignore                         Gitignore-style patterns for files to exclude
                                         Loaded from current directory and parents
  --config custom.ignore                 Use custom config file
        """,
    )

    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Directory to compact (default: current directory)',
    )

    parser.add_argument(
        '-o', '--output',
        metavar='FILE',
        help='Output file path (default: stdout)',
    )

    parser.add_argument(
        '-c', '--config',
        metavar='FILE',
        help='Custom config file (.compactignore style)',
    )

    parser.add_argument(
        '--include-hidden',
        action='store_true',
        help='Include hidden files and directories (those starting with .)',
    )

    parser.add_argument(
        '--max-size',
        type=int,
        metavar='BYTES',
        help='Maximum file size in bytes (skip larger files)',
    )

    parser.add_argument(
        '--count-tokens',
        action='store_true',
        help='Count and display token estimate for output',
    )

    parser.add_argument(
        '--estimate',
        action='store_true',
        help='Estimate output size without generating',
    )

    parser.add_argument(
        '--list-files',
        action='store_true',
        help='List files that would be included (dry run)',
    )

    parser.add_argument(
        '--show-config',
        action='store_true',
        help='Show effective config patterns (for debugging)',
    )

    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress output',
    )

    return parser


def main(args: Optional[list[str]] = None) -> int:
    """
    Main entry point for auto-compact CLI.

    Args:
        args: Command line arguments. If None, uses sys.argv.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    opts = parser.parse_args(args)

    # Validate path
    base_path = Path(opts.path).resolve()
    if not base_path.exists():
        print(f"Error: Path does not exist: {base_path}", file=sys.stderr)
        return 1

    if not base_path.is_dir():
        print(f"Error: Path is not a directory: {base_path}", file=sys.stderr)
        return 1

    # Show config mode
    if opts.show_config:
        patterns, config_files = get_effective_config(base_path, opts.config)
        print("Effective config patterns:")
        print("=" * 40)
        print(f"Config files used: {len(config_files)}")
        for cf in config_files:
            print(f"  - {cf}")
        print()
        print(patterns)
        return 0

    # Load ignore patterns
    try:
        ignore_patterns = load_ignore_patterns(base_path, opts.config)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Create file filter
    file_filter = FileFilter(
        ignore_patterns=ignore_patterns,
        include_hidden=opts.include_hidden,
        max_file_size=opts.max_size,
    )

    # Estimate mode
    if opts.estimate:
        file_count, byte_size = estimate_output_size(base_path, file_filter)
        print(f"Estimated output size:")
        print(f"  Files: {file_count}")
        print(f"  Bytes: {byte_size}")
        print(f"  KB: {byte_size / 1024:.1f}")
        print(f"  MB: {byte_size / 1024 / 1024:.2f}")
        return 0

    # List files mode
    if opts.list_files:
        files = file_filter.filter_files(base_path)
        print(f"Files to include ({len(files)}):")
        for f in files:
            rel_path = f.relative_to(base_path)
            size = f.stat().st_size
            print(f"  {rel_path} ({size} bytes)")
        return 0

    # Create token counter if requested
    token_counter = TokenCounter() if opts.count_tokens else None

    # Compact mode
    try:
        if opts.output:
            output_path = Path(opts.output)
            file_count, byte_size = compact_to_file(
                base_path,
                output_path,
                file_filter=file_filter,
                token_counter=token_counter,
            )

            if not opts.quiet:
                print(f"Compacted {file_count} files to {output_path}")
                print(f"Output size: {byte_size} bytes ({byte_size / 1024:.1f} KB)")

                if opts.count_tokens and token_counter:
                    print()
                    print(token_counter.get_report())
        else:
            # Output to stdout
            file_count, byte_size = compact_directory(
                base_path,
                output=sys.stdout,
                file_filter=file_filter,
                token_counter=token_counter,
            )

            # Print token report to stderr if requested
            if opts.count_tokens and token_counter:
                print("\n" + token_counter.get_report(), file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())