# Integration Deconstruction & Migration Guide

This guide outlines the complete, end-to-end workflow for migrating legacy Google SecOps integrations from the `tip-marketplace` repository to the modern Content Hub. It covers the initial automated deconstruction and refactoring of the source code, local testing and building, parity validation, and finally the processes for pushing the Pull Request, managing the automated CI/CD Louhi pipeline, and merging the final integration into production.

---

## Prerequisites

*   **Environment**: Python 3.11+, `uv`, and `addlicense` ([GitHub Link](https://github.com/google/addlicense)) installed.
*   **Repositories**: You must have the following repositories cloned locally:
    *   `marketplace` (the current workspace)
    *   `tip-marketplace` (the legacy original source repository)
    *   `tip-cicd-tools` (for comparison tools, not mandatory)

---

## Step 1: Refactor the Hub Source

The `scripts/refactor_integration.py` script deconstructs the original integration and automates the mandatory changes and code conversions required to meet the modern GitHub Content Hub infrastructure and templates.

1.  **Configure Paths**: Identify your source integrations directory and destination directory.
2.  **Run Refactor**: Provide a **space-separated list of PascalCase integration names** (e.g., "AWSGuardDuty CofenseTriage") to the `--integrations-list` argument.
    ```bash
    python3 scripts/improved_refactor_integration.py \
      ../tip-marketplace/Integrations \
      content/response_integrations/google \
      --tests-dir ../tip-marketplace/Tests/Integrations \
      --integrations-list "AWSGuardDuty CofenseTriage"
    ```

### 1.1 Cleanup on Refactor Failure
**AI Agent Instruction:** The refactor script will log a summary at the end of its run indicating how many integrations succeeded and how many failed. 

If an integration fails to refactor:
- **Immediately delete the integration folder** from the destination directory (e.g., `rm -rf <snake_case_name>`).
- **Notify the user** that the integration folder has been deleted due to the refactor failure.
- **Why**: A failed refactor often leaves behind a partial directory structure that looks like a successful migration but contains broken or missing files. Deleting it prevents confusion during subsequent build and validation steps.

### 1.2 The `integration_testing` Framework & TIPCommon Constraints
**The Shift in Test Infrastructure:** The legacy tests in GoB rely on a common and local (non-external) `mocks` directory. The new Content Hub infrastructure replaces this entirely with the `integration_testing` framework, which provides all the same functionalities but is managed as an external Python package via `uv`. 

The refactor script automatically converts the legacy tests to use this new package, but there is one major constraint: **integrations using `TIPCommon < 2.0.0` cannot install `integration_testing`** because the framework strictly requires `TIPCommon >= 2.0.0`. 

*   **If the integration only has import tests:** This is handled locally via logic automatically injected into their `conftest.py` files. No action is required.
*   **If the integration has functional tests:** A manual intervention is required. You must upgrade the integration to use a newer version of `TIPCommon` across all files, and then add this newer version and `integration_testing` as dependencies.

### 1.3 Detecting Silent Upgrades & uv add Failures
A successful refactor log should be clean of dependency warnings. **AI Agent Instruction:** Proactively search the execution log for the following signatures ONLY if failures happened during the refactor:

1.  **Local Resolution Failure** (`WARNING Could not resolve local dependency TIPCommon`):
    *Fix*: Add the missing `.whl` from the original integration's dependencies directory, or investigate the version mismatch.

2.  **Global Installation Failure** (`WARNING Failed to install dependencies: ... uv add ... returned non-zero exit status`):
    *Note: This failure does not crash the refactoring tool (the final tally may still report success), but, because this failure stops `uv` mid-way, it may prevent other dependencies from being installed. If you manually fix the generated `pyproject.toml`, run `uv sync` inside the integration folder to finish installing the remaining dependencies.*

    *   **Fixing a Naming Conflict (Self-Dependency in uv)**: If an integration directory shares a name with a PyPI dependency (e.g., `twilio`).
        *   *Integration-only dependency (e.g., `akamai`)*: Append `-integration` to the `name` field in `pyproject.toml` (do not rename the directory). Add this logic to `increment_version_and_sync` in the refactor script.
        *   *Shared dependency (e.g., `http`)*: Rename both the directory and the `pyproject.toml` name with an `_integration` suffix. Update the refactor script's `ImportTransformer` and `ExpressionTransformer` to handle this. You must also add the original name to `INTEGRATIONS_WITH_INTEGRATION_SUFFIX` in the `mp` source code for builds to work.
    *   **Fixing a Missing Binary Wheel ("Failed to download a binary wheel")**: The `mp build` tool strictly requires `.whl` files.
        *   Bypass this by pointing directly to the PyPI source distribution URL.
        *   In `pyproject.toml`, under `[tool.uv.sources.package-name]`, set `url = "https://.../.tar.gz"`.
        *   Run `uv lock` in the integration's root directory and retry the build.

### 1.4 Common Post-Refactor Code Fixes (Before Testing/Build)
After the refactor script completes, some integrations may still require manual code adjustments to satisfy modern SDK requirements or resolve import path changes that the automated tool might miss.

#### 1.4.1 Correcting CaseInfo and AlertInfo Imports
In `soar-sdk >= 0.2.0`, the SDK has been modularized. Data model classes like `CaseInfo`, `AlertInfo`, `ConnectorInfo`, and `ConnectorContext` have been moved to a dedicated module.

**Symptoms**:
Import tests or connector execution fails with:
`ImportError: cannot import name 'CaseInfo' from 'soar_sdk.SiemplifyConnectors'`

**Detection**:
Run the following grep command from the marketplace root to find incorrect imports in your refactored integrations:
```bash
grep -rE "from soar_sdk.SiemplifyConnectors import .*(CaseInfo|AlertInfo|ConnectorInfo|ConnectorContext)" content/response_integrations/
```

**Required Action**:
Update the import statement in the affected Python scripts (usually connectors):
- **Old**: `from soar_sdk.SiemplifyConnectors import CaseInfo, SiemplifyConnectorExecution`
- **New**:
  ```python
  from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
  from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
  ```

#### 1.4.2 Expected Google Cloud Auth (GCP) Test Fixes
When refactoring integrations that rely on Google Cloud authentication (such as `cloud_logging`, `gmail`, `pub_sub`, or any integration using `TIPCommon` GCP auth), tests may initially fail. The original mocks in the `tip-marketplace` tests directory patched globally the authentication process, but in the marketplace we omit it as it is unnecessary. Due to stricter mocking in the new `integration_testing` framework and missing global mocks, you must manually apply the following fixes:

**1. Mock the ADC in `conftest.py`**
You must add the following fixture to the integration's `conftest.py` to prevent `DefaultCredentialsError` in CI environments:
```python
@pytest.fixture(autouse=True)
def mock_google_adc(mocker):
    """Mock the ADC to prevent DefaultCredentialsError in CI environments."""
    mock_creds = mocker.Mock()
    mock_creds.universe_domain = "googleapis.com"
    mocker.patch("google.auth.default", return_value=(mock_creds, "test-project"))
    mocker.patch("TIPCommon.rest.auth.get_adc", return_value=(mock_creds, "test-project"))
    # Add any other required module paths for your specific integration here
```

**2. The Missing Metadata Mock Route**
*   **Reason**: Newer versions of `TIPCommon` fetch the workload service account email directly from the GCP metadata server using a raw `requests.get` call. The new test framework strictly intercepts these requests and requires a defined mock route to answer them.
*   **The Fix**: You must manually add a mock route to the integration's `core/session.py` (or `async_session.py`) to satisfy this request:
    ```python
    @router.get('/computeMetadata/v1/instance/service-accounts/default/email')
    def get_default_service_account_email(self, _: MockRequest) -> MockResponse:
        return MockResponse(content='default@domain.com', headers={'content-type': 'text/plain'})
    ```
    *(Remember to add `self.get_default_service_account_email` to the `get_routed_functions` return list).*

**3. Adjusting Request History Assertions**
*   **Reason**: Updated Google libraries and the `mock_google_adc` fixture heavily bypass background authentication requests (like tokens). As a result, the `request_history` array recorded by the mock session will be shorter than in the legacy tests.
*   **The Fix**: Manually change the expected length in the test assertions to `>= 0` (e.g., change `assert len(script_session.request_history) >= 3` to `assert len(script_session.request_history) >= 0`). If there are specific token request assertions, they can usually be removed.

#### 1.4.3 Updating Legacy `unittest.mock.patch` Target Strings
The refactoring script structurally updates imports and class definitions to the new `snake_case` layout (e.g., `okta.core.OktaManager`). However, if an integration test uses Python's `patch()` decorator or context manager, it passes the target path as a raw string literal (e.g., `@patch('Integrations.Okta.Managers.OktaManager.jwt.encode')`).

**Symptoms**:
Tests fail with a `ModuleNotFoundError` or `AttributeError` indicating that the patched target does not exist.

**Required Action**:
Manually update the patch target strings in the test files to point to the new modernized paths.
- **Old**: `@patch('Integrations.Okta.Managers.OktaManager.jwt.encode')`
- **New**: `@patch('okta.core.OktaManager.jwt.encode')`

---

## Step 2: Run Tests

Before building, it is crucial to run the unit tests to ensure the refactored code functions properly.

1.  **Navigate to MP package**:
    ```bash
    cd packages/mp
    ```
2.  **Sync Environment**:
    ```bash
    uv sync
    ```
3.  **Run the Tests**:
    ```bash
    mp test -i <snake_case_name>
    ```
3.  **Review Results**: Standard output is often suppressed and compiled to HTML reports unless tests fail. Review failing tests and apply fixes outlined in Section 1.4.

---

## Step 3: Build the Integration

The `mp build` command restructures the integration back to the source GoB repository style.

**Note**: The `mp` CLI typically expects integrations to be located in the `content/response_integrations/google/` directory to build them as official integrations.

1.  **Navigate to MP package**:
    ```bash
    cd packages/mp
    ```
2.  **Sync Environment**:
    ```bash
    uv sync
    ```
3.  **Run Build** (using a safe one-liner to temporarily copy and clean up):
    *Why copy? The `mp build` tool is strictly configured to expect Google integrations to be located in the `content/response_integrations/google/` directory. If you are developing in a separate batch or working directory, you must temporarily copy it to the `google` folder for the build to succeed.*
    ```bash
    cp -r ../../content/response_integrations/<your_working_dir>/<snake_case_name> ../../content/response_integrations/google/ && \
    .venv/bin/mp build integration <snake_case_name> && \
    rm -rf ../../content/response_integrations/google/<snake_case_name>
    ```
    *Builds are output to `marketplace/out/content/response_integrations/google/<PascalCaseName>`.*

---

## Step 4: Validate Parity & Log Results

Parity validation can be done **locally** (by running the steps in this section) or **automatically** through the Louhi flow after pushing your PR to GitHub (as described in Step 5).

Use the comparison tool to identify functional differences between your built artifact and the original legacy source. 

**Note on Test Comparison:** The comparison script in the `tip-cicd-tools` repo is **only for integration source files**, not for the tests. Test files will be compared locally using a separate `compare_tests` script.

### 4.1 Run Comparison (Locally)
Execute the following command, replacing `<PascalCaseName>` with the integration name:

```bash
python3 ../tip-cicd-tools/tools/compare_rebuilt_to_original/main.py \
  out/content/response_integrations/google/<PascalCaseName> \
  ../tip-marketplace/Integrations/<PascalCaseName> \
  --no-comparison-logs
```

### 4.2 Post-Comparison Log Cleanup
After the comparison runs, you can ignore the following "expected" differences:

*   **`INTEGRATION_PATH` Normalizations**: The refactor script correctly normalizes `INTEGRATION_PATH` to point to the parent directory correctly (`pathlib.Path(__file__).parent.parent`). These diffs are expected.
*   **Import and Mock Patch Updates**: Fixes made in Step 1.4 to `unittest.mock.patch` targets and standardized imports.
*   **Requests Version Bump**: The modern environment typically uses newer dependency versions than the legacy source.

---

## Step 5: Push PR & Automated Louhi Flow

Once refactored, tested, and validated locally, push the files to create a Pull Request in the [Content Hub GitHub Repository](https://github.com/chronicle/content-hub/).

Pushing the PR triggers the following automated CI/CD pipeline:
1.  **GitHub Actions**: Automated tests will run against your branch. *(Note: Failures in the code check and validation GitHub actions are expected at this stage, and should be fixed after migration).*
2.  **Louhi Flow (`sync content hub to github`)**: A Louhi pipeline is triggered which performs the following:
    *   Rebuilds the integration.
    *   Compares the built artifact to the original one from GoB (using the `tip-cicd-tools` comparison script). *Note: This automated comparison only runs if it's the very first PR for this integration, which applies to this migration.*
    *   Pushes a CL to GoB with the built artifacts to officially replace the current legacy integration.

**Reviewing CI/CD Logs**:
If you need to view the execution logs for the automated build or comparison, you can find the flow's main branch execution logs here:
[Louhi Flow Logs: sync content hub to github](https://louhi.dev/5046856399454208/flow-detail/f8b5cb19-e197-4fef-9d23-af22c21cdfc3?branch=main)

---

## Step 6: Refine & Merge

1. **Refining the PR**: As you discover issues during CI/CD checks, parity validation, or code review, refine the PR with further commits.
2. **Abandon Stale CLs**: Every commit to the PR triggers the Louhi flow, which generates a new CL in GoB. You must manually ensure that all old, intermediate CLs generated from earlier commits on the way to your final version are **abandoned**.
3. **Merge**: Once you are completely happy with the integration, merge both the PR to GitHub and the final CL to GoB subsequently.
4. **Future Development**: Any further development on migrated integrations will be done through GitHub and never directly in GoB. A placeholder file will be added to GoB upon the merge of the CL to enforce this.
