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
from unittest.mock import patch
from http import HTTPStatus

from TIPCommon.base.action import ExecutionState

from ...actions import send_itp_signal_to_okta
from ...core.utils import get_full_url
from ...tests.common import CONFIG_PATH
from ...tests.core.session import Session
from ...tests.core.product import Product
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Key ID": "test_key_id_123",
        "Private Key": "-----BEGIN RSA PRIVATE KEY-----"
        "test_private_key_123-----END RSA PRIVATE KEY-----",
        "User Email": "test@google.com",
        "Timestamp": "2025-03-17T08:22:50.057Z",
        "Reason": "test reason",
        "Severity": "Low",
        "Issuer URL": "https://test_url.com",
    },
)
def test_send_itp_signal_status_202_success(
    script_session: Session,
    action_output: MockActionOutput,
) -> None:
    with patch("okta.core.OktaManager.jwt.encode") as mock_jwt_encode:
        mock_jwt_encode.return_value = "test_token"
        send_itp_signal_to_okta.main()

    assert len(script_session.request_history) == 2
    assert script_session.request_history[0].request.url.path == "/api/v1/users/me"
    assert script_session.request_history[1].request.url.path == (
        "/security/api/v1/security-events"
    )
    assert (
        action_output.results.json_output.json_result["status"] == HTTPStatus.ACCEPTED
    )
    assert action_output.results.json_output.json_result["payload"]
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Key ID": "test_key_id_2",
        "Private Key": "-----BEGIN RSA PRIVATE KEY-----"
        "test_private_key_123-----END RSA PRIVATE KEY-----",
        "User Email": "test2@google.com",
        "Timestamp": "2020-03-17T08:22:50.057Z",
        "Reason": "test reason 2",
        "Severity": "Low",
        "Issuer URL": "https://test_url.com",
    },
)
def test_send_itp_signal_status_200_fail(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    okta_product.set_status(status=200)
    with patch("okta.core.OktaManager.jwt.encode") as mock_jwt_encode:
        mock_jwt_encode.return_value = "test_token"
        send_itp_signal_to_okta.main()
    assert len(script_session.request_history) == 2
    assert action_output.results.output_message == (
        "Failed to send the ITP Signal to Okta."
    )
    assert action_output.results.json_output.json_result["status"] == HTTPStatus.OK
    assert action_output.results.json_output.json_result["payload"]
    assert action_output.results.result_value is False


def test_request_url():
    data_okta_tenant_url = "https://nikhilp.oktapreview.com"
    request_url = get_full_url(
        api_root=data_okta_tenant_url, endpoint_id="send_itp_signal"
    )
    assert request_url == (
        "https://nikhilp.oktapreview.com/security/api/v1/security-events"
    )
