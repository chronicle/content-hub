# `mp describe action`

## Description

Generate AI-based descriptions for integration actions using Gemini. This command analyzes action scripts and YAML definitions to create detailed metadata, which is saved in
`Resources/ai/ai_description.yaml` within the integration's source directory.

The command supports both built integrations (in the `out/` directory) and source integrations.

## Usage

```bash
mp describe action [ACTION_NAMES]... [OPTIONS]
```

## Arguments

*
`[ACTION_NAMES]...`: Optional list of specific action names to describe. If omitted, all actions in the integration will be described.

## Options

| Option              | Description                                                                                  | Type   | Default |
|:--------------------|:---------------------------------------------------------------------------------------------|:-------|:--------|
| `-i, --integration` | The name of the integration to describe.                                                     | `str`  | `None`  |
| `-a, --all`         | Describe all integrations in the marketplace, or all actions if an integration is specified. | `bool` | `False` |
| `--src`             | Path to a custom source directory containing integrations.                                   | `Path` | `None`  |
| `--override`        | Rewrite actions that already have a description in `ai_description.yaml`.                    | `bool` | `False` |
| `-q, --quiet`       | Reduce logging output.                                                                       | `bool` | `False` |
| `-v, --verbose`     | Increase logging output (shows LLM prompts and responses).                                   | `bool` | `False` |

## Examples

### Describe all actions for a specific integration

```bash
mp describe action --integration aws_ec2
```

### Describe a specific action for an integration

```bash
mp describe action Ping --integration aws_ec2
```

### Describe all actions for all integrations in the marketplace

```bash
mp describe action --all
```

### Describe all actions for a specific integration and override existing descriptions

```bash
mp describe action --all --integration aws_ec2 --override
```

### Describe all integrations in a custom source directory

```bash
mp describe action --all --src /path/to/custom/integrations
```

## AI Metadata Aggregation

When running `mp build`, all generated
`ai_description.yaml` files from the source directories are aggregated into a single JSON file named
`actions_ai_metadata.json`, located in the `out/response_integrations` directory.
