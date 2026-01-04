# GitHub Actions Library

Welcome to the Google SecOps Content Hub Actions library. We provide custom GitHub Actions to help
you automate your content development and deployment workflows.

## Available Actions

### 1. Push Custom Integrations

**Link:** [custom-integration-push](content-hub/.github/actions/custom-integration-push)

This action streamlines the deployment process for custom integrations. It monitors your repository
for changes and automatically pushes updates to your Google SecOps SOAR environment.

#### Key Features

* **Automated Sync:** Monitors the `content/response_integrations/custom/` directory.
* **Flexible Auth:** Supports both API Key (recommended) and Username/Password authentication.
* **Smart Triggers:** Runs only when relevant files are modified.
