## Overview

The action monitors the `content/response_integrations/custom/` directory for changes. When a push
to your repository's `main` branch includes modifications in this path, the action will
automatically deploy those integrations to your SOAR instance.

## Authentication

The action supports two methods of authentication:

1. **API Key (Recommended):** Using a SOAR API key.
2. **Username/Password:** Using your SOAR username and password.

You must store your credentials as encrypted secrets in your GitHub repository.

#### API URL

To get your SecOps environment API url:

1. Open your SecOps environment in a web browser
2. Open the browser's Developer Console (F12)
3. Execute: `localStorage['soar_server-addr']`
4. Copy the returned URL - this is your API URL

#### API Key Creation

To create an API key for authentication:

1. Log into your SecOps environment
2. Navigate to **Settings** → **SOAR Settings** → **Advanced** → **API Keys**
3. Click **Create**
4. Set **Permission Groups** to `Admins`
5. Copy the generated API key

#### Configuring GitHub Secrets

Once you have your credentials, store them as secrets in your GitHub repository so the Action can
access them securely:

1. In your repository, navigate to **Settings** → **Secrets and variables** → **Actions**.
2. Click **New repository secret**.
3. Create the following secrets based on your chosen authentication method:

| Secret Name     | Value                                       | Required For             |
|:----------------|:--------------------------------------------|:-------------------------|
| `SOAR_API_URL`  | Your API URL (retrieved in the step above). | All methods              |
| `SOAR_API_KEY`  | Your API Key.                               | API Key method           |
| `SOAR_USER`     | Your SOAR username.                         | Username/Password method |
| `SOAR_PASSWORD` | Your SOAR password.                         | Username/Password method |

## Usage

To use this action, create a new workflow file in your repository under `.github/workflows/`. For
example, you can create `.github/workflows/deploy_custom_integrations.yml`.

### Example Workflow: Using API Key

This is the recommended method.

```yaml
name: 'Deploy Custom Integrations on Push'

on:
  push:
    branches:
    - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: 'Checkout repository'
      uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: 'Deploy Custom Integrations'
      uses: chronicle/content-hub/actions/custom-integration-deploy@main
      with:
        soar_api_url: ${{ secrets.SOAR_API_URL }}
        soar_api_key: ${{ secrets.SOAR_API_KEY }}
```

### Example Workflow: Using Username and Password

```yaml
name: 'Deploy Custom Integrations on Push'

on:
  push:
    branches:
    - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: 'Checkout repository'
      uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: 'Deploy Custom Integrations'
      uses: chronicle/content-hub/actions/custom-integration-deploy@main
      with:
        soar_api_url: ${{ secrets.SOAR_API_URL }}
        soar_username: ${{ secrets.SOAR_USER }}
        soar_password: ${{ secrets.SOAR_PASSWORD }}
```

## Inputs

| Input           | Description                                                                   | Required |
|-----------------|-------------------------------------------------------------------------------|----------|
| `soar_api_url`  | The API root URL of the SOAR environment.                                     | `true`   |
| `soar_api_key`  | The API key for SOAR authentication. (Recommended)                            | `false`  |
| `soar_username` | The username for SOAR authentication. Used if `soar_api_key` is not provided. | `false`  |
| `soar_password` | The password for SOAR authentication. Used if `soar_api_key` is not provided. | `false`  |

**Note:** You must provide either `soar_api_key` or both `soar_username` and `soar_password` for the
action to work.

# Guide: Deploying Custom Integrations

This guide explains how to use the "Deploy Custom Integrations" GitHub Action to automatically
synchronize your custom integrations with your SOAR environment.
