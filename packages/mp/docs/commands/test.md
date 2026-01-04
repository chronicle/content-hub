# `mp test`

## Description
Run pre-build integration tests. This command executes integration tests to validate the functionality of your integrations before they are built.

## Usage
```bash
mp test [OPTIONS]
```

## Options

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--repository` | `-r` | Test all integrations in specified integration repositories | `[RepositoryType]` | `[]` |
| `--integration` | `-i` | Test a specified integration | `[str]` | `[]` |
| `--raise-error-on-violations` | | Whether to raise error on lint and type check violations | `bool` | `False` |
| `--quiet` | | Log less on runtime. | `bool` | `False` |
| `--verbose` | | Log more on runtime. | `bool` | `False` |

## Examples

### Test a specific integration
```bash
mp test --integration my_integration
```

### Test all commercial integrations
```bash
mp test --repository google
```
