# `mp check`

## Description
Check and lint Python code within the project. This command allows you to specify files or directories to check, automatically fix minor issues, check only changed files, perform static type checking, and control output verbosity. It ensures code quality and consistency using tools like `ruff` and `ty`.

## Usage
```bash
mp check [OPTIONS] [FILE_PATHS]...
```

## Arguments

| Argument | Description | Type |
| :--- | :--- | :--- |
| `FILE_PATHS` | Path of the files or dirs to check | `[str]` |

## Options

| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--output-format` | Output serialization format for violations. | `CheckOutputFormat` | `FULL` |
| `--fix` | Fix minor issues in the code that require no action from the user. | `bool` | `False` |
| `--unsafe-fixes` | Fix issues in the code that needs to be reviewed by the user. Requires `--fix`. | `bool` | `False` |
| `--changed-files` | Check all changed files based on a diff with the head commit instead of `FILE_PATHS`. | `bool` | `False` |
| `--static-type-check` | Perform static type checking on the provided files. | `bool` | `False` |
| `--raise-error-on-violations` | Whether to raise error on lint and type check violations. | `bool` | `False` |
| `--quiet` | Log less on runtime. | `bool` | `False` |
| `--verbose` | Log more on runtime. | `bool` | `False` |

## Examples

### Check specific files
```bash
mp check path/to/file1.py path/to/dir
```

### Check and fix issues
```bash
mp check path/to/files --fix
```

### Check changed files with static type checking
```bash
mp check --changed-files --static-type-check
```
