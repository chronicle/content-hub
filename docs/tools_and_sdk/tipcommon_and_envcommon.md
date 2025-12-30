# Welcome to the Packages Directory!

Hello there, developer! This directory is home to a collection of shared code packages (think of
them as specialized
toolkits) designed to assist you in building and maintaining integrations for the Google SecOps
Content Hub. Our goal is
to simplify common development tasks, promote consistency, and help you create robust and reliable
integrations.

Below, you'll find information about the key packages available here.

## Core Libraries: `TIPCommon` & `EnvironmentCommon`

These are foundational libraries that you'll often use when developing integrations.

* **`TIPCommon`**: This is your go-to library for a wide range of common utilities and
  functionalities that are
  frequently needed when building integrations. It helps you avoid reinventing the wheel and focuses
  on common patterns
  seen in response integrations.
* **`EnvironmentCommon`**: This library provides functionalities that `TIPCommon` depends on, often
  related to handling
  environment-specific configurations or interactions.

### Keeping Up to date (Very Important!)

To benefit from the latest features, bug fixes, and security enhancements, it's crucial to **always
use the most recent
versions** of these packages. You can find the available versions within their respective folders in
this `packages`
directory (e.g., `TIPCommon-x.x.x`, `EnvironmentCommon-x.x.x`).

### How to Add Them to Your Integration

If you need to use `TIPCommon` (and by extension, `EnvironmentCommon`) as a dependency for your
integration, follow
these steps:

1. Identify the latest versions of `TIPCommon` and `EnvironmentCommon` available in this `packages`
   directory.
2. From your integration's root directory, run the following commands, replacing `x.x.x` with the
   actual latest version
   numbers:

   ```shell
   uv add ../../packages/tipcommon/TIPCommon-x.x.x/TIPCommon-x.x.x-py2.py3-none-any.whl
   uv add ../../packages/envcommon/EnvironmentCommon-x.x.x/EnvironmentCommon-x.x.x-py2.py3-none-any.whl
   ```
   > *(Remember to replace `x.x.x` with the correct version numbers you used in the `uv add`
   command.)*

3. This will update your integration's `pyproject.toml` file to include these dependencies. It
   should look something like this:

   ```toml
   [project]
   # ... other project configurations ...

   dependencies = [
       # ... other dependencies ...
       "environmentcommon",
       # ...
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

Please try to avoid using older versions unless absolutely necessary for a specific reason.

### Key Dependency Note

* If you add `TIPCommon` to your project, you **must** also add `EnvironmentCommon`, as `TIPCommon`
  depends on it.
* However, you can use `EnvironmentCommon` on its own if your integration only requires its specific
  functionalities.

### Looking Ahead: Future Installation

We plan to publish these dependencies in the future. This will allow you to install them more
conveniently using `uv`
directly from an online package repository, rather than relying on local wheel files. Stay tuned for
updates on this front!
