# `mp build`

## Description

Build the Content-Hub integrations or playbooks. This command processes integration/playbook repositories or individual integrations/playbooks, converting them into a deployable format. It also supports deconstructing built integrations/playbooks back into their development source structure.

## Usage

```bash
mp build [OPTIONS]
```

## Options

| Option                 | Shorthand | Description                                                                                                                                                      | Type               | Default |
|:-----------------------|:----------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------|:--------|
| `--repository`         | `-r`      | Build all integrations/playbooks in specified repositories. Available types: `google`, `third_party`, `custom` (integration repos), `playbook` (playbooks repo). | `[RepositoryType]` | `[]`    |
| `--integration`        | `-i`      | Build a specified integration                                                                                                                                    | `[str]`            | `[]`    |
| `--playbook`           | `-p`      | Build a specified playbook                                                                                                                                       | `[str]`            | `[]`    |
| `--deconstruct`        | `-d`      | Deconstruct built integrations or playbooks instead of building them.                                                                                            | `bool`             | `False` |
| `--src`                |           | Customize source folder to build or deconstruct from.                                                                                                            | `Path`             | `None`  |
| `--dst`                |           | Customize destination folder to build or deconstruct to.                                                                                                         | `Path`             | `None`  |
| `--custom-integration` |           | Build integration from the default custom repository.                                                                                                            | `bool`             | `False` |
| `--quiet`              |           | Log less on runtime.                                                                                                                                             | `bool`             | `False` |
| `--verbose`            |           | Log more on runtime.                                                                                                                                             | `bool`             | `False` |

## Examples

### Build a specific integration

```bash
mp build --integration my_integration
```

### Build a specific playbook

```bash
mp build --playbook my_playbook
```

### Build all integrations in google repository

```bash
mp build --repository google
```

### Build all playbooks

```bash
mp build --repository playbook
```

### Deconstruct an integration

```bash
mp build --integration my_integration --deconstruct
```

### Deconstruct a playbook

```bash
mp build --playbook my_playbook --deconstruct
```

### Build an integration with custom source and destination

```bash
mp build --integration my_integration --src /path/to/source --dst /path/to/destination
```
