# Contribution Guidelines for Parsers

This document outlines the standard workflow for contributing new parsers or updating existing ones, including local testing, required validations, and how to monitor the status of your Pull Request (PR) on GitHub.

## Prerequisites

*   All contributors must sign a Contributor License Agreement (CLA) before their submission can be considered for review.
*   The contributor should have a `chronicle.admin` role for the customer instance and have the ingested data for the logtype (can be custom/prebuilt) that the contributor needs to add/modify. At least 1000 log entries are expected to be ingested.

## 1. Local Development and Testing (Optional)

Before submitting a PR, you can run local tests to ensure faster iteration and catch basic errors.

*   **Authentication**: You must have `chronicle.parsers.run` permission, that is part of `chronicle.admin` default role.
*   **Action**: Modify the `parser.conf` file, and ensure that the `testdata/` subdirectory includes representative raw logs and corresponding expected UDM output files.
*   **Running Local Tests**: Use the provided command-line utility for sanity checks, refer to the [documentation](/tools/parsers/validations/docs/README.md) for more details.
*   **Mandatory `testdata/` changes whenever new PR is raised.**
*   This script runs your parser code against the raw logs in `testdata/` and compares the results to the expected events, reporting any errors to the console.

## 2. Pull Request Submission

*   **Fork or Branch**: Start by creating a new branch in the repository or forking it.
*   **Submit PR**: Once local development and testing are complete, submit a Pull Request targeting the `main` branch.
*   **PII Compliance**: You are strictly responsible for scrubbing any Personally Identifiable Information (PII) from the test data you submit to the repository.

## 3. Automated Validation and Status Checks

Upon submission, the automated system triggers a series of backend tests. The `main` branch has a GitHub Repository Ruleset that requires status checks to pass before a PR can be merged.

The system triggers two key check runs that must complete successfully:

*   **"Validate Parsers"** (Standalone parser validations)
*   **"Validate Google & Parsers"** (Validations on SecOps instance)

### 3a. Standalone parser validations

Basic Validations/Unit Tests are run automatically during PR raise event:

*   Checks folder structure validity.
*   Presence of all required files - `metadata.json`, `*.conf` file, events, test logs.
*   Validations of expected and actual events.
*   Support for multiple cases for single parser i.e. `testcase1_events.json`, `testcase1_logs.json`, `testcase2_events.json`, `testcase2_logs.json`. Validations match events and logs case wise according to the naming convention.
*   Runs unit tests using the parser logic against the data in `testdata/`.
*   Verifies that the log types in `metadata.json` are unique and present in SecOps.
*   Checks that no new logtype is added without support from internal team.

If these tests fail, you must fix the errors (e.g., structuring, unit tests) and push a new commit.

### 3b. Validations on SecOps instance (Manual step)

Certain validations that are part of **Validate Google & Parsers** require an execution against a live SecOps instance using customer logs. This is a mandatory step for the parsers that have `verified=True` in the `metadata.json`.

Due to access restrictions, this process must be manually triggered by the contributor.

*   **Purpose**: To check for negative functional and non-functional requirements (NFR) impact, such as degradation in parsing efficiency or unexpected drops in UDM field coverage, when the parser runs on actual customer data.
*   **Triggering**: You must call the appropriate API (e.g., the `RunAnalysis` API) to initiate the validation on a small sample of logs.
*   **Required Role**: To trigger this validation, you must have the `chronicle.admin` role in the corresponding SecOps instance.
*   **Status**: The overall success or failure status of this profiling validation will be reported back to your GitHub PR.
