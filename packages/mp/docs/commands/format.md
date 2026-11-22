# `mp format`

Format Python (`.py`) files using `ruff format`.

## Usage

```bash
mp format [OPTIONS] [FILE_PATHS]...
```

## Arguments

- `FILE_PATHS`: One or more paths to Python (`.py`) files, directories, or bare integration directory names (for example, `active_directory`). Non-Python file paths are ignored.

## Options

| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--changed-files` | Format files changed in the last commit (`git diff HEAD^ HEAD`) instead of providing `FILE_PATHS`. | `bool` | `False` |
| `--quiet / --no-quiet` | Log less on runtime (long option only; no `-q` shorthand on `format`). | `bool` | `False` |
| `--verbose / --no-verbose` | Log more on runtime (long option only; no `-v` shorthand on `format`). | `bool` | `False` |

> [!NOTE]
> `--changed-files` compares `HEAD^` to `HEAD` (the most recent commit). To format uncommitted working-tree edits, pass explicit file or directory paths in `FILE_PATHS`.

## Examples

### Format specific files or directories
```bash
mp format content/response_integrations/third_party/community/my_integration
```

### Format files changed in the last commit
```bash
mp format --changed-files
```
