# Set Up Your Environment!

## Tooling

This repository uses specific tools to streamline development and ensure code quality.

* [**mp CLI**](/docs/tools_and_sdk/mp.md): A command-line tool for building, testing, and managing
  response integrations and playbooks.
* [**Google SecOps SOAR SDK**](/docs/tools_and_sdk/soar_sdk.md): A library providing the necessary
  types and classes for developing integrations.

## JetBrains IDEs Setup Guide

This guide will help you configure JetBrains IDEs (like PyCharm, IntelliJ IDEA with Python plugin)
for development in the Google SecOps Content Hub Repository. Proper IDE configuration will
enhance your development experience with features like code completion, linting, and type checking.

### Project Setup

You have two options, to open the mono repo as a project or to open individual response integrations
as
projects. When opening a single integration as a project, you can set the python interpreter of the
project to be the interpreter found in the virtual environment of the integration.

1. Open the project:

    * Open PyCharm/IntelliJ
    * Select `File > Open` and navigate to your cloned repository
    * Select the repository root folder and click Open

2. Configure Python Interpreter:

    * Make sure to have uv installed in your system by running pip install uv
    * Go to `PyCharm > Settings > Python > Interpreter` (on macOS) or
      `File > Settings > Python > Interpreter` (on Windows/Linux).
    * **Tip:** You can also use the search feature in the Settings/Preferences dialog to find "
      Python Interpreter" quickly.
    * Click the gear icon and select Add
    * Choose python and select whether to generate a new one or select an existing environment if
      one exists. The venv’s name should be `.venv`. You can create it at the base of the project if
      you want. It will be used for running configurations, but when developing an integration, you
      will use the integration’s environment as the project’s/module’s interpreter to have resolved
      dependency imports and run the code locally. You’ll be able to do this easily using the
      recommended plugins
    * Select a base interpreter with version 3.11
    * Click OK to save your settings

## Essential Plugins

**Installation:**

1. Go to `PyCharm > Settings > Plugins` (macOS) or `File > Settings > Plugins` (Windows/Linux).
2. Select the "Marketplace" tab.
3. Search for the plugin name and click **Install**.

### Ruff

**Purpose:** Provides integration with the Ruff linter and formatter

**Configuration:**

* Go to `Settings > Python > Tools > Ruff`
* Enable all options
* Set the execution mode to the interpreter of a specific integration's interpreter you already created
* Enable Run on save by clicking on `All actions on save...`

### Ty

**Purpose:** Type checking integration

**Configuration:**

* Go to `Settings > Python > Tools > ty`
* Enable all options
* Set the execution mode to the interpreter of a specific integration's interpreter you already created


### Pydantic

**Purpose:** Enhanced support for Pydantic models

### PyVenv Manage 2

**Purpose:** Change the IDE's python interpreter

**Setting the project’s interpreter using this plugin**

This plugin is especially important because the repo contains many subprojects with their own
virtual environment. When working on an integration, you can open it from the repo’s root or open
the entire integration as a new project.

* Use `uv sync` or `mp test` to create the integration’s virtual environment.
* Right-click the `your_integration / .venv / bin` folder. (It should have a python logo with a
  small v for “venv”). Then select “Set as project interpreter” or as a module interpreter for
  specific modules if you prefer.

You can repeat the process with every “.venv” in the project for every folder that contains a
“pyproject.toml” file, so you could work on each project with its own separate dependencies

## Rainbow Brackets

**Purpose:** Colorizes matching brackets to improve code readability

### Key Promoter X

**Purpose:** Learn keyboard shortcuts by showing notifications when you use the mouse for actions
that have shortcuts

## Code Style Configuration

*Configuring Code Style*

Enable the ruff plugin to handle import optimization and code reformatting on either save or code
reformat.

As for IDE configurations, if you want, you can configure the following:

* Go to `File > Settings > Editor > Code Style > Python`
    * Set the following options:
        * Tabs and Indents:
            * Use four spaces for indentation
            * Tab size: 4
            * Indent size: 4
        * Spaces:
            * Check appropriate boxes to match our Code Style Guide
        * Imports:
            * Enable Sort imports and Join imports with the same source
            * Set import order to match our style guide (standard library, third-party, local)

*Configuring Line Length*

* Go to `File > Settings > Editor > Code Style`:
    * Set the Right margin (columns) to 88 (to match Black/Ruff default) or 100 if you follow our
      recommendations to use type hints for variables as well, to have more space to write types in
      a row

*Python Integrated Tools*

For consistent file headers:

* Go to `File > Settings > Tools > Python Integrated Tools`
* Under Testing set the Default test running to Pytest
* Under Docstring set the Docstring format to Google

## Run Configurations

Here's an example of how to add one of mp's commands as a run configuration to a project

**Setting Up Run Configurations for Running All Integration Tests**

You can set up mp commands as run configurations

* Go to `Run > Edit` Configurations
* Click the + button and select uv run
* Configure the following:
    * Name: Give it a descriptive name like "All Tests"
    * Run: Select Module
    * Modules: set to mp
    * Arguments: Add your arguments for mp. For this example, test `--repository third_party`
    * Python interpreter: Select the uv interpreter that was configured earlier
    * Click OK to save

It is highly recommended to read the documentation for these tools to understand the full
development workflow.
