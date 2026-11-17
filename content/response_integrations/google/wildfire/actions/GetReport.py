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
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import add_prefix_to_dict, dict_to_flat, flat_dict_to_csv, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.WildfireManager import WildfireManager, WildfireManagerError

INTEGRATION_NAME = "Wildfire"
ACTION_NAME = "Get Report"


def _attach_pdf_to_case(
    siemplify: SiemplifyAction,
    wildfire_manager: WildfireManager,
    identifier: str,
) -> None:
    try:
        pdf_report = wildfire_manager.get_pdf_report(identifier)
        b64_pdf = base64.b64encode(pdf_report["content"]).decode("utf-8")
        siemplify.result.add_attachment(f"WildFire report {identifier}", pdf_report["filename"], b64_pdf)
    except WildfireManagerError as pdf_err:
        siemplify.LOGGER.warn(f"Could not retrieve PDF report for {identifier}: {pdf_err}")


def _attach_pdf_to_entity(
    siemplify: SiemplifyAction,
    wildfire_manager: WildfireManager,
    identifier: str,
) -> None:
    try:
        pdf_report = wildfire_manager.get_pdf_report(identifier)
        b64_pdf = base64.b64encode(pdf_report["content"]).decode("utf-8")
        siemplify.result.add_entity_attachment(identifier, pdf_report["filename"], b64_pdf)
    except WildfireManagerError as pdf_err:
        siemplify.LOGGER.warn(f"Could not retrieve PDF report for {identifier}: {pdf_err}")


def _process_file_hash(
    siemplify: SiemplifyAction,
    wildfire_manager: WildfireManager,
    file_hash: str,
) -> tuple[str, bool, int]:
    try:
        report = wildfire_manager.get_report(file_hash)
    except Exception as e:
        siemplify.LOGGER.exception(f"Failed to download report for hash {file_hash}")
        return f"Error executing action '{ACTION_NAME}'. Reason: {e}", False, EXECUTION_STATE_FAILED

    siemplify.result.add_result_json([report])

    if report.get("task_info"):
        flat_reports = dict_to_flat(report["task_info"])
        csv_output = flat_dict_to_csv(flat_reports)
        siemplify.result.add_data_table("WildFire Task Info", csv_output)

    _attach_pdf_to_case(siemplify, wildfire_manager, file_hash)

    enriched_entities = []
    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH and entity.identifier.lower() == file_hash.lower():
            file_info = dict(report.get("file_info") or {})
            if file_info.get("malware") == "yes":
                entity.is_suspicious = True
                siemplify.add_entity_insight(entity, "File was found malicious by WildFire", triggered_by="WildFire")
            file_info = add_prefix_to_dict(file_info, "Wildfire")
            entity.additional_properties.update(file_info)
            enriched_entities.append(entity)

    if enriched_entities:
        siemplify.update_entities(enriched_entities)

    return f"Successfully downloaded report for {file_hash} from Wildfire.", True, EXECUTION_STATE_COMPLETED


def _process_entities(
    siemplify: SiemplifyAction,
    wildfire_manager: WildfireManager,
) -> tuple[str, bool, int]:
    enriched_entities = []
    errors: list[str] = []
    json_results: list[dict[str, Any]] = []

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH and len(entity.identifier) in {32, 64}:
            try:
                report = wildfire_manager.get_report(entity.identifier)
                file_info = dict(report.get("file_info") or {})

                if file_info.get("malware") == "yes":
                    entity.is_suspicious = True
                    siemplify.add_entity_insight(
                        entity,
                        "File was found malicious by WildFire",
                        triggered_by="WildFire",
                    )

                file_info = add_prefix_to_dict(file_info, "Wildfire")
                entity.additional_properties.update(file_info)

                if report.get("task_info"):
                    flat_reports = dict_to_flat(report["task_info"])
                    csv_output = flat_dict_to_csv(flat_reports)
                    siemplify.result.add_entity_table(entity.identifier, csv_output)

                _attach_pdf_to_entity(siemplify, wildfire_manager, entity.identifier)
                enriched_entities.append(entity)
                json_results.append(report)

            except Exception as e:
                siemplify.LOGGER.exception(f"Failed to get report for {entity.identifier}")
                errors.append(f"{entity.identifier}: {e}")

    if json_results:
        siemplify.result.add_result_json(json_results)

    if enriched_entities:
        siemplify.update_entities(enriched_entities)
        entities_names = [entity.identifier for entity in enriched_entities]
        msg = "Report was saved for the following entities:\n" + "\n".join(entities_names)
        if errors:
            msg += "\nErrors:\n" + "\n".join(errors)
        return msg, True, EXECUTION_STATE_COMPLETED

    msg = "No reports were downloaded."
    if errors:
        msg += "\nErrors:\n" + "\n".join(errors)
    status = EXECUTION_STATE_FAILED if errors else EXECUTION_STATE_COMPLETED
    return msg, False, status


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {ACTION_NAME}"

    file_hash = extract_action_param(
        siemplify,
        param_name="File Hash",
        is_mandatory=False,
        print_value=True,
    )

    try:
        wildfire_manager = WildfireManager.from_siemplify(siemplify)
    except Exception as e:
        siemplify.LOGGER.exception("Failed to initialize Wildfire manager")
        siemplify.end(f"Error executing action '{ACTION_NAME}'. Reason: {e}", False, EXECUTION_STATE_FAILED)
        return

    if file_hash:
        msg, is_success, status = _process_file_hash(siemplify, wildfire_manager, file_hash)
    else:
        msg, is_success, status = _process_entities(siemplify, wildfire_manager)

    siemplify.end(msg, is_success, status)


if __name__ == "__main__":
    main()
