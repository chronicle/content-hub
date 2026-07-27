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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from ..core.FalconSandboxManager import FalconSandboxManager
import sys
import base64
import json

SCRIPT_NAME = "Falcon Sandbox - AnalyzeFileUrl"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    configurations = siemplify.get_configuration("FalconSandbox")
    server_address = configurations["Api Root"]
    key = configurations["Api Key"]

    file_url = siemplify.parameters["File Url"]
    env_id = siemplify.parameters["Environment"]

    falcon_manager = FalconSandboxManager(server_address, key)
    siemplify.LOGGER.info("Connected to Falcon Sandbox")

    job_id, sha256 = falcon_manager.submit_file_by_url(file_url, env_id)
    max_threat_score = 0

    siemplify.LOGGER.info(f"Started job {job_id} - {sha256}")

    if falcon_manager.is_job_completed(job_id):
        siemplify.LOGGER.info(f"Job {job_id} is completed.")

        reports = falcon_manager.get_scan_info(sha256, env_id)

        for index, report in enumerate(reports, 1):
            threat_score = report["threat_score"]
            max_threat_score = max(threat_score, max_threat_score)

            siemplify.LOGGER.info(f"Threat Score: {threat_score}")

            siemplify.LOGGER.info("Attaching JSON report")
            siemplify.result.add_json(
                f"Falcon Sandbox Report {index} - {file_url} - Environment {env_id}",
                json.dumps(report),
            )

        mist_report_name, misp_report = falcon_manager.get_report(job_id, type="misp")

        # Not working in server - throws 500
        # misp_json_report = falcon_manager.get_report(job_id, type='misp_json')

        siemplify.result.add_attachment(
            "Falcon Sandbox Misp Report",
            mist_report_name,
            base64.b64encode(misp_report.encode("utf-8")),
        )

        # siemplify.result.add_attachment(
        #     "Falcon Sandbox Misp JSON Report",
        #     "misp_json_report.json",
        #     base64.b64encode(misp_json_report)
        # )

        siemplify.result.add_result_json(json.dumps(reports))
        siemplify.end(
            f"Analysis completed - {job_id}.\nMax Threat Score: {max_threat_score}",
            json.dumps(max_threat_score),
            EXECUTION_STATE_COMPLETED,
        )

    else:
        siemplify.end(
            f"Job {job_id} in progress.",
            json.dumps((job_id, sha256)),
            EXECUTION_STATE_INPROGRESS,
        )


def async_analysis():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("Start async")

    env_id = siemplify.parameters["Environment"]

    try:
        configurations = siemplify.get_configuration("FalconSandbox")
        server_address = configurations["Api Root"]
        key = configurations["Api Key"]

        file_url = siemplify.parameters["File Url"]

        job_id, sha256 = json.loads(siemplify.parameters["additional_data"])
        max_threat_score = 0

        falcon_manager = FalconSandboxManager(server_address, key)
        siemplify.LOGGER.info("Connected to Falcon Sandbox")

        if falcon_manager.is_job_completed(job_id):
            siemplify.LOGGER.info(f"Job {job_id} is completed.")

            reports = falcon_manager.get_scan_info(sha256, env_id)

            for index, report in enumerate(reports, 1):
                threat_score = report["threat_score"]
                max_threat_score = max(threat_score, max_threat_score)

                siemplify.LOGGER.info(f"Threat Score: {threat_score}")

                siemplify.LOGGER.info("Attaching JSON report")
                siemplify.result.add_json(
                    f"Falcon Sandbox Report {index} - {file_url} - Environment {env_id}",
                    json.dumps(report),
                )

            mist_report_name, misp_report = falcon_manager.get_report(
                job_id, type="misp"
            )

            # misp_json_report = falcon_manager.get_report(job_id,
            #                                              type='misp_json')

            siemplify.result.add_attachment(
                "Falcon Sandbox Misp Report",
                mist_report_name,
                base64.b64encode(misp_report.encode("utf-8")),
            )
            # siemplify.result.add_attachment(
            #     "Falcon Sandbox Misp JSON Report",
            #     "misp_json_report.json",
            #     base64.b64encode(misp_json_report)
            # )

            siemplify.result.add_result_json(json.dumps(reports))
            siemplify.end(
                f"Analysis completed - {job_id}.\nMax Threat Score: {max_threat_score}",
                json.dumps(max_threat_score),
                EXECUTION_STATE_COMPLETED,
            )

        else:
            siemplify.LOGGER.info(f"Job {job_id} in progress.")
            siemplify.end(
                f"Job {job_id} in progress.",
                json.dumps((job_id, sha256)),
                EXECUTION_STATE_INPROGRESS,
            )

    except Exception as e:
        # Log the exception to file and raise it to client
        siemplify.LOGGER._log.exception(e)
        raise


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        async_analysis()
