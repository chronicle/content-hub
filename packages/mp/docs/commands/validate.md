# `mp validate`

Validate content (integrations and playbooks) within the Content Hub.

## Usage

```bash
mp validate [SUBCOMMAND] [OPTIONS]
```

## Subcommands

### `integration`

Validate specific response integrations.

**Usage:**

```bash
mp validate integration [INTEGRATIONS]... [OPTIONS]
```

**Arguments:**

*   `INTEGRATIONS`: A list of integrations to validate.

**Options:**

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--only-pre-build` | | Execute only pre-build validations checks, skipping the full build process. | `bool` | `False` |
| `--quiet` | `-q` | Suppress most logging output during runtime. | `bool` | `False` |
| `--verbose` | `-v` | Enable verbose logging output during runtime. | `bool` | `False` |

### `playbook`

Validate specific playbooks.

**Usage:**

```bash
mp validate playbook [PLAYBOOKS]... [OPTIONS]
```

**Arguments:**

*   `PLAYBOOKS`: A list of playbooks to validate.

**Options:**

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--only-pre-build` | | Execute only pre-build validations checks, skipping the full build process. | `bool` | `False` |
| `--quiet` | `-q` | Suppress most logging output during runtime. | `bool` | `False` |
| `--verbose` | `-v` | Enable verbose logging output during runtime. | `bool` | `False` |

### `repository`

Validate entire content repositories.

**Usage:**

```bash
mp validate repository [REPOSITORIES]... [OPTIONS]
```

**Arguments:**

*   `REPOSITORIES`: One or more repository types to validate. Options:
    *   `google`: Commercial integrations.
    *   `third_party`: Community and partner integrations.
    *   `playbooks`: Playbooks.

**Options:**

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--only-pre-build` | | Execute only pre-build validations checks, skipping the full build process. | `bool` | `False` |
| `--quiet` | `-q` | Suppress most logging output during runtime. | `bool` | `False` |
| `--verbose` | `-v` | Enable verbose logging output during runtime. | `bool` | `False` |

## Examples

### Validate a specific integration
```bash
mp validate integration my_integration
```

### Validate a playbook with only pre-build checks
```bash
mp validate playbook my_playbook --only-pre-build
```

### Validate the third-party repository
```bash
mp validate repository third_party
```

---

## Deprecated Usage

The following flag-based usage is deprecated and will be removed in future versions. Please use the subcommands above.

```bash
mp validate --integration <name>
mp validate --playbook <name>
mp validate --repository <type>
```
