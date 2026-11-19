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

import base64
import time
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import InsightSeverity, InsightType
from soar_sdk.SiemplifyUtils import dict_to_flat, flat_dict_to_csv, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.WildfireManager import WildfireManager, WildfireManagerError

INTEGRATION_NAME = "Wildfire"
INTEGRATION_DISPLAY_NAME = "Palo Alto Wildfire"
ACTION_NAME = "Detonate File"


def _poll_reports(
    wildfire_manager: WildfireManager,
    file_infos: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    all_complete = False
    reports: dict[str, dict[str, Any]] = {}

    while not all_complete:
        all_complete = True

        for file_path, file_info in list(file_infos.items()):
            if not file_info["running"]:
                continue

            all_complete = False
            time.sleep(5)
            try:
                report = wildfire_manager.get_report(file_info["file_info"]["md5"])
            except WildfireManagerError:
                continue

            if report and report.get("task_info"):
                file_info["running"] = False
                reports[file_path] = {
                    "file_info": report.get("file_info"),
                    "task_info": report.get("task_info"),
                }

    return reports


def _attach_reports(
    siemplify: SiemplifyAction,
    wildfire_manager: WildfireManager,
    reports: dict[str, dict[str, Any]],
) -> None:
    for file_path, report in list(reports.items()):
        if report["file_info"]["malware"] == "yes":
            insight_msg = f"File {file_path} was found malicious by WildFire"
            siemplify.create_case_insight_internal(
                siemplify.case_id,
                None,
                "Entity insight",
                insight_msg,
                report["file_info"]["md5"],
                InsightSeverity.WARN,
                InsightType.General,
            )

        flat_reports = dict_to_flat(report["task_info"])
        csv_output = flat_dict_to_csv(flat_reports)
        siemplify.result.add_entity_table(file_path, csv_output)

        pdf_reports = wildfire_manager.get_pdf_report(report["file_info"]["md5"])
        siemplify.result.add_attachment(
            f"Wildfire report {file_path}",
            pdf_reports["filename"],
            base64.b64encode(pdf_reports["content"]).decode("utf-8"),
        )


def _parse_file_paths(file_paths_raw: Any) -> list[str]:
    file_paths = [path.strip() for path in str(file_paths_raw).split(",") if path.strip()]
    if not file_paths:
        msg = "At least one file path must be provided."
        raise ValueError(msg)
    return file_paths


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ACTION_NAME}"

    try:
        file_paths_raw = extract_action_param(
            siemplify,
            param_name="File Paths",
            is_mandatory=True,
            print_value=True,
        )
        file_paths = _parse_file_paths(file_paths_raw)

        wildfire_manager = WildfireManager.from_siemplify(siemplify)
        file_infos: dict[str, dict[str, Any]] = {
            file_path: {
                "file_info": wildfire_manager.submit_file(file_path),
                "running": True,
            }
            for file_path in file_paths
        }
        reports = _poll_reports(wildfire_manager, file_infos)
        _attach_reports(siemplify, wildfire_manager, reports)

        output_message = (
            f"Successfully uploaded files and downloaded reports using "
            f"{INTEGRATION_DISPLAY_NAME}: {', '.join(file_paths)}."
        )
        siemplify.end(output_message, True, EXECUTION_STATE_COMPLETED)

    except Exception as e:
        siemplify.LOGGER.exception("Failed to execute Detonate File action")
        siemplify.end(f'Error executing action "{ACTION_NAME}". Reason: {e}', False, EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
