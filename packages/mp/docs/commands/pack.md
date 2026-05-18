# `mp pack`

The `pack` command packages integrations into a SOAR-supported ZIP file, ready to be imported into the Google SecOps platform.

## Usage

```bash
mp pack [COMMAND] [ARGS]...
```

## Commands

### `mp pack integration`

Pack an integration into a SOAR-supported ZIP file.

**Arguments**:
- `INTEGRATION`: The name of the integration to pack. [required]

**Options**:
- `-v, --version FLOAT`: Old version to fetch from the repo (via Git) and create the ZIP.
- `-b, --beta TEXT`: Name of the custom beta integration (renames identifier and display name).
- `-d, --dst PATH`: Destination directory to save the ZIP file. Defaults to the configured `out` directory.
- `--interactive / --non-interactive`: Enable or disable interactive component selection. [default: interactive]

## Examples

### Standard Packaging
Packages the current version of the integration.
```bash
mp pack integration CyberX --non-interactive
```

### Custom Beta Identifier
Creates a ZIP with a custom identifier (e.g., `CyberXBeta`) to avoid conflicts.
```bash
mp pack integration CyberX --beta CyberXBeta --non-interactive
```

### Packaging an Old Version
Safely checks out an older version via Git worktree and packages it.
```bash
mp pack integration CyberX --version 5.0 --non-interactive
```

### Interactive Selection
Select which Actions, Connectors, Jobs, or Widgets to include (requires TTY).
```bash
mp pack integration CyberX
```
