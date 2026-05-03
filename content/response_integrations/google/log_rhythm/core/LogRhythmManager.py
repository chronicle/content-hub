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
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

import pytz
import requests

from .LogRhythmParser import LogRhythmParser
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import filter_old_alerts
from .constants import (
    CASE_PRIORITY_MAPPING,
    LOGRHYTHM_COMPLETED_STATUS,
    LOGRHYTHM_MITIGATED_STATUS,
    LOGRHYTHM_RESOLVED_STATUS,
)
from .datamodels import AlarmDrilldown
from .exceptions import (
    LogRhythmManagerBadRequestError,
    LogRhythmManagerError,
    LogRhythmManagerNotFoundError,
)

DEFAULT_PAGE_SIZE = 1000
LIMIT_PER_REQUEST = 25
UTC_TZ = "UTC"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
SUCCESS_STATUS_CODE = 200
COMPLETED_STATUS = "completed"
FILE_TYPE = "file"
NOT_FOUND_STATUS_CODE = 404
MAX_PAGE_SIZE = 1000
BAD_REQUEST_STATUS_CODE = 400
CLOSED_CASE_STATUS_CODE = 409

ENTITY_TYPE_MAPPING = {
    EntityTypes.ADDRESS: "IP",
    EntityTypes.URL: "URL",
    EntityTypes.HOSTNAME: "Hostname",
    EntityTypes.FILEHASH: "Hash",
    EntityTypes.USER: "User",
    EntityTypes.CVE: "CVE",
}


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            o = o.replace(tzinfo=pytz.timezone(UTC_TZ))
            return f"{o.isoformat().split('+')[0]}Z"

        return json.JSONEncoder.default(self, o)


class LogRhythmRESTManager:
    """
    LogRhythm Rest API Manager
    """

    ENDPOINTS = {
        "get-alarms": "/lr-alarm-api/alarms",
        "get-alarm-summary": "/lr-alarm-api/alarms/{alarm_id}/summary",
        "get-alarm-events": "/lr-alarm-api/alarms/{alarm_id}/events",
        "lists_users": "/lr-admin-api/lists/",
        "entity_details": "/lr-admin-api/hosts/",
        "alarm_details": "/lr-alarm-api/alarms/{alarm_id}",
        "alarms_to_case": "/lr-case-api/cases/{case_id}/evidence/alarms",
        "case_notes": "/lr-case-api/cases/{case_id}/evidence/note",
        "alarm_comment": "/lr-alarm-api/alarms/{alarm_id}/comment",
        "list_evidence": "/lr-case-api/cases/{case_id}/evidence",
        "update_alarm": "/lr-alarm-api/alarms/{alarm_id}",
        "download_file": "lr-case-api/cases/{case_id}/evidence/{evidence_id}/download",
        "update_case_status": "/lr-case-api/cases/{case_id}/actions/changeStatus",
        "update_case": "/lr-case-api/cases/{case_id}",
        "attach_file": "lr-case-api/cases/{case_id}/evidence/file",
        "get_evidence": "lr-case-api/cases/{case_id}/evidence/{evidence_id}",
        "case": "/lr-case-api/cases/",
        "initiate_query": "/lr-search-api/actions/search-task",
        "get_search_results": "/lr-search-api/actions/search-result",
        "get_comments": "/lr-alarm-api/alarms/{alarm_id}/history",
        "alarm_drilldown": "/lr-drilldown-cache-api/drilldown/{alarm_id}",
    }

    ALARMS_PAGE_SIZE = 100

    def __init__(
        self,
        api_root,
        api_key,
        verify_ssl=False,
        siemplify=None,
        force_check_connectivity=False,
    ):
        self.api_root = api_root
        self.session = requests.session()
        self.session.headers = {"Authorization": f"Bearer {api_key}"}
        self.session.verify = verify_ssl

        self.parser = LogRhythmParser()
        self.siemplify = siemplify

        if force_check_connectivity:
            self.test_connectivity()

    def _get_full_url(self, url_key: str, **kwargs):
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, self.ENDPOINTS[url_key].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity to LogRhythm Rest API
        :return: {bool} True if successful, exception otherwise.
        """
        response = self.session.get(self._get_full_url("lists_users"))
        self.validate_response(response, "Unable to connect to LogRhythm")
        return True

    def get_cases(
        self,
        priority=None,
        status_number=None,
        owner_number=None,
        collaborator_number=None,
        tag_number=None,
        text=None,
        evidence_type=None,
        reference_id=None,
        created_after=None,
        updated_after=None,
        limit=None,
    ):
        """
        Get list of cases
        :param priority: {int[]} Filter results that have a specific priority.
        :param status_number: {int[]} Filter results that have a specific status.
        :param owner_number: {int[]} Filter results that have a specific owner,
        by user number(s).
        :param collaborator_number: {int} Filter results that have a specific
        collaborator, by user number.
        :param tag_number: {int[]} Filter results that are tagged, by tag number(s).
        :param text: {str} Filter results that have a case number or name that
        contains the specified value.
        :param evidence_type: {str[]} Filter results that have evidence of
        the specified type.
        Valid items values: "alarm" "userEvents" "log" "note" "file"
        :param reference_id: {str} Filter results that have evidence with
        the given referenceId.
        :param created_after: {str} Filter results that were created after
        the specified date. Must be an RFC 3339 formatted string.
        :param updated_after: {str} Filter results that were updated after
        the specified date. Must be an RFC 3339 formatted string.
        :param limit: {str} Max number of cases to fetch
        (sorted, ascending by dateCreated).
        :return: {list} The found cases
        """
        params = {
            "priority": (
                ",".join(
                    [str(i) for i in CASE_PRIORITY_MAPPING.values() if priority >= i]
                )
                if priority
                else None
            ),
            "statusNumber": status_number,
            "ownerNumber": owner_number,
            "collaboratorNumber": collaborator_number,
            "tagNumber": tag_number,
            "text": text,
            "evidenceType": evidence_type,
            "referenceId": reference_id,
        }
        headers = self.session.headers
        headers.update(
            {
                "offset": "0",
                "count": str(limit) if limit else str(LIMIT_PER_REQUEST),
                "createdAfter": created_after,
                "updatedAfter": updated_after,
                "orderBy": "dateCreated",
                "direction": "asc",
            }
        )
        response = self.session.get(
            self._get_full_url("case"),
            params=self.validate_dict_values(params),
            headers=headers,
        )
        self.validate_response(response, "Unable to get results")

        return self.parser.build_results(
            response.json(), "build_siemplify_alert_obj", pure_data=True
        )

    def get_evidences(self, case_id):
        """
        Get evidences of a case
        :param case_id: {str} The case's id
        :return: {list} The found evidences.
        """
        response = self.session.get(
            self._get_full_url("list_evidence", case_id=case_id)
        )
        self.validate_response(response, f"Unable to get evidences of case {case_id}")

        return self.parser.build_results(
            response.json(), "build_siemplify_events_obj", pure_data=True
        )

    def get_user_events(self, case_id, evidence_id):
        """
        Get user events of a case
        :param case_id: {str} The case's id
        :param evidence_id: {str} The evidence's id
        :return: {list} The found user events.
        """
        url = (f"{self.api_root}/lr-case-api/cases/{case_id}/evidence/"
               f"{evidence_id}/userEvents/")
        response = self.session.get(url)

        self.validate_response(
            response,
            f"Unable to get user events of evidence {case_id} "
            f"of case {evidence_id}",
        )

        return response.json()

    def download_file_evidence(self, case_id, evidence_id):
        """
        Retrieve an uploaded item of file evidence on a case.
        :param case_id: {str} The case's id
        :param evidence_id: {str} The evidence's id
        :return: {str} The content of the file
        """
        response = self.session.get(
            self._get_full_url(
                "download_file", case_id=case_id, evidence_id=evidence_id
            )
        )
        self.validate_response(
            response,
            f"Unable to download file evidence {case_id} of case {evidence_id}",
        )

        return response.content

    def attach_file(self, case_id, file, note=None):
        """
        Attach file to provided case.
        :param case_id: {str} Case ID
        :param file: {str} File path
        :param note: {str} Additional note for file
        :return: {Evidence} Evidence data model
        """
        payload = {"note": note}

        files = [("file", (open(file, "rb")))]

        response = self.session.post(
            self._get_full_url("attach_file", case_id=case_id),
            data=payload,
            files=files,
        )
        self.validate_response(response, "Unable to submit file", handle_not_found=True)

        return self.parser.build_case_evidence_obj(response.json())

    def get_evidence(self, case_id, evidence_id):
        """
        Retrieve evidence on a case.
        :param case_id: {str} The case's id
        :param evidence_id: {str} The evidence's id
        :return: {Evidence} instance
        """
        response = self.session.get(
            self._get_full_url("get_evidence", case_id=case_id, evidence_id=evidence_id)
        )
        self.validate_response(
            response, f"Unable to get evidence {evidence_id} of case {case_id}"
        )

        return self.parser.build_case_evidence_obj(response.json())

    def get_associated_cases(self, case_id):
        """
        Retrieve the cases associated with a case.
        :param case_id: {str} Teh case's id
        :return: {list} The info of the associated cases
        """
        url = f"{self.api_root}/lr-case-api/cases/{case_id}/associated/"
        response = self.session.get(url)

        self.validate_response(
            response, f"Unable to get associated cases of case {case_id}"
        )
        return response.json()

    def get_case_metrics(self, case_id):
        """
        Retrieve metrics for a case.
        :param case_id: {str} Teh case's id
        :return: {dict} The case's metrics
        """
        url = f"{self.api_root}/lr-case-api/cases/{case_id}/metrics/"
        response = self.session.get(url)

        self.validate_response(response, f"Unable to get metrics of case {case_id}")
        return response.json()

    def remove_case_tags(self, case_id, tag_identifiers=[]):
        """
        Remove tags to case
        :param case_id: {str} The case's id
        :param tag_identifiers: {list} List of numeric tags identifiers to
        remove from case
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.api_root}/lr-case-api/cases/{case_id}/actions/removeTags/"

        response = self.session.put(url, json={"numbers": tag_identifiers})

        self.validate_response(response, f"Unable to remove tags from case {case_id}")
        return response.json()

    def change_case_owner(self, case_id, person_id):
        """
        Change the owner of a case. The new owner must already be a collaborator
        on the case.
        :param case_id: {str} The case's id
        :param person_id: {str} The new owner's id
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.api_root}/lr-case-api/cases/{case_id}/actions/changeOwner/"
        response = self.session.put(url, json={"number": person_id})

        self.validate_response(response, f"Unable to change owner of case {case_id}")
        return response.json()

    def create_tag(self, tag):
        """
        Create a new tag
        :param tag: {str} The text of the tag
        :return: {dict} The new tag's info.
        """
        url = f"{self.api_root}/lr-case-api/tags/"
        response = self.session.post(url, json={"text": tag})

        self.validate_response(response, f"Unable to create tag {tag}")
        return response.json()

    def delete_tag(self, tag_id):
        """
        Create a new tag
        :param tag_id: {str} The tag's numeric id
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.api_root}/lr-case-api/tags/{tag_id}/"
        response = self.session.delete(url)

        self.validate_response(response, f"Unable to delete tag {tag_id}")
        return True

    def change_case_status(self, case_id, status):
        """
        Change case status
        :param case_id: {str} The case's id
        :param status: {int} Numeric identifier of the  newstatus.
        Valid values are: 1, 2, 3, 4, 5.
        :return: {bool} True if successful, exception otherwise
        """
        url = f"{self.api_root}/lr-case-api/cases/{case_id}/actions/changeStatus/"
        response = self.session.put(url, json={"statusNumber": status})

        self.validate_response(response, f"Unable to update case {case_id} status")
        return True

    def get_alarms(self, inserted_after, existing_ids, limit):
        """
        Get alarms. Filter already seen alerts
        :param inserted_after: {str} Get alerts that were inserted after this date.
        Date must be provided
        in format "2021-04-02T09:09:52.98"
        :param existing_ids: {[str]} List of already fetched alert ids to filter
        :param limit: {int} Max alarms to return
        :return: {[Alarm]} List of fetched alarms
        """
        params = {
            "orderBy": "DateInserted",
            "alarmStatus": 0,
            "dir": "ascending",
            "dateInserted": inserted_after,
            "count": max(limit, self.ALARMS_PAGE_SIZE),
        }
        response = self.session.get(self._get_full_url("get-alarms"), params=params)
        self.validate_response(response, error_msg="Unable to get alarms")
        alarms = self.parser.build_results(
            response.json(), method="build_alarm_obj", data_key="alarmsSearchDetails"
        )
        filtered_alarms = filter_old_alerts(
            siemplify=self.siemplify,
            alerts=alarms,
            existing_ids=existing_ids,
            id_key="alarm_id",
        )

        return filtered_alarms[:limit]

    def get_alarm_summary(self, alarm_id):
        """
        Get alarm summary
        :param alarm_id: {int} Numeric ID of the Alarm to get
        :return: {AlarmSummaryDetails} Alarm summary details data model
        """
        response = self.session.get(
            self._get_full_url("get-alarm-summary", alarm_id=alarm_id)
        )
        self.validate_response(
            response,
            error_msg=f"Unable to get alarm summary for alarm with id {alarm_id}",
        )

        return self.parser.build_alarm_summary_obj(response.json())

    def get_alarm_events(self, alarm_id, limit=None):
        """
        Get alarm events
        :return: {[AlarmEvent]} List of alarm events data model
        """
        response = self.session.get(
            self._get_full_url("get-alarm-events", alarm_id=alarm_id)
        )
        self.validate_response(
            response,
            error_msg=f"Unable to get alarm events for alarm with id {alarm_id}",
            handle_not_found=True,
        )

        return self.parser.build_results(
            response.json(),
            "build_alarm_event_details_obj",
            data_key="alarmEventsDetails",
            limit=limit,
        )

    @classmethod
    def validate_response(
        cls,
        response: requests.Response,
        error_msg: Optional[str] = "An error occurred",
        handle_not_found: Optional[bool] = False,
    ):
        """
        Validate a response
        :param response: {requests.Response} The response to validate
        :param error_msg: {str} The message to display on error
        :param handle_not_found: {bool} Should not found error handled
        """
        try:
            response.raise_for_status()

        except requests.HTTPError as error:
            if handle_not_found and str(NOT_FOUND_STATUS_CODE) in str(error):
                raise LogRhythmManagerNotFoundError(
                    f"{cls.get_api_error_message(error)}"
                )
            if handle_not_found and str(BAD_REQUEST_STATUS_CODE) in str(error):
                raise LogRhythmManagerBadRequestError(
                    f"{cls.get_api_error_message(error)}"
                )
            if handle_not_found and str(CLOSED_CASE_STATUS_CODE) in str(error):
                raise LogRhythmManagerBadRequestError(
                    f"{cls.get_api_error_message(error)}"
                )

            raise LogRhythmManagerError(
                f"{error_msg}: {error} - {error.response.json()}"
            )

    @classmethod
    def get_api_error_message(cls, exception):
        """
        Get API error message
        :param exception: {Exception} The api error
        :return: {str} error message
        """
        try:
            if exception.response.json().get("details"):
                return exception.response.json().get("details")
            elif exception.response.json().get("responseMessage"):
                return exception.response.json().get("responseMessage")
            elif exception.response.json().get("validationErrors"):
                errors = exception.response.json().get("validationErrors")
                return ", ".join(errors) if isinstance(errors, list) else str(errors)
            elif exception.response.json().get("message"):
                return exception.response.json().get("message")
        except:
            return None

    def get_entity_details(self, entity_identifier):
        """
        Get Entity details
        :param entity_identifier: {str} Entity identifier
        :return: {EntityDetails}
        """
        params = {"hostIdentifier": entity_identifier}
        response = self.session.get(self._get_full_url("entity_details"), params=params)
        self.validate_response(
            response,
            error_msg=f"Unable to get {entity_identifier} entity details",
            handle_not_found=True,
        )

        return (
            self.parser.build_entity_details_obj(response.json()[0])
            if response.json()
            else None
        )

    def add_note_to_case(self, case_id, note):
        """
        Add note to case
        :param case_id: {str} The case's id
        :param note: {str} Note that should be added to the case.
        :return: {CaseNote}
        """
        payload = {"text": note}
        response = self.session.post(
            self._get_full_url("case_notes", case_id=case_id), json=payload
        )
        self.validate_response(
            response,
            error_msg=f"Unable to add note to case {case_id}",
            handle_not_found=True,
        )

        return self.parser.build_case_note_obj(response.json())

    def add_comment_to_alarm(self, alarm_id, comment):
        """
        Update alarm with comments
        :param alarm_id: {string} The unique ID of the alarm to update.
        :param comment: {string} The alarm comments.
        :return: {bool} True if successful, exception otherwise.
        """
        payload = {"alarmComment": comment}
        response = self.session.post(
            self._get_full_url("alarm_comment", alarm_id=alarm_id), json=payload
        )
        self.validate_response(
            response,
            error_msg=f"Unable to add comment to alarm {alarm_id}",
            handle_not_found=True,
        )

    def get_case_evidence(
        self, case_id, status_filter=None, type_filter=None, limit=None
    ):
        """
        Get case evidence
        :param case_id: {str} The case's id
        :param status_filter: {str} status to filter.
        :param type_filter: {str} type to filter.
        :param limit: {int} limit data
        :return: {list} CaseEvidence
        """
        params = {"type": type_filter, "status": status_filter}
        params = self.validate_dict_values(params)
        response = self.session.get(
            self._get_full_url("list_evidence", case_id=case_id), params=params
        )
        self.validate_response(
            response,
            error_msg=f"Unable to get case {case_id} evidence",
            handle_not_found=True,
        )

        evidence_list = self.parser.build_results(
            response.json(), method="build_case_evidence_obj", pure_data=True
        )
        return sorted(evidence_list, key=lambda item: item.date_created, reverse=True)[
            :limit
        ]

    def update_alarm(self, alarm_id, alarm_status=None, risk_score=None):
        """
        Update alarm
        :param alarm_id: {str} The ID of the alarm
        :param alarm_status: {str} The status of the alarm from possible values
        :param risk_score: {int} The risk score of the alarm between 0 and 100
        """
        payload = {"alarmStatus": alarm_status, "rBP": risk_score}
        payload = self.validate_dict_values(payload)
        response = self.session.patch(
            self._get_full_url("update_alarm", alarm_id=alarm_id), json=payload
        )

        self.validate_response(
            response,
            error_msg=f"Unable to update alarm {alarm_id}",
            handle_not_found=True,
        )

    @staticmethod
    def validate_dict_values(dictionary):
        """
        Validate dictionary
        :param dictionary: {dict} dictionary
        :return: {dict} Ditionary without None values
        """
        return {k: v for k, v in dictionary.items() if v is not None}

    def add_alarms_to_case(self, case_id, alarm_ids):
        """
        Add alarm to case
        :param case_id: {str} The case's id
        :param alarm_ids: {list} List of alarm ids
        :return: [list] list of CaseAlarm instances and status code
        """
        payload = {"alarmNumbers": alarm_ids}
        response = self.session.post(
            self._get_full_url("alarms_to_case", case_id=case_id), json=payload
        )
        self.validate_response(
            response,
            error_msg=f"Unable to add alarm to the case with ID {case_id}",
            handle_not_found=True,
        )

        return (
            self.parser.build_results(
                response.json(), "build_case_alarm_obj", pure_data=True
            ),
            response.status_code == SUCCESS_STATUS_CODE,
        )

    def get_alarm_details(self, alarm_id):
        """
        Get Alarm details
        :param alarm_id: {str} alarm id
        :return: {AlarmDetails}
        """
        response = self.session.get(
            self._get_full_url("alarm_details", alarm_id=alarm_id)
        )
        self.validate_response(
            response,
            error_msg=f"Unable to get alarm details for alarm with id {alarm_id}",
            handle_not_found=True,
        )

        return self.parser.build_alarm_details_obj(response.json())

    def execute_search(
        self, entity_identifier, entity_type, start_time, end_time, sort_order, limit
    ):
        """
        Execute search
        :param entity_identifier: {str} Entity identifier
        :param entity_type: {str} Entity type
        :param start_time: {str} date min to search
        :param end_time: {str} date max to search
        :param sort_order: {str} sort order
        :param limit: {int} limit events
        :return: {Task}
        """
        payload = {
            "maxMsgsToQuery": limit,
            "queryTimeout": 600,
            "queryRawLog": "true",
            "queryEventManager": "false",
            "includeDiagnosticEvents": "true",
            "searchMode": sort_order,
            "dateCriteria": {
                "useInsertedDate": True,
                "dateMin": start_time,
                "dateMax": end_time,
            },
            "queryLogSources": [],
            "queryFilter": {
                "msgFilterType": 2,
                "filterGroup": {
                    "filterItemType": "Group",
                    "fieldOperator": "And",
                    "filterMode": "FilterIn",
                    "filterGroupOperator": 1,
                    "filterItems": [
                        {
                            "filterItemType": "Filter",
                            "fieldOperator": "And",
                            "filterMode": "FilterIn",
                            "filterType": 0,
                            "values": [
                                {
                                    "filterType": ENTITY_TYPE_MAPPING.get(entity_type),
                                    "valueType": (
                                        5 if entity_type == EntityTypes.ADDRESS else 4
                                    ),
                                    "value": (
                                        entity_identifier
                                        if entity_type == EntityTypes.ADDRESS
                                        else {
                                            "value": entity_identifier,
                                            "matchType": "0",
                                        }
                                    ),
                                    "displayValue": "string",
                                }
                            ],
                            "name": "Siemplify",
                        }
                    ],
                    "name": "filterGroup",
                },
            },
        }

        response = self.session.post(self._get_full_url("initiate_query"), json=payload)
        self.validate_response(response)

        return self.parser.build_task_obj(response.json())

    def get_search_results(self, task_id, limit):
        """
        Get Events
        :param task_id: {str} task id
        :param limit: {int} limit events
        :return: {Task}
        """
        payload = {
            "data": {
                "searchGuid": task_id,
                "search": {"sort": [{}], "groupBy": None, "fields": []},
                "paginator": {"origin": 0, "page_size": limit},
            }
        }
        response = self.session.post(
            self._get_full_url("get_search_results"), json=payload
        )

        self.validate_response(response)

        return self.parser.build_task_obj(response.json())

    def create_case(self, name, priority, due_date=None, description=None):
        """
        Create a new case
        :param name: {str} The name of the case
        :param priority: {int} The priority of the case from possible values
        :param due_date: {str} The due_date of the case
        :param description: {str} The description of the case
        :return: {Case} Case data model
        """
        payload = {
            "name": name,
            "priority": priority,
            "dueDate": due_date,
            "summary": description,
        }

        response = self.session.post(
            self._get_full_url("case"), json=self.validate_dict_values(payload)
        )
        self.validate_response(
            response,
            error_msg=f"Unable to create case with name {name}",
            handle_not_found=True,
        )

        return self.parser.build_case_obj(response.json())

    def update_case_status(self, case_id, case_status=None):
        """
        Update case status
        :param case_id: {str} The ID of the case to update
        :param case_status: {int} The new status of the case from possible values
        """
        payload = {"statusNumber": case_status}
        response = self.session.put(
            self._get_full_url("update_case_status", case_id=case_id), json=payload
        )
        self.validate_response(
            response,
            error_msg=f"Unable to update status of the case with ID {case_id}",
            handle_not_found=True,
        )

        return self.parser.build_case_obj(response.json())

    def close_case(self, case_id):
        """
        Update case status as Completed or Resolved
        :param case_id: {str} The ID of the case to close
        """
        try:
            payload = {"statusNumber": LOGRHYTHM_COMPLETED_STATUS}
            response = self.session.put(
                self._get_full_url("update_case_status", case_id=case_id), json=payload
            )
            self.validate_response(
                response,
                error_msg=f"Unable to update status of the case with ID {case_id}",
                handle_not_found=True,
            )
        except Exception as e:
            # We need to close case with 2 steps, first set case as mitigated
            # only then set it as resolved
            payload = {"statusNumber": LOGRHYTHM_MITIGATED_STATUS}
            response = self.session.put(
                self._get_full_url("update_case_status", case_id=case_id), json=payload
            )
            self.validate_response(
                response,
                error_msg=f"Unable to update status of the case with ID {case_id}",
                handle_not_found=True,
            )
            payload = {"statusNumber": LOGRHYTHM_RESOLVED_STATUS}
            response = self.session.put(
                self._get_full_url("update_case_status", case_id=case_id), json=payload
            )
            self.validate_response(
                response,
                error_msg=f"Unable to update status of the case with ID {case_id}",
                handle_not_found=True,
            )

        return self.parser.build_case_obj(response.json())

    def get_case_status(self, case_id):
        """
        Gate case status
        :param case_id: {str} The ID of the case to get status
        :return: {Case} Update Case data model
        """
        response = self.session.get(self._get_full_url("update_case", case_id=case_id))
        self.validate_response(
            response, error_msg=f"Unable to update case with ID {case_id}"
        )

        return self.parser.build_case_obj(response.json())

    def update_case(
        self,
        case_id,
        name=None,
        due_date=None,
        description=None,
        resolution=None,
        priority=None,
    ):
        """
        Update case
        :param case_id: {str} The ID of the case to update
        :param name: {str} The name of the case
        :param priority: {int} The priority of the case from possible values
        :param due_date: {str} The due_date of the case
        :param description: {str} The description of the case
        :param resolution: {str} The resolution of the case
        :return: {Case} Case data model
        """
        payload = {
            "name": name,
            "priority": priority,
            "dueDate": due_date,
            "summary": description,
            "resolution": resolution,
        }

        response = self.session.put(
            self._get_full_url("update_case", case_id=case_id),
            json=self.validate_dict_values(payload),
        )
        self.validate_response(
            response,
            error_msg=f"Unable to update case with ID {case_id}",
            handle_not_found=True,
        )

        return self.parser.build_case_obj(response.json())

    def get_alarm_comments(self, alarm_id):
        """
        Get alarm comments
        :param alarm_id: {str} The ID of the alarm
        :return: {list} AlarmComment
        """

        response = self.session.get(
            self._get_full_url("get_comments", alarm_id=alarm_id)
        )
        self.validate_response(
            response, error_msg=f"Unable to get comments for alarm with id {alarm_id}"
        )

        return self.parser.build_results(
            response.json(), "build_alarm_comments_obj", data_key="alarmHistoryDetails"
        )

    def get_alarm_drilldown(self, alarm_id: str) -> AlarmDrilldown:
        """
        Retrieves Drilldown data for the given Alarm ID

        Args:
            alarm_id: Alarm ID

        Returns:
            AlarmDrilldown object
        """
        response = self.session.get(
            self._get_full_url("alarm_drilldown", alarm_id=alarm_id),
            headers={"Content-Type": "application/json"},
        )

        self.validate_response(
            response,
            error_msg=f"Unable to get alarm drilldown for alarm with id {alarm_id}",
            handle_not_found=True,
        )

        if response.status_code == 202:
            return self.parser.build_alarm_drilldown_obj(response.json())
        return self.parser.build_alarm_drilldown_obj({})
