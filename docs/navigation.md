# Google SecOps Content Hub's Content Repository Overview

This repository serves as the central hub for Google SecOps content, providing resources for
connecting
Google SecOps with other security tools and platforms. It's designed to help users effectively use,
develop, and
contribute to the Google SecOps ecosystem.

## Repository Structure

The repository is organized into several key directories under the main `content/` directory:

### 1. Content

#### Response Integrations

The `content/response_integrations/` directory contains various connectors that enable Google SecOps
to interact with other security
products and services. Response integrations are divided into two parts:

- `google` - Response integrations developed by Google SecOps Content Hub developers
- `third_party` - Response integrations developed by the community and our partners.
- `power_ups` - Utility Code Packs developed by the Google SecOps Content Hub developers.

#### Playbooks

The `content/playbooks/` directory contains various automated workflows that coordinate triggers,
actions, and logic to streamline incident response, enrich security alerts, and remediate threats
across your security stack.
Playbooks are divided into two parts:

- `google` - Playbooks developed by Google SecOps Content Hub developers
- `third_party` - Playbooks developed by the community and our partners.

### 2. Documentation

The `docs/` directory houses comprehensive documentation:

- **Core concepts** Fundamental principles of Google SecOps response integrations
- **Installation guides** Setup instructions for the repository
- **Development guides** Resources for creating and testing response integrations
- **Code standards** Style guides and best practices

### 3. Packages

The `packages/` directory contains reusable libraries and packages:

- **TIPCommon** A shared library with multiple versions (1.0.10 through 2.0.6)
- **EnvironmentCommon** A support package with versions 1.0.1 and 1.0.2
- **mp** A CLI tool for building, testing, and quality assurance of response integrations
- **integration_testing** A package that enables developers to test response integrations in a "
  black box" manner and run scripts
  locally.

### 4. Tools

The `tools/` directory provides utility scripts and command-line tools to help with development
tasks, including an
integration zipper for packaging.

## Development Environment

The project uses:

- Python 3.11
- `uv` for package management

## Community and Contribution

The repository is designed for community contributions with:

- Detailed contribution guidelines
- Code of conduct for maintaining a welcoming community
- Apache 2.0 licensing

## Current Status

The repository is marked as being in "Preview" status, with a warning that the structure might
change in the future.
Currently, only community response integrations are available in this repository.

This repository appears to be actively maintained, focusing on providing a robust ecosystem for
integrating Google
SecOps with other security tools and platforms through a standardized framework.