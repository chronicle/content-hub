# `mp config`

Configure persistent settings for the `mp` CLI tool. Settings are stored in `.mp_config` inside your platform user configuration directory (for example, `~/.config/mp-cli-tool/.mp_config` on Linux).

## Usage

```bash
mp config [OPTIONS]
```

## Options

| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--root-path` | Path to the local `content-hub` repository root directory (must exist and be a directory). Defaults to `~/marketplace` until configured. | `str` | `None` |
| `--processes` | Number of worker threads/processes to run in parallel (`1` to `10`, default `5`). | `int` | `None` |
| `--gemini-api-key` | Gemini API key used by `mp describe` commands (takes precedence over the `GEMINI_API_KEY` environment variable). | `str` | `None` |
| `--gemini-concurrency` | Maximum concurrent Gemini requests for `mp describe` (minimum `1`, default `5`). | `int` | `None` |
| `--display-config` | Display the active configuration (masking API keys). | `bool` | `False` |

## Examples

### Point `mp` at your `content-hub` checkout and inspect settings
```bash
mp config --root-path /path/to/content-hub --display-config
```

### Set parallel worker count
```bash
mp config --processes 8
```

### Configure Gemini credentials and concurrency
```bash
mp config --gemini-api-key <YOUR_API_KEY> --gemini-concurrency 5
```
