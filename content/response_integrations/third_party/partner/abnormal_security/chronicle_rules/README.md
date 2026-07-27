# Abnormal Security Chronicle Detection Rules

YARA-L 2.0 detection rules that bridge **Chronicle SIEM events** to **SOAR cases** for the Abnormal Security integration. Deploy these in your Chronicle tenant so events ingested by the Abnormal SIEM connector automatically generate alerts that flow into SOAR as cases.

## Rules

| File | Severity | Fires on |
|------|----------|----------|
| `abnormal_threat_critical.yaral` | HIGH | Threats with severity `HIGH`/`CRITICAL` or confidence ≥ 80 |
| `abnormal_threat_all.yaral` | MEDIUM | All Abnormal threat events (catch-all — tune or disable if noisy) |
| `abnormal_credential_phishing.yaral` | HIGH | Credential phishing, BEC, account takeover, and invoice fraud variants |

## Prerequisites

1. The **Abnormal Security SIEM connector** is configured in the Abnormal portal pointing at your Chronicle ingestion endpoint
2. Events are arriving with `log_type: ABNORMAL_SECURITY` (verify in Chronicle's raw log search)
3. Chronicle's parser for `ABNORMAL_SECURITY` is mapping events into UDM (vendor: `Abnormal Security`, event type: `EMAIL_TRANSACTION`)

## Deploy

### Option 1 — Chronicle UI (recommended)

1. Open Chronicle → **Detection** → **Rules and Detections**
2. Click **Create Rule**
3. Paste the contents of one `.yaral` file
4. Click **Save** → **Enable Live Rule**
5. Repeat for each rule you want active

### Option 2 — Chronicle API (`gcloud` or REST)

```bash
PROJECT_ID="your-chronicle-project"
LOCATION="us"  # or your region
INSTANCE="your-chronicle-instance"

for rule_file in *.yaral; do
  curl -X POST \
    "https://chronicle.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/${LOCATION}/instances/${INSTANCE}/rules" \
    -H "Authorization: Bearer $(gcloud auth print-access-token)" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --rawfile text "$rule_file" '{text: $text}')"
done
```

## Tuning

- **Too many alerts?** Disable `abnormal_threat_all.yaral` and rely on `_critical` + `_credential_phishing` only
- **Want all events as cases?** Lower the confidence threshold in `_critical` from `80` to `60`
- **Custom routing per attack type?** Clone the credential phishing rule and adjust the regex for other attack types (e.g., `extortion`, `malware`)

## Validation

After enabling rules:

1. Wait for the next batch of events to arrive (typically < 5 minutes)
2. Check **Detection** → **Alerts** for new alerts tagged with the rule name
3. Check SOAR → **Cases** — each alert should produce a corresponding case
4. Open a case and verify the action panel shows Abnormal Security actions (Get Threat, Remediate Messages, etc.)

## How this fits with the SOAR connector

This integration ships **two ingestion paths**:

1. **SIEM rules → SOAR** (this directory) — recommended primary path. Single source of truth in SIEM.
2. **SOAR connector** (in `connectors/`) — direct API polling. Use only if you don't have Chronicle SIEM or aren't using SIEM forwarding.

Pick one. Running both will create duplicate cases.
