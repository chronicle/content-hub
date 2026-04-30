# `mp check`

Check and lint Python code within the project. This command allows you to specify files or directories to check, automatically fix minor issues, check only changed files, perform static type checking, and control output verbosity.

## Usage

```bash
mp check [OPTIONS] [FILE_PATHS]...
```

## Arguments

*   `FILE_PATHS`: One or more paths to files or directories to check.

## Options

| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--output-format` | Output serialization format for violations. Options include: `concise`, `full`, `json`, `json-lines`, `junit`, `grouped`, `github`, `gitlab`, `pylint`, `rdjson`, `azure`, `sarif`. | `str` | `full` |
| `--fix` | Fix minor issues in the code that require no action from the user. | `bool` | `False` |
| `--unsafe-fixes` | Fix issues in the code that need to be reviewed by the user. Requires `--fix` to be set. | `bool` | `False` |
| `--changed-files` | Check all changed files based on a diff with the head commit instead of providing `FILE_PATHS`. | `bool` | `False` |
| `--static-type-check` | Perform static type checking on the provided files. | `bool` | `False` |
| `--raise-error-on-violations` | Whether to raise an error (exit code 1) on lint and type check violations. | `bool` | `False` |
| `--quiet` | `-q` | Log less on runtime. | `bool` | `False` |
| `--verbose` | `-v` | Log more on runtime. | `bool` | `False` |

## Examples

### Check specific files
```bash
mp check path/to/file1.py path/to/dir
```

### Check and automatically fix issues
```bash
mp check path/to/files --fix
```

### Check changed files including static type checking
```bash
mp check --changed-files --static-type-check
```