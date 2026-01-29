# `mp build`

Build content from the Content Hub and transform it into a format suitable for the Google SecOps SOAR platform.

## Usage

```bash
mp build [SUBCOMMAND] [OPTIONS]
```

## Subcommands

### `integration`

Build specific response integrations.

**Usage:**

```bash
mp build integration [INTEGRATIONS]... [OPTIONS]
```

**Arguments:**

*   `INTEGRATIONS`: A list of integration names to build.

**Options:**

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--src` | | Customize source folder to build or deconstruct from. | `Path` | `None` |
| `--dst` | | Customize destination folder to build or deconstruct to. | `Path` | `None` |
| `--deconstruct` | `-d` | Deconstruct built integrations instead of building them. | `bool` | `False` |
| `--custom-integration` | | Build a specific integration from the custom repository. | `bool` | `False` |
| `--quiet` | `-q` | Log less on runtime. | `bool` | `False` |
| `--verbose` | `-v` | Log more on runtime. | `bool` | `False` |

### `playbook`

Build specific playbooks.

**Usage:**

```bash
mp build playbook [PLAYBOOKS]... [OPTIONS]
```

**Arguments:**

*   `PLAYBOOKS`: A list of playbook names to build.

**Options:**

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--src` | | Customize source folder to build or deconstruct from. | `Path` | `None` |
| `--dst` | | Customize destination folder to build or deconstruct to. | `Path` | `None` |
| `--deconstruct` | `-d` | Deconstruct built playbooks instead of building them. | `bool` | `False` |
| `--quiet` | `-q` | Log less on runtime. | `bool` | `False` |
| `--verbose` | `-v` | Log more on runtime. | `bool` | `False` |

### `repository`

Build an entire content repository.

**Usage:**

```bash
mp build repository [REPOSITORIES]... [OPTIONS]
```

**Arguments:**

*   `REPOSITORIES`: One or more repository types to build. Options:
    *   `google`: Commercial integrations.
    *   `third_party`: Community and partner integrations.
    *   `custom`: Custom integrations.
    *   `playbooks`: Playbooks.

**Options:**

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--quiet` | `-q` | Log less on runtime. | `bool` | `False` |
| `--verbose` | `-v` | Log more on runtime. | `bool` | `False` |

## Examples

### Build specific integrations
```bash
mp build integration my_integration another_integration
```

### Deconstruct an integration
```bash
mp build integration my_integration --deconstruct
```

### Build a specific playbook
```bash
mp build playbook my_playbook
```

### Build the entire commercial repository
```bash
mp build repository google
```

---

## Deprecated Usage

The following flag-based usage is deprecated and will be removed in future versions. Please use the subcommands above.

```bash
mp build --integration <name>
mp build --playbook <name>
mp build --repository <type>
```
