# `mp` and development environment commands

Commands for interacting with the development environment (playground). This suite of commands helps you manage your connection to the Google SecOps environment and deploy your integrations for testing.

## Authentication modes

`mp login` supports two modes:

- **Legacy SOAR** (default) — an API root URL plus an API key (or username/password). Being retired by Google; legacy API keys stop functioning on 2026-09-30.
- **GCP / Chronicle API** (`--gcp`) — Google Application Default Credentials (ADC) against the Chronicle API, identified by a GCP project, Chronicle region, and instance UUID.

> [!IMPORTANT]
> Don't mix modes. Content pulled from a legacy SOAR instance should be pushed back to a legacy instance; content pulled over the Chronicle API should be pushed back over the Chronicle API.

> [!NOTE]
> **Chronicle API (`--gcp`) support:** `pull playbook` and `push playbook` are fully supported. Integration `pull`/`push` are still in progress — the underlying download/import work, but converting a pulled integration to (or from) repo source is not yet available.

## Getting Your Credentials

For legacy SOAR auth, you'll need the API Root URL and an API Key (or Username/Password). For `--gcp` mode, see the **GCP / Chronicle API** section below.

### API Root

1. Open your SecOps environment in a web browser.
2. Open the browser's Developer Console (F12).
3. Execute: `localStorage['soar_server-addr']`
4. Copy the returned URL. This is your API Root.

### API Key

1. Log into your SecOps environment.
2. Navigate to **Settings** → **SOAR Settings** → **Advanced** → **API Keys**.
3. Click **Create**.
4. Set **Permission Groups** to `Admins`.
5. Copy the generated API Key.

### GCP / Chronicle API

For `--gcp` mode you need your GCP **project ID**, Chronicle **region** (e.g. `us`, `europe`), and **instance UUID** (from your Chronicle instance configuration), plus GCP credentials:

1. Authenticate with ADC: `gcloud auth application-default login`. For CI, point `--credentials-file` at a service-account or external-account JSON instead.
2. Ensure your identity has the relevant Chronicle IAM permissions (e.g. `chronicle.integrations.get` / `chronicle.legacyPlaybooks.get`, plus the matching `update` permissions to push).

## Subcommands

### `login`

Authenticate to the dev environment. See [Authentication modes](#authentication-modes) for the two supported modes.

**Usage:**

```bash
# Legacy SOAR (API key)
mp login --api-root https://your-env.siemplify-soar.com --api-key <API_KEY>

# GCP / Chronicle API (ADC)
mp login --gcp --project <PROJECT_ID> --location us --instance <INSTANCE_UUID>
```

Run `mp login` with no options to be prompted interactively.

**Options:**

| Option               | Description                                                          | Type   | Default |
|:---------------------|:---------------------------------------------------------------------|:-------|:--------|
| `--api-root`         | API root URL (legacy SOAR auth).                                     | `str`  | `None`  |
| `--username`         | Authentication username (legacy SOAR auth).                          | `str`  | `None`  |
| `--password`         | Authentication password (legacy SOAR auth).                          | `str`  | `None`  |
| `--api-key`          | Authentication API key (legacy SOAR auth).                           | `str`  | `None`  |
| `--gcp`              | Authenticate to the Chronicle API using GCP credentials (ADC).       | `bool` | `False` |
| `--project`          | GCP project ID (`--gcp` mode).                                       | `str`  | `None`  |
| `--location`         | Chronicle region, e.g. `us` (`--gcp` mode).                          | `str`  | `None`  |
| `--instance`         | Chronicle instance UUID (`--gcp` mode).                              | `str`  | `None`  |
| `--credentials-file` | Path to a GCP credentials JSON file (`--gcp` mode; defaults to ADC). | `str`  | `None`  |
| `--no-verify`        | Skip credential verification after saving.                           | `bool` | `False` |

### `push integration`

Build and push an integration to the dev environment.

> [!NOTE]
> Not yet supported in `--gcp` (Chronicle API) mode — see [Authentication modes](#authentication-modes).

**Usage:**

```bash
mp push integration [INTEGRATION] [OPTIONS]
```

**Arguments:**

* `INTEGRATION`: The name of the integration to build and push.

**Options:**

| Option       | Description                                           | Type   | Default |
|:-------------|:------------------------------------------------------|:-------|:--------|
| `--src`      | Source folder, where the content will be pushed from. | `Path` | `None`  |
| `--staging`  | Push integration into staging mode.                   | `bool` | `False` |
| `--custom`   | Push integration from the custom repository.          | `bool` | `False` |
| `--keep-zip` | Keep the generated zip file after pushing.            | `bool` | `False` |

### `push playbook`

Build and push a playbook to the dev environment.

**Usage:**

```bash
mp push playbook [PLAYBOOK] [OPTIONS]
```

**Arguments:**

* `PLAYBOOK`: The name of the playbook to build and push.

**Options:**

| Option             | Description                                           | Type   | Default |
|:-------------------|:------------------------------------------------------|:-------|:--------|
| `--src`            | Source folder, where the content will be pushed from. | `Path` | `None`  |
| `--include-blocks` | Push all playbook dependent blocks.                   | `bool` | `False` |
| `--keep-zip`       | Keep the generated zip file after pushing.            | `bool` | `False` |

### `push custom-integration-repository`

Build, zip, and upload the entire custom integration repository.

**Usage:**

```bash
mp push custom-integration-repository
```

### `pull integration`

Pull and deconstruct an integration from the dev environment.

> [!NOTE]
> Not yet supported in `--gcp` (Chronicle API) mode — see [Authentication modes](#authentication-modes).

**Usage:**

```bash
mp pull integration [INTEGRATION] [OPTIONS]
```

**Arguments:**

* `INTEGRATION`: The integration to pull.

**Options:**

| Option       | Description                                                             | Type   | Default |
|:-------------|:------------------------------------------------------------------------|:-------|:--------|
| `--dst`      | Destination folder. Defaults to the `.downloads` directory in the repo. | `Path` | `None`  |
| `--keep-zip` | Keep the zip file after pulling.                                        | `bool` | `False` |

### `pull playbook`

Pull and deconstruct a playbook from the dev environment.

**Usage:**

```bash
mp pull playbook [PLAYBOOK] [OPTIONS]
```

**Arguments:**

* `PLAYBOOK`: The playbook to pull.

**Options:**

| Option             | Description                                                             | Type   | Default |
|:-------------------|:------------------------------------------------------------------------|:-------|:--------|
| `--dst`            | Destination folder. Defaults to the `.downloads` directory in the repo. | `Path` | `None`  |
| `--include-blocks` | Pull all playbook dependent blocks.                                     | `bool` | `False` |
| `--keep-zip`       | Keep the zip file after pulling.                                        | `bool` | `False` |