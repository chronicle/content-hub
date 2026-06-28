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

import pathlib
from http import HTTPStatus

from TIPCommon.base.action import ExecutionState

from okta.actions import ClearOktaUserSession
from okta.tests.common import CONFIG_PATH
from okta.tests.core.product import Product
from okta.tests.core.session import Session
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

USER_ID = "00u1a2b3c4d5e6f7g8h9"
USER_EMAIL = "test.user@example.com"
USER_NOT_FOUND = "not.found@example.com"


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "User IDs Or Logins": USER_ID,
        "Also Run On Scope": "false",
    },
)
def test_clear_session_for_single_user_id_success(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    okta_product.set_get_user_response(user_id=USER_ID, response_data={"id": USER_ID})
    okta_product.set_clear_user_sessions_response(
        user_id=USER_ID, status=HTTPStatus.NO_CONTENT
    )

    ClearOktaUserSession.main()

    assert len(script_session.request_history) == 2
    assert (
        script_session.request_history[0].request.url.path == f"/api/v1/users/{USER_ID}"
    )
    assert (
        script_session.request_history[1].request.url.path
        == f"/api/v1/users/{USER_ID}/sessions"
    )

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert f"Successfully cleared sessions for the following users: {USER_ID}" in (
        action_output.results.output_message
    )


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "User IDs Or Logins": USER_ID,
        "Also Run On Scope": "false",
    },
)
def test_clear_session_for_single_user_id_failure(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    okta_product.set_get_user_response(user_id=USER_ID, response_data={"id": USER_ID})
    okta_product.set_clear_user_sessions_response(
        user_id=USER_ID, status=HTTPStatus.INTERNAL_SERVER_ERROR
    )

    ClearOktaUserSession.main()

    assert len(script_session.request_history) == 2
    assert (
        script_session.request_history[0].request.url.path == f"/api/v1/users/{USER_ID}"
    )
    assert (
        script_session.request_history[1].request.url.path
        == f"/api/v1/users/{USER_ID}/sessions"
    )

    assert action_output.results.result_value is False
