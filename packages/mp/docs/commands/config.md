# `mp config`

Configure global settings for the `mp` CLI tool.

## Usage

```bash
mp config [OPTIONS]
```

## Options

| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--root-path` | Configure the path to the content-hub repository root directory. | `str` | `None` |
| `--processes` | Configure the number of processes that can be run in parallel (1-10). | `int` | `None` |
| `--gemini-api-key` | Configure the Gemini API key used for `mp describe`. | `str` | `None` |
| `--gemini-concurrency` | Configure the number of concurrent Gemini requests for action description (minimum 1). | `int` | `None` |
| `--display-config` | Show the current configuration. | `bool` | `False` |

## Examples

### Set marketplace root path
```bash
mp config --root-path /path/to/content-hub
```

### Set number of parallel processes
```bash
mp config --processes 4
```

### Set Gemini API key
```bash
mp config --gemini-api-key your-api-key
```

### Display current configuration
```bash
mp config --display-config
```