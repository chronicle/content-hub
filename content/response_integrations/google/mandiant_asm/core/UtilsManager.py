from __future__ import annotations
import re


def get_project_id(projects, project_name):
    """
    Helper function for getting project id from projects list
    :param projects: list of available projects in ASM
    :param project_name: name of project to extact id
    :return: {str} original identifier
    """
    for project in projects:
        if project["name"].lower() == project_name.lower():
            return str(project["id"])

    return None


def sanitize_identifiers(entities_identifier):
    identifiers_sanitized = []

    for identifier in entities_identifier:
        identifier = re.sub("http(s)?:\/\/", "", identifier)
        identifier = re.sub("\/.*", "", identifier)
        identifiers_sanitized.append(identifier)

    return identifiers_sanitized
