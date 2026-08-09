# `mp describe-regression-test`

Commands for executing end-to-end regression testing on AI-generated metadata descriptions by comparing baseline YAML metadata in the repository against newly generated or test metadata.

> **Note**: Every subcommand available under `mp describe` (`action`, `connector`, `job`, `integration`, `all-content`) is also available under `mp describe-regression-test` (and accessible via `mp describe describe-regression-test`).

---

## Overview & Classification Rules

The `describe-regression-test` command compares baseline metadata files (`actions_ai_description.yaml`, `integration_ai_description.yaml`, `connectors_ai_description.yaml`, `jobs_ai_description.yaml`) against test metadata files. This comparison verifies that `mp describe` metadata remains safe, accurate, and actionable for tool selection and action execution.

**Regression Classification Rules:**
- **Boolean attribute `True` → `False`**: Marked as `marked as a regression for manual checking`.
- **Boolean attribute `False` → `True`**: Marked as `might be a regression`.
- **Action missing in test** (Action present in baseline but missing in test code generation): Marked as `marked as a regression for manual checking (action missing in test)`.
- **Action missing in baseline** (Action present in code generation but missing in baseline): Marked as `action missing in baseline (needs mp describe)`.
- **Free-form text fields** (`ai_description`, `ai_short_description`, `parameters_description`): By default, natural phrasing variations between LLM runs are ignored. When `-j` / `--use-llm-judge` is enabled, an **Asymmetric LLM Judge** (`Gemini 3.1 Pro Preview`) evaluates mismatched text fields via **Deferred Batch Evaluation** (collecting text candidates across all integrations and evaluating them concurrently in a single batch):
  - **Asymmetric Separation of Concerns**: Gemini evaluates ONLY semantic operational equivalence (`EQUIVALENT` vs `NOT_EQUIVALENT`) and categorizes failures into 3 directed lists (`missing_operational_facts`, `introduced_operational_facts`, `quality_failures`). A deterministic Python classifier (`ChangeClassifier`) then assigns the provenance `change_type` (`GENERATOR_REGRESSION`, etc.) and CI gate decision (`PASS`, `BLOCK`, `REVIEW`).
  - **5-Rule Operational Equivalence Contract**:
    1. **Parameter & Constraint Integrity (CRITICAL)**: Dropping a parameter, altering data types, shifting applicability (`Mandatory` to `Optional`), reversing boolean intent, or introducing operational limits not in baseline is **`NOT_EQUIVALENT`**.
    2. **Flow & Core Intent Descriptions**: Omitting logical workflow steps/sequence or dropping declarative action is **`NOT_EQUIVALENT`**.
    3. **Zero Tolerance for Semantic Typos & Broken Grammar**: Typographical errors causing semantic drift, misspelled technical identifiers, or severely degraded grammar are **`NOT_EQUIVALENT`**.
    4. **Format & Markdown Agnosticism (FORGIVE)**: Flattening tables, removing styling tags, or deep domain synonyms are **`EQUIVALENT`**.
    5. **Backend Protocol Noise vs. Infrastructure**: Exposing generic network/transport/auth protocols is **`EQUIVALENT`**; introducing unverified infrastructure or proprietary databases not present in Baseline is **`NOT_EQUIVALENT`**.
  - Note that internal classifier `reasoning` fields are excluded from LLM Judge evaluation.
- **LLM Reasoning Context**: For any boolean attribute regression or text semantic mismatch, the corresponding reasoning and any reported failure facts are recorded in the `LLM Input` column of the CSV report.

---

## `mp describe-regression-test action`

Run regression test comparing baseline and test YAML for action descriptions.

### Usage

```bash
mp describe-regression-test action [ACTIONS]... [OPTIONS]
```

### Options

| Option             | Shorthand | Description                                                                                  | Type     | Default |
|:-------------------|:----------|:---------------------------------------------------------------------------------------------|:---------|:--------|
| `--integration`    | `-i`      | The name of the integration(s) containing the actions, comma-separated.                      | `str`    | `None`  |
| `--all`            | `-a`      | Test all integrations in the marketplace, or all actions if an integration is specified.     | `bool`   | `False` |
| `--src`            |           | Customize source folder to compare from.                                                     | `path`   | `None`  |
| `--dst`            |           | Customize destination/test folder to compare with (defaults to `test_descriptions/`).        | `path`   | `None`  |
| `--report-file`    |           | CSV report file path for results (defaults to `regression_report.csv`).                      | `path`   | `None`  |
| `--run-describe`   |           | Automatically run Gemini describe generation to `--dst` before comparing (default `True`).   | `bool`   | `True`  |
| `--use-llm-judge`  | `-j`      | Use Gemini Judge to evaluate text field semantic equivalence.                                | `bool`   | `False` |
| `--use-batch-api`  |           | Use Google GenAI Batch API for LLM Judge evaluation instead of fast concurrent requests.      | `bool`   | `False` |
| `--override`       | `-o`      | Force rewrite content when generating descriptions.                                           | `bool`   | `False` |
| `--quiet`          | `-q`      | Log less on runtime.                                                                         | `bool`   | `False` |
| `--verbose`        | `-v`      | Log more on runtime.                                                                         | `bool`   | `False` |

---

## `mp describe-regression-test connector`

Run regression test comparing baseline and test YAML for connector descriptions.

### Usage

```bash
mp describe-regression-test connector [CONNECTORS]... [OPTIONS]
```

### Options

| Option             | Shorthand | Description                                                                                  | Type     | Default |
|:-------------------|:----------|:---------------------------------------------------------------------------------------------|:---------|:--------|
| `--integration`    | `-i`      | The name of the integration containing the connectors.                                       | `str`    | `None`  |
| `--all`            | `-a`      | Test all integrations in the marketplace, or all connectors if an integration is specified.  | `bool`   | `False` |
| `--src`            |           | Customize source folder to compare from.                                                     | `path`   | `None`  |
| `--dst`            |           | Customize destination/test folder to compare with.                                           | `path`   | `None`  |
| `--report-file`    |           | CSV report file path for results.                                                            | `path`   | `None`  |
| `--run-describe`   |           | Automatically run Gemini describe generation to `--dst` before comparing.                   | `bool`   | `True`  |
| `--use-llm-judge`  | `-j`      | Use Gemini Judge to evaluate text field semantic equivalence.                                | `bool`   | `False` |
| `--use-batch-api`  |           | Use Google GenAI Batch API for LLM Judge evaluation instead of fast concurrent requests.      | `bool`   | `False` |
| `--override`       | `-o`      | Force rewrite content when generating descriptions.                                           | `bool`   | `False` |
| `--quiet`          | `-q`      | Log less on runtime.                                                                         | `bool`   | `False` |
| `--verbose`        | `-v`      | Log more on runtime.                                                                         | `bool`   | `False` |

---

## `mp describe-regression-test job`

Run regression test comparing baseline and test YAML for job descriptions.

### Usage

```bash
mp describe-regression-test job [JOBS]... [OPTIONS]
```

### Options

| Option             | Shorthand | Description                                                                                  | Type     | Default |
|:-------------------|:----------|:---------------------------------------------------------------------------------------------|:---------|:--------|
| `--integration`    | `-i`      | The name of the integration containing the jobs.                                             | `str`    | `None`  |
| `--all`            | `-a`      | Test all integrations in the marketplace, or all jobs if an integration is specified.        | `bool`   | `False` |
| `--src`            |           | Customize source folder to compare from.                                                     | `path`   | `None`  |
| `--dst`            |           | Customize destination/test folder to compare with.                                           | `path`   | `None`  |
| `--report-file`    |           | CSV report file path for results.                                                            | `path`   | `None`  |
| `--run-describe`   |           | Automatically run Gemini describe generation to `--dst` before comparing.                   | `bool`   | `True`  |
| `--use-llm-judge`  | `-j`      | Use Gemini Judge to evaluate text field semantic equivalence.                                | `bool`   | `False` |
| `--use-batch-api`  |           | Use Google GenAI Batch API for LLM Judge evaluation instead of fast concurrent requests.      | `bool`   | `False` |
| `--override`       | `-o`      | Force rewrite content when generating descriptions.                                           | `bool`   | `False` |
| `--quiet`          | `-q`      | Log less on runtime.                                                                         | `bool`   | `False` |
| `--verbose`        | `-v`      | Log more on runtime.                                                                         | `bool`   | `False` |

---

## `mp describe-regression-test integration`

Run regression test comparing baseline and test YAML for integration-level descriptions.

### Usage

```bash
mp describe-regression-test integration [INTEGRATIONS]... [OPTIONS]
```

### Options

| Option             | Shorthand | Description                                                                                  | Type     | Default |
|:-------------------|:----------|:---------------------------------------------------------------------------------------------|:---------|:--------|
| `--all`            | `-a`      | Test all integrations in the marketplace.                                                    | `bool`   | `False` |
| `--src`            |           | Customize source folder to compare from.                                                     | `path`   | `None`  |
| `--dst`            |           | Customize destination/test folder to compare with.                                           | `path`   | `None`  |
| `--report-file`    |           | CSV report file path for results.                                                            | `path`   | `None`  |
| `--run-describe`   |           | Automatically run Gemini describe generation to `--dst` before comparing.                   | `bool`   | `True`  |
| `--use-llm-judge`  | `-j`      | Use Gemini Judge to evaluate text field semantic equivalence.                                | `bool`   | `False` |
| `--use-batch-api`  |           | Use Google GenAI Batch API for LLM Judge evaluation instead of fast concurrent requests.      | `bool`   | `False` |
| `--override`       | `-o`      | Force rewrite content when generating descriptions.                                           | `bool`   | `False` |
| `--quiet`          | `-q`      | Log less on runtime.                                                                         | `bool`   | `False` |
| `--verbose`        | `-v`      | Log more on runtime.                                                                         | `bool`   | `False` |

---

## `mp describe-regression-test all-content`

Run regression test comparing baseline and test YAML for all content types (actions, connectors, jobs, integration) for integrations.

### Usage

```bash
mp describe-regression-test all-content [INTEGRATIONS]... [OPTIONS]
```

### Options

| Option             | Shorthand | Description                                                                                  | Type     | Default |
|:-------------------|:----------|:---------------------------------------------------------------------------------------------|:---------|:--------|
| `--all`            | `-a`      | Test all content for all integrations in the marketplace.                                    | `bool`   | `False` |
| `--src`            |           | Customize source folder to compare from.                                                     | `path`   | `None`  |
| `--dst`            |           | Customize destination/test folder to compare with.                                           | `path`   | `None`  |
| `--report-file`    |           | CSV report file path for results.                                                            | `path`   | `None`  |
| `--run-describe`   |           | Automatically run Gemini describe generation to `--dst` before comparing.                   | `bool`   | `True`  |
| `--use-llm-judge`  | `-j`      | Use Gemini Judge to evaluate text field semantic equivalence.                                | `bool`   | `False` |
| `--use-batch-api`  |           | Use Google GenAI Batch API for LLM Judge evaluation instead of fast concurrent requests.      | `bool`   | `False` |
| `--override`       | `-o`      | Force rewrite content when generating descriptions.                                           | `bool`   | `False` |
| `--quiet`          | `-q`      | Log less on runtime.                                                                         | `bool`   | `False` |
| `--verbose`        | `-v`      | Log more on runtime.                                                                         | `bool`   | `False` |

---

## Examples

### 1. Standard On-the-Fly Regression Test (Generate + Compare)

Generate new action descriptions for `duo` into `test_descriptions/` via Gemini and compare against repository baseline:

```bash
uv run --project packages/mp mp describe-regression-test action -i duo
```

### 2. Compare Pre-existing Test Directory (No LLM Call)

Compare baseline YAML against existing test YAML files in a custom folder without invoking Gemini API:

```bash
uv run --project packages/mp mp describe-regression-test action -i duo --dst /tmp/my_test_dir --no-run-describe
```

### 3. Test All Content Types with Custom Report File

Run regression testing on all content types (actions, connectors, jobs, integration) for `duo` and output report to `duo_report.csv`:

```bash
uv run --project packages/mp mp describe-regression-test all-content -i duo --report-file duo_report.csv
```

### 4. Marketplace-Wide Regression Test

Run regression testing across all marketplace integrations for all content types:

```bash
uv run --project packages/mp mp describe-regression-test all-content -a
```

### 5. Semantic Regression Test with LLM as a Judge

Run regression testing on `duo` action descriptions and use Gemini as an LLM Judge (`-j` / `--use-llm-judge`) to evaluate semantic equivalence of modified text descriptions:

```bash
uv run --project packages/mp mp describe-regression-test action -i duo -j
```

### 6. Filter by Specific Action Name with Debug Logging

Run regression testing on a specific action within an integration (`"Get Authentication Logs for User"`), using existing test files (`--no-run-describe`) and verbose debug logging (`-v`) to monitor live batch polling:

```bash
uv run --project packages/mp mp describe-regression-test action -i duo -j --no-run-describe -v "Get Authentication Logs for User"
```

### 7. Optional Batch API Execution (`--use-batch-api`)

By default, the LLM Judge executes via fast concurrent interactive requests (`asyncio.gather`), which takes ~3–8 seconds. For large-scale overnight regression tests across hundreds of marketplace integrations, use `--use-batch-api` to route requests through Google GenAI's asynchronous cloud Batch queue:

```bash
uv run --project packages/mp mp describe-regression-test action -i duo -j --use-batch-api --no-run-describe
```

### 8. Multi-Integration Regression Testing (`-i "duo,anomali"`)

Run regression testing across multiple integrations simultaneously by specifying a comma-separated list of integration names. The terminal report displays clean `Integration` and `Component` columns (`duo` | `action`, `anomali` | `action`) for readable console scanning:

```bash
uv run --project packages/mp mp describe-regression-test action -i "duo,anomali" -j --no-run-describe
```

> [!WARNING]
> **Execution Duration**: Running a marketplace-wide regression test processes every integration and content type across the entire repository. This operation invokes LLM API generation at scale, will take a very long time to complete, and the exact execution duration cannot be predicted in advance.

---

## Promoting Generated Descriptions (`mp describe-accept` / `mp accept`)

When `mp describe-regression-test` identifies differences between existing baselines in `resources/ai/` and newly generated test descriptions in `test_descriptions/`, there are three primary operational scenarios:

### 1. Scenario 1: Refactoring or Bugfix without Contract Change (`EQUIVALENT`)
When a developer modifies internal implementation details (e.g., bug fixes, logging improvements, refactored helpers) without altering the action's operational contract, the **Asymmetric LLM Judge** (`-j`) evaluates phrasing variations as **`EQUIVALENT`**.
- **Action**: No baseline update is needed. The existing baseline in `resources/ai/` remains accurate and valid. Do **NOT** run `mp describe-accept`.

### 2. Scenario 2: Legitimate Contract Change (`NOT_EQUIVALENT` -> Accept)
When a developer intentionally updates the operational contract (e.g., adding a parameter, changing data types, or adding external mutation capabilities), the regression test returns **`NOT_EQUIVALENT` (`GENERATOR_REGRESSION`)**.
- **Action**: Once verified, run `mp describe-accept -i <integration>` to promote the newly generated candidate in `test_descriptions/` to the official baseline in `resources/ai/`:

```bash
# Simulate which baselines would be updated (dry run)
uv run --project packages/mp mp describe-accept action -i duo --dry-run

# Promote candidate files and update official baselines in resources/ai/
uv run --project packages/mp mp describe-accept action -i duo
```

### 3. Scenario 3: Unintended Contract Regression (`NOT_EQUIVALENT` -> Fix Code)
If an action contract is accidentally broken (e.g., dropping a required parameter or filter check during refactoring), the regression test alerts the developer.
- **Action**: Fix the Python source code and re-run the regression test. Do **NOT** run `mp describe-accept`.

