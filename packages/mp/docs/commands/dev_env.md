# `mp dev-env`

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
mp dev-env login [OPTIONS]
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
mp dev-env push integration [INTEGRATION] [OPTIONS]
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
mp dev-env push playbook [PLAYBOOK] [OPTIONS]
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
mp dev-env push custom-integration-repository
```

### `pull integration`

Pull and deconstruct an integration from the dev environment.

**Usage:**

```bash
mp dev-env pull integration [INTEGRATION] [OPTIONS]
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
mp dev-env pull playbook [PLAYBOOK] [OPTIONS]
```

**Arguments:**

* `PLAYBOOK`: The playbook to pull.

**Options:**

| Option             | Description                                                             | Type   | Default |
|:-------------------|:------------------------------------------------------------------------|:-------|:--------|
| `--dst`            | Destination folder. Defaults to the `.downloads` directory in the repo. | `Path` | `None`  |
| `--include-blocks` | Pull all playbook dependent blocks.                                     | `bool` | `False` |
| `--keep-zip`       | Keep the zip file after pulling.                                        | `bool` | `False` |