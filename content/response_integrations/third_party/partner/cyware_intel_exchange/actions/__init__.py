from __future__ import annotations

from importlib import import_module

add_iocs_to_allowed_list = import_module(".Add IOCs to Allowed list", package=__name__)
add_note_to_iocs = import_module(".Add Note to IOCs", package=__name__)
create_intel_in_cyware_intel_exchange = import_module(
    ".Create Intel in Cyware Intel Exchange", package=__name__
)
create_task_for_iocs = import_module(".Create Task for IOCs", package=__name__)
get_allowed_iocs = import_module(".Get Allowed IOCs", package=__name__)
get_ioc_details = import_module(".Get IOC Details", package=__name__)
manage_tags_in_iocs = import_module(".Manage Tags in IOCs", package=__name__)
mark_iocs_false_positive = import_module(".Mark IOCs False Positive", package=__name__)
ping = import_module(".Ping", package=__name__)
remove_iocs_from_allowed_list = import_module(".Remove IOCs from Allowed list", package=__name__)

__all__ = [
    "add_iocs_to_allowed_list",
    "add_note_to_iocs",
    "create_intel_in_cyware_intel_exchange",
    "create_task_for_iocs",
    "get_allowed_iocs",
    "get_ioc_details",
    "manage_tags_in_iocs",
    "mark_iocs_false_positive",
    "ping",
    "remove_iocs_from_allowed_list",
]
