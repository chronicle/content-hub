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

from typing import TYPE_CHECKING
from urllib.parse import parse_qs

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from .product import SentinelOne

if TYPE_CHECKING:
    from collections.abc import Iterable

    from TIPCommon.types import SingleJson


class SentinelOneSession(MockSession[MockRequest, MockResponse, SentinelOne]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.graphql_endpoint,
            self.users_endpoint,
        ]

    @router.post(r"/web/api/v2.1/unifiedalerts/graphql")  # type: ignore # noqa: PGH003
    def graphql_endpoint(self, request: MockRequest) -> MockResponse:  # noqa: PLR0911
        try:
            payload: SingleJson = get_request_payload(request)
        except Exception as e:  # noqa: BLE001
            return MockResponse(
                content={"errors": [{"message": f"Invalid payload: {e}"}]},
                status_code=400,
            )

        query = payload.get("query", "")
        variables = payload.get("variables", {})

        assert self._product is not None

        if "GetUnifiedAlerts" in query:
            first = variables.get("first", 1)
            after = variables.get("after")
            view_type = variables.get("viewType", "ALL")
            try:
                data = self._product.get_unified_alerts(first, view_type, after)
                return MockResponse(content=data, status_code=200)
            except Exception as e:  # noqa: BLE001
                return MockResponse(
                    content={"errors": [{"message": str(e)}]}, status_code=500
                )

        elif "GetAlertByIdAllFields" in query:
            alert_id = variables.get("id")
            try:
                data = self._product.get_alert_details(alert_id)
                return MockResponse(content=data, status_code=200)
            except Exception as e:  # noqa: BLE001
                return MockResponse(
                    content={"errors": [{"message": str(e)}]}, status_code=500
                )

        elif "AlertTriggerActions" in query:
            actions = variables.get("actions", [])
            alert_filter = variables.get("filter", {})
            try:
                data = self._product.trigger_actions(actions, alert_filter)
                return MockResponse(content=data, status_code=200)
            except Exception as e:  # noqa: BLE001
                return MockResponse(
                    content={"errors": [{"message": str(e)}]}, status_code=500
                )

        elif "AddAlertNote" in query:
            alert_id = variables.get("alertId")
            text = variables.get("text")
            plain_text = variables.get("plainText")
            note_type = variables.get("type")
            try:
                data = self._product.add_alert_note(
                    alert_id=alert_id,
                    text=text,
                    plain_text=plain_text,
                    note_type=note_type,
                )
                return MockResponse(content=data, status_code=200)
            except Exception as e:  # noqa: BLE001
                return MockResponse(
                    content={"errors": [{"message": str(e)}]}, status_code=500
                )

        return MockResponse(
            content={"errors": [{"message": "Unknown query"}]}, status_code=200
        )

    @router.get(r"/web/api/v2.1/users")  # type: ignore # noqa: PGH003
    def users_endpoint(self, request: MockRequest) -> MockResponse:
        email = None
        params_kwarg = request.kwargs.get("params") or {}
        if isinstance(params_kwarg, dict):
            email = params_kwarg.get("email")

        if not email:
            params = parse_qs(request.url.query)
            email = params.get("email", [None])[0]

        assert self._product is not None
        try:
            data = self._product.get_users(email=email)
            return MockResponse(content=data, status_code=200)
        except Exception as e:  # noqa: BLE001
            return MockResponse(
                content={"errors": [{"message": str(e)}]}, status_code=500
            )
