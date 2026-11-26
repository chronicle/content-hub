# `mp check`

Lint Python code with `ruff check` and optionally run static type checking with `ty check`.

## Usage

```bash
mp check [OPTIONS] [FILE_PATHS]...
```

## Arguments

- `FILE_PATHS`: One or more paths to Python (`.py`) files, directories, or bare integration directory names (for example, `active_directory`). Required unless `--changed-files` is set (the two cannot be combined). Non-Python file paths are ignored.

## Options

| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--output-format` | Output serialization format for `ruff` violations (`concise`, `full`, `json`, `json-lines`, `junit`, `grouped`, `github`, `gitlab`, `pylint`, `rdjson`, `azure`, `sarif`). | `str` | `full` |
| `--fix` | Automatically apply safe `ruff` fixes. | `bool` | `False` |
| `--unsafe-fixes` | Apply `ruff` fixes that require human review. Requires `--fix`. | `bool` | `False` |
| `--changed-files` | Check files changed in the last commit (`git diff HEAD^ HEAD`) instead of `FILE_PATHS`. | `bool` | `False` |
| `--static-type-check` | Also run `ty check` static type analysis on the target paths. | `bool` | `False` |
| `--raise-error-on-violations` | Exit with status code `1` (raising warnings as errors) when lint or type violations are found. | `bool` | `False` |
| `--quiet / --no-quiet` | Log less on runtime (long option only; no `-q` shorthand on `check`). | `bool` | `False` |
| `--verbose / --no-verbose` | Log more on runtime (long option only; no `-v` shorthand on `check`). | `bool` | `False` |

> [!IMPORTANT]
> By default, `mp check` emits `LinterWarning` / `TypeCheckerWarning` and exits with code `0`. Pass `--raise-error-on-violations` in CI scripts or automated checks when a non-zero exit status is required on violations. Also note that `--changed-files` inspects `HEAD^..HEAD` (the last commit), so pass explicit `FILE_PATHS` when checking uncommitted working-tree changes.

## Examples

### Check an integration with static type checking and non-zero failure exit
```bash
mp check content/response_integrations/third_party/community/my_integration --static-type-check --raise-error-on-violations
```

### Auto-fix lint issues and emit JSON diagnostics
```bash
mp check path/to/dir --fix --output-format json
```

### Check files modified in the latest commit
```bash
mp check --changed-files --static-type-check --raise-error-on-violations
```
