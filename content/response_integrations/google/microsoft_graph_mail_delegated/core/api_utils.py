from __future__ import annotations
from typing import Any

from collections.abc import Callable, MutableMapping, MutableSequence

from urllib.parse import urljoin

import requests
from . import constants
from . import exceptions


def get_full_url(api_root: str, url_id: str, **kwargs) -> str:
    """Construct the full URL using a URL identifier and optional variables.

    Args:
        api_root (str): The root of the API endpoint.
        url_id (str): The identifier for the specific URL.
        kwargs (dict): Variables passed for string formatting.

    Returns:
        str: The full URL constructed by combining the API root, URL identifier, and
            variables.
    """
    return urljoin(api_root, constants.ENDPOINTS[url_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg="An error occurred",
) -> None:
    """Validate response

    Args:
        response (requests.Response): The response to validate
        error_msg (str):  Default message to display on error.
            Defaults to 'An error occurred'.
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            err = response.json().get("error")
            err_codes = response.json().get("error_codes") or []
            err_msg = err.get("message") if "message" in err else err
            if (
                constants.REFRESH_TOKEN_ERR_CODE in err_codes
                and response.status_code == constants.FAILURE_STATUS_CODE
            ):
                raise exceptions.InvalidRefreshTokenError(
                    "Refresh Token is invalid or malformed. "
                    "(Token is valid only for 90 days, "
                    "please renew your refresh token.)"
                )
            if (
                constants.INVALID_CLIENT_ID_ERR_CODE in err_codes
                and response.status_code == constants.FAILURE_STATUS_CODE
            ):
                raise exceptions.InvalidClientIdError(
                    "The provided 'Client ID' is invalid. Please verify and try again."
                )
            if (
                constants.INVALID_TENANT_ID_ERR_CODE in err_codes
                and response.status_code == constants.FAILURE_STATUS_CODE
            ):
                raise exceptions.InvalidTenantIdError(
                    "The provided 'Microsoft Entra ID Directory ID' is invalid. "
                    "Please verify and try again."
                )
            if (
                constants.INVALID_CLIENT_SECRET_ERR_CODE in err_codes
                and response.status_code == constants.HTTP_STATUS_UNAUTHORIZED
            ):
                raise exceptions.InvalidClientSecretError(
                    "The provided 'Client Secret Value' is invalid. Please verify and "
                    "try again."
                )
            if err_msg.lower() == constants.DELEGATION_PERMISSION_ERR:
                raise exceptions.InvalidDelegationPermissionError(
                    "The account does not have delegated permissions for the "
                    "requested 'User Mailbox'."
                )
            raise exceptions.MicrosoftGraphMailManagerError(
                f"{error_msg}: {err_msg}"
            ) from error

        except (ValueError, requests.exceptions.JSONDecodeError) as exc:
            raise exceptions.MicrosoftGraphMailManagerError(
                f"{error_msg}: {error} {response.content}"
            ) from exc


def requests_in_batches(
    request_func: Callable[[str, Any], requests.Response],
    batch_url: str,
    batch_requests: MutableSequence[MutableMapping[str, str]],
    batch_limit: int = constants.BATCH_RATE_LIMIT,
) -> list[Any]:
    """
    Send batched requests to an API endpoint and aggregate the results.

    Args:
        request_func (Callable[[str, Any], requests.Response]): A function to send the
        request, typically a wrapper around an HTTP request method like `requests.post`.
        batch_url (str): The API endpoint URL to which the batched requests will
            be sent.
        batch_requests (MutableSequence[MutableMapping[str, str]]): A list of
        dictionaries, where each dictionary represents an individual request payload.
        batch_limit (int): The maximum number of requests to include in each batch.
        Defaults to the constant `constants.BATCH_RATE_LIMIT`.

    Returns:
        list[Any]: A list of responses from the API, aggregated from each batch.
    """
    results = []
    for i in range(0, len(batch_requests), batch_limit):
        batch = batch_requests[i : i + batch_limit]
        response = request_func(batch_url, json={"requests": batch})
        validate_response(response=response)
        results.extend(response.json()["responses"])

    return results
