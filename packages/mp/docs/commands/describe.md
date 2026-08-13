# `mp describe`

Commands for creating AI-based descriptions for marketplace content using Gemini. This set of commands analyzes Python scripts and metadata to create detailed documentation and capabilities summaries.

## `mp describe action`

Generate AI-based descriptions for integration actions.

### Usage

```bash
mp describe action [ACTIONS]... [OPTIONS]
```

### Options

| Option               | Shorthand | Description                                                                                  | Type   | Default |
|:---------------------|:----------|:---------------------------------------------------------------------------------------------|:-------|:--------|
| `--integration`      | `-i`      | The name of the integration containing the actions.                                          | `str`  | `None`  |
| `--all`              | `-a`      | Describe all integrations in the marketplace, or all actions if an integration is specified. | `bool` | `False` |
| `--src`              |           | Customize source folder to describe from.                                                    | `path` | `None`  |
| `--dst`              |           | Customize destination folder to save the AI descriptions.                                    | `path` | `None`  |
| `--prompt-overrides` |           | Path to JSON prompt configuration file to override prompts for specific fields.              | `path` | `None`  |
| `--quiet`            | `-q`      | Log less on runtime.                                                                         | `bool` | `False` |
| `--verbose`          | `-v`      | Log more on runtime.                                                                         | `bool` | `False` |
| `--override`         | `-o`      | Rewrite actions that already have a description.                                             | `bool` | `False` |

#### Prompt Overrides Configuration

When `--prompt-overrides` is provided, custom prompt templates and field schema specifications can be defined for individual fields. Supplementary LLM calls are made using these custom prompts and schemas to override specific fields in the baseline description.

Expected JSON Configuration Schema:

```json
{
  "prompt_config": [
    {
      "location": "/path/to/ai_description.md",
      "field_name": "ai_description"
    },
    {
      "location": "/path/to/prompt.md",
      "field_name": "field_with_undefined_schema",
      "schema": {
        "model_name": "Model",
        "type": "string",
        "description": "Description of the field we do not have schema defined in code.",
        "required": true
      }
    }
  ]
}
```

If `--prompt-overrides` is omitted or empty, the original baseline result is returned without modifications.


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
| `--src`         |           | The path to the marketplace. If not provided, the configured path will be used.                | `path` | `None`  |
| `--dst`         |           | The path to save the descriptions to. If not provided, they will be saved in the marketplace.  | `path` | `None`  |
| `--quiet`       | `-q`      | Log less on runtime.                                                                           | `bool` | `False` |
| `--verbose`     | `-v`      | Log more on runtime.                                                                           | `bool` | `False` |
| `--override`    | `-o`      | Rewrite connectors that already have a description.                                            | `bool` | `False` |

## `mp describe job`

Generate AI-based descriptions for integration jobs.

### Usage

```bash
mp describe job [JOBS]... [OPTIONS]
```

### Options

| Option          | Shorthand | Description                                                                                   | Type   | Default |
|:----------------|:----------|:----------------------------------------------------------------------------------------------|:-------|:--------|
| `--integration` | `-i`      | The name of the integration to describe jobs for.                                             | `str`  | `None`  |
| `--all`         | `-a`      | Describe all integrations in the marketplace, or all jobs if an integration is specified.     | `bool` | `False` |
| `--src`         |           | The path to the marketplace. If not provided, the configured path will be used.               | `path` | `None`  |
| `--dst`         |           | The path to save the descriptions to. If not provided, they will be saved in the marketplace. | `path` | `None`  |
| `--quiet`       | `-q`      | Log less on runtime.                                                                          | `bool` | `False` |
| `--verbose`     | `-v`      | Log more on runtime.                                                                          | `bool` | `False` |
| `--override`    | `-o`      | Rewrite jobs that already have a description.                                                 | `bool` | `False` |

## `mp describe integration`

Determine product categories for an integration based on its actions, connectors, and jobs descriptions.

### Usage

```bash
mp describe integration [INTEGRATIONS]... [OPTIONS]
```

### Options

| Option       | Shorthand | Description                                               | Type   | Default |
|:-------------|:----------|:----------------------------------------------------------|:-------|:--------|
| `--all`      | `-a`      | Describe all integrations in the marketplace.             | `bool` | `False` |
| `--src`      |           | Customize source folder to describe from.                 | `path` | `None`  |
| `--dst`      |           | Customize destination folder to save the AI descriptions. | `path` | `None`  |
| `--quiet`    | `-q`      | Log less on runtime.                                      | `bool` | `False` |
| `--verbose`  | `-v`      | Log more on runtime.                                      | `bool` | `False` |
| `--override` | `-o`      | Rewrite integrations that already have a description.     | `bool` | `False` |

## `mp describe all-content`

Describe all content (actions, connectors, jobs, and the integration) for integrations.

### Usage

```bash
mp describe all-content [INTEGRATIONS]... [OPTIONS]
```

### Options

| Option       | Shorthand | Description                                               | Type   | Default |
|:-------------|:----------|:----------------------------------------------------------|:-------|:--------|
| `--all`      | `-a`      | Describe all content for all integrations.                | `bool` | `False` |
| `--src`      |           | Customize source folder to describe from.                 | `path` | `None`  |
| `--dst`      |           | Customize destination folder to save the AI descriptions. | `path` | `None`  |
| `--quiet`    | `-q`      | Log less on runtime.                                      | `bool` | `False` |
| `--verbose`  | `-v`      | Log more on runtime.                                      | `bool` | `False` |
| `--override` | `-o`      | Rewrite content that already have their description.      | `bool` | `False` |

---

## `mp describe-regression-test`

For end-to-end regression testing of AI descriptions against baseline repository metadata, see [describe_regression_test.md](file:///usr/local/google/home/siedovolosyi/repos/content-hub/packages/mp/docs/commands/describe_regression_test.md).