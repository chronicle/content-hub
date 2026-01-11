# `mp dev-env`

## Description
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

## Sub-commands

### `login`

Authenticate to the dev environment (playground).

#### Usage
```bash
mp dev-env login [OPTIONS]
```

#### Options
| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--api-root` | The API root URL (e.g., `https://your-env.siemplify.com`). | `str` | `None` |
| `--username` | Authentication username. | `str` | `None` |
| `--password` | Authentication password. | `str` | `None` |
| `--api-key` | Authentication API key. | `str` | `None` |
| `--no-verify` | Skip credential verification after saving. | `bool` | `False` |

#### Examples
```bash
mp dev-env login --api-root https://my-env.siemplify.com --api-key my-api-key
```

### `push integration`

Build and deploy an integration to the dev environment (playground).

#### Usage
```bash
mp dev-env push integration INTEGRATION [OPTIONS]
```

#### Arguments
| Argument | Description | Type |
| :--- | :--- | :--- |
| `INTEGRATION` | The name of the integration to build and deploy. | `str` |

#### Options
| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--staging` | Deploy integration into staging mode. | `bool` | `False` |
| `--custom` | Deploy integration from the custom repository. | `bool` | `False` |

#### Examples
```bash
mp dev-env push integration my_integration
```

### `push custom-integration-repository`

Build, zip, and upload the entire custom integration repository.

#### Usage
```bash
mp dev-env push custom-integration-repository
```

### `push playbook`

Build and deploy a playbook to the dev environment (playground).

#### Usage
```bash
mp dev-env push playbook PLAYBOOK [OPTIONS]
```

#### Arguments
| Argument | Description | Type |
| :--- | :--- | :--- |
| `PLAYBOOK` | The name of the playbook to build and push. | `str` |

#### Options
| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--include-blocks` | Push all playbook dependent blocks. | `bool` | `False` |

#### Examples
```bash
mp dev-env push playbook my_playbook --include-blocks
```

### `pull playbook`

Pull a playbook from the dev environment (playground).

#### Usage
```bash
mp dev-env pull playbook PLAYBOOK [OPTIONS]
```

#### Arguments
| Argument | Description | Type |
| :--- | :--- | :--- |
| `PLAYBOOK` | The name of the playbook to pull. | `str` |

#### Options
| Option | Description | Type | Default |
| :--- | :--- | :--- | :--- |
| `--dest` | Destination folder. | `Path` | `None` |
| `--include-blocks` | Pull all playbook dependent blocks. | `bool` | `False` |
| `--keep-zip` | Keep the zip file after pulling. | `bool` | `False` |

#### Examples
```bash
mp dev-env pull playbook soar_playbook --include-blocks --dest ./downloads
```
