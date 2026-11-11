from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv
from intezer.core.IntezerManager import IntezerManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
import json
import sys

SCRIPT_NAME = "Intezer - Submit File"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("Intezer")
    api_root = conf["API Root"]
    api_key = conf["API key"]
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"

    intezer_manager = IntezerManager(
        api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
    )

    file_paths = (
        siemplify.parameters.get("File Paths").split(",")
        if siemplify.parameters.get("File Paths")
        else []
    )

    scanned_files = {"existing_files": [], "new_files": []}

    errors = []
    submitted_files = []
    error_msg = ""

    for file_path in file_paths:
        try:
            file_sha256 = intezer_manager.sha256(file_path)
            existing_results = intezer_manager.get_existing_analysis(file_sha256)

            if existing_results:
                siemplify.LOGGER.info(
                    f"File {file_path} was already analyzed. Fetching report."
                )
                scanned_files["existing_files"].append((file_path, existing_results))

            else:
                siemplify.LOGGER.info(f"Submitting {file_path}.")
                results_url = intezer_manager.submit_file(file_path)
                scanned_files["new_files"].append((file_path, results_url))

            submitted_files.append(file_path)

        except Exception as e:
            errors.append(file_path)
            siemplify.LOGGER.error(f"Unable to submit {file_path}")
            siemplify.LOGGER.exception(e)

    if errors:
        error_msg = f"\nErrors occurred on the following files: {', '.join(errors)}.\nCheck logs for details."

    siemplify.end(
        f"The following files were submitted to scan: {', '.join(submitted_files)}.{error_msg}",
        json.dumps(scanned_files),
        EXECUTION_STATE_INPROGRESS,
    )


def async_analysis():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("Start async")

    try:
        conf = siemplify.get_configuration("Intezer")
        api_root = conf["API Root"]
        api_key = conf["API key"]
        verify_ssl = conf.get("Verify SSL", "False").lower() == "true"

        intezer_manager = IntezerManager(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )
        siemplify.LOGGER.info("Connected to Intezer")

        scanned_files = json.loads(siemplify.parameters["additional_data"])

        if all(
            [
                intezer_manager.is_analysis_completed(results_url)
                for file_path, results_url in scanned_files["new_files"]
            ]
        ):
            siemplify.LOGGER.info("All scans completed.")

            results_json = {}

            reports = scanned_files["existing_files"]

            errors = []
            error_msg = ""

            for file_path, results_url in scanned_files["new_files"]:
                try:
                    siemplify.LOGGER.info(f"Fetching report for {file_path}")
                    report = intezer_manager.get_results(results_url)
                    reports.append((file_path, report))
                except Exception as e:
                    errors.append(file_path)
                    siemplify.LOGGER.error(f"Unable to get report of {file_path}")
                    siemplify.LOGGER.exception(e)

            verdicts = []

            for file_path, report in reports:
                if report:
                    verdicts.append(report.get("verdict", "no_verdict").lower())

                    results_json[file_path] = report
                    csv_output = flat_dict_to_csv(dict_to_flat(report))
                    siemplify.LOGGER.info(f"Attaching report for {file_path}")

                    siemplify.result.add_data_table(f"Report - {file_path}", csv_output)

            siemplify.result.add_result_json(json.dumps(results_json))

            if errors:
                error_msg = f"\nErrors occurred on the following files: {', '.join(errors)}.\nCheck logs for details."

            siemplify.end(
                f"Analysis completed for all files.{error_msg}",
                ",".join(verdicts),
                EXECUTION_STATE_COMPLETED,
            )

        else:
            siemplify.end(
                "Analysis is still in progress.",
                json.dumps(scanned_files),
                EXECUTION_STATE_INPROGRESS,
            )

    except Exception as e:
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        async_analysis()
