---
name: mp-login
description: Authenticates the mp CLI to a Google Chronicle SecOps (GCP IAM/ADC) or legacy SOAR environment and persists session settings in ~/.mp_dev_env.json. Use when setting up or switching the target SecOps tenant before pulling or pushing content, or fixing unauthenticated dev-env errors. Don't use for local .mp_config settings or Gemini API keys (use mp-config).
---

# `mp login` Skill

Authenticates against either the Chronicle REST API (GCP IAM / Application Default Credentials) or a legacy SOAR API (API key or username/password) and writes `~/.mp_dev_env.json`. Replaces deprecated `mp dev-env login`.

> **Invocation**: Run `mp ...` if installed on `PATH` (`wmp` on Windows), or `uv run --frozen --project packages/mp mp ...` from the `content-hub` repository root (see `mp` skill [SKILL.md](../mp/SKILL.md)).

## Exact Command Syntax

Never run bare `mp login` in an automated shell: missing fields trigger interactive `typer.prompt(...)` calls that block stdin. Supply a complete flag set for one auth mode:

### Mode A: Google Chronicle SecOps (GCP IAM / ADC)

```bash
# Option A1: Parse project, location, and instance directly from Chronicle API root URL (uses ADC unless --credentials-file is set)
mp login --gcp --api-root "https://<location>-chronicle.googleapis.com/v1alpha/projects/<PROJECT>/locations/<LOCATION>/instances/<INSTANCE_UUID>" [--credentials-file <SA_JSON_PATH>] [--no-verify]

# Option A2: Explicit project, location, and instance flags
mp login --gcp --project <PROJECT> --location <LOCATION> --instance <INSTANCE_UUID> [--credentials-file <SA_JSON_PATH>] [--no-verify]
```

### Mode B: Legacy SOAR (API Key or Username/Password)

Never pass literal secrets directly in argv (which records them in agent transcripts and shell history). Expand from environment variables set by the user or ask the user to run `mp login` interactively in their own terminal:

```bash
mp login --api-root "https://<legacy-soar-host>" --api-key "$SOAR_API_KEY" [--no-verify]
mp login --api-root "https://<legacy-soar-host>" --username "$SOAR_USERNAME" --password "$SOAR_PASSWORD" [--no-verify]
```

## Agentic Workflow

1. **Inspect and back up existing `~/.mp_dev_env.json` safely**:
   - Inspect only non-secret keys (`auth_mode`, `project`, `location`, `instance`, `api_root`) via Python `json.load` so `api_key` and `password` are never printed.
   - **Side-effect gate & backup**: `mp login` overwrites `~/.mp_dev_env.json` **before** running live credential verification, so a failed login clobbers the previous working session! Confirm with the user before switching tenants, and copy `~/.mp_dev_env.json` to `~/.mp_dev_env.json.bak` (`chmod 600`) first so you can restore it if verification fails (then delete the backup on success).
   **Done when:** Existing session state is backed up (if present) and user approval is obtained if switching tenants.

2. **Verify prerequisite GCP credentials (for `--gcp` mode)**:
   If `--credentials-file` is omitted, `ChronicleClient` uses Application Default Credentials (`GOOGLE_APPLICATION_CREDENTIALS` or `gcloud auth application-default`). Confirm ADC is active before running without `--no-verify`.
   **Done when:** Credentials source (ADC or service account JSON) is verified.

3. **Execute non-interactive `mp login`**:
   Run the Mode A or env-expanded Mode B command above (restore `~/.mp_dev_env.json.bak` if verification fails; remove `.bak` once verified).
   **Done when:** Command exits `0` and logs `Credentials verified successfully.` (or `Credentials saved` when `--no-verify` is used).

## Key Gotchas

- **Mode conflicts exit `1`**: Combining Chronicle GCP flags (`--gcp`, `--credentials-file`, `--project`, `--location`, `--instance`, or a `chronicle.googleapis.com` URL) with legacy flags (`--api-key`, `--username`, `--password`) fails immediately.
- **Plaintext storage**: `~/.mp_dev_env.json` stores credentials in plaintext JSON. Never copy it into the repository or print raw file contents.
