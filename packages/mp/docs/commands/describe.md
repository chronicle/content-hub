# `mp describe action`

Generate AI-based descriptions for integration actions using Gemini. This command analyzes action scripts and metadata to create detailed documentation and capabilities summaries.

## Usage

```bash
mp describe action [ACTIONS]... [OPTIONS]
```

## Arguments

*   `ACTIONS`: Optional list of specific action names to describe. If omitted and a specific integration is targeted, all actions in that integration will be described.

## Options

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--integration` | `-i` | The name of the integration containing the actions. | `str` | `None` |
| `--all` | `-a` | Describe all integrations in the marketplace, or all actions if an integration is specified. | `bool` | `False` |
| `--src` | | Customize source folder to describe from. | `Path` | `None` |
| `--override` | | Rewrite actions that already have a description. | `bool` | `False` |
| `--quiet` | `-q` | Log less on runtime. | `bool` | `False` |
| `--verbose` | `-v` | Log more on runtime. | `bool` | `False` |

## Examples

### Describe specific actions in an integration
```bash
mp describe action ping get_logs --integration aws_ec2
```

### Describe all actions in a specific integration
```bash
mp describe action --integration aws_ec2 --all
```

### Describe all actions in the entire marketplace
```bash
mp describe action --all
```

### Describe all actions in a custom source directory
```bash
mp describe action --all --src ./custom_integrations
```