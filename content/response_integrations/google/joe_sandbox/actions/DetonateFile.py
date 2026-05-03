from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.JoeSandboxManager import (
    JoeSandboxManager,
    REPORT_WEB_LINK,
    JoeSandboxLimitManagerError,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
import sys
import base64
import json


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "JoeSandbox - Detonate file"

    conf = siemplify.get_configuration("JoeSandbox")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]
    use_ssl = conf["Use SSL"].lower() == "true"
    joe = JoeSandboxManager(api_root, api_key, use_ssl)

    file_paths = (
        siemplify.parameters.get("File Paths", "").split(",")
        if siemplify.parameters.get("File Paths")
        else []
    )

    # value returned by get
    comments = siemplify.parameters.get("Comment", "Uploaded by Siemplify")
    siemplify.LOGGER.info("Start Detonate File Action.")

    # TODO: Check Linux
    web_ids = []

    for file_path in file_paths:
        try:
            with open(file_path, "rb") as sample:
                web_ids.append(
                    (joe.analyze(sample, comments=comments), file_path)
                )
        except JoeSandboxLimitManagerError as e:
            # Reached max allowed API requests - notify user
            siemplify.LOGGER.error(
                "The number of allowed submissions (20) "
                f"per day have been reached. {e}"
            )
            siemplify.end(
                "The number of allowed submissions (20)per"
                "day have been reached.",
                "false",
                EXECUTION_STATE_FAILED,
            )
        except Exception as e:
            siemplify.LOGGER.error(
                f"Unable to submit {file_path}. Error: {str(e)}"
            )
            siemplify.LOGGER.exception(e)

    if not web_ids:
        siemplify.end(
            "No files were submitted. Check logs for details.",
            "false",
            EXECUTION_STATE_FAILED,
        )

    output_massage = (
        "Successfully submitted files: "
        f"{', '.join([file_path for _, file_path in web_ids])}."
    )
    siemplify.LOGGER.info(output_massage)

    siemplify.end(
        output_massage,
        json.dumps(web_ids),
        EXECUTION_STATE_INPROGRESS
    )


def fetch_scan_report_async():

    siemplify = SiemplifyAction()
    siemplify.script_name = "JoeSandbox - Detonate file"
    try:
        conf = siemplify.get_configuration("JoeSandbox")
        api_root = conf["Api Root"]
        api_key = conf["Api Key"]
        use_ssl = conf["Use SSL"].lower() == "true"
        joe = JoeSandboxManager(api_root, api_key, use_ssl)

        download_resource = siemplify.parameters.get("Report Format", "html")
        # Extract web_ids
        web_ids = json.loads(siemplify.parameters["additional_data"])

        is_completed = True
        json_results = {}

        for web_id, file_path in web_ids:
            try:
                joe.get_analysis_info(web_id)
                if not joe.is_analysis_completed(web_id):
                    is_completed = False

            except Exception as e:
                siemplify.LOGGER.error(
                    f"Unable to get analysis of file {file_path}. Waiting."
                )
                siemplify.LOGGER.exception(e)

        if is_completed:
            detected_files = []

            for web_id, file_path in web_ids:
                try:
                    analysis_info = joe.get_analysis_info(web_id)
                    siemplify.LOGGER.info(f"Fetching report for {file_path}.")

                    json_results[file_path] = analysis_info
                    # Download analysis
                    full_report = joe.download_report(web_id, download_resource)
                    try:
                        siemplify.result.add_attachment(
                            f"{file_path} Report",
                            f"JoeSandboxReport.{download_resource}",
                            base64.b64encode(full_report.encode('utf-8')),
                        )
                    except Exception as e:
                        # Attachment cannot be larger than 3 MB
                        siemplify.LOGGER.error(
                            f"Can not add attachment: {file_path}.\n{str(e)}."
                        )

                    siemplify.result.add_link(
                        "JoeSandbox Report - Web Link",
                        REPORT_WEB_LINK.format(analysis_info.get("analysisid")),
                    )

                    # Check for detection risk - result 'suspicious'
                    if joe.is_detection_suspicious(analysis_info):
                        detected_files.append(file_path)
                        try:
                            siemplify.create_case_insight(
                                title="Case Insight",
                                content="Found as suspicious by JoeSandbox.",
                                triggered_by="JoeSandbox",
                                entity_identifier=file_path,
                                insight_type=0,
                                severity=1,
                            )
                        except Exception as e:
                            siemplify.LOGGER.error(
                                f"Can not add insight. Error: {e}"
                            )

                except Exception as e:
                    siemplify.LOGGER.error(
                        "Can get report of "
                        f"file {file_path}. Skipping. Error: {str(e)}"
                    )
                    siemplify.LOGGER.exception(e)

            if detected_files:
                output_massage = (
                    f"{len(detected_files)} files were detected as "
                    "suspicious by Joe Sandbox."
                )

            else:
                output_massage = (f"Completed analysis of {len(web_ids)} "
                                  "files. No files were detected as "
                                  "suspicious by Joe Sandbox.")

            # add json
            siemplify.result.add_result_json(json_results)
            siemplify.end(
                output_massage,
                "true",
                EXECUTION_STATE_COMPLETED
            )

        else:
            siemplify.LOGGER.info("Files are still queued for analysis.")
            output_massage = (
                "Continuing...the requested items are still queued for analysis"
            )
            siemplify.end(
                output_massage, json.dumps(web_ids), EXECUTION_STATE_INPROGRESS
            )

    except Exception as e:
        siemplify.LOGGER.exception(e)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        fetch_scan_report_async()
