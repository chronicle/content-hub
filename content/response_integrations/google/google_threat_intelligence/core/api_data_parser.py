from __future__ import annotations

from typing import Any
from google_threat_intelligence.core import data_models
from google_threat_intelligence.core.constants import (
    AGENT_FINAL_RESPONSE_MESSAGE_TYPE,
    AGENT_RESPONSE_TEXT_SEPARATOR,
    AGENT_USER_MESSAGE_TYPE,
    IOC_MAPPING,
)
from TIPCommon.types import SingleJson


def build_base_object(raw_data: SingleJson) -> data_models.BaseObject:
    """Build BaseObject from JSON data

    Args:
        raw_data (SingleJson): raw JSON data

    Returns:
        data_models.BaseObject: BaseObject

    """
    return data_models.BaseObject.from_json(raw_data=raw_data)


def get_results_from_raw_data(raw_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Get results from raw data

    Args:
        raw_data (dict[str, Any]): raw JSON data

    Returns:
        list[dict[str, Any]]: list of results

    """
    return raw_data.get("data", [])


def get_next_page_url(raw_data: dict[str, Any]) -> str:
    """Get next page url from raw data

    Args:
        raw_data (dict[str, Any]): raw JSON data

    Returns:
        str: next page url

    """
    return raw_data.get("links", {}).get("next")


def build_graph_details_object(
    raw_data: dict, links_limit: int
) -> data_models.GraphDetails:
    """Build GraphDetails dataclass

    Args:
        raw_data (dict): raw data dict
        links_limit (int): maximum links amount to return

    Returns:
        data_models.GraphDetails: GraphDetails dataclass

    """
    links = (
        raw_data.get("data", {}).get("attributes", {}).get("links", [])[:links_limit]
    )
    raw_data.get("data", {}).get("attributes", {})["links"] = links

    return data_models.GraphDetails.from_json(
        raw_data=raw_data,
        links=[data_models.Link.from_json(link) for link in links],
    )


def build_graph_objects(raw_data: list[dict[str, Any]]) -> list[data_models.Graph]:
    """Build list of Graph dataclasses

    Args:
        raw_data (list[dict[str, Any]]): list of raw graphs data

    Returns:
        list[data_models.Graph]: list of Graph dataclasses

    """
    return [data_models.Graph.from_json(raw_data=item) for item in raw_data]


def build_dtm_alert_object(raw_data: dict) -> data_models.DTMAlert:
    """Build DTMAlert dataclass

    Args:
        raw_data (dict): raw data dict

    Returns:
        data_models.DTMAlert: DTMAlert dataclass

    """
    return data_models.DTMAlert.from_json(
        raw_data=raw_data, topics=raw_data.get("topics", [])
    )


def build_dtm_alert_objects(raw_data: dict) -> list[data_models.DTMAlert]:
    """Build list of Alert dataclasses

    Args:
        raw_data (dict): raw data dict

    Returns:
        data_models.DTMAlert: DTMAlert dataclass

    """
    return [
        data_models.DTMAlert.from_json(
            raw_data=item,
            topics=[data_models.Topic(topic) for topic in item.get("topics", [])],
        )
        for item in raw_data.get("alerts", [])
    ]


def build_asm_entity_object(raw_data: dict) -> data_models.ASMEntity:
    """Build ASMEntity dataclasses

    Args:
        raw_data (dict): raw data dict

    Returns:
        data_models.ASMEntity: ASMEntity dataclass

    """
    return data_models.ASMEntity.from_json(
        raw_data=raw_data.get("result", {}),
    )


def build_issue_objects(raw_data: dict) -> list[data_models.ASMIssue]:
    """Build ASMIssue dataclasses

    Args:
        raw_data (dict): raw data dict

    Returns:
        list[data_models.Issue]: list of ASMIssue dataclasses

    """
    return [data_models.ASMIssue.from_json(raw_data=item) for item in raw_data]


def build_asm_entity_objects(raw_data: dict) -> list[data_models.ASMEntity]:
    """Build list of ASMEntity dataclasses

    Args:
        raw_data (dict): raw data dict

    Returns:
        list[data_models.ASMEntity]: list of ASMEntity dataclass

    """
    return [
        data_models.ASMEntity.from_json(
            raw_data=item,
        )
        for item in raw_data
    ]


def build_asm_issue_object(issue_json: dict) -> data_models.ASMIssue:
    """Build ASMIssue dataclas

    Args:
        issue_json (dict): raw data dict

    Returns:
        data_models.ASMIssue: ASMIssue dataclass

    """
    return data_models.ASMIssue.from_json(
        raw_data=issue_json,
    )


def build_related_ioc_objects(
    raw_data: list[dict[str, Any]],
) -> list[data_models.RelatedIOC]:
    """Build list of RelatedIOC dataclasses
    Args:
        raw_data (list[dict[str, Any]]): list of raw iocs data
    Returns:
        list[data_models.RelatedIOC]: list of RelatedIOC dataclasses

    """
    return [data_models.RelatedIOC.from_json(raw_data=item) for item in raw_data]


def build_threat_actor_objects(raw_data):
    return [data_models.ThreatActor.from_json(raw_data=item) for item in raw_data]


def build_ioc_object(raw_data: SingleJson, ioc_type: str, ioc: str):
    """Build IOC dataclas

    Args:
        raw_data (dict): raw data dict
        ioc_type (str): ioc type
        ioc (str): ioc identifier
    Returns:
        data_models.IOC: IOC dataclass

    """
    ioc_type = IOC_MAPPING.get(ioc_type)
    if ioc_type == "ip-address":
        return data_models.IP.from_json(
            raw_data=raw_data.get("data", {}), ioc_type=ioc_type, ioc=ioc
        )
    if ioc_type == "url":
        return data_models.URL.from_json(
            raw_data=raw_data.get("data", {}), ioc_type=ioc_type, ioc=ioc
        )
    if ioc_type == "file":
        return data_models.Hash.from_json(
            raw_data=raw_data.get("data", {}), ioc_type=ioc_type, ioc=ioc
        )
    return data_models.Domain.from_json(
        raw_data=raw_data.get("data", {}), ioc_type=ioc_type, ioc=ioc
    )


def build_comment_objects(raw_data: dict) -> list[data_models.Comment]:
    return [data_models.Comment.from_json(raw_data=item) for item in raw_data]


def build_threat_actor_object(raw_data: SingleJson):
    return data_models.ThreatActor.from_json(raw_data=raw_data)


def build_vulnerability_obj(raw_data: SingleJson):
    return data_models.Vulnerability.from_json(
        raw_data=raw_data.get("data", {}),
    )


def build_sandbox_object(raw_data: SingleJson):
    return data_models.Sandbox.from_json(raw_data=raw_data.get("data", {}))


def build_mitre_object(raw_data: SingleJson):
    return data_models.Mitre.from_json(mitre_data=raw_data)


def get_analysis_id(raw_data: SingleJson):
    return raw_data.get("data", {}).get("id")


def get_analysis_status(raw_data: SingleJson):
    return raw_data.get("data", {}).get("attributes", {}).get("status")


def get_upload_url(raw_data):
    return raw_data.get("data", {})


def get_hash_from_url_analysis(raw_data):
    return raw_data.get("meta", {}).get("url_info", {}).get("id", "")


def get_hash_from_file_analysis(raw_data):
    url_id = get_hash_from_url_analysis(raw_data)
    if not url_id:
        return raw_data.get("meta", {}).get("file_info", {}).get("sha256", "")
    return url_id


def build_ioc_search_result_objects(
    raw_data: dict,
) -> list[data_models.IOCSearchResult]:
    return [
        data_models.IOCSearchResult.from_json(raw_data=item)
        for item in raw_data.get("data", [])
    ]


def build_notification_objects(raw_data: dict) -> list[data_models.Notification]:
    """Build list of Notification dataclasses

    Args:
        raw_data (dict): raw data dict

    Returns:
        list[data_models.Notification]: list of Notification dataclasses

    """
    return [
        data_models.Notification.from_json(raw_data=item)
        for item in raw_data.get("data", [])
    ]


def build_association_items_objects(
    raw_data: dict
) -> list[data_models.AssociationItem]:
    """Builds a list of AssociationItem objects from a raw data dictionary."""
    return [
        data_models.AssociationItem.from_dict(item) for item in raw_data
    ]


def get_agentic_session_events(raw_data: SingleJson) -> list[SingleJson]:
    """Get the events of an agentic session payload, in the order returned by the API."""
    return raw_data.get("data", {}).get("attributes", {}).get("events", [])


def build_agentic_session_object(
    raw_data: SingleJson,
    events_offset: int = 0,
) -> data_models.AgenticSession:
    """Build AgenticSession from JSON data.

    Args:
        raw_data: The agentic session payload returned by the API.
        events_offset: The number of session events that existed before the current prompt
            was submitted. Only later events are used, so an earlier answer is never returned.

    Returns:
        The agentic session with the agent's final response to the current prompt, if available.
    """
    data = raw_data.get("data", {})
    attributes = data.get("attributes", {})
    new_events = get_agentic_session_events(raw_data)[events_offset:]

    return data_models.AgenticSession(
        raw_data=raw_data,
        session_id=data.get("id", ""),
        title=attributes.get("title"),
        response_text=_get_last_final_response_text(new_events),
        is_completed=_has_final_response(new_events),
    )


def build_agentic_turn_object(raw_data: SingleJson) -> data_models.AgenticSession:
    """Build AgenticSession from the response to posting a prompt.

    The response holds only the agent events of the submitted prompt, without the user message
    or earlier turns. If it holds the whole session instead, only the events after the last user
    message are used, so an earlier answer is never returned.

    Args:
        raw_data: The agentic session payload returned when posting a prompt.

    Returns:
        The agentic session with the agent's final response to the submitted prompt, if available.
    """
    last_user_message_index = max(
        (
            index
            for index, event in enumerate(get_agentic_session_events(raw_data))
            if event.get("message_type") == AGENT_USER_MESSAGE_TYPE
        ),
        default=-1,
    )

    return build_agentic_session_object(raw_data, events_offset=last_user_message_index + 1)


def _has_final_response(events: list[SingleJson]) -> bool:
    """Check whether the events contain a final response of the agent."""
    return any(event.get("message_type") == AGENT_FINAL_RESPONSE_MESSAGE_TYPE for event in events)


def _get_last_final_response_text(events: list[SingleJson]) -> str | None:
    """Return the full markdown text of the agent's last final response.

    The agent can split one answer into several markdown widgets, for example around MITRE ATT&CK
    tree widgets, so the texts of all its markdown widgets are joined in their original order.
    """
    final_response = next(
        (
            event
            for event in reversed(events)
            if event.get("message_type") == AGENT_FINAL_RESPONSE_MESSAGE_TYPE
        ),
        {},
    )
    texts = [
        (widget["markdown_text_widget"].get("text") or "").strip()
        for widget in final_response.get("agent_final_response", {}).get("widgets", [])
        if "markdown_text_widget" in widget
    ]

    return AGENT_RESPONSE_TEXT_SEPARATOR.join(filter(None, texts)) or None
