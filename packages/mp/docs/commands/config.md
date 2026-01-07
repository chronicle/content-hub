# `mp config`

## Description
Configure script settings. This command allows you to set global configurations for the `mp` tool, such as the path to the marketplace repository and the number of parallel processes.

## Usage
```bash
mp config [OPTIONS]
```

## Options

| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--root-path` | Configure the path to tip-marketplace repository root directory. | `str` | `None` |
| `--processes` | Configure the number of processes can be run in parallel (1-10). | `int` | `None` |
| `--display-config` | Show the current configuration. | `bool` | `False` |

## Examples

### Set marketplace root path
```bash
mp config --root-path /path/to/repo
```

### Set number of parallel processes
```bash
mp config --processes 4
```

### Display current configuration
```bash
mp config --display-config
```

### Configure multiple settings and display
```bash
mp config --root-path . --processes 10 --display-config
```
