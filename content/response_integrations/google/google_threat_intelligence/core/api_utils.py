from __future__ import annotations

import re
import urllib.parse
from json import JSONDecodeError

import requests
from google_threat_intelligence.core.constants import AGENT_HTTP_ERROR_MESSAGE, EMAIL_ENTITY_TYPE, ENDPOINTS, QUERY_JOIN_PARAMETER
from google_threat_intelligence.core.exceptions import (
    GoogleThreatIntelligenceBadRequestException,
    GoogleThreatIntelligenceHTTPException,
    GoogleThreatIntelligenceNotFoundException,
    GoogleThreatIntelligencePermissionException,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.types import Entity
from TIPCommon.utils import get_entity_original_identifier
from google_threat_intelligence.core.utils import get_entity_type

ENTITY_TYPE_TO_QUERY_KEY_MAPPING = {
    EntityTypes.FILEHASH: "file",
    EntityTypes.URL: "url",
    EntityTypes.ADDRESS: "ip_address",
    EntityTypes.HOSTNAME: "domain",
    EntityTypes.THREATACTOR: "actor",
    EMAIL_ENTITY_TYPE: "email",
    EntityTypes.DOMAIN: "domain",
    EntityTypes.USER: "victim",
}
FORBIDDEN_STATUS_CODE = 403
NOT_FOUND_STATUS_CODE = 404
UNAUTHORIZED_STATUS_CODE = 401
BAD_REQUEST = 400

GTI_HTTP_EXCEPTION_MAPPING = {
    BAD_REQUEST: GoogleThreatIntelligenceBadRequestException,
    FORBIDDEN_STATUS_CODE: GoogleThreatIntelligencePermissionException,
    NOT_FOUND_STATUS_CODE: GoogleThreatIntelligenceNotFoundException,
}


def get_full_url(
    api_root: str, endpoint_id: str, endpoints: dict[str, str] = None, **kwargs
) -> str:
    """Construct the full URL using a URL identifier and optional variables

    Args:
        api_root (str): The root of the API endpoint
        endpoint_id (str): The identifier for the specific URL
        endpoints (dict[str, str]): endpoints dictionary object
        kwargs (dict): Variables passed for string formatting

    Returns:
        str: The full URL constructed from API root, endpoint identifier and variables

    """
    endpoints = endpoints or ENDPOINTS
    return urllib.parse.urljoin(api_root, endpoints[endpoint_id].format(**kwargs))


def validate_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
    show_entity_status: bool = False,
) -> None:
    """Validate response

    Args:
        response (requests.Response): Response to validate
        error_msg (str): Default message to display on error
        show_entity_status (bool, optional):  Return error message for entity

    Raises:
        GoogleThreatIntelligenceHTTPException: If there is any error in the response

    """
    try:
        response.raise_for_status()

    except requests.HTTPError as error:
        if response.status_code == NOT_FOUND_STATUS_CODE:
            if show_entity_status:
                api_error = response.json().get("error", {})
                raise GoogleThreatIntelligenceNotFoundException(
                    f"{api_error.get('code')}. {api_error.get('message')}"
                ) from error
            raise GoogleThreatIntelligenceNotFoundException(error) from error

        if response.status_code == BAD_REQUEST:
            if show_entity_status:
                api_error = response.json().get("error", {})
                raise GoogleThreatIntelligenceBadRequestException(
                    f"{api_error.get('code')}. {api_error.get('message')}"
                ) from error

            # Extract detailed error message if available
            try:
                detail = response.json().get("error", {}).get("message", response.text)
                error_desc = f"{error}. API Error: {detail}"
            except JSONDecodeError:
                error_desc = f"{error}. API Error: {response.text}"

            raise GoogleThreatIntelligenceBadRequestException(error_desc) from error

        if response.status_code == FORBIDDEN_STATUS_CODE:
            raise GoogleThreatIntelligencePermissionException(error) from error
        raise GoogleThreatIntelligenceHTTPException(
            f"{error_msg}: {error} {error.response.content}",
            status_code=error.response.status_code,
        ) from error


def validate_gti_response(
    response: requests.Response,
    error_msg: str = "An error occurred",
) -> None:
    """Checks a requests.Response for HTTP errors and raises a custom GTI exception
    based on common errors mapping.

    Args:
        response: The requests.Response object to validate.
        error_msg: A generic error message to use if a detailed one cannot be found.

    Raises:
        GoogleThreatIntelligenceBadRequestException: On 400 Bad Request errors.
        GoogleThreatIntelligencePermissionException: On 403 Forbidden errors.
        GoogleThreatIntelligenceNotFoundException: On 404 Not Found errors.
        GoogleThreatIntelligenceHTTPException: For any other unmapped HTTP error.
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        detail = str(error)
        # Safely parse the detailed error message from the JSON body.
        try:
            # Try to get the specific message from the API.
            detail = error.response.json().get("message", error.response.text or detail)
        except JSONDecodeError:
            if error.response.text:
                detail = error.response.text

        exception_class = GTI_HTTP_EXCEPTION_MAPPING.get(
            error.response.status_code, GoogleThreatIntelligenceHTTPException
        )

        raise exception_class(f"{error_msg}: {detail}") from error


def validate_agent_session_response(response: requests.Response) -> None:
    """Validate a response from the Google Threat Intelligence agentspace sessions API.

    Args:
        response: The response to validate.

    Raises:
        GoogleThreatIntelligenceBadRequestException: On 400 Bad Request errors.
        GoogleThreatIntelligencePermissionException: On 403 Forbidden errors.
        GoogleThreatIntelligenceNotFoundException: On 404 Not Found errors.
        GoogleThreatIntelligenceHTTPException: For any other HTTP error.
    """
    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        exception_class = GTI_HTTP_EXCEPTION_MAPPING.get(
            response.status_code,
            GoogleThreatIntelligenceHTTPException,
        )
        raise exception_class(
            AGENT_HTTP_ERROR_MESSAGE.format(
                status_code=response.status_code,
                details=_get_api_error_details(response),
            )
        ) from error


def _get_api_error_details(response: requests.Response) -> str:
    """Get the API error message from a failed response, or its text when there is none."""
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        api_error = payload.get("error")
        message = api_error.get("message") if isinstance(api_error, dict) else payload.get("message")
        if message:
            return str(message).strip().rstrip(".")

    return (response.text or response.reason or "").strip().rstrip(".")


def get_project_id(projects, project_name) -> (str, None):
    """Helper function for getting project id from projects list
    Args:
        projects: list of available projects in ASM
        project_name: name of project to extact id
    Returns:
        str: original identifier
    """
    for project in projects:
        if project["name"] == project_name:
            return str(project["id"])

    return None


def build_query(entities: [Entity], join_operator: str = QUERY_JOIN_PARAMETER) -> str:
    """Build query based on entity types

    Args:
        entities ([Entity]): list of entities to build query
        join_operator (str): operator to concatenate different entities in the query

    Returns:
        str: constructed query string

    """
    queries = []

    for entity in entities:
        entity_type = get_entity_type(entity)
        query_field = ENTITY_TYPE_TO_QUERY_KEY_MAPPING.get(entity_type)
        query_value = get_entity_original_identifier(entity)

        queries.append(
            f'{query_field}:"{query_value}"'
            if entity_type == EntityTypes.URL
            else f"{query_field}:{query_value}"
        )

    return join_operator.join(queries)


def sanitize_identifiers(entities_identifier):
    """Sanitizes a list of identifiers by removing protocol
    prefixes (e.g., "http://" or "https://") and any trailing paths.

    Args:
        entities_identifier (list of str): A list of identifier strings, typically URLs.

    Returns:
        list of str: A list of sanitized identifier strings, with protocols and paths
                     removed.

    """
    identifiers_sanitized = []

    for identifier in entities_identifier:
        identifier = re.sub(r"http(s)?:\/\/", "", identifier)
        identifier = re.sub(r"\/.*", "", identifier)
        identifiers_sanitized.append(identifier)

    return identifiers_sanitized


def build_query_for_single_params(**kwargs):
    """Constructs a query string from single-value parameters, where each parameter
    is formatted as `key:value`. Only parameters with non-empty values are included.

    Args:
        **kwargs: Key-value pairs representing parameter names and their values.

    Returns:
        str: A query string with key-value pairs separated by spaces.

    """
    query_string = ""
    for param_name, param_value in kwargs.items():
        if param_value:
            query_string += f"{param_name}:{param_value} "

    return query_string


def build_query_for_collection_params(**kwargs):
    """Constructs a query string from collection-based parameters, where each value
    in the collection is formatted as `key:value`. Only non-empty collections are
    included.

    Args:
        **kwargs: Key-value pairs where values are lists or iterables of parameter
                values.

    Returns:
        str: A query string with key-value pairs for all items in the collections,
             separated by spaces.

    """
    query_string = ""
    for param_name, param_values in kwargs.items():
        if param_values:
            for param_value in param_values:
                query_string += f"{param_name}:{param_value} "

    return query_string


def build_query_string(
    entity_name: list[str],
    issue_ids: list[str],
    entity_ids: list[str],
    tags: list[str],
    time_parameter: str,
    start_time: str,
    end_time: str,
    status: str,
    lowest_severity: int,
) -> str:
    """Build query string for GTI ASM.

    Args:
         entity_name: {List[str]} Entity names list
         issue_ids: {List[str]} List of issue ids
         entity_ids: {List[str]} List of entity ids
         tags: {List[str]} List of entity tags
         time_parameter: {str} Time parameter to Last seen / First seen
         start_time: {str} Start time for period
         end_time: {str} End time for period
         status: {str} Status to filter out by
         lowest_severity: {int} lowest severity

    Returns:
        {str} query string to use in filter

    """
    query_string = ""
    time_kwargs = {}

    if time_parameter == "First Seen":
        time_kwargs = {
            "first_seen_before": end_time,
            "first_seen_after": start_time,
        }
    elif time_parameter == "Last Seen":
        time_kwargs = {
            "last_seen_before": end_time,
            "last_seen_after": start_time,
        }

    query_string += build_query_for_single_params(
        status_new=status, severity_lte=lowest_severity, **time_kwargs
    )

    query_string += build_query_for_collection_params(
        entity_name=sanitize_identifiers(entity_name) if entity_name else [],
        id=issue_ids,
        entity_uid=entity_ids,
        tag=tags,
    )

    return query_string


def build_asm_entity_query_string(
    names,
    tags,
    minimum_vulns,
    minimum_issues,
    critical_or_high,
):
    """Builds a query string for ASM entities based on provided criteria.

    Args:
        names {List[str]}: A list of entity names to include in the query.
        tags {List[str]}: A list of tags to include in the query.
        minimum_vulns (int): The minimum number of vulnerabilities to filter by.
        minimum_issues (int): The minimum number of issues to filter entities.
        critical_or_high (bool): Whether to filter entities with critical or high
                                severity issues.

    Returns:
        str: A query string based on the provided parameters. Defaults to
             "last_seen_after:last_refresh" if no valid query criteria are specified

    """
    query_string = ""
    query_string += build_query_for_single_params(
        vuln_count_gte=minimum_vulns,
        issue_count_gte=minimum_issues,
        critical_or_high="true" if critical_or_high else "",
    )
    query_string += build_query_for_collection_params(
        name=sanitize_identifiers(names) if names else [], tag=tags
    )
    if query_string:
        return query_string

    return "last_seen_after:last_refresh"
