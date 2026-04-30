# `mp test`

Run pre-build integration tests.

## Usage

```bash
mp test [OPTIONS]
```

## Options

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--repository` | `-r` | Test all integrations in specified integration repositories. | `list[RepositoryType]` | `[]` |
| `--integration` | `-i` | Test specified integrations. | `list[str]` | `[]` |
| `--raise-error-on-violations` | | Whether to raise an error on lint and type check violations. | `bool` | `False` |
| `--quiet` | `-q` | Log less on runtime. | `bool` | `False` |
| `--verbose` | `-v` | Log more on runtime. | `bool` | `False` |

## Examples

### Test specific integrations
```bash
mp test --integration my_integration --integration another_integration
```

### Test all commercial integrations
```bash
mp test --repository google
```