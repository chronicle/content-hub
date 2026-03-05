"""Proof of concept script to run parser validations using secops-wrapper (External Version)."""

from datetime import datetime
import json
import os

import jsondiff

from absl import app
from absl import flags
from secops.client import SecOpsClient

FLAGS = flags.FLAGS

flags.DEFINE_string("parser_source", "community", "Source of the parser.")
flags.DEFINE_string("customer_id", None, "Chronicle customer ID.")
flags.DEFINE_string("project_id", None, "Google Cloud project ID.")
flags.DEFINE_string("region", None, "Chronicle region.")
flags.DEFINE_boolean("generate_report", False, "Whether to generate the markdown report file.")
flags.DEFINE_list("log_type_folders", [], "Comma-separated list of specific log type folders to validate. If empty, all folders are validated.")

_CONTENT_RELATIVE_PATH_TEMPLATE = (
    "./{parser_source}"
)
_REPORT_RELATIVE_PATH = (
    "validation_report.md"
)
# DO NOT MODIFY THIS VALUE - as your log type may not be registered yet!
_DEFAULT_LOG_TYPE = "DUMMY_LOGTYPE"


def main(argv):
  del argv  # Unused.

  print("-" * 80)
  print("Usage example:")
  print("  python3 run_parser_validations_external.py \\")
  print("    --parser_source=community \\")
  print("    --customer_id=ebdc4bb9-878b-11e7-8455-10604b7cb5c1 \\")
  print("    --project_id=malachite-catfood-byop \\")
  print("    --region=us \\")
  print("    --generate_report=True \\")
  print("    --log_type_folders=DUMMY_LOGTYPE,DUMMY_LOGTYPE2")
  print("-" * 80)

  mandatory_flags = ["customer_id", "project_id", "region"]
  missing_flags = [f for f in mandatory_flags if not getattr(FLAGS, f)]
  if missing_flags:
    print(f"Error: The following mandatory arguments are missing: {', '.join(missing_flags)}")
    return

  base_path = _CONTENT_RELATIVE_PATH_TEMPLATE.format(
      parser_source=FLAGS.parser_source
  )
  report_path = _REPORT_RELATIVE_PATH

  print("Initializing SecOpsClient...")
  secops_client = SecOpsClient()
  chronicle_client = secops_client.chronicle(
      customer_id=FLAGS.customer_id,
      project_id=FLAGS.project_id,
      region=FLAGS.region,
  )

  if not os.path.exists(base_path):
    print(f"Error: Base path {base_path} does not exist. Ensure you are running the script from the root directory that contains the 'content' folder.")
    return

  all_results = []  # List of (log_type, [usecase_results], [errors])

  log_types = sorted(os.listdir(base_path))
  if FLAGS.log_type_folders:
    log_types = [lt for lt in log_types if lt in FLAGS.log_type_folders]

  for log_type in log_types:
    log_type_path = os.path.join(base_path, log_type)
    if not os.path.isdir(log_type_path):
      continue

    log_type_results = []
    log_type_errors = []

    cbn_path = os.path.join(log_type_path, "cbn")
    if not os.path.isdir(cbn_path):
      log_type_errors.append("missing cbn folder")
      all_results.append((log_type, [], log_type_errors))
      continue

    # Find the config file.
    config_file = next((f for f in os.listdir(cbn_path) if f.endswith(".conf")), None)
    if not config_file:
      log_type_errors.append("missing .conf file")
      all_results.append((log_type, [], log_type_errors))
      continue

    config_path = os.path.join(cbn_path, config_file)
    with open(config_path, "r") as f:
      config = f.read()
    print(f"  Configuration file: {config_path}")

    raw_logs_path = os.path.join(cbn_path, "testdata", "raw_logs")
    expected_events_path = os.path.join(cbn_path, "testdata", "expected_events")

    if not os.path.exists(raw_logs_path):
      log_type_errors.append("no raw_logs folder found")
      all_results.append((log_type, [], log_type_errors))
      continue

    print(f"\nProcessing Log Type: {log_type}")

    for log_filename in sorted(os.listdir(raw_logs_path)):
      if not log_filename.endswith("_log.json"):
        continue

      usecase = log_filename[: -len("_log.json")]
      expected_filename = f"{usecase}_events.json"
      expected_path = os.path.join(expected_events_path, expected_filename)

      if not os.path.exists(expected_path):
        print(f"  Warning: No expected events file found for use case '{usecase}' at {expected_path}")
        continue

      logs_file_path = os.path.join(raw_logs_path, log_filename)
      with open(logs_file_path, "r") as f:
        logs_data = json.load(f)
      logs = logs_data.get("raw_logs", [])

      print(f"    Raw logs file: {logs_file_path}")

      print(f"  Validating Use Case: {usecase}...")
      try:
        validation_results = chronicle_client.run_parser(
            log_type=_DEFAULT_LOG_TYPE,
            parser_code=config,
            parser_extension_code="",
            logs=logs,
        )
        print(f"    Parser execution successful.")
      except Exception as e:
        print(f"  Error: Failed to run parser for use case {usecase}: {e}")
        log_type_results.append({
            "test_file": log_filename,
            "status": "FAILED",
            "details": f"API Error: {e}",
            "failures": []
        })
        continue

      def clean_val(v):
        if v is None:
          return ""
        if isinstance(v, str):
          return v.strip().rstrip(",").strip('"').strip()
        return v

      def normalize_timestamp(ts):
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

      output_data = {"events": transformed_events}

      with open(expected_path, "r") as f:
        test_events_data = json.load(f)

      def filter_timestamps(obj):
        if isinstance(obj, dict):
          return {
              k: filter_timestamps(v)
              for k, v in obj.items()
              if k not in ["timestamp", "event_timestamp"]
          }
        elif isinstance(obj, list):
          return [filter_timestamps(i) for i in obj]
        return obj

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

          def get_diff_str(d, path="$"):
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
                          f"path: {path}.{rk},\nexpected:"
                          f" {json.dumps(rv)},\ngot: <DELETED>"
                      )
                  elif isinstance(v, list):
                    for pos, val in v:
                      lines.append(
                          f"path: {path}[{pos}],\nexpected:"
                          f" {json.dumps(val)},\ngot: <DELETED>"
                      )
                elif k is jsondiff.insert:
                  if isinstance(v, dict):
                    for ak, av in v.items():
                      lines.append(
                          f"path: {path}.{ak},\nexpected: <MISSING>,\ngot:"
                          f" {json.dumps(av)}"
                      )
                  elif isinstance(v, list):
                    for pos, val in v:
                      lines.append(
                          f"path: {path}[{pos}],\nexpected: <MISSING>,\ngot:"
                          f" {json.dumps(val)}"
                      )
                else:
                  new_segment = f"[{k}]" if str(k).isdigit() else f".{k}"
                  lines.extend(get_diff_str(v, path + new_segment))
            return lines

          diff_lines = get_diff_str(event_diff)
          event_failures.append({"index": i, "diff": "\n".join(diff_lines)})

      def get_pretty_relpath(path):
        return os.path.relpath(path, os.getcwd())

      usecase_res = {
          "test_file": log_filename,
          "status": "PASSED" if not event_failures else "FAILED",
          "details": (
              f"{len(event_failures)} of"
              f" {max(len(expected_events), len(actual_events))} events failed."
              if event_failures
              else f"All {len(actual_events)} events matched expected output."
          ),
          "event_failures": event_failures,
          "config_path": get_pretty_relpath(config_path),
          "log_path": get_pretty_relpath(logs_file_path),
      }
      print(f"    Status: {usecase_res['status']}. {usecase_res['details']}")

      log_type_results.append(usecase_res)
      print("-" * 80)
    all_results.append((log_type, log_type_results, log_type_errors))

  # Generate Markdown Report
  report = ["# Parser Unit Test Results\n", "Summary of tests run on parser configurations and test data.\n"]
  overall_passed = True

  for i, (log_type, results, errors) in enumerate(all_results):
    if i > 0:
      report.append("---\n")
    report.append(f"## Parser: {log_type}\n")
    if errors:
      report.append("The following files are not found, "+
                    "so validation could not be completed:\n")
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
          report.append(
              f"  {res['config_path']} Log entry at index {fail['index']} in"
          )
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
    print(f"\nWriting Markdown report to {report_path}...")
    with open(report_path, "w") as f:
      f.write("\n".join(report))
  else:
    print("\nReport generation skipped (--generate_report=False).")

  # Final Failure Summary
  print("\n" + "=" * 80)
  print("FINAL FAILURE SUMMARY")
  print("=" * 80)
  any_failures = False
  for log_type, results, errors in all_results:
    if errors:
      any_failures = True
      print(f"\nParser: {log_type}")
      for err in errors:
        print(f"  - ERROR: {err}")

    for res in results:
      if res["status"] == "FAILED":
        any_failures = True
        print(f"\nParser: {log_type}")
        print(f"  - Test File: {res['test_file']}")
        print(f"    Status: {res['status']}")
        print(f"    Details: {res['details']}")
        if "event_failures" in res and res["event_failures"]:
          print("    Differences:")
          for fail in res["event_failures"]:
            print(f"    Log Entry {fail['index']}:")
            for line in fail["diff"].split("\n"):
              print(f"      {line}")

  if not any_failures:
    print("\nGreat, No failures found. Good to Go!!")
  print("=" * 80)


if __name__ == "__main__":
  app.run(main)
