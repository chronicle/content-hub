# Welcome to the Packages Directory!

Hello there, developer! This directory is home to a collection of shared code packages (think of them as specialized
toolkits) designed to assist you in building and maintaining integrations for the Google SecOps marketplace. Our goal is
to simplify common development tasks, promote consistency, and help you create robust and reliable integrations.

Below, you'll find information about the key packages available here.

## Core Libraries: `TIPCommon` & `EnvironmentCommon`

These are foundational libraries that you'll often use when developing integrations.

* **`TIPCommon`**: This is your go-to library for a wide range of common utilities and functionalities that are
  frequently needed when building integrations. It helps you avoid reinventing the wheel and focuses on common patterns
  seen in marketplace integrations.
* **`EnvironmentCommon`**: This library provides functionalities that `TIPCommon` depends on, often related to handling
  environment-specific configurations or interactions.

### Keeping Up to date (Very Important!)

To benefit from the latest features, bug fixes, and security enhancements, it's crucial to **always use the most recent
versions** of these packages. You can find the available versions within their respective folders in this `packages`
directory (e.g., `TIPCommon-x.x.x`, `EnvironmentCommon-x.x.x`).

### How to Add Them to Your Integration

If you need to use `TIPCommon` (and by extension, `EnvironmentCommon`) as a dependency for your integration, follow
these steps:

1. Identify the latest versions of `TIPCommon` and `EnvironmentCommon` available in this `packages` directory.
2. From your integration's root directory, run the following commands, replacing `x.x.x` with the actual latest version
   numbers:

   ```shell
   uv add ../../packages/tipcommon/TIPCommon-x.x.x/TIPCommon-x.x.x-py2.py3-none-any.whl
   uv add ../../packages/envcommon/EnvironmentCommon-x.x.x/EnvironmentCommon-x.x.x-py2.py3-none-any.whl
   ```

3. This will update your integration's `pyproject.toml` file to include these dependencies. It should look something
   like this:

   ```toml
   [project]
   # ... other project configurations ...

   dependencies = [
       # ... other dependencies ...
       "environmentcommon",
       "tipcommon",
       # ... other dependencies ...
   ]

   # ... other configurations ...

   [tool.uv.sources]
   # ... other sources ...
   environmentcommon = { path = "../../../packages/envcommon/EnvironmentCommon-x.x.x/EnvironmentCommon-x.x.x-py2.py3-none-any.whl" }
   tipcommon = { path = "../../../packages/tipcommon/TIPCommon-x.x.x/TIPCommon-x.x.x-py2.py3-none-any.whl" }
   # ...
   ```
   *(Remember to replace `x.x.x` with the correct version numbers you used in the `uv add` command.)*

Please try to avoid using older versions unless absolutely necessary for a specific reason.

### Key Dependency Note

* If you add `TIPCommon` to your project, you **must** also add `EnvironmentCommon`, as `TIPCommon` depends on it.
* However, you can use `EnvironmentCommon` on its own if your integration only requires its specific functionalities.

### Looking Ahead: Future Installation

We plan to publish these dependencies in the future. This will allow you to install them more conveniently using `uv`
directly from an online package repository, rather than relying on local wheel files. Stay tuned for updates on this
front!

## Integration Testing: `integration_testing`

This package is your ally for thoroughly testing your marketplace integration scripts locally.

### What It Does

* **Simulate Third-Party Products:** It provides tools to create a "mock" version of the third-party product your
  integration interacts with. This means you can test your integration's logic without needing a live, configured
  instance of the external service.
* **Track Interactions:** It helps you monitor the requests your integration sends and the responses it would receive,
  allowing you to verify its behavior in a controlled "black-box" manner.

This is invaluable for ensuring your integration behaves as expected before deploying it.

### Dive Deeper

For comprehensive details on how to use this package and its features, please check
the [Integration Testing documentation](./integration_testing/README.md).

## Marketplace CLI Tool: `mp` (Your Integration Powerhouse!)

`mp` (short for `marketplace`) is a powerful command-line interface (CLI) tool specifically designed to streamline the
development, testing, and maintenance of your Google SecOps marketplace integrations.

### Key Superpowers (Features)

* **Effortless Integration Building & Deconstruction:** Convert your source code into the format required by the Google
  SecOps Marketplace, or deconstruct a built integration back into its source code format.
* **Automated Code Quality:** Keep your codebase clean and robust. `mp` integrates with tools like Ruff for formatting
  and linting your Python code, and Mypy for static type-checking, helping you catch potential issues early.
* **Streamlined Developer Workflow:** `mp` offers a suite of helpful commands to simplify common development tasks. It
  also leverages `uv` for fast and efficient dependency management.

### Install and Use as a Tool (Recommended)

You can install `mp` once and use it everywhere using `uv`. This is the easiest way to manage the tool:

```bash
# Install from the main branch
uv tool install mp --from git+https://github.com/chronicle/content-hub.git#subdirectory=packages/mp

# Use the tool directly:
mp --help
```

For more details, please refer to the [Marketplace CLI Tool (mp) documentation](./mp/README.md) and the [Installation Guide](./mp/docs/installation.md).

---

We hope these packages and tools make your integration development journey smoother and more productive. Happy coding!
