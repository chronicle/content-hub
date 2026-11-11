from __future__ import annotations
import requests
from hashi_corp_vault.core.HashiCorpVaultExceptions import HashiCorpVaultException, NotFoundException


def validate_response(response, error_msg="An error occurred"):
    """
    Validate response
    Args:
        response (requests.Response): The response to validate
        error_msg (str): Default message to display on error

    Returns:
        True, if successful, HashiCorpVaultException otherwise
    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        try:
            error_messages = response.json().get("errors", [])
            error_string = (
                "\n".join(error_messages) if error_messages else response.status_code
            )

            if "not found" in error_string.casefold():
                raise NotFoundException(error_string)
            raise HashiCorpVaultException(error_string)

        except (ValueError, KeyError):
            pass

        raise HashiCorpVaultException(f"{error_msg}: {error} {error.response.content}")
