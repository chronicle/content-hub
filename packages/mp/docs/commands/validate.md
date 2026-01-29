# `mp validate`

## Description

Validate the marketplace content. This command validates integrations, playbooks, or entire repositories within the content-hub based on specified criteria, such as directory structure, file naming conventions, and required metadata.

## Usage

```bash
mp validate [SUBCOMMAND] [OPTIONS]
```

## Subcommands

### `integration` (alias: `i`)

Validate specific integrations.

**Usage:**

```bash
mp validate integration [INTEGRATIONS]... [OPTIONS]
```

**Arguments:**

- `INTEGRATIONS`: One or more integration names to validate.

### `playbook` (alias: `p`)

Validate specific playbooks.

**Usage:**

```bash
mp validate playbook [PLAYBOOKS]... [OPTIONS]
```

**Arguments:**

- `PLAYBOOKS`: One or more playbook names to validate.

### `repository` (alias: `r`)

Validate entire repositories.

**Usage:**

```bash
mp validate repository [REPOSITORIES]... [OPTIONS]
```

**Arguments:**

- `REPOSITORIES`: One or more repository types (`google`, `third_party`, `playbooks`,
  `all_content`).

## Options

The following options are available for all subcommands:

| Option             | Shorthand | Description                                                                 | Type   | Default |
|:-------------------|:----------|:----------------------------------------------------------------------------|:-------|:--------|
| `--only-pre-build` |           | Execute only pre-build validations checks, skipping the full build process. | `bool` | `False` |
| `--quiet`          | `-q`      | Suppress most logging output during runtime.                                | `bool` | `False` |
| `--verbose`        | `-v`      | Enable verbose logging output during runtime.                               | `bool` | `False` |

## Examples

### Validate specific integrations

```bash
mp validate integration my_integration another_integration --only-pre-build
```

### Validate a specific playbook

```bash
mp validate playbook my_playbook --only-pre-build
```

### Validate all third-party integrations

```bash
mp validate repository third_party --only-pre-build
```

---

## Deprecated Usage

The legacy flag-based usage is deprecated and will be removed in a future version.

```bash
# Deprecated:
mp validate --integration my_integration
mp validate --playbook my_playbook
mp validate --repository google
```