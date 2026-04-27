from __future__ import annotations
from .consts import USER, GROUP, ALL_USERS, ALL_AUTHENTICATED_USER
from .exceptions import GoogleCloudStorageValidationException


def load_csv_to_list(csv, param_name):
    """
    Load comma separated values represented as string to a list
    :param csv: {str} of comma separated values with delimiter ','
    :param param_name: {str} the name of the variable we are validation
    :return: {list} of values
            raise GoogleCloudStorageValidationException if failed to parse csv
    """
    try:
        return [t.strip() for t in csv.split(",")]
    except Exception:
        raise GoogleCloudStorageValidationException(
            f"Failed to parse parameter {param_name}"
        )


def should_update(current_roles, new_role):
    """
    Check if the current roll smaller in manner of permissions level than the new role
    :param current_roles: {set} Set of roles that the entity currently have
    :param new_role: {str} The requested role to assign. OWNER, WRITER or READER
    :return: {tuple} (True, current highest role) if new role bigger in manner of permissions level,
    (False, current highest role) otherwise
    """
    if new_role in current_roles:
        return False, new_role

    return True, None


def is_entity_valid(entity):
    """
    Entity validation. checks if is of a kind: user-userId, user-emailAddress, group-groupId,
     group-emailAddress, allUsers, or allAuthenticatedUsers.
    :param entity: {str} Entity value
    :return: True if the entity parameter is of the permitted kind, false otherwise
    """
    if (
        entity == ALL_USERS
        or entity == ALL_AUTHENTICATED_USER
        or entity[: len(USER)] == USER
        or entity[: len(GROUP)] == GROUP
    ):
        return True
    return False
