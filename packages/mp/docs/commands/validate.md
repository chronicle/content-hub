# `mp validate`

## Description
Validate the marketplace content. This command validates integrations within the marketplace based on specified criteria, such as directory structure, file naming conventions, and required metadata.

## Usage
```bash
mp validate [OPTIONS]
```

## Options

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--repository` | `-r` | Run validations on all integrations in specified repositories. Available types: `google` , `third_party`, `playbook`.  | `[RepositoryType]` | `[]` |
| `--integration` | `-i` | Run validations on a specified integrations | `[str]` | `[]` |
| `--playbook` | `-p` | Run validations on a specified playbook | `[str]` | `[]` |
| `--only-pre-build` | | Execute only pre-build validations checks on the integrations, skipping the full build process. | `bool` | `False` |
| `--quiet` | | Suppress most logging output during runtime. | `bool` | `False` |
| `--verbose` | | Enable verbose logging output during runtime. | `bool` | `False` |

## Examples

### Validate a specific integration
```bash
mp validate --integration my_integration --only-pre-build
```

### Validate a specific playbook
```bash
mp validate --playbook my_playbook --only-pre-build
```

### Validate all third-party integrations
```bash
mp validate --repository third_party --only-pre-build
```
