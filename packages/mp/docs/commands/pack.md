# `mp pack`

Package an integration into a SOAR-supported `.zip` archive (`<identifier><YYYYMMDD>.zip`) ready to import into a Google SecOps environment.

## Usage

```bash
mp pack integration <INTEGRATION> [OPTIONS]
```

## Subcommands

### `mp pack integration`

Builds the integration in a temporary directory, sets `IsCustom = true` on `Integration-*.def`, optionally checks out a historical integration version via a temporary Git worktree or renames identifiers for beta testing, optionally prompts to select components, and writes `<identifier><YYYYMMDD>.zip`.

**Arguments:**

- `INTEGRATION`: *(Required)* Integration directory name or identifier to package.

**Options:**

| Option | Shorthand | Description | Type | Default |
| :--- | :--- | :--- | :--- | :--- |
| `--src` | | Custom source directory containing the integration. Searches configured `content/` by default. | `Path` | `None` |
| `--version` | `-v` | Historical integration version string (for example, `5.0`) located in Git history and checked out via a temporary Git worktree when it differs from the current `pyproject.toml` version. | `str` | `None` |
| `--beta` | `-b` | Custom beta integration identifier and display name to apply to the package. | `str` | `None` |
| `--dst` | `-d` | Destination directory to save the `.zip` file. Defaults to `<marketplace_path>/out/pack`. | `Path` | `None` |
| `--interactive / --non-interactive` | | Enable or disable interactive component selection checkboxes (auto-skipped when non-TTY). | `bool` | `True` |

> [!NOTE]
> On `mp pack integration`, `-v` is shorthand for `--version` (not `--verbose`), and it accepts an integration version number (such as `5.0`), not a raw Git commit SHA or tag. Pass `--non-interactive` in scripts, CI, or automated shells to include all components without interactive prompts.

## Examples

### Standard non-interactive packaging
```bash
mp pack integration CyberX --non-interactive
```

### Package from a custom source directory
```bash
mp pack integration CyberX --src /path/to/my/integrations --non-interactive
```

### Package with a custom beta identifier
```bash
mp pack integration CyberX --beta CyberXBeta --non-interactive
```

### Package an older integration version via Git worktree
```bash
mp pack integration CyberX --version 5.0 --non-interactive
```

### Interactive component selection (requires TTY)
```bash
mp pack integration CyberX
```
