# `mp format`

Format Python (`.py`) files using `ruff`.

## Usage

```bash
mp format [OPTIONS] [FILE_PATHS]...
```

## Arguments

*   `FILE_PATHS`: One or more paths to files or directories to format.

## Options

| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--changed-files` | Check all changed files based on a diff with the origin/develop branch instead of providing `FILE_PATHS`. | `bool` | `False` |
| `--quiet` | `-q` | Log less on runtime. | `bool` | `False` |
| `--verbose` | `-v` | Log more on runtime. | `bool` | `False` |

## Examples

### Format specific files
```bash
mp format path/to/file.py path/to/dir
```

### Format changed files
```bash
mp format --changed-files
```