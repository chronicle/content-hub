"""
******************************************************************************
* Copyright (c) [2021 -2025] Netenrich, Inc. All rights reserved.
* This script is the intellectual property of Netenrich, Inc.
You are not allowed to modify or distribute this script without explicit
written consent from Netenrich, Inc.
* DISCLAIMER: This script is provided "as is" without warranty of any kind,
express or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose, and non-infringement.
In no event shall Netenrich, Inc. be liable for any claim, damages, or other
liability, whether in an action of contract, tort, or otherwise, arising
from, out of, or in connection with the script or the use or other dealings
in the script.
*****************************************************************************/
"""

from __future__ import annotations

import base64
import json
import os
import time
import traceback

import requests
from requests.adapters import HTTPAdapter
from soar_sdk.SiemplifyJob import SiemplifyJob
from urllib3.util.retry import Retry

INTEGRATION_NAME = "Resolution Intelligence Cloud"
RI_CUSTOM_ENTITY = "RI_CUSTOM_ENTITY_FOR_CASE_{case_id}"
DEFAULT_ENTITY_TYPE = "asset"
RI_SYSTEM_NOTE_ID = 155
RI_SYSTEM_NOTE_TYPE = "Alert-Notes"
RIC_COMMENT_PREFIX = "FROM:RICOPSASSIST\n---------------------\n"
SYSTEM_NOTES_MESSAGE_IDS = [155, 0]

# Endpoints
DESCRIPTION_UPDATE_ENDPOINT = "/external/v1/cases/ChangeCaseDescription"
UPDATE_ENTITY_ENDPOINT = "/external/v1/dynamic-cases/AddOrUpdateEntityProperty"
CASE_TITLE_UPDATE_ENDPOINT = "/external/v1/cases/RenameCase"
BULK_CASE_TAGS_ENDPOINT = "/external/v1/cases/ExecuteBulkAddCaseTag"
REMOVE_CASE_TAG_ENDPOINT = "/external/v1/cases/RemoveCaseTag"
SOC_ROLE_BY_ID_ENDPOINT = "/external/v1/socroles/GetSocRole/{soc_role_id}"
SEARCH_SOC_ROLES_ENDPOINT = "/external/v1/socroles/getSocRoles"
SEARCH_STAGE_ENDPOINT = "/external/v1/settings/getCaseStageDefinitionRecords"


# Data Ingest Post Content Messages
TICKET_CREATED_MSG = "Ticket Created In External System"
TICKET_UPDATED_MSG = "Ticket Updated In External System"


def save_decoded_file(siemplify, base64_content, output_folder, output_filename):
    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        siemplify.LOGGER.info(f"Folder '{output_folder}' created successfully.")
    else:
        siemplify.LOGGER.info(f"Folder '{output_folder}' already exists.")

    # Decode the base64 content
    try:
        decoded_content = base64.b64decode(base64_content)
    except base64.binascii.Error as e:
        siemplify.LOGGER.info(f"Error decoding Base64 content: {e}")
        return

    # Create the full output file path
    output_file_path = os.path.join(output_folder, output_filename)
    siemplify.LOGGER.info(f"OUTPUT FILE PATH: {output_file_path}")
    # Save the decoded content to the file
    try:
        with open(output_file_path, "wb") as file:
            file.write(decoded_content)
        siemplify.LOGGER.info(
            f"File '{output_filename}' has been successfully saved in"
            f" '{output_folder}'."
        )
    except Exception as e:
        siemplify.LOGGER.info(f"Error writing file: {e}")


def add_comment_to_case(
    siemplify,
    case_id: str,
    posts: list,
    alert_identifier: str,
    ric_prefix: str,
    allow_system_notes: str,
):
    try:
        for post in posts or []:
            if (
                allow_system_notes != "true"
                and post.get("messageTypeId")
                and post.get("messageTypeId", 0) in SYSTEM_NOTES_MESSAGE_IDS
            ):
                siemplify.LOGGER.info(
                    f"As Allow System Notes : {allow_system_notes}, not updating"
                    " comment"
                )
                continue
            siemplify.LOGGER.info(
                "Proceeding with adding comments with system notes flag :"
                f" {allow_system_notes}"
            )
            if (post.get("content") or post.get("postContent")) and post.get(
                "attachments"
            ):
                for attachment in post.get("attachments"):
                    add_attachment(
                        siemplify,
                        case_id=case_id,
                        alert_identifier=alert_identifier,
                        attachment_data=attachment,
                        description=ric_prefix + post.get("postContent")
                        if post.get("postContent")
                        else ric_prefix + post.get("content"),
                    )

            elif post.get("content") or post.get("postContent"):
                siemplify.add_comment(
                    case_id=case_id,
                    alert_identifier=alert_identifier,
                    comment=ric_prefix + post.get("content")
                    if post.get("content")
                    else ric_prefix + post.get("postContent"),
                )

        siemplify.LOGGER.info(
            "Successfully updated comments for Case ID:{}".format(case_id)
        )
    except Exception as e:
        siemplify.LOGGER.error(
            f"Unable to add comments for case: {case_id} with error : {str(e)}"
        )


def prepare_ri_payload(case_info: dict, posts: list[dict]) -> dict:
    return {
        "posts": posts,
        "status": case_info.get("status"),
        "title": case_info.get("title"),
        "description": case_info.get("description"),
        "team": case_info.get("team"),
        "priority": case_info.get("priority"),
        "ticketId": case_info.get("ticket_id"),
        "caseId": case_info.get("identifier"),
        "ticketPolicy": case_info.get("ticketPolicy"),
        "environment": case_info.get("environment"),
        "action": "CREATED",
        "stageId": case_info.get("stageId"),
    }


def post_to_inbound_ingest_webhook(siemplify, posts: list, case_info: dict):
    ri_webhook = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="RI Inbound Webhook URL"
    )
    token = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="Token"
    )
    ri_webhook = ri_webhook.format(token=token)
    headers = {"content-type": "application/json"}
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[504, 502, 503, 500])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    case_id = case_info.get("identifier")
    try:
        data_ingest_payload = prepare_ri_payload(case_info=case_info, posts=posts)
        siemplify.LOGGER.info(
            f"Case info before posting to Webhook: {data_ingest_payload}"
        )
        resp = session.post(
            ri_webhook, data=json.dumps(data_ingest_payload), headers=headers
        )
        siemplify.LOGGER.info(f"Response from Webhook: {resp}")
        resp.raise_for_status()
        siemplify.LOGGER.info(f"posted to RI for the case id : {case_id}")
    except requests.exceptions.RequestException as e:
        siemplify.LOGGER.error(
            f"Failed to post Case info for case id : {case_id} with Error: {str(e)}"
        )


def update_description(
    siemplify, case_description: str, incoming_description: str, case_id: str
):
    if incoming_description and case_description != incoming_description:
        data = {"caseId": case_id, "description": incoming_description}
        try:
            response = siemplify.session.post(
                siemplify.API_ROOT + DESCRIPTION_UPDATE_ENDPOINT, data=json.dumps(data)
            )
            siemplify.LOGGER.info(
                f"Response code from update description API is: {response.status_code}"
            )
            response.raise_for_status()
            siemplify.LOGGER.info(
                f"Successfully updated description info for the case id : {case_id}"
            )
        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to update case description for the case : {case_id}"
                f" with Error: {str(e)}"
            )


def update_title(siemplify, case_id: str, incoming_title: str, case_title: str):
    if incoming_title and (not case_title or case_title != incoming_title):
        data = {"caseId": case_id, "title": incoming_title}
        try:
            response = siemplify.session.post(
                siemplify.API_ROOT + CASE_TITLE_UPDATE_ENDPOINT, data=json.dumps(data)
            )
            siemplify.LOGGER.info(
                f"Response code from update title API is: {response.status_code}"
            )
            response.raise_for_status()
            siemplify.LOGGER.info(
                f"Successfully updated title for the case id : {case_id}"
            )
        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to update case title for the case : {case_id} with Error:"
                f" {str(e)}"
            )


def sync_priority(
    siemplify,
    case_id: str,
    incoming_priority: str,
    alert_identifier: str,
    case_priority: str,
):
    if incoming_priority and int(incoming_priority) != int(case_priority):
        siemplify.change_case_priority(
            case_id=case_id,
            priority=incoming_priority,
            alert_identifier=alert_identifier,
        )
        siemplify.LOGGER.info(
            f"Successfully updated priority for the case id : {case_id}"
        )


def delta_sync_entities(siemplify, ri_entities: list[dict], case_info: dict):
    if not case_info.get("cyber_alerts"):
        return

    cyber_alert = case_info.get("cyber_alerts")[0]
    soar_entities = cyber_alert.get("domain_entities")
    soar_entity_names = [
        entity.get("identifier") for entity in soar_entities if entity.get("identifier")
    ]

    siemplify.LOGGER.info(f"Existing SOAR entity names: {soar_entity_names}")
    ri_entities = ri_entities if ri_entities else []
    for ri_entity in ri_entities:
        formatted_ri_entity_name = ri_entity.get("name").replace(" ", "_")
        if formatted_ri_entity_name not in soar_entity_names:
            entity_type = (
                ri_entity.get("type") if ri_entity.get("type") else DEFAULT_ENTITY_TYPE
            )
            properties = {"event_link": ri_entity.get("event_link")}
            additional_properties = cyber_alert.get("additional_properties")
            alert_identifier_value = cyber_alert.get("identifier")
            try:
                siemplify.LOGGER.info(f"Entity Name : {formatted_ri_entity_name}")

                siemplify.add_entity_to_case(
                    entity_identifier=formatted_ri_entity_name,
                    entity_type=entity_type,
                    is_internal=(
                        True
                        if additional_properties.get("IsInternalAsset") == "True"
                        else False
                    ),
                    is_suspicous=(
                        True
                        if additional_properties.get("IsSuspicious") == "True"
                        else False
                    ),
                    is_enriched=(
                        True
                        if additional_properties.get("IsEnriched") == "True"
                        else False
                    ),
                    is_vulnerable=(
                        True
                        if additional_properties.get("IsVulnerable") == "True"
                        else False
                    ),
                    properties=properties,
                    environment=case_info.get("environment"),
                    case_id=case_info.get("identifier"),
                    alert_identifier=alert_identifier_value,
                )
            except Exception as e:
                siemplify.LOGGER.error(
                    "Exception occurred while adding entity to case. Discarding other"
                    f" updates. The error is: {e}"
                )
                return
    siemplify.LOGGER.info(
        "Successfully updated entities info for the case id :"
        f" {case_info.get('identifier')}"
    )


def update_entity_api(
    siemplify,
    case_id: str,
    entity_identifier: str,
    entity_type: str,
    key: str,
    value: str,
):
    request_body = {
        "caseId": case_id,
        "property": {"key": key, "value": value},
        "identifier": entity_identifier,
        "type": entity_type,
    }

    try:
        response = siemplify.session.post(
            siemplify.API_ROOT + UPDATE_ENTITY_ENDPOINT, data=json.dumps(request_body)
        )
        siemplify.LOGGER.info(
            f"Response code from update entity API is: {response.status_code}"
        )
        response.raise_for_status()
        siemplify.LOGGER.info(
            f"Updated ticket data for entity: {entity_identifier}, for key : {key}"
        )
    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to update entity key : {key} with value: {value}, the error is:"
            f" {e}"
        )


def prepare_scoring_evidence_body(ticket_data: dict) -> list[dict]:
    scoring_evidence_list = ticket_data.get("scoringEvidence", [])
    extracted_scoring_evidence_data = [
        {
            "evaluationTime": scoring_evidence.get("evaluationTime"),
            "evidenceType": scoring_evidence.get("evidenceType"),
            "firstEventTime": scoring_evidence.get("firstEventTime"),
            "message": scoring_evidence.get("message"),
            "severity": scoring_evidence.get("severity"),
            "entities": scoring_evidence.get("entities"),
            "name": scoring_evidence.get("name"),
        }
        for scoring_evidence in scoring_evidence_list
    ]
    return extracted_scoring_evidence_data


def prepare_alerts_body(ticket_data: dict) -> list[dict]:
    # Appending the first 10 alerts of the ticket based on the limit for the additional
    # attributes in SOAR Case
    alerts_list = ticket_data.get("alerts", [])[0:10]
    extracted_alert_data = [
        {
            "alertCategory": alert.get("alertCategory"),
            "alertSubCategory": alert.get("alertSubCategory"),
            "alertId": alert.get("alertId"),
            "alertSourceUrl": alert.get("alertSourceUrl"),
            "subject": alert.get("subject"),
            "alertTime": alert.get("alertTime"),
        }
        for alert in alerts_list
    ]
    return extracted_alert_data


def choose_entity_for_ri_acton_data_store(
    case_info: dict,
    case_id: str,
) -> dict:
    soar_entities = case_info.get("cyber_alerts")[0].get("domain_entities")

    for entity in soar_entities:
        if entity.get("identifier") == RI_CUSTOM_ENTITY.format(case_id=case_id):
            return entity


def extract_scores(ticket_data: dict) -> dict:
    scores = ticket_data.get("scores", [])
    extracted_scores = {}
    for score in scores:
        extracted_scores[score["type"]] = score["value"]

    return extracted_scores


def update_ticket_data(
    siemplify,
    case_info: dict,
    ticket_data: dict,
    alert_identifier: str,
    case_id: str,
    environment: str,
):
    extracted_scoring_evidence_data = prepare_scoring_evidence_body(
        ticket_data=ticket_data
    )
    extracted_alert_data = prepare_alerts_body(ticket_data=ticket_data)
    extracted_scores = extract_scores(ticket_data=ticket_data)

    ri_acton_id = ticket_data.get("ticketId")
    ticket_data["services"] = [
        service
        for service in ticket_data.get("services", []) or []
        if service.get("scope") == "customer"
    ]

    siemplify.LOGGER.info(f"Adding all necessary properties of ActOn for {case_id}")
    # Appending first 10 entities, 10 alerts based on the limit for the additional
    # attributes in SOAR Case
    body = {
        "scoringEvidence": json.dumps(extracted_scoring_evidence_data),
        "riActonId": ri_acton_id,
        "incidentCategory": json.dumps(ticket_data.get("incidentCategory", [])),
        "evidences": json.dumps(ticket_data.get("evidences", [])),
        "alertsCount": json.dumps(ticket_data.get("alertsCount", 0)),
        "services": json.dumps(ticket_data.get("services", [])),
        "entities": json.dumps(ticket_data.get("entities", [])[0:10]),
        "status": ticket_data.get("status").get("subStatusName"),
    }
    body.update(extracted_scores)
    entity_data = choose_entity_for_ri_acton_data_store(
        case_info=case_info, case_id=case_id
    )
    if not entity_data:
        siemplify.LOGGER.info("Creating custom entity to store acton data")
        # Appending alerts only on the creation of ticket data in SOAR Case
        body["alerts"] = json.dumps(extracted_alert_data)
        siemplify.add_entity_to_case(
            case_id=case_id,
            alert_identifier=alert_identifier,
            entity_identifier=RI_CUSTOM_ENTITY.format(case_id=case_id),
            entity_type=DEFAULT_ENTITY_TYPE,
            is_internal=True,
            is_suspicous=False,
            is_vulnerable=False,
            is_enriched=True,
            properties=body,
            environment=environment,
        )
        return

    for key, val in body.items():
        update_entity_api(
            siemplify,
            case_id=case_id,
            key=key,
            value=val,
            entity_type=DEFAULT_ENTITY_TYPE,
            entity_identifier=entity_data.get("identifier"),
        )


def get_or_create_case(siemplify, input_payload: dict, is_new: bool = True) -> str:
    if is_new:
        siemplify.create_case(input_payload)
        siemplify.LOGGER.info(
            f"Case created for Acton ID : {input_payload.get('ticket_id')}"
        )
        retries = 3
        while retries > 0:
            time.sleep(1)
            case_ids = siemplify.get_cases_by_filter(
                environments=[input_payload.get("environment")],
                ticked_ids_free_search=input_payload.get("ticket_id"),
            )
            if case_ids:
                return case_ids[0]
            retries -= 1
    else:
        return input_payload.get("ticket", {}).get("custTicketId")


def get_case_info(siemplify, case_id: str) -> dict:
    case_info = siemplify._get_case_by_id(case_id)
    siemplify.LOGGER.info(f"case_info for the case ID: {case_info} is: {case_info}")
    return case_info


def fetch_soc_role(siemplify, soc_role_id: str) -> dict:
    try:
        url = siemplify.API_ROOT + SOC_ROLE_BY_ID_ENDPOINT.format(
            soc_role_id=soc_role_id
        )
        response = siemplify.session.get(url)
        siemplify.LOGGER.info(
            f"Response code from soc role API is: {response.status_code}"
        )
        response.raise_for_status()
        siemplify.LOGGER.info(f"Successfully fetched soc role for id : {soc_role_id}")
        return response.json()
    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to fetch soc role information for the id: {soc_role_id}, the error"
            f" is: {e}"
        )


def search_soc_role(siemplify, soc_role_name: str) -> dict | None:
    try:
        url = siemplify.API_ROOT + SEARCH_SOC_ROLES_ENDPOINT
        request_body = {"searchTerm": soc_role_name}
        response = siemplify.session.post(url, data=json.dumps(request_body))
        siemplify.LOGGER.info(
            f"Response code from soc role search API is: {response.status_code}"
        )
        response.raise_for_status()
        siemplify.LOGGER.info(
            f"Successfully fetched soc role for name : {soc_role_name}"
        )
        roles_info = response.json()
        if roles_info.get("objectsList"):
            return roles_info["objectsList"][0]
    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to search soc role information for the name: {soc_role_name},"
            f" the error is: {e}"
        )


def get_default_soc_role(siemplify) -> dict | None:
    try:
        url = siemplify.API_ROOT + SEARCH_SOC_ROLES_ENDPOINT
        request_body = {}
        response = siemplify.session.post(url, data=json.dumps(request_body))
        siemplify.LOGGER.info(
            "Response code from soc role search API for default role is:"
            f" {response.status_code}"
        )
        response.raise_for_status()
        roles_info = response.json()
        for role in roles_info.get("objectsList", []) or []:
            if role.get("isDefault"):
                return role
    except Exception as e:
        siemplify.LOGGER.error(f"Failed to fetch defaault role the error is: {e}")


def update_assignee(
    siemplify, alert_identifier: str, case_info: dict, ticket_role_id: str, is_new: bool
) -> dict:
    ticket_assigned_role = None
    case_assigned_role = None
    updated_assignee_info = None

    if ticket_role_id:
        ticket_assigned_role = fetch_soc_role(siemplify, soc_role_id=ticket_role_id)
    if case_info and case_info.get("assigned_user"):
        case_assigned_role = search_soc_role(
            siemplify, soc_role_name=case_info.get("assigned_user").replace("@", "")
        )

    if ticket_assigned_role:
        if case_assigned_role and case_assigned_role.get(
            "id"
        ) != ticket_assigned_role.get("id"):
            updated_assignee_info = ticket_assigned_role
        elif not case_assigned_role:
            updated_assignee_info = ticket_assigned_role
    elif is_new:
        default_role = get_default_soc_role(siemplify)
        if default_role:
            updated_assignee_info = default_role

    siemplify.LOGGER.info(f"Updated assignee info :: {updated_assignee_info}")
    if updated_assignee_info:
        siemplify.assign_case(
            case_id=case_info.get("identifier"),
            user="@" + updated_assignee_info.get("name"),
            alert_identifier=alert_identifier,
        )
        siemplify.LOGGER.info(
            "Updated assignee with user: {}".format(updated_assignee_info.get("name"))
        )
        case_info["team"] = {
            "id": str(updated_assignee_info.get("id")),
            "assigned": True,
        }

    return case_info


def add_attachment(
    siemplify,
    case_id: str,
    alert_identifier: str,
    attachment_data: dict,
    description: str,
):
    try:
        save_decoded_file(
            siemplify,
            base64_content=attachment_data.get("fileContent"),
            output_filename=attachment_data.get("fileName"),
            output_folder=case_id,
        )
        if not attachment_data:
            return
        siemplify.LOGGER.info(f"Adding attachment for case : {case_id}")
        attachment_id = siemplify.add_attachment(
            case_id=case_id,
            alert_identifier=alert_identifier,
            file_path=f"{case_id}/{attachment_data.get('fileName', '')}",
            description=description,
        )
        siemplify.LOGGER.info(
            f"Added attachment {attachment_id} for case: {case_id} with size:"
            f" {attachment_data.get('fileSize')}MB"
        )
    except Exception as ex:
        siemplify.LOGGER.info(
            f"Unable to process attachment for case: {case_id} with error: {str(ex)}"
        )


def update_status(siemplify, case_id: str, alert_identifier: str, incoming_status: str):
    if incoming_status == "Closed":
        siemplify.close_case(
            reason="NotMalicious",
            root_cause="Benign",
            comment="Acton closed from RIC",
            case_id=case_id,
            alert_identifier=alert_identifier,
        )
        siemplify.LOGGER.info(f"Successfully closed the case id : {case_id}")


def filter_case_stage(siemplify, incoming_stage_id: int) -> str:
    try:
        url = siemplify.API_ROOT + SEARCH_STAGE_ENDPOINT
        # Assuming that no instance will have more than 1000 stages
        request_body = {"pageSize": 1000}
        response = siemplify.session.post(url, data=json.dumps(request_body))
        siemplify.LOGGER.info(
            f"Response code from stage API is: {response.status_code}"
        )
        response.raise_for_status()
        siemplify.LOGGER.info("Successfully fetched case stages")
        stages_info = response.json()
        siemplify.LOGGER.info(f"stages info: {stages_info}")
        siemplify.LOGGER.info(f"incoming stage info: {incoming_stage_id}")
        for stage in stages_info.get("objectsList") or []:
            if int(stage.get("id")) == int(incoming_stage_id):
                return stage.get("name")

    except Exception as e:
        siemplify.LOGGER.error(f"Failed to search stage, the error is: {e}")


def update_stage(
    siemplify,
    case_info: dict,
    alert_identifier: str,
    incoming_stage_id: int,
    existing_case_stage: str,
) -> dict:
    try:
        if not incoming_stage_id:
            return case_info

        siemplify.LOGGER.info(f"Existing case stage: {existing_case_stage}")
        stage_name = filter_case_stage(siemplify, incoming_stage_id=incoming_stage_id)
        if not stage_name or stage_name == existing_case_stage:
            return case_info

        siemplify.change_case_stage(
            case_id=case_info.get("identifier"),
            alert_identifier=alert_identifier,
            stage=stage_name,
        )
        siemplify.LOGGER.info(
            f"Successfully updated the case stage : {case_info.get('identifier')}"
        )
        case_info["stageId"] = incoming_stage_id
        return case_info
    except Exception as e:
        siemplify.LOGGER.error(f"Failed to update case stage, the error is: {e}")


def main():
    siemplify = SiemplifyJob()
    siemplify.LOGGER.info("Job started to update from RI to Siemplify")
    siemplify.LOGGER.info(siemplify.parameters)
    if siemplify.parameters.get("CREATE"):
        input_payload = json.loads(siemplify.parameters.get("CREATE"))
        if input_payload.get("posts"):
            input_payload["posts"] = None
    elif siemplify.parameters.get("UPDATE"):
        input_payload = json.loads(siemplify.parameters.get("UPDATE"))
    elif siemplify.parameters.get("COMMENT"):
        input_payload = json.loads(siemplify.parameters.get("COMMENT"))
    else:
        siemplify.LOGGER.info("Got invalid event, discarding the request")
        return

    is_new = False if input_payload.get("ticket", {}).get("custTicketId") else True
    ticket_data = input_payload.get("ticket")
    case_id = get_or_create_case(siemplify, input_payload=input_payload, is_new=is_new)
    case_info = get_case_info(siemplify, case_id=case_id)
    # As per the requirement, we are not grouping alerts in the SOAR instances of
    # customer, so taking the first alert
    alert_identifier = case_info.get("cyber_alerts")[0].get("identifier")
    if siemplify.parameters.get("COMMENT"):
        add_comment_to_case(
            siemplify,
            case_id=case_id,
            posts=input_payload.get("posts"),
            alert_identifier=alert_identifier,
            ric_prefix=RIC_COMMENT_PREFIX,
            allow_system_notes=input_payload.get("allow_system_notes"),
        )
        return

    update_description(
        siemplify,
        case_description=case_info.get("description"),
        incoming_description=input_payload.get("description"),
        case_id=case_id,
    )
    sync_priority(
        siemplify,
        case_id=case_id,
        incoming_priority=input_payload.get("priority"),
        alert_identifier=alert_identifier,
        case_priority=case_info.get("priority"),
    )
    update_title(
        siemplify,
        case_id=case_id,
        case_title=case_info.get("name"),
        incoming_title=ticket_data.get("subject"),
    )
    case_info = update_assignee(
        siemplify,
        alert_identifier=alert_identifier,
        case_info=case_info,
        ticket_role_id=input_payload.get("team"),
        is_new=is_new,
    )
    add_comment_to_case(
        siemplify,
        case_id=case_id,
        posts=input_payload.get("posts"),
        alert_identifier=alert_identifier,
        ric_prefix=RIC_COMMENT_PREFIX,
        allow_system_notes=input_payload.get("allow_system_notes"),
    )
    update_ticket_data(
        siemplify,
        case_info=case_info,
        ticket_data=ticket_data,
        case_id=case_id,
        environment=input_payload.get("environment"),
        alert_identifier=alert_identifier,
    )
    update_status(
        siemplify,
        case_id=case_id,
        alert_identifier=alert_identifier,
        incoming_status=input_payload.get("status"),
    )
    case_info = update_stage(
        siemplify,
        case_info=case_info,
        alert_identifier=alert_identifier,
        incoming_stage_id=input_payload.get("stage"),
        existing_case_stage=case_info.get("stage"),
    )
    case_info["status"] = {"subStatusName": input_payload.get("status")}
    case_info["ticket_id"] = ticket_data.get("ticketId")
    case_info["title"] = ticket_data.get("subject")

    if is_new:
        post_to_inbound_ingest_webhook(
            siemplify,
            posts=[
                {
                    "postContent": TICKET_CREATED_MSG,
                    "postType": RI_SYSTEM_NOTE_TYPE,
                    "postTypeId": RI_SYSTEM_NOTE_ID,
                }
            ],
            case_info=case_info,
        )
        post_to_inbound_ingest_webhook(
            siemplify,
            posts=[
                {
                    "postContent": TICKET_UPDATED_MSG,
                    "postType": RI_SYSTEM_NOTE_TYPE,
                    "postTypeId": RI_SYSTEM_NOTE_ID,
                }
            ],
            case_info=case_info,
        )
    delta_sync_entities(
        siemplify, ri_entities=input_payload.get("entities"), case_info=case_info
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print(f"Exception occurred while processing the request: {ex}")
        traceback.print_exc()
