# `mp build`

## Description
Build the Content-Hub integrations or playbooks. This command processes integration/playbook repositories or individual integrations/playbooks, converting them into a deployable format. It also supports deconstructing built integrations/playbooks back into their development source structure.

## Usage
```bash
mp build [SUBCOMMAND] [OPTIONS]
```

## Subcommands

### `integration`
Build specific integrations.

**Usage:**
```bash
mp build integration [INTEGRATIONS]... [OPTIONS]
```

**Arguments:**
- `INTEGRATIONS`: One or more integration names to build.

**Options:**
- `--deconstruct`, `-d`: Deconstruct built integrations instead of building them.
- `--src`: Customize source folder to build or deconstruct from.
- `--dst`: Customize destination folder to build or deconstruct to.
- `--custom-integration`: Build a specific integration from the custom repository.

### `playbook`
Build specific playbooks.

**Usage:**
```bash
mp build playbook [PLAYBOOKS]... [OPTIONS]
```

**Arguments:**
- `PLAYBOOKS`: One or more playbook names to build.

**Options:**
- `--deconstruct`, `-d`: Deconstruct built playbooks instead of building them.
- `--src`: Customize source folder to build or deconstruct from.
- `--dst`: Customize destination folder to build or deconstruct to.

### `repository`
Build entire repositories.

**Usage:**
```bash
mp build repository [REPOSITORIES]... [OPTIONS]
```

**Arguments:**
- `REPOSITORIES`: One or more repository types (`google`, `third_party`, `custom`, `playbooks`).

## Options

The following options are available for all subcommands:

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--quiet` | `-q` | Suppress most logging output during runtime. | `bool` | `False` |
| `--verbose` | `-v` | Enable verbose logging output during runtime. | `bool` | `False` |

## Notes

- The `--src` and `--dst` options cannot be used with the `--custom-integration` option.
- Use `--custom-integration` to build or deconstruct from a managed custom repository for SecOps.
- Use `--src` and `--dst` for building or deconstructing from any other source and destination directories.

## Examples

### Build a specific integration
```bash
mp build integration my_integration
```

### Build a specific playbook
```bash
mp build playbook my_playbook
```

### Build all integrations in the google repository
```bash
mp build repository google
```

### Deconstruct an integration
```bash
mp build integration my_integration --deconstruct
```

### Build an integration with custom source and destination
```bash
mp build integration my_integration --src /path/to/source --dst /path/to/destination
```

---

## Deprecated Usage
The legacy flag-based usage is deprecated and will be removed in a future version.

```bash
# Deprecated:
mp build --integration my_integration
mp build --playbook my_playbook
mp build --repository google
```