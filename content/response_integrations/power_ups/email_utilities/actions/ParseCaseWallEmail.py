# Copyright 2025 Google LLC
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
import datetime
import json
import os

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.AttachmentsManager import AttachmentsManager
from ..core.EmailManager import EmailManager

SUPPORTED_ATTACHMENTS = [".eml", ".msg"]
ORIG_EMAIL_DESCRIPTION = [
    "This is the original message as EML",
    "Original email attachment",
]
CASE_EVIDENCE_ID = "evidenceId"

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime.datetime):
        serial = obj.isoformat()
        return serial
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode()
    raise TypeError("Type not serializable")


@output_handler
def main():
    siemplify = SiemplifyAction()

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = True

    siemplify.script_name = "Parse Email"
    siemplify.LOGGER.info(f"Starting {siemplify.script_name}.")

    save_to_case_wall = (
        siemplify.parameters["Save Attachments to Case Wall"].lower() == "true"
    )
    create_base_entities = siemplify.parameters["Create Entities"].lower() == "true"
    create_observed_entity_types = siemplify.parameters.get(
        "Create Observed Entities",
        "All",
    )
    original_eml_only = siemplify.parameters["Original EML Only"].lower() == "true"

    exclude_regex = siemplify.parameters.get("Exclude Entities Regex", None)
    fang_entities = siemplify.parameters["Fang Entities"].lower() == "true"
    custom_regex = siemplify.parameters.get("Custom Entity Regexes", "{}")

    try:
        custom_regex = json.loads(custom_regex)
    except Exception as e:
        siemplify.LOGGER.error(e)
        output_message += "\nFailed to load custom regex mappings."
        custom_regex = {}

    parsed_emails = []

    email_mgr = EmailManager(
        siemplify=siemplify,
        logger=siemplify.LOGGER,
        custom_regex=custom_regex,
    )
    attach_mgr = AttachmentsManager(siemplify=siemplify)
    attachments = attach_mgr.get_alert_attachments()

    orig_email_attachment = {}
    attached_email = {}

    for eml_attachment in attachments:
        if (
            eml_attachment["description"] in ORIG_EMAIL_DESCRIPTION
            and eml_attachment["fileType"] in SUPPORTED_ATTACHMENTS
        ):
            orig_email_attachment = eml_attachment
            if orig_email_attachment["fileType"] == ".eml" and original_eml_only:
                break
        elif (
            eml_attachment["fileType"] in SUPPORTED_ATTACHMENTS
            and eml_attachment["description"] not in ORIG_EMAIL_DESCRIPTION
        ):
            attached_email = eml_attachment

    if attached_email and not original_eml_only:
        attachment = attached_email
    else:
        attachment = orig_email_attachment

    if not attachment:
        attachments = attach_mgr.get_attachments()
        orig_email_attachment = {}
        attached_email = {}

        for eml_attachment in attachments:
            if (
                eml_attachment["description"] in ORIG_EMAIL_DESCRIPTION
                and eml_attachment["fileType"] in SUPPORTED_ATTACHMENTS
            ):
                orig_email_attachment = eml_attachment
                if orig_email_attachment["fileType"] == ".eml" and original_eml_only:
                    break
            elif (
                eml_attachment["fileType"] in SUPPORTED_ATTACHMENTS
                and eml_attachment["description"] not in ORIG_EMAIL_DESCRIPTION
            ):
                attached_email = eml_attachment

        if attached_email:
            attachment = attached_email
        else:
            attachment = orig_email_attachment

    if not attachment or CASE_EVIDENCE_ID not in attachment:
        output_message += "No EML attachments found on the case."
        siemplify.LOGGER.info(
            f"\n  status: {status}\n result_value: False\n output_message: {output_message}"
        )
        siemplify.end(output_message, False, status)

    attachment_record = siemplify.get_attachment(attachment[CASE_EVIDENCE_ID])
    attachment_name = f"{attachment['evidenceName']}{attachment['fileType']}"
    attachment_content = attachment_record.getvalue()
    siemplify.LOGGER.info(f"Extracting from Case Wall Attachment: {attachment_name}")
    parsed_email = email_mgr.parse_email(attachment_name, attachment_content)
    parsed_email["attachment_name"] = (
        f"{attachment['evidenceName']}{attachment['fileType']}"
    )
    parsed_email["attachment_id"] = attachment[CASE_EVIDENCE_ID]
    parsed_emails.append(parsed_email)

    if create_observed_entity_types != "None" or create_base_entities:
        sorted_emails = sorted(
            parsed_email["attached_emails"],
            key=lambda d: d["level"],
            reverse=True,
        )
        for r_email in sorted_emails:
            email_mgr.create_entities(
                create_base_entities,
                create_observed_entity_types,
                exclude_regex,
                r_email,
                fang_entities,
            )

    if save_to_case_wall:
        updated_entities = []
        for attachment in parsed_email["attachments"]:
            if attachment["raw"] != "":
                try:
                    attachment_res = attach_mgr.add_attachment(
                        attachment["filename"],
                        attachment["raw"],
                        siemplify.case_id,
                        siemplify.alert_id,
                    )
                    del attachment["raw"]
                    name, attachment_type = os.path.splitext(
                        attachment["filename"].strip().upper(),
                    )
                    for entity in email_mgr.get_alert_entities():
                        if (
                            attachment["filename"].strip().upper()
                            == entity.identifier.strip().upper()
                            or name == entity.identifier.strip().upper()
                        ) and entity.entity_type == "FILENAME":
                            entity.additional_properties["attachment_id"] = (
                                attachment_res
                            )
                            updated_entities.append(entity)
                            break
                except Exception as e:
                    if "raw" in attachment:
                        del attachment["raw"]
                    siemplify.LOGGER.error(e)
                    output_message += f"Unable to add file {attachment['filename']}.  "
                    raise

        if updated_entities:
            siemplify.LOGGER.info(
                f"updating file entity attachment_id: {updated_entities}",
            )
            siemplify.update_entities(updated_entities)
    siemplify.result.add_json(attachment_name, parsed_email, "Email File")

    siemplify.result.add_result_json(
        json.dumps(
            {"parsed_emails": parsed_emails},
            sort_keys=True,
            default=json_serial,
        ),
    )

    output_message += "Parsed message file."
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
