# `mp` and development environment commands

Commands for interacting with the development environment (playground). This suite of commands helps you manage your connection to the Google SecOps environment and deploy your integrations and playbooks for testing.

## Authentication modes

`mp login` supports two modes:

- **Google Chronicle SOAR** — Chronicle REST API using Google Cloud IAM (Service Account JSON key file or Application Default Credentials). Provide the instance's `--api-root` (or `--credentials-file` / `--gcp`).
- **Legacy SOAR** — an API root URL plus an API key (or username/password) for on-prem/legacy environments.

> [!IMPORTANT]
> Content pulled from a legacy SOAR instance should be pushed back to a legacy instance; content pulled over the Chronicle API should be pushed back over the Chronicle API.

## Getting Your Credentials

### Google Chronicle SOAR (Service Account Key / ADC)

For Chronicle SOAR authentication, you can pass the **API Root** URL (matching the format in the Google Chronicle integration in SecOps) along with your Service Account key file:

```bash
mp login --api-root "https://<location>-chronicle.googleapis.com/v1alpha/projects/<project>/locations/<location>/instances/<instance_uuid>" --credentials-file /path/to/sa_key.json
```

#### Minimum API Permissions & IAM Roles
When creating a Service Account for `mp`, assign the following:

* **Predefined IAM Roles:**
  * `roles/chronicle.admin` (Chronicle Admin), or a custom role with Chronicle SOAR permissions.
* **Minimum Granular IAM Permissions:**
  * **Integrations (Push / Pull):**
    * `chronicle.instances.get`
    * `chronicle.integrations.get`, `chronicle.integrations.list`
    * `chronicle.integrations.import` *(Push / Upload)*
    * `chronicle.integrations.export` *(Pull / Download)*
  * **Playbooks (Push / Pull):**
    * `chronicle.legacyPlaybooks.get`, `chronicle.legacyPlaybooks.list`
    * `chronicle.legacyPlaybooks.import` *(Push / Upload)*
    * `chronicle.legacyPlaybooks.export` *(Pull / Download)*
* **OAuth Scope:**
  * `https://www.googleapis.com/auth/cloud-platform`

### Legacy SOAR (On-Prem API Key / User & Pass)

1. Open your SecOps environment in a web browser.
2. Open the browser's Developer Console (F12) and execute: `localStorage['soar_server-addr']` to get your API Root.
3. In SecOps, navigate to **Settings** → **SOAR Settings** → **Advanced** → **API Keys**, create an API key with `Admins` permissions, and copy it.

## Subcommands

### `login`

Authenticate to the dev environment. See [Authentication modes](#authentication-modes) for supported modes.

**Usage:**

```bash
# Google Chronicle SOAR (Service Account Key + API Root)
mp login --api-root "https://us-chronicle.googleapis.com/v1alpha/projects/<PROJECT_ID>/locations/us/instances/<INSTANCE_UUID>" --credentials-file /path/to/sa.json

# Google Chronicle SOAR (Application Default Credentials - ADC)
mp login --gcp --api-root "https://us-chronicle.googleapis.com/v1alpha/projects/<PROJECT_ID>/locations/us/instances/<INSTANCE_UUID>"

# Legacy SOAR (API key)
mp login --api-root https://your-env.siemplify-soar.com --api-key <API_KEY>

# Legacy SOAR (Username / Password)
mp login --api-root https://your-env.siemplify-soar.com --username <USERNAME> --password <PASSWORD>
```

Run `mp login` with no options to be prompted interactively.

**Options:**

| Option               | Description                                                                           | Type   | Default |
|:---------------------|:--------------------------------------------------------------------------------------|:-------|:--------|
| `--api-root`         | API root URL (legacy SOAR URL or Chronicle instance URL).                             | `str`  | `None`  |
| `--credentials-file` | Path to a GCP Service Account JSON credentials file.                                  | `str`  | `None`  |
| `--username`         | Authentication username (legacy SOAR auth).                                           | `str`  | `None`  |
| `--password`         | Authentication password (legacy SOAR auth).                                           | `str`  | `None`  |
| `--api-key`          | Authentication API key (legacy SOAR auth).                                            | `str`  | `None`  |
| `--gcp`              | Force Chronicle API auth using GCP credentials (ADC or Service Account).              | `bool` | `False` |
| `--project`          | GCP project ID (optional if present in `--api-root` or `--credentials-file`).         | `str`  | `None`  |
| `--location`         | Chronicle region, e.g. `us` (optional if present in `--api-root`; defaults to `us`).   | `str`  | `None`  |
| `--instance`         | Chronicle instance UUID (optional if present in `--api-root`).                        | `str`  | `None`  |
| `--no-verify`        | Skip credential verification after saving.                                            | `bool` | `False` |

### `push integration`

Build and push an integration to the dev environment.

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

### `push view`

Build and push Case or Alert view template(s) to the dev environment.

**Usage:**

```bash
mp push view [VIEW] [OPTIONS]
```

**Arguments:**

* `[VIEW]`: *(Optional)* The view name, folder name, or UUID identifier to push. Required unless `--all` is specified.

**Options:**

| Option       | Description                                                             | Type   | Default |
|:-------------|:------------------------------------------------------------------------|:-------|:--------|
| `--all`      | Push all views from the local repository.                               | `bool` | `False` |
| `--custom`   | Path to custom source directory containing views.                       | `Path` | `None`  |
| `--force`    | Force creating new views if they do not exist on the platform.          | `bool` | `False` |
| `--validate` | Validate local view configuration on target server without pushing.    | `bool` | `False` |

**Examples:**

```bash
# Push a single view
mp push view "Default Case View"

# Push all views in the repository
mp push view --all

# Force creating a new view
mp push view "New Case View" --force

# Validate a view configuration without pushing
mp push view "Default Case View" --validate
```

**Validation & Verification Notes:**

* **Validation (`--validate`)**: Aggregates and reports all missing Custom Fields, missing platform Widgets, and missing Integration dependencies required by view widget actions in a single output before exiting.
* **Post-Push Widget Verification**: After a push completes (with `--force`), `mp` automatically performs an in-memory layout check against the server. If the target SOAR instance omits any submitted widgets (e.g., due to disabled feature flags or missing license modules like `GenerativeAI`), `mp` displays a `[VALIDATION WARNING] Widget Not Persisted by Platform` notice.

### `push custom-field`

Push custom field(s) to the dev environment.

**Usage:**

```bash
mp push custom-field [FIELD] [OPTIONS]
```

**Arguments:**

* `[FIELD]`: *(Optional)* The custom field name or YAML file path to push. Required unless `--all` is specified.

**Options:**

| Option     | Description                                                    | Type   | Default |
|:-----------|:---------------------------------------------------------------|:-------|:--------|
| `--all`    | Push all custom fields from the local repository.              | `bool` | `False` |
| `--custom` | Path to custom source directory containing custom fields.      | `Path` | `None`  |
| `--force`  | Force creating new custom fields if not present on server.     | `bool` | `False` |
| `--scope`  | Filter custom fields to push by scope (e.g., `alert`, `case`, `alert,case` [OR filter], or `shared` [AND filter for both alert and case]). | `str`  | `None`  |

**Examples:**

```bash
# Push a single custom field
mp push custom-field "Is False Positive"

# Push all alert-scoped custom fields in the repository
mp push custom-field --all --scope alert

# Push a custom field using its local filename (matches exact name or scope suffix)
mp push custom-field "Free_Text_[Serhii_2]_alert" --force
```

### `push alert-grouping-rule`

Push alert grouping rule(s) to the dev environment.

**Usage:**

```bash
mp push alert-grouping-rule [RULE] [OPTIONS]
```

**Arguments:**

* `[RULE]`: *(Optional)* The alert grouping rule category name, filename stem, or YAML file path to push. Required unless `--all` is specified.

**Options:**

| Option     | Description                                                        | Type   | Default |
|:-----------|:-------------------------------------------------------------------|:-------|:--------|
| `--all`    | Push all alert grouping rules from the local repository.           | `bool` | `False` |
| `--custom` | Path to custom source directory containing alert grouping rules.   | `Path` | `None`  |
| `--force`  | Force creating new alert grouping rules if not present on server.  | `bool` | `False` |

**Examples:**

```bash
# Push an alert grouping rule by category name
mp push alert-grouping-rule "AlertType"

# Push a specific alert grouping rule by exact local YAML file path
mp push alert-grouping-rule "content/alert_grouping_rules/DataSource_jira_microsoft_casb_microsoftgraphmail.yaml"

# Push a specific alert grouping rule by filename stem (without .yaml extension)
mp push alert-grouping-rule "DataSource_jira_microsoft_casb_microsoftgraphmail"

# Push all alert grouping rules in the repository
mp push alert-grouping-rule --all
```

### `push custom-integration-repository`

Build, zip, and upload the entire custom integration repository.

**Usage:**

```bash
mp push custom-integration-repository
```

### `pull integration`

Pull and deconstruct an integration from the dev environment.

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

### `pull view`

Pull and deconstruct Case or Alert view template(s) from the dev environment.

**Usage:**

```bash
mp pull view [VIEW] [OPTIONS]
```

**Arguments:**

* `[VIEW]`: *(Optional)* The view name or UUID identifier to pull. Required unless `--all` or `--list` is specified.

**Options:**

| Option     | Description                                                             | Type   | Default |
|:-----------|:------------------------------------------------------------------------|:-------|:--------|
| `--all`    | Pull all views from the dev environment.                                | `bool` | `False` |
| `--list`   | List all installed view templates on the dev environment.              | `bool` | `False` |
| `--custom` | Destination folder path. Defaults to `content/views/<identifier_uuid>`. | `Path` | `None`  |

**Examples:**

```bash
# List all view templates on the server
mp pull view --list

# Pull a single view
mp pull view "Default Case View"

# Pull all views from the server
mp pull view --all
```

### `pull custom-field`

Pull custom field(s) from the dev environment.

**Usage:**

```bash
mp pull custom-field [FIELD] [OPTIONS]
```

**Arguments:**

* `[FIELD]`: *(Optional)* The custom field name to pull. Required unless `--all` or `--list` is specified.

**Options:**

| Option     | Description                                                                     | Type   | Default |
|:-----------|:--------------------------------------------------------------------------------|:-------|:--------|
| `--all`    | Pull all custom fields from the dev environment.                                | `bool` | `False` |
| `--list`   | List all installed custom fields on the dev environment.                        | `bool` | `False` |
| `--custom` | Destination directory or file path. Defaults to `content/custom_fields/<scope>`.| `Path` | `None`  |
| `--scope`  | Filter custom fields to pull by scope (e.g., `alert`, `case`, `alert,case` [OR filter], or `shared` [AND filter for both alert and case]).| `str`  | `None`  |

> [!NOTE]
> **Renamed Local Files Preservation:** If a local YAML configuration already matches a pulled custom field's configuration (by `displayName` and `scopes`) but has a custom filename, `mp` will automatically find and overwrite that file directly instead of creating a new default file.

**Examples:**

```bash
# List installed custom fields
mp pull custom-field --list

# Pull a single custom field by display name
# (Downloads from server and saves it to the default path: content/custom_fields/alert/Is_False_Positive_alert.yaml)
mp pull custom-field "Is False Positive"

# Pull a custom field matching a local filename (e.g., Free_Text_[Custom_Name]_random.yaml)
# (Reads displayName/scopes from local file, fetches matching server field, and overwrites the local file)
mp pull custom-field "Free_Text_[Custom_Name]_random"

# Pull all case-scoped custom fields
mp pull custom-field --all --scope case
```

### `pull alert-grouping-rule`

Pull alert grouping rule(s) from the dev environment.

**Usage:**

```bash
mp pull alert-grouping-rule [RULE] [OPTIONS]
```

**Arguments:**

* `[RULE]`: *(Optional)* The alert grouping rule category name, filename stem, or local YAML file path to pull. Required unless `--all` or `--list` is specified.

**Options:**

| Option     | Description                                                                     | Type   | Default |
|:-----------|:--------------------------------------------------------------------------------|:-------|:--------|
| `--all`    | Pull all alert grouping rules from the dev environment.                         | `bool` | `False` |
| `--list`   | List all installed alert grouping rules on the dev environment.                 | `bool` | `False` |
| `--custom` | Destination directory or file path. Defaults to `content/alert_grouping_rules`. | `Path` | `None`  |

> [!NOTE]
> **Renamed Local Files Preservation:** If a local YAML configuration already matches a pulled grouping rule's configuration (by `category` and its subcategory list `categoryDetails`) or filename stem, `mp` will automatically find and overwrite that file directly instead of creating a new default file.

**Examples:**

```bash
# List installed alert grouping rules
mp pull alert-grouping-rule --list

# Pull all grouping rules under a category (e.g., AlertType)
mp pull alert-grouping-rule "AlertType"

# Pull a specific alert grouping rule matching a local filename (e.g., DataSource_jira_microsoft_casb_microsoftgraphmail.yaml)
# (Reads category/categoryDetails from local file, fetches matching server rule, and overwrites the local file)
mp pull alert-grouping-rule "DataSource_jira_microsoft_casb_microsoftgraphmail.yaml"

# Pull a specific alert grouping rule by filename stem (without .yaml extension)
mp pull alert-grouping-rule "DataSource_jira_microsoft_casb_microsoftgraphmail"

# Pull all alert grouping rules
mp pull alert-grouping-rule --all
```