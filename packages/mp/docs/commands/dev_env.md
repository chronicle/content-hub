# `mp` and development environment commands

Commands for interacting with the development environment (playground). This suite of commands helps you manage your connection to the Google SecOps SOAR environment and deploy your integrations for testing.

## Getting Your Credentials

To use these commands, you'll need the API Root URL and an API Key (or Username/Password).

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

## Subcommands

### `login`

Authenticate to the dev environment.

**Usage:**

```bash
mp login [OPTIONS]
```

**Options:**

| Option        | Description                                            | Type   | Default |
|:--------------|:-------------------------------------------------------|:-------|:--------|
| `--api-root`  | API root URL (e.g., `https://your-env.siemplify.com`). | `str`  | `None`  |
| `--username`  | Authentication username.                               | `str`  | `None`  |
| `--password`  | Authentication password.                               | `str`  | `None`  |
| `--api-key`   | Authentication API key.                                | `str`  | `None`  |
| `--no-verify` | Skip credential verification after saving.             | `bool` | `False` |

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

* `VIEW`: The view name, folder name, or UUID identifier to push. Optional if `--all` is specified.

**Options:**

| Option       | Description                                                             | Type   | Default |
|:-------------|:------------------------------------------------------------------------|:-------|:--------|
| `--all`      | Push all views from the local repository.                               | `bool` | `False` |
| `--custom`   | Path to custom source directory containing views.                       | `Path` | `None`  |
| `--force`    | Force creating new views if they do not exist on the platform.          | `bool` | `False` |
| `--validate` | Validate local view configuration on target server without pushing.    | `bool` | `False` |

### `push custom-field`

Push custom field(s) to the dev environment.

**Usage:**

```bash
mp push custom-field [FIELD] [OPTIONS]
```

**Arguments:**

* `FIELD`: The custom field name or YAML file path to push. Optional if `--all` is specified.

**Options:**

| Option     | Description                                                    | Type   | Default |
|:-----------|:---------------------------------------------------------------|:-------|:--------|
| `--all`    | Push all custom fields from the local repository.              | `bool` | `False` |
| `--custom` | Path to custom source directory containing custom fields.      | `Path` | `None`  |
| `--force`  | Force creating new custom fields if not present on server.     | `bool` | `False` |

### `push alert-grouping-rule`

Push alert grouping rule(s) to the dev environment.

**Usage:**

```bash
mp push alert-grouping-rule [RULE] [OPTIONS]
```

**Arguments:**

* `RULE`: The alert grouping rule category name or YAML file path to push. Optional if `--all` is specified.

**Options:**

| Option     | Description                                                        | Type   | Default |
|:-----------|:-------------------------------------------------------------------|:-------|:--------|
| `--all`    | Push all alert grouping rules from the local repository.           | `bool` | `False` |
| `--custom` | Path to custom source directory containing alert grouping rules.   | `Path` | `None`  |
| `--force`  | Force creating new alert grouping rules if not present on server.  | `bool` | `False` |

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

* `VIEW`: The view name or UUID identifier to pull. Optional if `--all` is specified.

**Options:**

| Option     | Description                                                             | Type   | Default |
|:-----------|:------------------------------------------------------------------------|:-------|:--------|
| `--all`    | Pull all views from the dev environment.                                | `bool` | `False` |
| `--custom` | Destination folder path. Defaults to `content/views/<identifier_uuid>`. | `Path` | `None`  |

### `pull custom-field`

Pull custom field(s) from the dev environment.

**Usage:**

```bash
mp pull custom-field [FIELD] [OPTIONS]
```

**Arguments:**

* `FIELD`: The custom field name to pull. Optional if `--all` or `--list` is specified.

**Options:**

| Option     | Description                                                                     | Type   | Default |
|:-----------|:--------------------------------------------------------------------------------|:-------|:--------|
| `--all`    | Pull all custom fields from the dev environment.                                | `bool` | `False` |
| `--list`   | List all installed custom fields on the dev environment.                        | `bool` | `False` |
| `--custom` | Destination directory or file path. Defaults to `content/custom_fields/<scope>`.| `Path` | `None`  |

### `pull alert-grouping-rule`

Pull alert grouping rule(s) from the dev environment.

**Usage:**

```bash
mp pull alert-grouping-rule [RULE] [OPTIONS]
```

**Arguments:**

* `RULE`: The alert grouping rule category name to pull. Optional if `--all` or `--list` is specified.

**Options:**

| Option     | Description                                                                     | Type   | Default |
|:-----------|:--------------------------------------------------------------------------------|:-------|:--------|
| `--all`    | Pull all alert grouping rules from the dev environment.                         | `bool` | `False` |
| `--list`   | List all installed alert grouping rules on the dev environment.                 | `bool` | `False` |
| `--custom` | Destination directory or file path. Defaults to `content/alert_grouping_rules`. | `Path` | `None`  |