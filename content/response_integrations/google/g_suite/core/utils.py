from __future__ import annotations
import json
from typing import List

from TIPCommon.types import SingleJson
from g_suite.core import consts
from g_suite.core.datamodels import Role
from g_suite.core.exceptions import InvalidJSONFormatException


def remove_empty_kwargs(**kwargs) -> dict:
    """
    Remove keys from dictionary that has empty value (None, empty list, dict, str..)
    :param kwargs: key value arguments
    :return: dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v or isinstance(v, bool)}


def map_boolean_query_param(param: bool) -> str:
    """
    Map boolean query parameter. Used in list-users API call to list users.
    :param param: {bool} True or False
    :return: {str} 'true' if param is True and 'false' if param is False
    """
    return consts.TRUE if param else consts.FALSE


def map_str_query_param(param: str):
    """
    Map string query parameter. String query parameter must escape single quotes characters inside the string, and replace double quotes to single quotes on both ends of the string.
    For example: "my tip" -> 'my tip', 'my"s tip' -> 'my"s tip', "my's tip" -> 'my\'s tip'
    :param param: {str} the parameter to map
    :return: {str} mapped string
    """
    try:
        escaped_json = param.replace("'", "\\'")
        return f"'{escaped_json}'"
    except Exception:
        return param


# Move to TIPCommon
def parse_string_to_dict(string) -> SingleJson:
    """Parse json string to dict.
    Args:
        string: string to parse.

    Returns:
        {dict} parsed dict.
    """
    try:
        return json.loads(string)
    except json.JSONDecodeError as err:
        error_message = "Unable to parse provided json. Error is:"
        raise InvalidJSONFormatException(f"{error_message} {err}") from err


def prepare_roles(roles_to_check: List[str], roles_list: List[Role]) -> List[Role]:
    """
    Prepares list of roles that should be used based on roles to check.
    If roles to check are None than the full roles_list is returned.

    Args:
        roles_list: {List[Role]} list of roles got from the API for a given user.

    Returns:
        List of roles ready to be attached to the object.
    """
    if not roles_to_check:
        return roles_list
    return [role for role in roles_list if role.role_name in roles_to_check]


def prepare_privileges(
    privileges_to_check: List[str], privileges: List[str]
) -> List[str]:
    """
    Prepares list of privileges that should be used based on privileges to check.
    If privileges to check are None than the full privileges is returned.

    Args:
        privileges: {List[str]} list privileges names that were in roles list.

    Returns:
        List of privileges that is ready to be attached to the object.
    """
    if not privileges_to_check:
        return privileges
    return [privilege for privilege in privileges if privilege in privileges_to_check]


def prepare_result(
    roles: List[Role],
    privileges: List[str],
    max_roles: int,
    max_privileges: int,
    expand_privileges: bool,
):
    """
    Function that is used to create result for each user.

    Args:
    roles: {List[Role]} list of roles that needs to be included in the user result.
    privileges: {List[str]} list of privileges that needs to be included in
        the result.
    max_roles: {int} maximum number of the roles to be returned.
    max_privileges: {int} maximum number of the privileges to be returned.
    expand_privileges: {bool} variable that defines if the privileges should be added to
    the result.

    Returns:
        {dict} Dict that holds data about email account and its roles and privileges.
    """
    if not roles or not privileges:
        return None

    result = {"roles": [role.role_name for role in roles[:max_roles]]}

    if expand_privileges:
        result["unique_privileges"] = privileges[:max_privileges]

    return result


def extract_privileges(roles_list: List[Role]) -> List[str]:
    return list(
        {
            privilege["privilegeName"]
            for role in roles_list
            for privilege in role.role_privileges
        }
    )
