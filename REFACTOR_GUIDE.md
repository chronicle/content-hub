# Integration Building & Validation Guide

This guide outlines the end-to-end workflow for building a Google SecOps integration using the `mp` CLI and validating parity against the original source.

---

## Prerequisites

*   **Environment**: Python 3.11+ and `uv` installed.
*   **Marketplace Repo**: `/Users/haggit/PycharmProjects/marketplace`
*   **Original Source Repo**: `/Users/haggit/PycharmProjects/tip-marketplace`
*   **Comparison Tools**: `../tip-cicd-tools/` (relative to marketplace)

---

## Step 1: Refactor the Hub Source (Optional)

The `scripts/refactor_integration.py` script automates the conversion of legacy file naming and star-imports to Hub standards using LibCST.

1.  **Configure Paths**: Identify your source integrations directory and destination directory.
2.  **Run Refactor**: Provide a **space-separated list of PascalCase integration names** (e.g., "AWSGuardDuty CofenseTriage") to the `--integrations-list` argument.
    ```bash
    python3 scripts/refactor_integration.py \
      /Users/haggit/PycharmProjects/tip-marketplace/Integrations \
      content/response_integrations/batch3_stash_v2 \
      --tests-dir /Users/haggit/PycharmProjects/tip-marketplace/Tests/Integrations \
      --integrations-list "AWSGuardDuty CofenseTriage"
    ```

### 1.1 Cleanup on Refactor Failure
The refactor script may sometimes fail mid-way (e.g., due to dependency resolution or metadata loading errors). **You must check the execution log for "ERROR" or "Failed to refactor" messages.**

If an integration fails to refactor:
- **Immediately delete the integration folder** from the destination directory (e.g., `rm -rf <snake_case_name>`).
- **Notify the user** that the integration folder has been deleted due to the refactor failure.
- **Why**: A failed refactor often leaves behind a partial directory structure that looks like a successful migration but contains broken or missing files. Deleting it prevents confusion during subsequent build and validation steps.

### 1.2 Handling TIPCommon & EnvironmentCommon Mismatches
If an integration uses a `TIPCommon` version > `1.0.14`, the `mp` tool implicitly requires `EnvironmentCommon`. If the legacy source's `Dependencies/` directory contains such a `TIPCommon` wheel but is missing `EnvironmentCommon`, the refactor will fail during the `uv add` stage.

**Required Action**:
1.  **Identify the mismatch**: Check the refactor log for `uv add ... EnvironmentCommon` returning exit status 1.
2.  **Add the missing dependency**: Manually copy a compatible `EnvironmentCommon` wheel (typically the latest stable version from `packages/envcommon/whls/`) into the legacy source's `Dependencies/` folder:
    ```bash
    cp packages/envcommon/whls/EnvironmentCommon-1.0.3-py3-none-any.whl /Users/haggit/PycharmProjects/tip-marketplace/Integrations/<PascalCaseName>/Dependencies/
    ```
3.  **Notify the User**: Inform the user about the incident and the specific version of `EnvironmentCommon` added.
4.  **Retry Refactor**: Re-run the `refactor_integration.py` script for that specific integration.

### 1.3 Detecting Silent Upgrades & uv add Failures
A successful refactor log should be clean of dependency warnings. You must proactively search the execution log for the following signatures to identify "silent upgrades" (where the tool fallbacks to the latest Hub version due to a resolution failure):

1.  **Local Resolution Failure** (Missing wheels in Hub or version mismatch):
    ```text
    WARNING Could not resolve local dependency TIPCommon: No wheel or source distribution found
    ```
    *Check if the requested version exists in `packages/tipcommon/whls/`. If missing, you may need to add it or investigate the mismatch.*

2.  **Global Installation Failure** (uv add crash):
    ```text
    WARNING Failed to install dependencies: Error happened while executing a command: ... uv add ... returned non-zero exit status
    ```
    *This usually happens if a third-party library has a naming conflict or is missing from PyPI. When this fails, the tool often fallbacks to version 2.3.8 of TIPCommon.*

**Action**: If either warning is found, notify the user with as much detail as possible (do not take any automated action yet).

### 1.4 Common Post-Refactor Code Fixes (Before Build)
After the refactor script completes, some integrations may still require manual code adjustments to satisfy modern SDK requirements or resolve import path changes that the automated tool might miss.

#### 1.4.1 Correcting CaseInfo and AlertInfo Imports
In `soar-sdk >= 0.2.0`, the SDK has been modularized. Data model classes like `CaseInfo`, `AlertInfo`, `ConnectorInfo`, and `ConnectorContext` have been moved to a dedicated module.

**Symptoms**:
Import tests or connector execution fails with:
`ImportError: cannot import name 'CaseInfo' from 'soar_sdk.SiemplifyConnectors'`

**Detection**:
Run the following grep command from the marketplace root to find incorrect imports in your refactored integrations:
```bash
grep -rE "from soar_sdk.SiemplifyConnectors import .*(CaseInfo|AlertInfo|ConnectorInfo|ConnectorContext)" content/response_integrations/google/
```

**Required Action**:
Update the import statement in the affected Python scripts (usually connectors):
- **Old**: `from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution`
- **New**:
  ```python
  from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
  from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
  ```

---

## Step 2: Build the Integration

The `mp build` command restructures the YAML/Python source into a deployable JSON-based artifact.

**Note**: The `mp` CLI typically expects integrations to be located in the `content/response_integrations/google/` directory to build them as official integrations.

1.  **Navigate to MP package**:
    ```bash
    cd packages/mp
    ```
2.  **Sync Environment**:
    ```bash
    uv sync
    ```
3.  **Self Update**:
    ```bash
    .venv/bin/mp self update
    ```
4.  **Temporarily copy** the integration folder from its staging area (e.g., `batch3_stash_v2/`) to `content/response_integrations/google/`.
5.  **Run Build**:
    ```bash
    .venv/bin/mp build integration <snake_case_name>
    ```
    *Builds are output to `marketplace/out/content/response_integrations/google/<PascalCaseName>`.*
6.  **Delete the temporary copy** from `content/response_integrations/google/` after the build is complete.

---

## Step 3: Validate Parity & Log Results

Use the comparison tool to identify functional differences between your built artifact and the original legacy source.

### 3.1 Run Comparison
Execute the following command, replacing `<PascalCaseName>` with the integration name:

```bash
python3 ../tip-cicd-tools/tools/compare_rebuilt_to_original/main.py \
  out/content/response_integrations/google/<PascalCaseName> \
  /Users/haggit/PycharmProjects/tip-marketplace/Integrations/<PascalCaseName> \
  --no-comparison-logs
```

### 3.2 Automated Logging Logic
To run a batch comparison and save results to a standardized log file, use a loop or script with the following naming convention:
`source_dir_name__num_of_integrations_comparison_log.txt`

**Example Bash Script for Batch Logging**:
```bash
#!/bin/bash
SOURCE_DIR="batch3_stash"
INTEGRATIONS=("alien_vault_anywhere" "arcsight" "aws_guard_duty") # Add your list here
NUM=${#INTEGRATIONS[@]}
LOG_FILE="${SOURCE_DIR}__${NUM}_comparison_log.txt"

echo "Starting comparison for $NUM integrations..." > "$LOG_FILE"

for name in "${INTEGRATIONS[@]}"; do
    # Map snake_case to PascalCase (Example: aws_guard_duty -> AWSGuardDuty)
    PASCAL_NAME=$(echo "$name" | perl -pe 's/(^|_)./uc($&)/ge;s/_//g')
    
    echo "--------------------------------------------" >> "$LOG_FILE"
    echo "Integration: $name" >> "$LOG_FILE"
    
    python3 ../tip-cicd-tools/tools/compare_rebuilt_to_original/main.py \
      "out/content/response_integrations/google/$PASCAL_NAME" \
      "/Users/haggit/PycharmProjects/tip-marketplace/Integrations/$PASCAL_NAME" \
      --no-comparison-logs >> "$LOG_FILE" 2>&1
done

echo "Results saved to $LOG_FILE"
```

### 3.3 Post-Comparison Log Cleanup
After the comparison runs, clean the logs by ignoring the following "expected" differences to reduce noise:

*   **AI Metadata Files**: Differences in `resources/ai/` files are expected as these are often only present in the modern Hub structure or generated during refactoring.
    ```text
    Only in OUT    : resources/ai/actions_ai_description.yaml
    resources/ai/integration_ai_description.yaml
    ```
*   **Requests Version Bump**: The modern environment typically uses `requests-2.32.4`, while legacy sources may use `2.31.0`.
    ```text
    ❌ Main dependency mismatch
    Only in OUT    : requests-2.32.4-py3-none-any.whl
    Only in SOURCE : requests-2.31.0-py3-none-any.whl
    ```

---

## Troubleshooting

*   **Comparison shows everything as missing**: Ensure you are comparing the **built artifact** in `out/` to the source, NOT the hub source folder.
*   **Path Nesting**: The built artifact directory inside `out/` must match the directory structure of the source for the tool to find files.
