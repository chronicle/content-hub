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
import pathlib
import re
from collections.abc import Iterable

from TIPCommon.base.action import CaseComment, EntityTypesEnum
from TIPCommon.data_models import AlertCard, CaseDetails, SLA
from TIPCommon.types import SingleJson

from google_sec_ops_ai_agents.tests.mocks.siemplify.common import (
    ALERT_IDENTIFIER,
    CASE_META_DATA1,
    CASE_META_DATA2,
    FULL_ALERT_DATA,
    GET_WALL_ACTIVITY,
    minutes_from_now_to_ms,
    MockAttachmentResponse,
    calculate_remaining_time_ms,
    calculate_future_time_milliseconds
)
from google_sec_ops_ai_agents.tests.mocks.siemplify.core.product import GoogleSecOpsSoar
from integration_testing import router
from integration_testing.common import (
    create_case_comment,
    get_request_payload,
    get_def_file_content
)
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


MOCK_CASE_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "mock_data.json"
MOCK_CASE: SingleJson = get_def_file_content(MOCK_CASE_PATH)["mock_case"]
MOCK_CYBER_ALERTS: SingleJson = get_def_file_content(MOCK_CASE_PATH)["mock_cyber_alert"]
MOCK_SEARCH_CASES: SingleJson = get_def_file_content(MOCK_CASE_PATH)["search_cases"]


class GoogleSecOpsSoarSession(MockSession[MockRequest, MockResponse, GoogleSecOpsSoar]):

    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.add_tag,
            self.add_comment,
            self.assign_user,
            self.change_description,
            self.remove_tag,
            self.alert_details,
            self.mark_as_important,
            self.case_meta_data,
            self.case_meta_data_2,
            self.change_priority,
            self.change_case_stage,
            self.close_case,
            self.set_case_sla,
            self.update_alert_priority,
            self.set_alert_sla,
            self.close_alert,
            self.raise_alert,
            self.attache_workflow_to_case,
            self.get_case_details,
            self.create_entity,
            self.create_insight,
            self.any_entity_in_custom_list,
            self.add_entities_to_custom_list,
            self.get_current_siemplify_version,
            self.pause_alert_sla,
            self.resume_alert_sla,
            self.get_custom_list_categories,
            self.remove_entities_from_custom_list,
            self.update_entities,
            self.list_custom_fields,
            self.list_custom_field_values,
            self.get_playbook_instance,
            self.get_alert_full_details,
            self.get_alert_full_details_false,
            self.set_custom_field_values,
            self.get_gemini_case_summary,
            self.batch_set_custom_field_values,
            self.get_wall_activity,
            self.get_wall_activity,
            self.pause_case_sla,
            self.resume_case_sla,
            self.get_case_alerts,
            self.get_case_full_details,
            self.get_case_attachments,
            self.get_attachment,
            self.search_cases,
        ]

    @router.get(r"/api/external/v1/cases/(?:\d+|-)(/alerts/\d+)?/customFieldValues")
    def list_custom_field_values(self, _: MockRequest) -> MockResponse:
        """List custom field values."""
        values = self._product.list_custom_field_values()
        return MockResponse(({"customFieldValues": values} if values else ""))

    @router.get(r"/api/external/v1/cases/insights/[0-9]+")
    def get_wall_activity(self, _: MockRequest) -> MockResponse:
        """Get case wall activity."""
        try:
            return MockResponse(content=GET_WALL_ACTIVITY, status_code=200)
        except ValueError:
            return MockResponse("Activities not found", status_code=404)

    @router.get("/api/external/v1/customFields")
    def list_custom_fields(self, request: MockRequest) -> MockResponse:
        """List custom fields."""
        custom_field_filter = get_request_payload(request, ["params"]).get("filter", "")
        display_name_match = re.match(r"displayName eq '(\w+)'", custom_field_filter)
        custom_fields_name = (
            display_name_match.groups()[1] if display_name_match is not None else None
        )
        return MockResponse(
            {"customFields": self._product.list_custom_fields(custom_fields_name)}
        )

    @router.patch(
        r"/api/external/v1/cases/\d+(/alerts/\d+)?/customFieldValues/[0-1]+"
    )
    def set_custom_field_values(self, _: MockRequest) -> MockResponse:
        """Set custom field values."""
        values = self._product.list_custom_field_values()

        return MockResponse((values[0] if values else {}))

    @router.post(
        r"/api/external/v1/cases/customFieldValues:batchUpdate"
    )
    def batch_set_custom_field_values(self, _: MockRequest) -> MockResponse:
        """Batch set custom field values."""
        values = self._product.list_custom_field_values()

        return MockResponse(
            {
                "customFieldValues": values or []
            }
        )

    @router.post("/api/external/v1/sdk/AddTag")
    def add_tag(self, request: MockRequest) -> MockResponse:
        """Route /AddTage requests"""
        return MockResponse(status_code=204)

    @router.post("/api/external/v1/cases/comments")
    def add_comment(self, request: MockRequest) -> MockResponse:
        """Route /comment requests"""
        case_id: int = request.kwargs["json"]["case_id"]
        comment: str = request.kwargs["json"]["comment"]
        alert_id: str = request.kwargs["json"]["alert_identifier"]
        try:
            comment_id: int = self._product.case_number_of_comments(case_id) + 1
            case_comment: CaseComment = create_case_comment(
                comment_id=comment_id,
                comment=comment,
                case_id=case_id,
                alert_identifier=alert_id,
            )
            self._product.add_case_comment(case_id=case_id, comment=case_comment)
            return MockResponse("Comment was added successfully", status_code=201)

        except ValueError:
            return MockResponse(f"Case {case_id} not found", status_code=404)

    @router.post("/api/external/v1/sdk/AssignUser")
    def assign_user(self, _: MockResponse) -> MockResponse:
        """Route /AssignUser requests"""
        return MockResponse(status_code=200)

    @router.post("/api/external/v1/cases/ChangeCaseDescription")
    def change_description(self, request: MockResponse) -> MockResponse:
        """Route /ChangeCaseDescription requests"""
        case_id: int = request.kwargs["json"]["case_id"]
        description: str = request.kwargs["json"]["description"]
        try:
            case: CaseDetails = self._product.get_case(case_id)
            case.description = description

            return MockResponse("Description was added successfully", status_code=201)

        except ValueError:
            return MockResponse(f"Case {case_id} not found", status_code=404)

    @router.post("/api/external/v1/cases/RemoveCaseTag")
    def remove_tag(self, request: MockRequest) -> MockResponse:
        """Route /RemoveCaseTag requests"""
        case_id: int = request.kwargs["json"]["caseId"]
        try:
            case: CaseDetails = self._product.get_case(case_id)
            case.tags = None if isinstance(case.tags, str) else []

            return MockResponse("Tag was Removed successfully", status_code=201)

        except ValueError:
            return MockResponse(f"Case {case_id} not found", status_code=404)

    @router.get(r"/api/external/v1/sdk/Attachments/[0-9]+")
    def get_case_attachments(self, _: MockRequest) -> MockResponse:
        """Get case attachments."""
        attachments: SingleJson = [
            {
                "id": "1",
                "name": "sample_attachment.txt",
                "type": ".txt",
                "case_id": 1,
            }
        ]

        return MockResponse(content=attachments, status_code=200)

    @router.get(r"/api/external/v1/sdk/AttachmentData/[0-9]+")
    def get_attachment(self, _: MockRequest) -> MockAttachmentResponse:
        """Get a single attachment's content."""
        content: bytes = b"this is a test file"

        return MockAttachmentResponse(content=content, status_code=200)

    @router.post("/api/external/v1/sdk/AlertFullDetails")
    def alert_details(self, _) -> MockResponse:
        """Route /AlertFullDetails requests"""
        content = {
            **FULL_ALERT_DATA,
            "domain_entities": [
                entity.to_dict() for entity in self._product.get_entities()
            ]
        }
        return MockResponse(content=content, status_code=200)

    @router.post("/api/external/v1/sdk/MarkAsImportant")
    def mark_as_important(self, _) -> MockResponse:
        """Route /MarkAsImportant requests"""
        try:
            case: CaseDetails = self._product.get_case(1)
            case.is_important = True

            return MockResponse("Marked As Important", status_code=201)

        except ValueError:
            return MockResponse(f"Case {1} not found", status_code=404)

    @router.get("/api/external/v1/sdk/CaseMetadata/[0-1]+")
    def case_meta_data(self, _) -> MockResponse:
        """Route /CaseMetadata requests"""
        try:
            return MockResponse(content=CASE_META_DATA1, status_code=200)

        except ValueError:
            return MockResponse("Case not found", status_code=404)

    @router.get("/api/external/v1/sdk/CaseMetadata/[2-9]+")
    def case_meta_data_2(self, _) -> MockResponse:
        """Route /CaseMetadata2 requests"""
        try:
            return MockResponse(content=CASE_META_DATA2, status_code=200)

        except ValueError:
            return MockResponse("Case not found", status_code=404)

    @router.post("/api/external/v1/sdk/cases/[0-9]+/sla")
    def set_case_sla(self, request: MockRequest) -> MockResponse:
        """Route /Case sla requests"""
        period_time: int = request.kwargs["json"]["period_time"]
        critical_period_time: int = request.kwargs["json"]["critical_period_time"]
        try:
            case: CaseDetails = self._product.get_case(1)
            case.stage_sla = {
                "slaExpirationTime": minutes_from_now_to_ms(period_time),
                "criticalExpirationTime": minutes_from_now_to_ms(critical_period_time),
                "expirationStatus": 0,
                "remainingTimeSinceLastPause": None,
            }

            return MockResponse("sla of the case has been set", status_code=201)

        except ValueError:
            return MockResponse("Case not found", status_code=404)

    @router.post("/api/external/v1/sdk/cases/[0-9]+/alerts//sla")
    def set_alert_sla(self, request: MockRequest) -> MockResponse:
        """Route /alert sla requests"""
        period_time: int = request.kwargs["json"]["period_time"]
        critical_period_time: int = request.kwargs["json"]["critical_period_time"]
        try:
            alert: AlertCard = self._product.get_alert(ALERT_IDENTIFIER)
            alert.sla = SLA.from_json(
                sla_json={
                    "slaExpirationTime": minutes_from_now_to_ms(period_time),
                    "criticalExpirationTime": minutes_from_now_to_ms(
                        critical_period_time
                    ),
                    "expirationStatus": 0,
                    "remainingTimeSinceLastPause": None,
                }
            )

            return MockResponse("sla of the alert has been set", status_code=201)

        except ValueError:
            return MockResponse("Case not found", status_code=404)

    @router.post("/api/external/v1/sdk/ChangePriority")
    def change_priority(self, request: MockRequest) -> MockResponse:
        """Route /changePriority requests"""
        case_id: int = request.kwargs["json"]["case_id"]
        priority: int = request.kwargs["json"]["priority"]
        try:
            case: CaseDetails = self._product.get_case(case_id)
            case.priority = priority

            return MockResponse("Priority was added successfully", status_code=201)

        except ValueError:
            return MockResponse(f"Case {case_id} not found", status_code=404)

    @router.post("/api/external/v1/sdk/ChangeCaseStage")
    def change_case_stage(self, request: MockRequest) -> MockResponse:
        """Route /ChangeCaseStage requests"""
        case_id: int = request.kwargs["json"]["case_id"]
        stage: int = request.kwargs["json"]["stage"]
        try:
            case: CaseDetails = self._product.get_case(case_id)
            case.stage = stage

            return MockResponse("Case stage was added successfully", status_code=201)

        except ValueError:
            return MockResponse(f"Case {case_id} not found", status_code=404)

    @router.post("/api/external/v1/sdk/UpdateAlertPriority")
    def update_alert_priority(self, request: MockRequest) -> MockResponse:
        """Route /UpdateAlertPriority requests"""

        alert_name: int = request.kwargs["json"]["alertIdentifier"]
        priority: int = request.kwargs["json"]["priority"]
        try:
            alert: AlertCard = self._product.get_alert(alert_name)
            alert.priority = priority

            return MockResponse("Priority was added successfully", status_code=201)

        except ValueError:
            return MockResponse("Case not found", status_code=404)

    @router.post("/api/external/v1/sdk/Close")
    def close_case(self, request: MockRequest) -> MockResponse:
        """Route /close case requests"""
        json_data: SingleJson = request.kwargs["json"]
        case_id: int = json_data.get("source_case_id", json_data.get("case_id"))

        case: CaseDetails = self._product.get_case(case_id)
        if case.status != 1:
            return MockResponse(
                "Cannot close case, as it is already not opened.", status_code=201
            )

        case.status = 2
        return MockResponse("Case is closed successfuly", status_code=201)

    @router.post("/api/external/v1/sdk/CloseAlert")
    def close_alert(self, _: MockRequest) -> MockResponse:
        """Route /CloseAlert requests"""
        alert: AlertCard = self._product.get_alert(ALERT_IDENTIFIER)
        if alert.status != 0:
            content = {
                "errorCode": 2000,
                "errorMessage": "You can not perform this action on a closed alert",
                "innerException": None,
                "innerExceptionType": None,
            }
            return MockResponse(content=content, status_code=400)

        alert.status = 1
        return MockResponse(
            content={"is_request_valid": True, "errors": [], "new_case_id": None},
            status_code=200,
        )

    @router.post("/api/external/v1/sdk/RaiseIncident")
    def raise_alert(self, request: MockRequest) -> MockResponse:
        """Route /RaiseIncident requests"""
        case_id: int = request.kwargs["json"]["case_id"]

        try:
            case: CaseDetails = self._product.get_case(case_id)
            case.is_incident = True
            case.stage = "Incident"

            return MockResponse("Incident raised successfuly", status_code=201)
        except ValueError:
            return MockResponse(f"Case {case_id} not found", status_code=404)

    @router.post("/api/external/v1/sdk/AttacheWorkflowToCase")
    def attache_workflow_to_case(self, request: MockRequest) -> MockResponse:
        """Route /AttacheWorkflowToCase requests"""
        case_id: int = request.kwargs["json"]["cyber_case_id"]
        alert_identifier = request.kwargs["json"]["alert_identifier"]
        playbook_name: int = request.kwargs["json"]["wf_name"]

        try:
            alert: AlertCard = self._product.get_alert(alert_identifier)
            alert.workflow_status = 2
            alert.playbook_attached = playbook_name
            alert.playbook_run_count = 1

            return MockResponse(content=True, status_code=200)
        except ValueError:
            return MockResponse(f"Case {case_id} not found", status_code=404)

    @router.post("/api/external/v1/sdk/CreateEntity")
    def create_entity(self, request: MockRequest) -> MockResponse:
        """Route /CreateEntity requests"""
        identifier: str = request.kwargs["json"]["entity_identifier"]
        entity_type: str = request.kwargs["json"]["entity_type"]
        category: EntityTypesEnum = EntityTypesEnum[entity_type]
        try:
            self._product.add_entity(identifier=identifier, category=category)
            return MockResponse("Successfully Created Entity", status_code=200)

        except ValueError:
            return MockResponse("Unable to create entity", status_code=404)

    @router.post("/api/external/v1/sdk/CreateCaseInsight")
    def create_insight(self, request: MockRequest) -> MockResponse:
        """Route /CreateCaseInsight requests"""
        case_id: int = request.kwargs["json"]["case_id"]
        try:
            self._product.get_case(case_id)
            return MockResponse({}, status_code=201)

        except ValueError:
            return MockResponse(f"Case {case_id} Not Found", status_code=404)

    @router.post("/api/external/v1/sdk/AnyEntityInCustomList")
    def any_entity_in_custom_list(self, _) -> MockResponse:
        """Route /AnyEntityInCustomList requests"""
        try:
            return MockResponse(content=True, status_code=201)

        except ValueError:
            return MockResponse("list was not found", status_code=404)

    @router.post("/api/external/v1/sdk/AddEntitiesToCustomList")
    def add_entities_to_custom_list(self, _) -> MockResponse:
        """Route /AddEntitiesToCustomList requests"""
        try:
            entity: list[dict] = [
                {
                    "identifier": "list",
                    "category": "list",
                    "environment": "Default Environment",
                }
            ]
            return MockResponse(content=entity, status_code=201)

        except ValueError:
            return MockResponse("Custom List not found", status_code=404)

    @router.get(r"/api/external/v1/sdk/GetCurrentSiemplifyVersion/?")
    def get_current_siemplify_version(self, _) -> MockResponse:
        """Route /GetCurrentSiemplifyVersion requests"""
        try:
            return MockResponse(content=json.dumps("5.6.1.0"), status_code=200)

        except ValueError:
            return MockResponse("Value not found", status_code=404)

    @router.post("/api/external/v1/cases/PauseAlertSla")
    def pause_alert_sla(self, request: MockRequest) -> MockResponse:
        """Route /PauseAlertSla requests"""
        case_id: int = request.kwargs["json"]["caseId"]
        try:
            self._product.get_alert(ALERT_IDENTIFIER)
            return MockResponse(content={}, status_code=200)

        except ValueError:
            return MockResponse(f"case {case_id} not found", status_code=404)

    @router.post("/api/external/v1/cases/ResumeAlertSla")
    def resume_alert_sla(self, request: MockRequest) -> MockResponse:
        """Route /ResumeAlertSla requests"""
        case_id: int = request.kwargs["json"]["caseId"]
        if case_id == "no_case_id":
            return MockResponse(f"case {case_id} not found", status_code=404)

        try:
            self._product.get_alert(ALERT_IDENTIFIER)
            return MockResponse(content={}, status_code=200)

        except ValueError:
            return MockResponse(f"case {case_id} not found", status_code=404)

    @router.get("/api/external/v1/sdk/GetCustomListCategories")
    def get_custom_list_categories(self, _) -> MockResponse:
        """Route /GetCustomListCategories requests"""
        try:
            return MockResponse(content=json.dumps(["list"]), status_code=200)

        except ValueError:
            return MockResponse("Custom List not found", status_code=404)

    @router.post("/api/external/v1/sdk/RemoveEntitiesFromCustomList")
    def remove_entities_from_custom_list(self, _) -> MockResponse:
        """Route /RemoveEntitiesFromCustomList requests"""
        try:
            entity: dict = [
                {
                    "identifier": "test_entity",
                    "category": "list",
                    "environment": "Default Environment",
                }
            ]
            return MockResponse(content=entity, status_code=201)

        except ValueError:
            return MockResponse("Categroy not found", status_code=404)

    @router.post("/api/external/v1/sdk/UpdateEntities")
    def update_entities(self, _) -> MockResponse:
        """Route /RemoveEntitiesFromCustomList requests"""
        try:
            return MockResponse(content={}, status_code=201)

        except ValueError:
            return MockResponse("entity not found", status_code=404)

    @router.get("/api/external/v1/dynamic-cases/GetCaseDetails/[0-9]+")
    def get_case_details(self, _: MockRequest) -> MockResponse:
        """Route /GetCaseDetails requests"""
        try:
            case: SingleJson = MOCK_CASE
            return MockResponse(content=case, status_code=200)

        except ValueError:
            return MockResponse("Case not found", status_code=404)

    @router.post("/api/external/v1/cases/GetWorkflowInstancesCards")
    def get_playbook_instance(self, _: MockRequest) -> MockResponse:
        """Handle playbook instance requests"""
        return MockResponse(content=[], status_code=200)

    @router.get("/api/external/v1/sdk/AlertsFullDetails/[0-9]+")
    def get_alert_full_details(self, _: MockRequest) -> MockResponse:
        """Handle alert full details requests"""
        alert = self._product.get_alerts()[0]
        return MockResponse(
            content=[alert.to_json()],
            status_code=200,
        )

    @router.get("/api/external/v1/sdk/AlertsFullDetails/[0-9]+/[a-zA-Z]+")
    def get_alert_full_details_false(self, _: MockRequest) -> MockResponse:
        """Handle alert full details false requests"""
        alert = self._product.get_alerts()[0]
        return MockResponse(
            content=[alert.to_json()],
            status_code=200,
        )

    @router.post("/api/1p/external/v1/cases/[0-9]+:getOrCreateCaseSummary")
    def get_gemini_case_summary(self, request: MockRequest) -> MockResponse:
        """Handle gemini case summary requests"""
        case_id = int(request.url.path.split("/")[-1].split(":")[-2])
        case_summary = self._product.get_case_summary(case_id)
        content = case_summary.to_json()
        case_id_to_summary_state_mapping = {
            1: 2,  # SUCCESS
            2: 1,  # IN_PROGRESS
            3: 3,  # ERROR
            4: 4,  # UNEXPECTED_STATE  (assuming 4 maps to an unexpected state)
        }
        state = case_id_to_summary_state_mapping.get(case_id, 2)
        if state in [0, 1]:
            case_summary.gemini_case_summary = None
        if state == 2:
            case_summary.gemini_case_summary = True
        if state in [3, 4]:
            case_summary.gemini_case_summary = False
        content["state"] = state

        return MockResponse(
            content=content,
            status_code=200,
        )

    @router.post(
        "/v1alpha/projects/project/locations/location/instances/instance/cases/[0-9]+:"
        "pauseSla"
    )
    def pause_case_sla(self, request: MockRequest) -> MockResponse:
        """Handle pause case sla requests"""
        case_id = int(request.url.path.split("/")[-1].split(":")[-2])
        try:
            case:CaseDetails = self._product.get_case(case_id)
            if case.stage_sla is not None:
                remaining_time_ms:int = calculate_remaining_time_ms(
                    case.stage_sla.sla_expiration_time
                )
                case.stage_sla.sla_expiration_time = -1
                case.stage_sla.critical_expiration_time = -1
                case.stage_sla.remaining_time_since_last_pause = remaining_time_ms
                self._product.update_case(case)
                return MockResponse(content="SLA paused successfully", status_code=200)

            return MockResponse(
                content="There is no active SLA to pause",
                status_code=200
            )

        except ValueError:
            return MockResponse(
                content=f"Case {case_id} not found",
                status_code=404
            )

    @router.post(
        "/v1alpha/projects/project/locations/location/instances/instance/cases/[0-9]+:"
        "resumeSla"
    )
    def resume_case_sla(self, request: MockRequest) -> MockResponse:
        """Handle resume case sla requests"""
        case_id = int(request.url.path.split("/")[-1].split(":")[-2])
        try:
            case:CaseDetails = self._product.get_case(case_id)
            if case.stage_sla is not None:
                remaining_time_ms:int = case.stage_sla.remaining_time_since_last_pause
                case.stage_sla.sla_expiration_time = calculate_future_time_milliseconds(
                    milliseconds_to_add=remaining_time_ms
                )
                case.stage_sla.critical_expiration_time = -1
                case.stage_sla.remaining_time_since_last_pause = None
                self._product.update_case(case)
                return MockResponse(content="SLA resumed successfully", status_code=200)

            return MockResponse(
                content="There is no active SLA to resume",
                status_code=200
            )

        except ValueError:
            return MockResponse(
                content=f"Case {case_id} not found",
                status_code=404
            )

    @router.get("/api/external/v1/sdk/CaseFullDetails/[0-9]+/False")
    def get_case_alerts(self, _: MockRequest) -> MockResponse:
        """Get case details."""
        return MockResponse(MOCK_CYBER_ALERTS, status_code=200)

    @router.get(r"/api/external/v1/cases/GetCaseFullDetails/[0-9]+")
    def get_case_full_details(self, _: MockRequest) -> MockResponse:
        """Get case full details."""
        return MockResponse(MOCK_CYBER_ALERTS, status_code=200)

    @router.get(r"/api/external/v1/cases")
    def search_cases(self, _: MockRequest) -> MockResponse:
        """Search cases."""
        return MockResponse(MOCK_SEARCH_CASES, status_code=200)
