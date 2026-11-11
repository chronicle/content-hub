from __future__ import annotations

import base64
import contextlib
import html
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from functools import partial
from typing import Any, Callable
from urllib.parse import ParseResult, urlparse

from bs4 import BeautifulSoup, Tag
from requests import Response, Session
from requests.structures import CaseInsensitiveDict
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon.base.interfaces import Logger
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.types import Entity, SingleJson
from TIPCommon.utils import get_entity_original_identifier

from google_threat_intelligence.core.constants import (
    ASM_ISSUES_WINDOW_WALK_TIMEOUT_THRESHOLD,
    DOC_KEY,
    EMAIL_ENTITY_TYPE,
    EMAIL_REGEX,
    PASSWORD_KEY,
    PASSWORD_MASK_CHAR,
    PLAIN_TEXT_KEY,
    SERVICE_ACCOUNT_KEY,
    SUSPICIOUS_VERDICTS,
)
from google_threat_intelligence.core import data_models

from google_threat_intelligence.core.data_models import ThreatActor
from google_threat_intelligence.core.exceptions import GoogleThreatIntelligenceExceptions, PathNotExistException

SEVERITY_DICT = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "UNKNOWN": 0}
ASSET_CACHE = {}


def get_entity_type(entity: Entity) -> str:
    """Helper function to get entity type

    Args:
        entity (Entity): entity to get type from

    Returns:
        str: entity type

    """
    if (
        re.search(EMAIL_REGEX, get_entity_original_identifier(entity))
        and entity.entity_type == EntityTypes.USER
    ):
        return EMAIL_ENTITY_TYPE

    return entity.entity_type


def prepare_hash_identifier(identifier: str) -> str:
    """Normalized the given identifier by converting it to lowercase.

    Args:
        identifier: The input identifier string.

    Returns:
        str: The normalized lowercase identifier.

    """
    return identifier.lower()


def prepare_entity_for_manager(entity: Entity) -> str:
    """Prepare an entity's identifier for the manager based on its type.

    Args:
        entity: The Entity object.

    Results:
        str: A processed entity identifier string.

    """
    identifier = get_entity_original_identifier(entity)

    if entity.entity_type == EntityTypes.URL:
        return encode_url(identifier)

    if entity.entity_type in [
        EntityTypes.FILEHASH,
        EntityTypes.CHILDHASH,
        EntityTypes.PARENTHASH,
    ]:
        return prepare_hash_identifier(identifier)

    return identifier


def encode_url(url):
    return base64.urlsafe_b64encode(url.encode()).decode().strip("=")


def get_next_page_url(headers: CaseInsensitiveDict[str]) -> str:
    """Get next page url from response headers

    Args:
        headers (CaseInsensitiveDict[str]): response headers

    Returns:
        str: next page url

    """
    # extract next page url from response link header
    matches = re.findall(r"<(.*?)>", headers.get("link", ""))
    return matches[0] if matches else None


def adjust_time(
    time_str: str,
    hours: float = 6,
    now: datetime | None = None,
) -> datetime:
    """Adjusts the given time by adding the given amount of hours (6 by default).
    If the result is greater than the current time, return the current time.

    Args:
        time_str: Input time in format 'YYYY-MM-DDTHH:MM:SSZ'.
        hours: Amount of hours to add to the given time.
        now: Reference current UTC time. Defaults to utcnow().

    Returns:
        Adjusted time as a datetime object.

    """
    given_time: datetime = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
    updated_time: datetime = given_time + timedelta(hours=hours)
    now_time: datetime = now if now is not None else datetime.utcnow()

    return min(updated_time, now_time)


def get_search_window_total(search_result: SingleJson) -> int:
    """Returns the amount of issues an ASM search window holds.

    The live API reports it in `total_hits`; `total` is accepted as a
    fallback and the size of the fetched page is used as a last resort.

    Args:
        search_result: The `result` object of a search page.

    Returns:
        Amount of issues in the window.

    """
    for key in ("total_hits", "total"):
        total: int | None = search_result.get(key)
        if isinstance(total, int) and not isinstance(total, bool):
            return total

    return len(search_result.get("hits", []))


def is_window_walk_timeout(
    connector_starting_time: int | None,
    python_process_timeout: int | None,
) -> bool:
    """Checks whether the connector is close enough to its timeout to stop
    walking through empty search windows, leaving time to process issues.

    Args:
        connector_starting_time: Connector start time in unix ms.
        python_process_timeout: Connector timeout in seconds.

    Returns:
        True if the window walk should stop, False otherwise.

    """
    if connector_starting_time is None or python_process_timeout is None:
        return False

    return is_approaching_timeout(
        connector_starting_time,
        python_process_timeout,
        timeout_threshold=ASM_ISSUES_WINDOW_WALK_TIMEOUT_THRESHOLD,
    )


def get_threat_actor_id_by_origin(threat_actors: list[ThreatActor]) -> str:
    """Returns the ID of the first object with origin "Google Threat Intelligence".

    If not found, returns the first object with origin "Partner".
    If neither exists, returns the ID of the first object in the list.
    """
    id_from_gti = None
    community_id = None

    for threat_actor in threat_actors:
        if threat_actor.origin == "Google Threat Intelligence":
            return threat_actor.id
        if threat_actor.origin == "Partner" and community_id is None:
            community_id = threat_actor.id
        if id_from_gti is None:
            id_from_gti = threat_actor.id

    return community_id if community_id is not None else id_from_gti


def get_threat_actor_by_origin(threat_actors: list[ThreatActor]) -> ThreatActor:
    """Returns the object with origin "Google Threat Intelligence".

    If not found, returns the first object with origin "Partner".
    If neither exists, returns the object in the list.

    Args:
        threat_actors: List of ThreatActor objects.

    Returns:
        ThreatActor: The ThreatActor object based on the specified logic.

    """
    from_gti = None
    community = None

    for threat_actor in threat_actors:
        if threat_actor.origin == "Google Threat Intelligence":
            return threat_actor
        if threat_actor.origin == "Partner" and community is None:
            community = threat_actor
        if from_gti is None:
            from_gti = threat_actor

    return community if community is not None else from_gti


class WidgetComponentPreprocessor:
    def __init__(self, widget_url: str, session: Session) -> None:
        """
        Fetches and prepares widget from GoogleThreatIntelligence service
        Args:
            widget_url (str) Base: url to fetch widget
            session (Session): call request session
        Returns:
            GoogleThreatIntelligenceWidget
        """
        self.widget_url = widget_url
        api_root: ParseResult = urlparse(widget_url)
        self.api_root: str = f"{api_root.scheme}://{api_root.netloc}"
        self.session = session

    def prepare_cached_widget(self) -> str:
        """Fetching widget and tripping the excessive data from html.

        Args:
        Returns:
            str: Modified html widget html content
        """

        root_html = self._fetch_from_url(self.widget_url, cacheable=False).text.replace(
            "Enriched by", "Cached Widget"
        )
        parsed_html = BeautifulSoup(root_html, "html.parser")
        self._inline_stylesheet(parsed_html)
        self._inline_scripts(parsed_html)
        self._inline_images(parsed_html)
        self._remove_redundant_components(parsed_html)

        # Add Google Fonts CDN link to head for styling
        head = parsed_html.head or parsed_html.find("head")
        if not head and parsed_html.html:
            head = parsed_html.new_tag("head")
            parsed_html.html.insert(0, head)
        if head:
            link_tag = parsed_html.new_tag(
                "link",
                rel="stylesheet",
                href=(
                    "https://fonts.googleapis.com/css?family=Open+Sans:300,400,"
                    "500,600,700,800|Source+Sans+Pro:300,400,600,700&display=swap"
                ),
            )
            head.append(link_tag)

        return html.escape(str(parsed_html))

    def _inline_stylesheet(self, parsed_html: BeautifulSoup):
        """
        Finds stylesheet links in html and replaces them with fetched stylesheets
        Args:
            parsed_html: Input DOM
        """

        for node in parsed_html.find_all("link", rel="stylesheet"):
            url = f"{self.api_root}{node.get('href')}"
            stylesheet_content = self._fetch_from_url(url).text

            # Remove @font-face rules entirely to prevent loading local fonts (avoiding CORS and bloat)
            stylesheet_content = re.sub(
                r"@font-face\s*\{[^}]*\}", "", stylesheet_content
            )

            inlined = f"<style>\n{stylesheet_content}\n</style>"
            inlined = BeautifulSoup(inlined, "html.parser")
            node.replace_with(inlined)

    def _inline_scripts(self, parsed_html: BeautifulSoup):
        """
        Finds JS script links in html and removes (decomposes) them.
        This keeps the cached widget extremely lightweight (under 150KB)
        while maintaining a perfect static preview layout.
        Args:
            parsed_html: Input DOM
        """
        for node in parsed_html.find_all("script"):
            if node.get("src"):
                node.decompose()

    def _inline_images(self, parsed_html: BeautifulSoup):
        """
        Finds images in html and replaces them with fetched images converted to base64
        Args:
            parsed_html: Input DOM
        """
        for node in parsed_html.find_all("img"):
            if (
                not node.get("src")
                or node.get("src").startswith("data:")
                or node.get("src").startswith("http")
            ):
                continue
            url = f"{self.api_root}{node.get('src')}"
            image = self._fetch_from_url(url).content
            image_b64 = base64.b64encode(image).decode()
            node["src"] = f"data:image/png;base64,{image_b64}"

    @staticmethod
    def _remove_redundant_components(parsed_html: BeautifulSoup):
        """
        Removes parts that does not need to be presented in output widget;
        - navbar
        - base tag
        - favicon
        Args:
            parsed_html: Input DOM
        """

        def decompose_if_present(component: Tag) -> None:
            if component:
                component.decompose()

        decompose_if_present(parsed_html.find("ul", {"class": "nav-tabs"}))
        decompose_if_present(parsed_html.find("base"))
        decompose_if_present(parsed_html.find("link", rel="icon"))

    def _fetch_from_url(self, url: str, cacheable: bool = True) -> Response:
        """Fetch contents from given url.

        Args:
            url (str): url to fetch
            cacheable (bool): whether to cache this request

        Returns:
            requests.Response
        """
        if cacheable:
            if url in ASSET_CACHE:
                return ASSET_CACHE[url]

            response = self.session.get(
                url,
                headers={
                    "Content-Type": "text/html",
                },
            )
            ASSET_CACHE[url] = response
            return response

        return self.session.get(
            url,
            headers={
                "Content-Type": "text/html",
            },
        )


def get_highest_severity(signature_list) -> str:
    """Get the Highest Severity available in mitre technique.

    Args:
        signature_list: It takes signature list in mitre technique

    Returns:
        str: Return Highest severity in signature list in mitre technique

    """
    for p in SEVERITY_DICT:
        if p in signature_list:
            return p
    return " ".join([str(elem) for elem in list(SEVERITY_DICT)[-1:]])


def compare_severity(technique_severity: str, lowest_mitre_technique: str):
    """Check the item severity should be greater than lowest mitre technique.

    Args:
        lowest_mitre_technique: It takes severity input as a parameter
        technique_severity: sealing severity value of mitre technique
    Returns:
        bool: Return true if item severity is higher or equal else return false

    """
    return SEVERITY_DICT[technique_severity] >= SEVERITY_DICT[lowest_mitre_technique]


def remove_duplicate_mitre(json_data: list[dict]) -> list[dict]:
    """Remove duplicate items from the json response.

    Args:
        It takes Json response and filter out duplicate items
    Returns:
        list: Returns list of unique mitre technique

    """
    unique_identifier = set()
    unique_data = []

    for data in json_data:
        identifier = (data["id"], data["severity"])
        if identifier not in unique_identifier:
            unique_identifier.add(identifier)
            unique_data.append(data)
    sorted_data = sorted(
        unique_data, key=lambda d: SEVERITY_DICT[d["severity"]] + 1, reverse=True
    )
    return sorted_data


def fetch_mitre_data(raw_data, lowest_mitre_technique_severity):
    """Extracts MITRE tactics/techniques, filtering by severity."""
    related_mitre_tactics = []
    related_mitre_techniques = []
    mitre_date = {}
    try:
        raw_data = raw_data.get("data")

        tactics_unique_identifier = set()
        my_tactics = []
        my_techniques = []

        for key in raw_data:
            my_tactics.extend(raw_data.get(key, {}).get("tactics", []))

        # Fetching mitre tactics
        for tactic in my_tactics:
            tactics_json = {
                "id": tactic.get("id", ""),
                "name": tactic.get("name", ""),
            }
            identifier = tactics_json["id"]
            if identifier not in tactics_unique_identifier:
                tactics_unique_identifier.add(identifier)
                related_mitre_tactics.append(tactics_json)
            my_techniques.extend(tactic.get("techniques", []))

        # Fetching mitre techniques
        for technique in my_techniques:
            signature = technique.get("signatures", [])
            severities = [
                severity_value.get("severity", {}) for severity_value in signature
            ]
            highest_severity = get_highest_severity(severities)
            if compare_severity(highest_severity, lowest_mitre_technique_severity):
                techniques_json = {
                    "id": technique.get("id", ""),
                    "name": technique.get("name", ""),
                    "severity": highest_severity,
                }
                related_mitre_techniques.append(techniques_json)
        related_mitre_techniques = remove_duplicate_mitre(related_mitre_techniques)
        status = "completed"
        mitre_date = {
            "raw_data": raw_data,
            "status": status,
            "mitre_tactics": related_mitre_tactics,
            "mitre_techniques": related_mitre_techniques,
        }
    except (AttributeError, TypeError):
        status = "failed"
        mitre_date = {
            "raw_data": raw_data,
            "status": status,
            "mitre_tactics": related_mitre_tactics,
            "mitre_techniques": related_mitre_techniques,
        }

    return mitre_date


def convert_days_to_milliseconds(days: int) -> int:
    """Convert days to milliseconds.

    Args:
        days: {int} days to convert
    Returns:
        int: converted milliseconds

    """
    return days * 24 * 60 * 60 * 1000


def clean_file_path(file_path: str) -> str:
    """Remove the surrounding quotes and whitespace from a file path."""
    return file_path.strip("'\"").strip()


def verify_paths_accessibility(file_paths: list[str], logger: Logger) -> None:
    """
    Verifies file accessibility by attempting to open them.

    Uses `contextlib.ExitStack` to guarantee that a dynamic number of
    successfully opened files are all properly closed.
    Raises an exception on failure.

    Args:
      file_paths: A list of file paths to check.
      logger: A logger for recording I/O errors.

    Returns:
      None

    """
    with contextlib.ExitStack() as stack:
        error_report = defaultdict(list)
        for file_path in file_paths:
            try:
                stack.enter_context(open(file_path, "rb"))
            except FileNotFoundError as e:
                logger.error(e, exc_info=True)
                msg = (
                    "The following files were not found: {paths}. "
                    "Please check the spelling."
                )
                error_report[msg].append(file_path)
            except OSError as e:
                logger.error(e, exc_info=True)
                msg = (
                    "Error reading files at {paths}. Please check the spelling "
                    "and the application has permissions to access it."
                )
                error_report[msg].append(file_path)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(e, exc_info=True)
                msg = "An unexpected error occurred during reading files at: {paths}"
                error_report[msg].append(file_path)

        if error_report:
            msg = "\n".join(
                [
                    msg.format(paths=", ".join(file_paths))
                    for msg, file_paths in error_report.items()
                ]
            )
            raise GoogleThreatIntelligenceExceptions(msg)


def map_by_case_insensitive_keys(keys: list[str], mapping: dict[str, str]) -> list[str]:
    """
    Maps a list of strings to new values using a case-insensitive mapping.

    This function validates each item against the mapping's keys. If any
    items are not found, it raises a ValueError.

    Args:
        keys: A list of strings to be mapped (e.g., from user input).
        mapping: The dictionary mapping original names to new values.

    Returns:
        A list of validated, mapped values.

    Raises:
        ValueError: If any of the provided items are not in the mapping.
    """
    lowercase_mapping = {key.lower(): value for key, value in mapping.items()}

    mapped_items = []
    invalid_items = []

    for key in keys:
        key_lower = key.lower()

        if key_lower in lowercase_mapping:
            mapped_items.append(lowercase_mapping[key_lower])
        else:
            invalid_items.append(key)

    if invalid_items:
        available_options = ", ".join(f"'{key}'" for key in mapping.keys())
        raise ValueError(f"Available options are: [{available_options}]")

    return mapped_items


def save_file(path, name: str, content: str) -> str:
    """Saves file content to a local file.

    Args:
        path: The directory path where the file should be saved.
        name: The filename to use.
        content: The file content to write.

    Returns:
        str: The full local path to the saved file.

    Raises:
        PathNotExistException: If the specified directory path does not exist.

    """
    if not os.path.exists(path):
        raise PathNotExistException(f"Folder {path} not found.")

    local_path = os.path.join(path, name)
    with open(local_path, "wb") as file:
        file.write(content.encode(encoding="UTF-8"))

    return local_path


def prepare_ioc_for_manager(ioc, ioc_type) -> str:
    """Prepares an Indicator of Compromise (IOC) for a manager.

    Transforms IOCs based on their type, such as URL encoding.

    Args:
        ioc (str): The IOC string.
        ioc_type (str): The type of the IOC (e.g., "URL").

    Returns:
        str: The transformed IOC string.

    """
    if ioc_type == "URL":
        return encode_url(ioc)

    return ioc


def parse_entity_filters(
    filters: set[str],
) -> tuple[set[str], set[str]]:
    """Parses an event type filter list into allow and block sets.

    Args:
        filters (list): The list of event filters, e.g., "typeA, !typeB, typeC".

    Returns:
        A tuple containing two sets: (allow_list, block_list).
    """

    allow_list = set()
    block_list = set()

    for event_type in filters:
        if event_type.startswith("!"):
            block_list.add(event_type.lstrip("!").strip())
        else:
            allow_list.add(event_type)

    return allow_list, block_list


def prepare_entity_filter(
    extractor: Callable[[Any], str] = lambda x: x,
    allow_list: set[Any] = None,
    block_list: set[Any] = None,
) -> Callable[[Any], bool]:
    """
    Creates a filter that allows all items from whitelist, and drops all items
    from block_list.
    If allow_list has at least 1 element then no item from block_list is considered.
    If neither allow_list nor black_list has any elements then input value is returned.

    Args:
        extractor: Function to extract value to identify in either of lists
        allow_list: Allowed elements
        block_list: Disallowed elements
    """

    def _filter(entity: Any):
        entity = extractor(entity)
        return entity in allow_list if allow_list else entity not in block_list

    return _filter


def anonymize_password(password: str) -> str:
    """Mask a password, keeping only its first and last characters.

    Args:
        password: Password string to anonymize.

    Returns:
        Anonymized password string.

    """
    length = len(password)
    if length <= 2:
        return PASSWORD_MASK_CHAR * length

    return f"{password[0]}{PASSWORD_MASK_CHAR * (length - 2)}{password[-1]}"


def anonymize_compromised_credentials(alert_data: SingleJson) -> None:
    """Mask doc.service_account.password.plain_text of a DTM alert in place.

    Args:
        alert_data: Alert raw data dictionary to modify in-place.

    """
    doc = alert_data.get(DOC_KEY)
    service_account = (
        doc.get(SERVICE_ACCOUNT_KEY) if isinstance(doc, dict) else None
    )
    password_obj = (
        service_account.get(PASSWORD_KEY)
        if isinstance(service_account, dict)
        else None
    )
    if isinstance(password_obj, dict) and isinstance(
        password_obj.get(PLAIN_TEXT_KEY), str
    ):
        password_obj[PLAIN_TEXT_KEY] = anonymize_password(
            password_obj[PLAIN_TEXT_KEY]
        )


class Enricher:
    def __init__(self, api_client, logger):
        self.api_client = api_client
        self.logger = logger

    def get_sandbox_response(
        self,
        entity_identifier: str,
        sandboxes: list,
    ) -> dict[str, data_models.Sandbox | None]:
        """Retrieve sandbox response data for a given entity from list of sandboxes.

        Args:
            entity_identifier: The identifier of the entity.
            sandboxes: A list of sandbox names.

        Returns:
            Dict[str, Optional[datamodels.Sandbox]]:A mapping of
            sandbox names to data or None on error.

        """
        sandboxes_data = {}
        for sandbox in sandboxes:
            try:
                sandboxes_data[sandbox] = self.api_client.get_sandbox_data(
                    entity_identifier, sandbox, show_entity_status=True
                )
            except GoogleThreatIntelligenceExceptions as err:
                self.logger.error(
                    f"Error retrieving sandbox data for {entity_identifier} "
                    f"and sandbox {sandbox}: {err}"
                )
                sandboxes_data[sandbox] = None
        return sandboxes_data

    def get_mitre_response(
        self,
        entity_identifier: str,
        lowest_mitre_severity: str,
    ) -> data_models.Mitre | None:
        """Get MITRE response for a given entity identifier.

        Args:
            entity_identifier: The identifier of the entity.
            lowest_mitre_severity: The lowest severity level
            to use when querying MITRE data.

        Returns:
           Optional[datamodels.Mitre]: MITRE response data or None if an error occurs.

        """
        try:
            return self.api_client.get_mitre(
                file_hash=entity_identifier,
                show_entity_status=True,
                lowest_mitre_severity=lowest_mitre_severity,
            )
        except GoogleThreatIntelligenceExceptions as err:
            self.logger.error(
                f"Error retrieving MITRE data for {entity_identifier}: {err}"
            )
            return None


def _log_risk_assessment_result(logger, method: str, result: bool, **params) -> None:
    """Log the result of a risk assessment method.

    Args:
        logger: The logger.
        method: The name of the assessment method.
        result: The result of the assessment.
        **params: Additional parameters used in the assessment.

    """
    params_str = ", ".join(f"{k}: {v}" for k, v in params.items())
    logger.info(
        f"Risk assessment method: {method}. Result: {result}. Parameters: {params_str}"
    )


def _is_risky_by_engine_count(malicious_count: int, engine_threshold: int) -> bool:
    """Check risk based on engine count threshold."""
    return malicious_count >= engine_threshold


def _is_risky_by_engine_percentage_metrics(
    malicious_count: int,
    total_count: int,
    engine_percentage_threshold: int,
) -> bool:
    """Check risk based on engine percentage threshold."""
    malicious_percentage = (malicious_count / total_count) * 100
    malicious_percentage = math.ceil(malicious_percentage)
    return malicious_percentage >= engine_percentage_threshold


def _get_malicious_and_total_counts(
    ioc_data: data_models.IOC, engine_allowlist: list[str] | None, logger: Logger
) -> tuple[int, int]:
    """Get malicious and total engine result counts."""
    engine_results = ioc_data.last_analysis_results.values()
    if engine_allowlist:
        logger.info(f"Filtering with allowlist: {engine_allowlist}")
        engine_results = filter(
            lambda v: v.get("engine_name") in engine_allowlist,
            engine_results,
        )

    categories = map(lambda v: v.get("category"), engine_results)
    counted_results = Counter(categories)
    malicious_results_count = counted_results.get("malicious", 0)

    try:
        total_results = counted_results.total()
    except AttributeError:  # fallback for python < 3.10
        total_results = sum(counted_results.values())

    return malicious_results_count, total_results


def _is_risky_by_gti_score(
    ioc_data: data_models.IOC, gti_score: int | None, logger: Logger
) -> bool:
    """Assess risk based on GTI Score."""
    if gti_score is None:
        return False

    result = ioc_data.threat_score >= gti_score
    _log_risk_assessment_result(
        logger,
        method="GTI Score",
        result=result,
        threat_score=ioc_data.threat_score,
        threshold=gti_score,
    )
    return result


def _is_risky_by_engine_threshold(
    ioc_data: data_models.IOC,
    engine_threshold: int | None,
    engine_allowlist: list[str] | None,
    logger: Logger,
) -> bool:
    """Assess risk based on engine count threshold."""
    if engine_threshold is None:
        return False

    malicious_count, total_count = _get_malicious_and_total_counts(
        ioc_data, engine_allowlist, logger
    )

    if total_count == 0:
        return False

    result = _is_risky_by_engine_count(malicious_count, engine_threshold)
    _log_risk_assessment_result(
        logger,
        method="Engine Count Threshold",
        result=result,
        malicious_count=malicious_count,
        total_count=total_count,
        threshold=engine_threshold,
        engine_allowlist=engine_allowlist,
    )
    return result


def _is_risky_by_engine_percentage(
    ioc_data: data_models.IOC,
    engine_percentage_threshold: int | None,
    engine_allowlist: list[str] | None,
    logger: Logger,
) -> bool:
    """Assess risk based on engine percentage threshold."""
    if engine_percentage_threshold is None:
        return False

    malicious_count, total_count = _get_malicious_and_total_counts(
        ioc_data, engine_allowlist, logger
    )

    if total_count == 0:
        return False

    result = _is_risky_by_engine_percentage_metrics(
        malicious_count,
        total_count,
        engine_percentage_threshold,
    )
    _log_risk_assessment_result(
        logger,
        method="Engine Percentage Threshold",
        result=result,
        malicious_count=malicious_count,
        total_count=total_count,
        threshold=engine_percentage_threshold,
        engine_allowlist=engine_allowlist,
    )
    return result


def _is_risky_by_verdict(ioc_data: data_models.IOC, logger: Logger) -> bool:
    """Assess risk based on verdict."""
    result = ioc_data.verdict in SUSPICIOUS_VERDICTS
    _log_risk_assessment_result(
        logger,
        method="Verdict",
        result=result,
        verdict=ioc_data.verdict,
    )
    return result


def assess_risk(
    ioc_data: data_models.IOC,
    gti_score: int | None,
    engine_threshold: int | None,
    engine_percentage_threshold: int | None,
    engine_allowlist: list[str] | None,
    logger: Logger,
) -> bool:
    """Assess the risk of an IOC based on various criteria.

    Args:
        ioc_data: The IOC data.
        gti_score: The GTI score threshold.
        engine_threshold: The engine count threshold.
        engine_percentage_threshold: The engine percentage threshold.
        engine_allowlist: A list of allowed engines.
        logger: The logger.

    Returns:
        True if the IOC is considered risky, False otherwise.
    """
    strategies: list[Callable[[], bool]] = [
        partial(_is_risky_by_gti_score, ioc_data, gti_score, logger)
    ]

    if engine_threshold is not None:
        strategies.append(
            partial(
                _is_risky_by_engine_threshold,
                ioc_data,
                engine_threshold,
                engine_allowlist,
                logger,
            )
        )
    elif engine_percentage_threshold is not None:
        strategies.append(
            partial(
                _is_risky_by_engine_percentage,
                ioc_data,
                engine_percentage_threshold,
                engine_allowlist,
                logger,
            )
        )

    strategies.append(partial(_is_risky_by_verdict, ioc_data, logger))

    return any(strategy() for strategy in strategies)
