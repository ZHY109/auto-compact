"""
Entry point for running auto-compact as a module.

Usage: python -m auto_compact [options]
"""

import sys
from auto_compact.cli import main

if __name__ == '__main__':
    sys.exit(main())