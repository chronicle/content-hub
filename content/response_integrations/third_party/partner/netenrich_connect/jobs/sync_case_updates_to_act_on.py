"""******************************************************************************
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
import time
import traceback

import requests
from requests.adapters import HTTPAdapter
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler, utc_now
from urllib3.util.retry import Retry

INTG_NAME = "Resolution Intelligence Cloud"
SCRIPT_NAME = "Sync Case Updates To ActOn"
JOB_SCHEDULE_INTERVAL_IN_MIN = 1
RIC_COMMENT_PREFIX = "FROM:RICOPSASSIST\n---------------------\n"

ASSIGNEE_ACTIVITY_TYPE = 8
MANUAL_CASE_CREATION_TYPE = 7
RI_CUSTOM_ENTITY = "RI_CUSTOM_ENTITY_FOR_CASE_{case_id}"
AUTOMATED_CREATOR_IDS = ["System", "Siemplify automation", None]
DEFAULT_RI_STATUS = "New"
RI_CLOSED_STATUS = "Closed"
TICKET_POLICY_MODIFICATION_TYPE = "manual"

# Endpoints
WALL_ACTIVITY_ENDPOINT = "/external/v1/dynamic-cases/GetWallActivitiesV2/{case_id}"
SEARCH_SOC_ROLES_ENDPOINT = "/external/v1/socroles/getSocRoles"
SEARCH_STAGE_ENDPOINT = "/external/v1/settings/getCaseStageDefinitionRecords"


def get_attachment_data_base64(attachment_id, siemplify):
    try:
        attachment_data_utf = siemplify.get_attachment(attachment_id).getvalue()
        base64_encoded = base64.b64encode(attachment_data_utf).decode("utf-8")
        return base64_encoded
    except Exception as e:
        siemplify.LOGGER.error(f"Unable to process attachment with exception : {e!s}")
        return None


def prepare_posts_for_the_activities(activities: list[dict], siemplify) -> list[dict]:
    posts = []
    for activity in activities or []:
        if activity.get("evidenceName") and not activity.get(
            "commentForClient"
        ).startswith(RIC_COMMENT_PREFIX):
            posts.append(
                {
                    "postContent": activity.get("commentForClient")
                    .replace("<", "")
                    .replace(">", "")
                    or "Attachment Added",
                    "attachments": [
                        {
                            "fileName": activity.get("evidenceName")
                            + activity.get("fileType"),
                            "base64encodedStr": get_attachment_data_base64(
                                activity.get("evidenceId"), siemplify
                            )
                            or "",
                            "sizeBytes": 0,
                            "contentType": activity.get("fileType").replace(".", ""),
                        }
                    ],
                },
            )
        elif activity.get("commentForClient") and not activity.get(
            "commentForClient"
        ).startswith(RIC_COMMENT_PREFIX):
            posts.append(
                {
                    "postContent": activity.get("commentForClient")
                    .replace("<", "")
                    .replace(">", ""),
                },
            )
        elif activity.get("description"):
            posts.append(
                {
                    "postType": "Alert-Notes",
                    "postTypeId": 155,
                    "postContent": activity.get("description")
                    .replace("<", "")
                    .replace(">", ""),
                },
            )
    posts.reverse()
    return posts


def transform_tags(tags, case_id, siemplify):
    try:
        tags_final = {"updated": []}
        if tags:
            tags = tags.split(",")
            for tag in tags:
                if tag:  # Ensures that empty strings are not processed
                    tag_dict = {
                        "key": tag,
                        "value": tag,
                        "type": tag,
                        "source": "SIEMPLIFY",
                    }
                    tags_final.get("updated").append(tag_dict)
    except Exception:
        siemplify.LOGGER.error(
            f"Unable to process tags for the case: {case_id}, setting it to None"
        )
        tags_final = None
    siemplify.LOGGER.info(f"Tags from source: {tags_final}")
    return tags_final


def get_ri_custom_entity(entities: list[dict], case_id: str) -> dict | None:
    for entity in entities or []:
        if entity["identifier"] == RI_CUSTOM_ENTITY.format(case_id=case_id):
            return entity


def prepare_ri_payload(case_info: dict, siemplify) -> dict:
    action = "UPDATED"
    if not case_info.get("ticket_id"):
        action = "CREATED"

    return {
        "posts": case_info.get("posts"),
        "status": case_info.get("status"),
        "title": case_info.get("title"),
        "description": case_info.get("description"),
        "team": case_info.get("team"),
        "priority": case_info.get("priority"),
        "ticketId": case_info.get("ticket_id"),
        "caseId": case_info.get("identifier"),
        "ticketPolicy": case_info.get("ticketPolicy"),
        "environment": case_info.get("environment"),
        "action": action,
        "stageId": case_info.get("stageId"),
        "tags": transform_tags(
            case_info.get("additional_properties").get("Tags"),
            case_info.get("identifier"),
            siemplify,
        ),
    }


def post_to_inbound_ingest_webhook(case_info: dict, siemplify):
    ri_webhook = siemplify.extract_configuration_param(
        provider_name=INTG_NAME,
        param_name="RI Inbound Webhook URL",
    )
    token = siemplify.extract_configuration_param(
        provider_name=INTG_NAME,
        param_name="Token",
    )
    ri_webhook = ri_webhook.format(token=token)
    headers = {"content-type": "application/json"}
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[504, 502, 503, 500])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    case_id = case_info.get("identifier")
    try:
        data_ingest_payload = prepare_ri_payload(
            case_info=case_info, siemplify=siemplify
        )
        siemplify.LOGGER.info(
            f"Case info before sending to data ingest: {data_ingest_payload}",
        )

        resp = session.post(
            ri_webhook,
            data=json.dumps(data_ingest_payload),
            headers=headers,
        )
        siemplify.LOGGER.info(
            f"Status code from data ingest API: {resp.status_code}",
        )
        resp.raise_for_status()
        siemplify.LOGGER.info(
            f"posted to RI for the case id : {case_id} with posts :"
            f" {case_info.get('posts')}",
        )
    except requests.exceptions.RequestException as e:
        siemplify.LOGGER.error(
            f"Failed to post case  info for case id : {case_id} with Error: {e!s}",
        )


def filter_wall_activity_info(
    case_id: str,
    current_utc: int,
    last_sync_utc: int,
    siemplify,
) -> list[dict]:
    try:
        wall_api_end_point = WALL_ACTIVITY_ENDPOINT.format(case_id=case_id)
        response = siemplify.session.get(siemplify.API_ROOT + wall_api_end_point)
        response.raise_for_status()
        activities_info = response.json()
        siemplify.LOGGER.info(
            f"Successfully fetched activity info for the case id : {case_id} from:"
            f" {last_sync_utc} to: {current_utc}",
        )
        activities_info = sorted(
            activities_info,
            key=lambda x: x["creationTimeUnixTimeInMs"],
            reverse=True,
        )

        filtered_activities = []
        for activity_info in activities_info or []:
            is_updated_during_interval = (
                current_utc
                >= activity_info["creationTimeUnixTimeInMs"]
                >= last_sync_utc
            )
            if (activity_info.get("activityKind") == 9) or (
                (activity_info.get("creatorUserId") not in AUTOMATED_CREATOR_IDS)
                and is_updated_during_interval
            ):
                filtered_activities.append(activity_info)
        return filtered_activities
    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to call activity api for the case : {case_id} with Error: {e}",
        )


def search_soc_role(soc_role_name: str, siemplify) -> dict | None:
    try:
        url = siemplify.API_ROOT + SEARCH_SOC_ROLES_ENDPOINT
        request_body = {"searchTerm": soc_role_name}
        siemplify.LOGGER.info(f"URL: {url}")
        response = siemplify.session.post(url, data=json.dumps(request_body))
        siemplify.LOGGER.info(
            f"Response code from soc role search API is: {response.status_code}",
        )
        response.raise_for_status()
        siemplify.LOGGER.info(
            f"Successfully fetched soc role for name : {soc_role_name}",
        )
        roles_info = response.json()
        if roles_info.get("objectsList"):
            return roles_info["objectsList"][0]
    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to search soc role information for the name: {soc_role_name},"
            f" the error is: {e}",
        )


def validate_and_update_assignee_in_case_data(
    filtered_activities: list[dict],
    case_data: dict,
    siemplify,
) -> dict:
    is_assignee_update = False
    for activity in filtered_activities or []:
        if activity.get("activityKind") == ASSIGNEE_ACTIVITY_TYPE or (
            activity.get("type") == MANUAL_CASE_CREATION_TYPE
        ):
            is_assignee_update = True
            break

    soc_role = search_soc_role(
        soc_role_name=case_data.get("assigned_user").replace("@", ""),
        siemplify=siemplify,
    )

    if is_assignee_update and soc_role:
        case_data["team"] = {
            "id": str(soc_role.get("id")),
            "assigned": True,
        }
    else:
        case_data["team"] = None

    return case_data


def update_case_data(
    filtered_activities: list[dict],
    case_id: str,
    case_data: dict,
    siemplify,
) -> dict:
    comments = prepare_posts_for_the_activities(
        activities=filtered_activities, siemplify=siemplify
    )
    case_data = validate_and_update_assignee_in_case_data(
        filtered_activities=filtered_activities,
        case_data=case_data,
        siemplify=siemplify,
    )
    case_data["posts"] = comments
    domain_entities = case_data.get("cyber_alerts")[0].get("domain_entities")
    status = None
    ri_custom_entity = get_ri_custom_entity(entities=domain_entities, case_id=case_id)
    if ri_custom_entity:
        ri_entity_additional_props = ri_custom_entity["additional_properties"]
        case_data["ticket_id"] = ri_entity_additional_props.get("riActonId")
        status = (
            ri_entity_additional_props.get("status")
            if ri_entity_additional_props.get("status")
            else DEFAULT_RI_STATUS
        )
    if not status:
        status = DEFAULT_RI_STATUS

    if case_data["status"] == 2:
        case_data["status"] = {"subStatusName": RI_CLOSED_STATUS}
    else:
        case_data["status"] = {"subStatusName": status}

    case_stage_id = get_case_stage_id(
        stage_name=case_data.get("stage"), siemplify=siemplify
    )
    if case_stage_id:
        case_data["stageId"] = str(case_stage_id)

    is_manual_case = (
        "Tags" in case_data.get("additional_properties", {})
        and "Manual Case" in case_data["additional_properties"]["Tags"]
    )
    if is_manual_case or not ri_custom_entity:
        current_time_stamp = int(time.time() * 1000)
        case_data["ticketPolicy"] = {
            "partner": {
                "modificationTime": current_time_stamp,
                "modificationType": TICKET_POLICY_MODIFICATION_TYPE,
                "isTicket": True,
            },
            "service_provider": {
                "modificationTime": current_time_stamp,
                "modificationType": TICKET_POLICY_MODIFICATION_TYPE,
                "isTicket": True,
            },
            "customer": {
                "modificationTime": current_time_stamp,
                "modificationType": TICKET_POLICY_MODIFICATION_TYPE,
                "isTicket": True,
            },
        }
    return case_data


def get_updated_cases(last_sync_utc, current_utc, siemplify) -> list[dict]:
    siemplify.LOGGER.info(
        f"Synchronize update incident from SOAR to RIC from: {last_sync_utc} to"
        f" {current_utc}"
    )

    siemplify.LOGGER.info(
        f"Fetching case id's that are updated {JOB_SCHEDULE_INTERVAL_IN_MIN} minutes"
        f" ago"
    )
    case_ids = siemplify.get_cases_ids_by_filter(
        update_time_from_unix_time_in_ms=last_sync_utc,
        status="BOTH",
        max_results=10000,
    )
    siemplify.LOGGER.info(f"Found {case_ids} case ids to update")
    environment = siemplify.extract_configuration_param(
        provider_name=INTG_NAME,
        param_name="Environment",
    )

    updated_cases = []
    for case_id in case_ids or []:
        try:
            case_data = siemplify._get_case_by_id(case_id)
            if case_data.get("environment") != environment:
                siemplify.LOGGER.info(
                    f"Skipping the case: {case_id} as it is not in: {environment}",
                )
                continue
            filtered_activities = filter_wall_activity_info(
                case_id=case_id,
                current_utc=current_utc,
                last_sync_utc=last_sync_utc,
                siemplify=siemplify,
            )
            if filtered_activities:
                case_data = update_case_data(
                    filtered_activities=filtered_activities,
                    case_id=case_id,
                    case_data=case_data,
                    siemplify=siemplify,
                )
                if case_data["posts"]:
                    updated_cases.append(case_data)
        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to fetch case with case id {case_id}, the error is: {e}",
            )
    siemplify.LOGGER.info(f"Found {len(updated_cases)} updated cases")
    return updated_cases


def get_case_stage_id(stage_name: str, siemplify) -> str:
    try:
        url = siemplify.API_ROOT + SEARCH_STAGE_ENDPOINT
        request_body = {"searchTerm": stage_name}
        response = siemplify.session.post(url, data=json.dumps(request_body))
        siemplify.LOGGER.info(
            f"Response code from stage API is: {response.status_code}",
        )
        response.raise_for_status()
        siemplify.LOGGER.info(
            "Successfully fetched case stages",
        )
        stages_info = response.json()
        for stage in stages_info.get("objectsList") or []:
            if stage_name == stage.get("name"):
                return stage.get("id")

    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to search stage, the error is: {e}",
        )


@output_handler
def main():
    siemplify = SiemplifyJob()
    last_sync_utc = siemplify.get_scoped_job_context_property("last_sync_time")
    current_utc = int(utc_now().timestamp() * 1000)
    last_sync_utc = int(last_sync_utc) if last_sync_utc else current_utc
    siemplify.LOGGER.info(f"Last synced: {last_sync_utc}")
    siemplify.set_scoped_job_context_property("last_sync_time", current_utc)
    updated_cases = get_updated_cases(
        last_sync_utc=last_sync_utc, current_utc=current_utc, siemplify=siemplify
    )
    for updated_case in updated_cases or []:
        post_to_inbound_ingest_webhook(case_info=updated_case, siemplify=siemplify)

    siemplify.end_script()


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print(f"Exception occurred while processing the request: {ex}")
        traceback.print_exc()
