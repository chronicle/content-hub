# `mp format`

## Description
Format Python (`.py`) files. This command allows you to specify files or directories for formatting and can also format only the files that have been changed according to the Git history. It uses `ruff` to ensure consistent code style and readability.

## Usage
```bash
mp format [OPTIONS] [FILE_PATHS]...
```

## Arguments

| Argument | Description | Type |
| :--- | :--- | :--- |
| `FILE_PATHS` | Path of the files or dirs to format | `[str]` |

## Options

| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--changed-files` | Format all changed files based on a diff with the origin. | `bool` | `False` |
| `--quiet` | Log less on runtime. | `bool` | `False` |
| `--verbose` | Log more on runtime. | `bool` | `False` |

## Examples

### Format detailed files
```bash
mp format path/to/file.py path/to/dir
```

### Format changed files
```bash
mp format --changed-files
```
