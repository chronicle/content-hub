# How to Contribute

We would love to accept your patches and contributions to this project.

## Before you begin

### Sign our Contributor License Agreement

Contributions to this project must be accompanied by a
[Contributor License Agreement](https://cla.developers.google.com/about) (CLA).
You (or your employer) retain the copyright to your contribution; this simply
gives us permission to use and redistribute your contributions as part of the
project.

If you or your current employer have already signed the Google CLA (even if it
was for a different project), you probably don't need to do it again.
# Contributing to MP

We love your input! We want to make contributing to `mp` as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

### Pull Requests

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Pull Request Guidelines

- Update the README.md or documentation with details of changes to the interface, if applicable
- Update the tests to cover your changes
- Ensure the test suite passes
- Ensure your code passes static type checking and linting
- Keep the PR as focused as possible, if you have multiple features, submit multiple PRs

## Code Style

This project uses:

- [Ruff](https://github.com/charliermarsh/ruff) for linting and formatting
- [MyPy](https://mypy.readthedocs.io/) for static type checking

Before submitting your code, run:

```bash
mp format
mp check --static-type-check
```

## Testing

All new features should include appropriate tests. Run the tests with:

```bash
python -m pytest
```

Additionally, you can use the pre-configured run/debug configurations. When using these, please ensure the correct Python interpreter from the project's virtual environment is selected in the specific run configuration you are using. See [ide_configuration](installation.md#ide-configuration) for the correct interpreter paths.

## Error Handling

To provide a clean and professional user experience, the `mp` CLI hides verbose stack traces by default. 

*   **Global Exception Handling:** We wrap the main Typer application (`main.py`) with a global `try...except` block. If an unhandled exception bubbles up, we print a concise, user-friendly error message. If the user runs the command with the `--verbose` (or `-v`) flag, the full stack trace is printed.
*   **Explicit Exceptions:** Contributors should raise explicit exception types (like `FatalCommandError`) instead of catching errors locally and calling `sys.exit()` themselves. Let the exception bubble up to the global handler.
*   **Multithreaded Operations:** When using `ThreadPoolExecutor` or similar concurrency mechanisms (e.g., in `build_integrations`), **do not** use `pool.map()` directly if it allows errors to bubble up with confusing multiprocess stack traces. Instead, use `concurrent.futures.as_completed()`. Catch exceptions in each thread, log the specific failure (e.g., which integration failed and why), and at the end of the loop, raise a single summarized `FatalCommandError`. This prevents generic thread stack traces from cluttering the terminal.

## License

By contributing, you agree that your contributions will be licensed under the project's [Apache 2.0 License](../LICENSE).

## Code of Conduct

This project follows the Google Open Source Community Guidelines. By participating, you are expected to uphold this code.

## Questions?

Feel free to contact the project maintainers with any questions or concerns.
Visit <https://cla.developers.google.com/> to see your current agreements or to
sign a new one.

### Review our Community Guidelines

This project follows [Google's Open Source Community
Guidelines](https://opensource.google/conduct/).

## Contribution process

### Code Reviews

All submissions, including submissions by project members, require review. We
use [GitHub pull requests](https://docs.github.com/articles/about-pull-requests)
for this purpose.
