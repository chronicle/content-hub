# Contributing to `mp`

We welcome bug reports, fixes, documentation improvements, and feature proposals for `mp`.

## Before You Begin

### Sign the Contributor License Agreement

Contributions to this project must be accompanied by a [Contributor License Agreement](https://cla.developers.google.com/about) (CLA). You (or your employer) retain the copyright to your contribution; this gives Google permission to use and redistribute your contributions as part of the project.

If you or your employer have already signed the Google CLA, you do not need to sign it again. Visit <https://cla.developers.google.com/> to check your current agreements.

## Development Workflow

1. Fork or branch from `main` (`git checkout -b feat/your-change`).
2. Sync the development environment in `packages/mp`:
   ```bash
   cd packages/mp
   uv sync --dev
   source .venv/bin/activate
   ```
3. Make focused changes and add or update tests under `packages/mp/tests/` and docs under `packages/mp/docs/`.
4. If you modified files in `packages/mp/src/` or `packages/mp/tests/`, bump the package version and verify the lockfile:
   ```bash
   uv version --bump patch
   uv lock --check
   ```
5. Run all quality checks before opening a pull request.

## Code Quality & Testing

`packages/mp` uses:

- [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- [ty](https://docs.astral.sh/ty/) and [Pyrefly](https://pyrefly.org/) for static type checking
- [pytest](https://docs.pytest.org/) and [Hypothesis](https://hypothesis.readthedocs.io/) for testing

From `packages/mp` (with `.venv` activated):

```bash
ruff format <modified_files>
ruff check --output-format grouped
ty check --output-format concise
pyrefly check --min-severity info
pytest tests -n auto --cov
```

Or via `mp` itself:

```bash
mp format <modified_files>
mp check src tests --static-type-check --raise-error-on-violations
```

For IDE interpreter configuration, see [installation.md#ide-configuration](installation.md#ide-configuration).

## Error Handling Conventions

`mp` hides raw tracebacks during normal CLI execution unless `--verbose` (`-v`) is passed:

- **Global Exception Handling**: `src/mp/main.py` wraps `app()` and logs concise errors by default, printing full tracebacks only when verbose mode is active.
- **Explicit Exceptions**: Raise domain exceptions (such as `FatalCommandError` or `typer.Exit(1)`) rather than calling `sys.exit()` deep inside helper modules.
- **Concurrent Operations**: When running `ThreadPoolExecutor` jobs across many integrations or playbooks, collect per-item failures cleanly and report specific item names before exiting non-zero.

## Code Reviews & Community Guidelines

All submissions require review via GitHub pull requests and must follow [Google's Open Source Community Guidelines](https://opensource.google/conduct/).

## License

By contributing, you agree that your contributions will be licensed under the project's [Apache 2.0 License](../LICENSE).
