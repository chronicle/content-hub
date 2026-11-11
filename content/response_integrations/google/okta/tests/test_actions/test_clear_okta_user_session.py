from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from TIPCommon.base.action import ExecutionState

from okta.actions import ClearOktaUserSession
from okta.tests.common import CONFIG_PATH
from integration_testing.set_meta import set_metadata

if TYPE_CHECKING:
    from okta.tests.core.product import Product
    from okta.tests.core.session import Session
    from integration_testing.platform.script_output import MockActionOutput

USER_ID = "00u1a2b3c4d5e6f7g8h9"
EXPECTED_OAUTH_SCOPES = "okta.users.read okta.groups.read okta.users.manage"


def _generate_test_rsa_private_key() -> str:
    """Generates an ephemeral PEM-encoded RSA private key for OAuth JWT signing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem_bytes.decode("utf-8")


OAUTH_CONFIG: dict[str, str] = {
    "Api Root": "https://{okta_domain}.com/",
    "Use Oauth Authentication": "true",
    "Client ID": "0oa_test_client_id",
    "Key ID": "test_kid_01",
    "Private Key": _generate_test_rsa_private_key(),
    "Verify SSL": "False",
}


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


@set_metadata(
    integration_config=OAUTH_CONFIG,
    parameters={
        "User IDs Or Logins": USER_ID,
        "Also Run On Scope": "false",
    },
)
def test_clear_session_with_oauth_authentication_success(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    """Regression test for b/575763651: OAuth token requests okta.users.manage scope."""
    okta_product.set_get_user_response(user_id=USER_ID, response_data={"id": USER_ID})
    okta_product.set_clear_user_sessions_response(
        user_id=USER_ID, status=HTTPStatus.NO_CONTENT
    )

    ClearOktaUserSession.main()

    assert len(script_session.request_history) == 3
    token_request = script_session.request_history[0].request
    get_user_request = script_session.request_history[1].request
    clear_session_request = script_session.request_history[2].request

    assert token_request.url.path == "/oauth2/v1/token"
    token_data = token_request.kwargs["data"]
    assert token_data["grant_type"] == "client_credentials"
    assert token_data["scope"] == EXPECTED_OAUTH_SCOPES
    assert "okta.users.manage" in token_data["scope"]

    assert get_user_request.url.path == f"/api/v1/users/{USER_ID}"
    assert get_user_request.headers["Authorization"] == "Bearer mock_oauth_access_token"
    assert clear_session_request.url.path == f"/api/v1/users/{USER_ID}/sessions"
    assert (
        clear_session_request.headers["Authorization"]
        == "Bearer mock_oauth_access_token"
    )

    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.result_value is True
    assert f"Successfully cleared sessions for the following users: {USER_ID}" in (
        action_output.results.output_message
    )


@set_metadata(
    integration_config=OAUTH_CONFIG,
    parameters={
        "User IDs Or Logins": USER_ID,
        "Also Run On Scope": "false",
    },
)
def test_clear_session_with_oauth_authentication_forbidden_failure(
    script_session: Session,
    action_output: MockActionOutput,
    okta_product: Product,
) -> None:
    """Verify 403 Forbidden during OAuth session clearance transitions to FAILED."""
    okta_product.set_get_user_response(user_id=USER_ID, response_data={"id": USER_ID})
    okta_product.set_clear_user_sessions_response(
        user_id=USER_ID, status=HTTPStatus.FORBIDDEN
    )

    ClearOktaUserSession.main()

    assert len(script_session.request_history) == 3
    assert script_session.request_history[0].request.url.path == "/oauth2/v1/token"
    assert (
        script_session.request_history[1].request.url.path == f"/api/v1/users/{USER_ID}"
    )
    assert (
        script_session.request_history[2].request.url.path
        == f"/api/v1/users/{USER_ID}/sessions"
    )

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
    assert f"Failed to clear sessions for user {USER_ID}: 403" in (
        action_output.results.output_message
    )
