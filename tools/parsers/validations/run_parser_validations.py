"""Script to run parser validations using secops-wrapper (External Version)."""

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import jsondiff
from absl import app, flags
from google.api_core import exceptions as api_core_exceptions
from google.auth import exceptions as auth_exceptions
from secops.client import SecOpsClient

FLAGS = flags.FLAGS

flags.DEFINE_string("parser_source", "community", "Source of the parser.")
flags.DEFINE_string("customer_id", None, "Chronicle customer ID.")
flags.DEFINE_string("project_id", None, "Google Cloud project ID.")
flags.DEFINE_string("region", None, "Chronicle region.")
flags.DEFINE_boolean("generate_report", False, "Whether to generate the markdown report file.")
flags.DEFINE_list(
    "log_type_folders",
    [],
    "Comma-separated list of specific log type folders to validate. If empty, all folders are "
    "validated.",
)

_CONTENT_RELATIVE_PATH_TEMPLATE = "./../../../content/parsers/third_party/{parser_source}"
_REPORT_RELATIVE_PATH = "validation_report.md"
# DO NOT MODIFY THIS VALUE - as your log type may not be registered yet!
_DEFAULT_LOG_TYPE = "DUMMY_LOGTYPE"


def clean_val(v: Any) -> Any:
    """Removes unwanted characters and formatting from a value."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip().rstrip(",").strip('"').strip()
    return v


def normalize_timestamp(ts: str | None) -> str | None:
    """Normalizes a timestamp string to a consistent format."""
    if not ts or not isinstance(ts, str):
        return ts
    try:
        if "." in ts:
            dt = datetime.strptime(ts.rstrip("Z"), "%Y-%m-%dT%H:%M:%S.%f")
        else:
            dt = datetime.strptime(ts.rstrip("Z"), "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
    except ValueError:
        return ts


def filter_timestamps(obj: Any) -> Any:
    """Recursively removes timestamp fields from a dictionary or list."""
    if isinstance(obj, dict):
        return {
            k: filter_timestamps(v)
            for k, v in obj.items()
            if k not in ["timestamp", "event_timestamp"]
        }
    elif isinstance(obj, list):
        return [filter_timestamps(i) for i in obj]
    return obj


def get_diff_str(d: dict | list, path: str = "$") -> list[str]:
    """Generates a list of strings representing the differences between two objects."""
    lines = []
    if isinstance(d, list) and len(d) == 2:
        lines.append(f"path: {path},")
        lines.append(f"expected: {json.dumps(d[0])},")
        lines.append(f"got: {json.dumps(d[1])}")
    elif isinstance(d, dict):
        for k, v in d.items():
            if k is jsondiff.delete:
                if isinstance(v, dict):
                    for rk, rv in v.items():
                        lines.append(
                            f"path: {path}.{rk},\nexpected: {json.dumps(rv)},\ngot: <DELETED>"
                        )
                elif isinstance(v, list):
                    for pos, val in v:
                        lines.append(
                            f"path: {path}[{pos}],\nexpected: {json.dumps(val)},\ngot: <DELETED>"
                        )
            elif k is jsondiff.insert:
                if isinstance(v, dict):
                    for ak, av in v.items():
                        lines.append(
                            f"path: {path}.{ak},\nexpected: <MISSING>,\ngot: {json.dumps(av)}"
                        )
                elif isinstance(v, list):
                    for pos, val in v:
                        lines.append(
                            f"path: {path}[{pos}],\nexpected: <MISSING>,\ngot: {json.dumps(val)}"
                        )
            else:
                new_segment = f"[{k}]" if str(k).isdigit() else f".{k}"
                lines.extend(get_diff_str(v, path + new_segment))
    return lines


def get_pretty_relpath(path: Path) -> str:
    """Returns the relative path of a file in a user-friendly format."""
    return os.path.relpath(path)


def main(argv: list[str]) -> None:
    """Runs parser validations on log types.

    Args:
      argv: A list of command-line arguments.

    """
    del argv  # Unused.

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logging.info("-" * 80)
    logging.info("Usage example:")
    logging.info("  python3 run_parser_validations_external.py \\")
    logging.info("    --parser_source=community \\")
    logging.info("    --customer_id={CUSTOMER_ID} \\")
    logging.info("    --project_id={PROJECT_ID}} \\")
    logging.info("    --region=us \\")
    logging.info("    --generate_report=True \\")
    logging.info("    --log_type_folders=DUMMY_LOGTYPE,DUMMY_LOGTYPE2")
    logging.info("-" * 80)

    mandatory_flags = ["customer_id", "project_id", "region"]
    missing_flags = [f for f in mandatory_flags if not getattr(FLAGS, f)]
    if missing_flags:
        logging.error(f"The following mandatory arguments are missing: {', '.join(missing_flags)}")
        return

    base_path = Path(_CONTENT_RELATIVE_PATH_TEMPLATE.format(parser_source=FLAGS.parser_source))
    report_path = Path(_REPORT_RELATIVE_PATH)

    secops_client = SecOpsClient()
    chronicle_client = secops_client.chronicle(
        customer_id=FLAGS.customer_id,
        project_id=FLAGS.project_id,
        region=FLAGS.region,
    )

    if not base_path.exists():
        logging.error(
            f"Base path {base_path} does not exist. Ensure you are running the script from the "
            f"root directory that contains the 'content' folder."
        )
        return

    all_results = []  # List of (log_type, [usecase_results], [errors])

    log_types = sorted([d.name for d in base_path.iterdir() if d.is_dir()])
    if FLAGS.log_type_folders:
        log_types = [lt for lt in log_types if lt in FLAGS.log_type_folders]

    if not log_types:
        logging.info("No log type content found. Nothing to validate.")
        return

    for log_type in log_types:
        log_type_path = base_path / log_type
        if not log_type_path.is_dir():
            continue

        log_type_results = []
        log_type_errors = []

        cbn_path = log_type_path / "cbn"
        if not cbn_path.is_dir():
            log_type_errors.append("missing cbn folder")
            all_results.append((log_type, [], log_type_errors))
            continue

        # Find the config file.
        try:
            config_file = next(cbn_path.glob("*.conf"))
        except StopIteration:
            log_type_errors.append("missing .conf file")
            all_results.append((log_type, [], log_type_errors))
            continue

        config = config_file.read_text()
        logging.info(f"  Configuration file: {get_pretty_relpath(config_file)}")

        raw_logs_path = cbn_path / "testdata" / "raw_logs"
        expected_events_path = cbn_path / "testdata" / "expected_events"

        if not raw_logs_path.exists():
            log_type_errors.append("no raw_logs folder found")
            all_results.append((log_type, [], log_type_errors))
            continue

        logging.info(f"\nProcessing Log Type: {log_type}")

        for log_file in sorted(raw_logs_path.glob("*_log.json")):
            usecase = log_file.name.rsplit("_log.json", 1)[0]
            expected_filename = f"{usecase}_events.json"
            expected_path = expected_events_path / expected_filename

            if not expected_path.exists():
                logging.warning(
                    f"  Warning: No expected events file found for use case '{usecase}' at "
                    f"{expected_path}"
                )
                continue

            logs_data = json.loads(log_file.read_text())
            logs = logs_data.get("raw_logs", [])

            logging.info(f"    Raw logs file: {get_pretty_relpath(log_file)}")

            logging.info(f"  Validating Use Case: {usecase}...")
            try:
                validation_results = chronicle_client.run_parser(
                    log_type=_DEFAULT_LOG_TYPE,
                    parser_code=config,
                    parser_extension_code="",
                    logs=logs,
                )
                logging.info("    Parser execution successful.")
            except (
                auth_exceptions.DefaultCredentialsError,
                api_core_exceptions.GoogleAPICallError,
            ) as e:
                logging.error(f"  Error: Failed to run parser for use case {usecase}: {e}")
                log_type_results.append({
                    "test_file": log_file.name,
                    "status": "FAILED",
                    "details": f"API Error: {e}",
                    "failures": [],
                })
                continue

            transformed_events = []
            for result in validation_results.get("runParserResults", []):
                parsed_events = result.get("parsedEvents", {}).get("events", [])
                for event_wrapper in parsed_events:
                    old_event = event_wrapper.get("event", {})
                    old_metadata = old_event.get("metadata", {})

                    timestamp = normalize_timestamp(old_metadata.get("eventTimestamp"))

                    new_event = {
                        "event": {
                            "timestamp": timestamp,
                            "idm": {
                                "read_only_udm": {
                                    "metadata": {
                                        "event_timestamp": timestamp,
                                        "event_type": old_metadata.get("eventType"),
                                        "description": clean_val(old_metadata.get("description")),
                                    },
                                    "additional": {
                                        k: clean_val(v)
                                        for k, v in old_event.get("additional", {}).items()
                                    },
                                }
                            },
                        }
                    }
                    transformed_events.append(new_event)

            test_events_data = json.loads(expected_path.read_text())

            expected_events = test_events_data.get("events", [])
            actual_events = transformed_events

            event_failures = []
            for i in range(max(len(expected_events), len(actual_events))):
                exp = expected_events[i] if i < len(expected_events) else None
                act = actual_events[i] if i < len(actual_events) else None

                event_diff = jsondiff.diff(
                    filter_timestamps(exp),
                    filter_timestamps(act),
                    syntax="symmetric",
                )

                if event_diff:
                    diff_lines = get_diff_str(event_diff)
                    event_failures.append({"index": i, "diff": "\n".join(diff_lines)})

            usecase_res = {
                "test_file": log_file.name,
                "status": "PASSED" if not event_failures else "FAILED",
                "details": (
                    f"{len(event_failures)} of"
                    f" {max(len(expected_events), len(actual_events))} events failed."
                    if event_failures
                    else f"All {len(actual_events)} events matched expected output."
                ),
                "event_failures": event_failures,
                "config_path": get_pretty_relpath(config_file),
                "log_path": get_pretty_relpath(log_file),
            }
            logging.info(f"    Status: {usecase_res['status']}. {usecase_res['details']}")

            log_type_results.append(usecase_res)
            logging.info("-" * 80)
        all_results.append((log_type, log_type_results, log_type_errors))

    # Generate Markdown Report
    report = [
        "# Parser Unit Test Results\n",
        "Summary of tests run on parser configurations and test data.\n",
    ]
    overall_passed = True

    for i, (log_type, results, errors) in enumerate(all_results):
        if i > 0:
            report.append("---\n")
        report.append(f"## Parser: {log_type}\n")
        if errors:
            report.append(
                "The following files are not found, " + "so validation could not be completed:\n"
            )
            for err in errors:
                report.append(f"- {err}")
            report.append("\n")
            overall_passed = False
            continue

        report.append("| Test File | Status | Details |")
        report.append("| :--- | :--- | :--- |")
        for res in results:
            status_emoji = "✅ PASSED" if res["status"] == "PASSED" else "❌ FAILED"
            report.append(f"| {res['test_file']} | {status_emoji} | {res['details']} |")
            if res["status"] == "FAILED":
                overall_passed = False
        report.append("\n")

        for res in results:
            if res["event_failures"]:
                report.append(f"### Failure Details for {res['test_file']}\n")
                for fail in res["event_failures"]:
                    report.append(f"* **Log Entry {fail['index']}**")
                    report.append(f"  {res['config_path']} Log entry at index {fail['index']} in")
                    report.append(f"  {res['log_path']}: unexpected events")
                    report.append("  Diff (-Expected, +Actual):")
                    report.append("  ```")
                    for line in fail["diff"].split("\n"):
                        report.append(f"  {line}")
                    report.append("  ```\n")

    if overall_passed:
        report.append("**Overall Status:** All tests passed.")
    else:
        report.append("**Overall Status:** Failures detected. Please review the details above.")

    report.append("\n[View more details on Google SecOps Bot](https://chronicle.security/)\n")

    if FLAGS.generate_report:
        logging.info(f"\nWriting Markdown report to {report_path}...")
        with open(report_path, "w") as f:
            f.write("\n".join(report))
    else:
        logging.info("\nReport generation skipped (--generate_report=False).")

    # Final Failure Summary
    logging.info("\n" + "=" * 80)
    logging.info("FINAL FAILURE SUMMARY")
    logging.info("=" * 80)
    any_failures = False
    for log_type, results, errors in all_results:
        if errors:
            any_failures = True
            logging.error(f"\nParser: {log_type}")
            for err in errors:
                logging.error(f"  - ERROR: {err}")

        for res in results:
            if res["status"] == "FAILED":
                any_failures = True
                logging.error(f"\nParser: {log_type}")
                logging.error(f"  - Test File: {res['test_file']}")
                logging.error(f"    Status: {res['status']}")
                logging.error(f"    Details: {res['details']}")
                if "event_failures" in res and res["event_failures"]:
                    logging.error("    Differences:")
                    for fail in res["event_failures"]:
                        logging.error(f"    Log Entry {fail['index']}:")
                        for line in fail["diff"].split("\n"):
                            logging.error(f"      {line}")

    if not any_failures:
        logging.info("\nGreat, No failures found. Good to Go!!")
    logging.info("=" * 80)


if __name__ == "__main__":
    app.run(main)
