# `mp describe`

Commands for creating AI-based descriptions for marketplace content using Gemini. This set of commands analyzes Python scripts and metadata to create detailed documentation and capabilities summaries.

## `mp describe action`

Generate AI-based descriptions for integration actions.

### Usage

```bash
mp describe action [ACTIONS]... [OPTIONS]
```

### Options

| Option          | Shorthand | Description                                                                                  | Type   | Default |
|:----------------|:----------|:---------------------------------------------------------------------------------------------|:-------|:--------|
| `--integration` | `-i`      | The name of the integration containing the actions.                                          | `str`  | `None`  |
| `--all`         | `-a`      | Describe all integrations in the marketplace, or all actions if an integration is specified. | `bool` | `False` |
| `--override`    |           | Rewrite actions that already have a description.                                             | `bool` | `False` |

## `mp describe connector`

Generate AI-based descriptions for integration connectors.

### Usage

```bash
mp describe connector [CONNECTORS]... [OPTIONS]
```

### Options

| Option          | Shorthand | Description                                                                                    | Type   | Default |
|:----------------|:----------|:-----------------------------------------------------------------------------------------------|:-------|:--------|
| `--integration` | `-i`      | The name of the integration to describe connectors for.                                        | `str`  | `None`  |
| `--all`         | `-a`      | Describe all integrations in the marketplace, or all connectors if an integration is specified | `bool` | `False` |
| `--override`    | `-o`      | Rewrite connectors that already have a description.                                            | `bool` | `False` |

## `mp describe job`

Generate AI-based descriptions for integration jobs.

### Usage

```bash
mp describe job [JOBS]... [OPTIONS]
```

### Options

| Option          | Shorthand | Description                                                                               | Type   | Default |
|:----------------|:----------|:------------------------------------------------------------------------------------------|:-------|:--------|
| `--integration` | `-i`      | The name of the integration to describe jobs for.                                         | `str`  | `None`  |
| `--all`         | `-a`      | Describe all integrations in the marketplace, or all jobs if an integration is specified. | `bool` | `False` |
| `--override`    | `-o`      | Rewrite jobs that already have a description.                                             | `bool` | `False` |

## `mp describe integration`

Determine product categories for an integration based on its actions, connectors, and jobs descriptions.

### Usage

```bash
mp describe integration [INTEGRATIONS]... [OPTIONS]
```

### Options

| Option       | Shorthand | Description                                           | Type   | Default |
|:-------------|:----------|:------------------------------------------------------|:-------|:--------|
| `--all`      | `-a`      | Describe all integrations in the marketplace.         | `bool` | `False` |
| `--override` | `-o`      | Rewrite integrations that already have a description. | `bool` | `False` |

## `mp describe all-content`

Describe all content (actions, connectors, jobs, and the integration) for integrations.

### Usage

```bash
mp describe all-content [INTEGRATIONS]... [OPTIONS]
```

### Options

| Option       | Shorthand | Description                                          | Type   | Default |
|:-------------|:----------|:-----------------------------------------------------|:-------|:--------|
| `--all`      | `-a`      | Describe all content for all integrations.           | `bool` | `False` |
| `--override` | `-o`      | Rewrite content that already have their description. | `bool` | `False` |
| `--quiet`    | `-q`      | Log less on runtime.                                 | `bool` | `False` |
| `--verbose`  | `-v`      | Log more on runtime.                                 | `bool` | `False` |