# SecOps Parser Validation Script

This script allows you to run validations on your parser configurations and test against the test data present for each parser.

## Prerequisites

- Python 3.10+
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)
- Dependencies: See `requirements.txt`
- Installation:
  ```bash
  python3 -m pip install -r requirements.txt
  ```

## Installing the gcloud CLI

The `gcloud` CLI is required to authenticate with Google Cloud. Follow the instructions for your platform:

- **Linux / macOS / Windows**: See the [Official Installation Guide](https://cloud.google.com/sdk/docs/install).

For a quick installation on Linux/macOS, you can run:
```bash
curl https://sdk.cloud.google.com | bash
```

## Authentication

You must authenticate to access the Google SecOps APIs. Use one of the following methods:

### 1. User Account Login (Recommended)
This is the simplest way for local development. Run:
```bash
gcloud auth login
```
This command opens a browser to authenticate your user account.

### 2. Application Default Credentials (ADC)
Some libraries used by this script may require ADC. If you encounter authentication errors, run:
```bash
gcloud auth application-default login
```

### 3. Service Account
For automated environments (CI/CD, VMs), use a service account key:
```bash
gcloud auth activate-service-account --key-file=<PATH_TO_KEY_JSON>
```
Alternatively, set the environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="<PATH_TO_KEY_JSON>"
```

## Directory Structure

The script expects to be run from the `tools/parsers/` directory:

```
content-hub/
├── content/
│   └── parsers/
│       └── third_party/
│           └── <parser_source>/
│               └── <log_type_identifier>/
│                   └── cbn/
│                       ├── <config>.conf
│                       ├── metadata.json
│                       └── testdata/
│                           ├── raw_logs/
│                           │   └── <usecase>_log.json
│                           └── expected_events/
│                               └── <usecase>_events.json
└── tools/
    └── parsers/
        ├── run_parser_validations.py
        └── docs/
            └── README.md
```

## Usage

```bash
python3 run_parser_validations.py \
  --parser_source=community \
  --customer_id=<YOUR_CUSTOMER_ID> \
  --project_id=<YOUR_PROJECT_ID> \
  --region=<YOUR_REGION> \
  --generate_report=True \
  --log_type_folders=DUMMY_LOGTYPE,DUMMY_LOGTYPE2
```

### Flags

- `--parser_source`: Source of the parser (default: `community`).
- `--customer_id` (Mandatory): Your Chronicle customer ID.
- `--project_id` (Mandatory): Your Google Cloud project ID.
- `--region` (Mandatory): Your Chronicle region (e.g., `us`, `eu`).
- `--generate_report`: Set to `True` to generate a markdown report `validation_report_poc.md`.
- `--log_type_folders`: Comma-separated list of specific log type folders to validate (e.g., `DUMMY_LOGTYPE,DUMMY_LOGTYPE2`). If not set, all folders in the `parser_source` are validated.

## Output

The script will iterate through all log types in the specified `parser_source` directory, run the parser against the raw logs, and compare the output with the expected events.

A **FINAL FAILURE SUMMARY** will be printed at the end, showing any technical errors or test case failures with detailed differences.

## PII Redaction

It is important to ensure that no Personally Identifiable Information (PII) is included in the raw logs or expected events that are committed to the repository. Please redact any sensitive information before committing your changes.

