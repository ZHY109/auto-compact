# Auto-Compact

A Python CLI tool that compacts local files into a single text file, optimized for web-based AI tools to read.

## Installation

```bash
# Clone or download this repository
cd auto-compact

# Install dependencies
pip install pathspec tiktoken

# Or install the package
pip install .
```

## Usage

```bash
# Compact current directory, output to stdout
python -m auto_compact

# Compact to a file
python -m auto_compact . -o output.txt

# Compact a specific directory
python -m auto_compact src -o src.txt

# Count tokens for context window planning
python -m auto_compact . -o output.txt --count-tokens

# Include hidden files
python -m auto_compact . -o output.txt --include-hidden

# Skip large files (over 100KB)
python -m auto_compact . -o output.txt --max-size 100000

# List files that would be included (dry run)
python -m auto_compact . --list-files

# Estimate output size without generating
python -m auto_compact . --estimate

# Use custom config file
python -m auto_compact . -o output.txt --config my-ignore.txt
```

## Output Format

The output uses XML-style tags for clear file boundaries:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<compact>
<!-- Source: /path/to/project -->
<!-- Files: 5 -->

<file path="src/main.py">
def main():
    print("Hello")
</file>

<file path="README.md">
# My Project
</file>

</compact>
```

## Configuration

### .compactignore

Create a `.compactignore` file in your project directory (gitignore-style syntax):

```
# Custom patterns
*.test.js
temp/
large-data.json

# Include a file that's normally ignored
!important.pyc
```

Config files are loaded from:
1. `~/.compactignore` (user home)
2. `.compactignore` in parent directories
3. `.compactignore` in the target directory (highest precedence)

## Default Exclusions

The tool automatically excludes:

| Category | Patterns |
|----------|----------|
| Dependencies | `node_modules/`, `__pycache__/`, `venv/`, `.venv/` |
| Version Control | `.git/`, `.svn/`, `.hg/` |
| IDE/Editors | `.idea/`, `.vscode/`, `*.swp` |
| Build Outputs | `dist/`, `build/`, `*.egg-info/` |
| Lock Files | `package-lock.json`, `yarn.lock`, `poetry.lock` |
| Binary Files | `*.so`, `*.dll`, `*.exe`, `*.png`, `*.jpg`, `*.zip` |
| Secrets | `.env`, `*.pem`, `*.key`, `credentials.json` |

## Token Counting

When using `--count-tokens`, the tool reports:

- Total token count
- Per-file breakdown (top 20 files)
- Context window fit for common models (GPT-4, Claude, etc.)

```
Token Count Report
========================================

Total tokens: 15420
Files counted: 12

Per-file breakdown:
----------------------------------------
src/main.py: 3200
src/utils.py: 2100
...

Context window fit:
----------------------------------------
gpt-4: 188.7% [OVER]
gpt-4-turbo: 12.0% [OK]
claude-3-opus: 7.7% [OK]
```

## CLI Options

| Option | Description |
|--------|-------------|
| `path` | Directory to compact (default: current) |
| `-o, --output` | Output file path (default: stdout) |
| `-c, --config` | Custom config file |
| `--include-hidden` | Include hidden files/directories |
| `--max-size` | Skip files larger than N bytes |
| `--count-tokens` | Show token count estimate |
| `--estimate` | Estimate size without generating |
| `--list-files` | List files to include (dry run) |
| `--show-config` | Show effective config patterns |
| `-q, --quiet` | Suppress progress output |
| `-v, --version` | Show version |

## Examples

### Compact for ChatGPT

```bash
# Compact your project and check if it fits in GPT-4's context
python -m auto_compact . -o project.txt --count-tokens

# If too large, exclude more files
echo "tests/\ndocs/" >> .compactignore
python -m auto_compact . -o project.txt --count-tokens
```

### Share Code with Claude Web

```bash
# Compact specific source files
python -m auto_compact src -o claude-input.txt

# Copy and paste into claude.ai
```

## License

MIT