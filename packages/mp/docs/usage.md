# Usage Guide

This guide provides an index of commands and global options in the `mp` CLI.

For a high-level overview, see the [Main README](../README.md).

## Global Options

These options apply at the root `mp` invocation:

| Option | Shorthand | Description |
| :--- | :--- | :--- |
| `--version` | `-V` | Print the installed `mp` version and exit. |
| `--verbose` | `-v` | Enable verbose debug output (pass `--verbose`/`-v` directly on subcommands that define their own verbosity flags). |
| `--quiet` | `-q` | Suppress non-error output (pass `--quiet`/`-q` directly on subcommands that define their own verbosity flags). Cannot be combined with `--verbose`. |
| `--install-completion` | | Install shell tab-completion for the current shell. |
| `--show-completion` | | Print the shell tab-completion script. |
| `--help` | | Show help output and exit. |

## Command Index

- [**Build**](commands/build.md): Build or deconstruct integrations, playbooks, or full repositories (`mp build`).
- [**Check**](commands/check.md): Lint (`ruff`) and type-check (`ty`) Python code (`mp check`).
- [**Config**](commands/config.md): Configure `mp` settings (`mp config`).
- [**Describe**](commands/describe.md): Generate AI action descriptions.
- [**Describe Regression Test**](commands/describe_regression_test.md): Run regression testing on AI-generated metadata.
- [**Environment Sync (`login`, `push`, `pull`)**](commands/dev_env.md): Authenticate to a SecOps tenant and push or pull integrations, playbooks, views, custom fields, and alert grouping rules.
- [**Format**](commands/format.md): Format Python code with `ruff format` (`mp format`).
- [**Pack**](commands/pack.md): Package integrations into SOAR-importable ZIP files (`mp pack`).
- [**Self**](commands/self.md): Upgrade `mp` from the `content-hub` repository (`mp self update`).
- [**Test**](commands/test.md): Run pre-build integration `pytest` suites (`mp test`).
- [**Validate**](commands/validate.md): Validate integration and playbook structure, metadata, and release hygiene (`mp validate`).

## General Usage

To inspect available commands or subcommand flags at any time, run:

```bash
mp --help
mp <command> --help
```

> [!NOTE]
> **Windows Users**: Please use the `wmp` command (for example, `wmp --help`) instead of `mp` to avoid conflicts with default PowerShell system aliases.
