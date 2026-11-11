from __future__ import annotations
from enum import Enum
from scc_enterprise.core import JiraConstants


class JiraStatusCategory(Enum):
    TO_DO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


JIRA_STATUS_MAPPING = {
    "Open": JiraStatusCategory.TO_DO,
    "Assigned": JiraStatusCategory.IN_PROGRESS,
    "In Progress": JiraStatusCategory.IN_PROGRESS,
    "Resolved": JiraStatusCategory.DONE,
    "Won`t Do": JiraStatusCategory.DONE,
}

JIRA_SEVERITY_CUSTOM_FIELD = {
    "options": ["Critical", "High", "Medium", "Low", "Info"],
    "type_": "select",
    "name": "Severity",
    "searcher_key": "multiselectsearcher",
}

ISSUE_SYSTEM_FIELDS_JSON = [
    # Type specified here isn't a real field type displayed in API,
    # it's a custom field analogous
    {"type_": "userpicker", "name": "Assignee"},
    {"type_": "textfield", "name": "Summary"},
    {"type_": "textarea", "name": "Description"},
    {"options": JIRA_STATUS_MAPPING.keys(), "type_": "select", "name": "Status"},
    {
        # TODO: This is NOT what we have in Jira
        "choices": ["Time Critical", "High", "Medium", "Low"],
        "type_": "select",
        "name": "Priority",
    },
    {"type_": "datetime", "name": "Created"},
    {"type_": "datetime", "name": "Updated"},
    {"type_": "datetime", "name": "Resolved"},
    {"type_": "userpicker", "name": "Reporter"},
    {"type_": "datetime", "name": "Due date"},
]

ISSUE_CUSTOM_FIELDS_JSON = [
    {
        "type_": "textfield",
        "name": "Vulnerability Exploitation Activity",
        "searcher_key": "textsearcher",
    },
    {
        "type_": "textfield",
        "name": "Affected Organization",
        "searcher_key": "textsearcher",
    },
    {"type_": "textfield", "name": "Finding Count"},
    {
        "type_": "textfield",
        "name": "Affected Azure Resource Group",
        "searcher_key": "textsearcher",
    },
    {
        "type_": "textfield",
        "name": "Vulnerability Was Zero Day",
        "searcher_key": "textsearcher",
    },
    JIRA_SEVERITY_CUSTOM_FIELD,
    {
        "type_": "textfield",
        "name": "Vulnerability Observed in the Wild",
        "searcher_key": "textsearcher",
    },
    {
        "type_": "textfield",
        "name": "Affected Azure Subscription",
        "searcher_key": "textsearcher",
    },
    {"type_": "textfield", "name": "Finding Category", "searcher_key": "textsearcher"},
    {"type_": "textfield", "name": "Parent Type", "searcher_key": "textsearcher"},
    {
        "type_": "textfield",
        "name": "Affected Resource Types",
        "searcher_key": "textsearcher",
    },
    {
        "type_": "textfield",
        "name": "Affected AWS Account",
        "searcher_key": "textsearcher",
    },
    {
        "type_": "textfield",
        "name": "Vulnerability Impact",
        "searcher_key": "textsearcher",
    },
    {
        "options": ["Google Cloud", "AWS", "Azure", "Other"],
        "type_": "select",
        "name": "Cloud Environment",
        "searcher_key": "multiselectsearcher",
    },
    {"type_": "url", "name": "Source Link", "searcher_key": "exacttextsearcher"},
    {"type_": "textfield", "name": "Finding Class", "searcher_key": "textsearcher"},
    {"type_": "textfield", "name": "Affected Projects", "searcher_key": "textsearcher"},
]

GENERAL_FIELDS = [
    "Assignee",
    "Priority",
    "Severity",
    "Due date",
    "Cloud Environment",
    "Source Link",
    "Finding Count",
    "Affected Projects",
    "Affected Resource Types",
    "Vulnerability Impact",
    "Vulnerability Was Zero Day",
    "Vulnerability Observed in the Wild",
    "Vulnerability Exploitation Activity",
]

FIELD_TAB_FIELDS = ["Summary", "Description"]

EXTRA_TAB_FIELDS = [
    "Affected AWS Account",
    "Affected Azure Resource Group",
    "Affected Azure Subscription",
    "Affected Organization",
    "Creator",
    "Finding Category",
    "Finding Class",
    "Parent Type",
    "Resolved",
    "Reporter",
]

FIELD_TABS_MAPPING = {
    None: GENERAL_FIELDS,
    f"{JiraConstants.CUSTOM_ISSUE_TYPE_NAME} Summary": FIELD_TAB_FIELDS,
    f"{JiraConstants.CUSTOM_ISSUE_TYPE_NAME} Details": EXTRA_TAB_FIELDS,
}

FIELDS_TYPE_MAPPING = {
    "datetime": "com.atlassian.jira.plugin.system.customfieldtypes:datetime",
    "readonlyfield": "com.atlassian.jira.plugin.system.customfieldtypes:readonlyfield",
    "select": "com.atlassian.jira.plugin.system.customfieldtypes:select",
    "textfield": "com.atlassian.jira.plugin.system.customfieldtypes:textfield",
    "textarea": "com.atlassian.jira.plugin.system.customfieldtypes:textarea",
    "url": "com.atlassian.jira.plugin.system.customfieldtypes:url",
    "userpicker": "com.atlassian.jira.plugin.system.customfieldtypes:userpicker",
}
