from __future__ import annotations
from scc_enterprise.core.ServiceNowConsts import DEFAULT_VIEW
from scc_enterprise.core.ServiceNowConsts import CUSTOM_TICKET_TABLE_NAME


TABLE_FIELDS_JSON = [
    {
        "internal_type": "string",
        "element": "u_vulnerability_exploitation_activity",
        "max_length": "40",
        "column_label": "Vulnerability Exploitation Activity",
    },
    {
        "internal_type": "string",
        "element": "u_affected_organization",
        "max_length": "128",
        "column_label": "Affected Organization",
    },
    {
        "internal_type": "journal_input",
        "element": "u_additional_comments",
        "max_length": "10000",
        "column_label": "Additional Comments",
    },
    {
        "internal_type": "integer",
        "element": "u_finding_count",
        "max_length": "40",
        "column_label": "Finding Count",
    },
    {
        "internal_type": "string",
        "element": "u_affected_azure_resource_group",
        "max_length": "128",
        "column_label": "Affected Azure Resource Group",
    },
    {
        "reference": "sys_user",
        "internal_type": "reference",
        "element": "u_assigned_to",
        "max_length": "32",
        "mandatory": "true",
        "column_label": "Assigned To",
    },
    {
        "internal_type": "string",
        "element": "u_ticket_name",
        "max_length": "256",
        "mandatory": "true",
        "column_label": "Ticket Name",
    },
    {
        "internal_type": "string",
        "element": "u_vulnerability_was_zero_day",
        "max_length": "40",
        "column_label": "Vulnerability Was Zero Day",
    },
    {
        "internal_type": "html",
        "element": "u_overview",
        "max_length": "100000",
        "column_label": "Overview",
    },
    {
        "choices": ["Critical", "High", "Medium", "Low", "Info"],
        "internal_type": "string",
        "element": "u_severity",
        "max_length": "128",
        "mandatory": "true",
        "column_label": "Severity",
        "default_value": "Medium",
        "choice": "3",
    },
    {
        "internal_type": "string",
        "element": "u_vulnerability_observed_in_the_wild",
        "max_length": "40",
        "column_label": "Vulnerability Observed in the Wild",
    },
    {
        "internal_type": "string",
        "element": "u_affected_azure_subscription",
        "max_length": "128",
        "column_label": "Affected Azure Subscription",
    },
    {
        "internal_type": "string",
        "element": "u_finding_category",
        "max_length": "128",
        "column_label": "Finding Category",
    },
    {
        "internal_type": "string",
        "element": "u_parent_type",
        "max_length": "128",
        "column_label": "Parent Type",
    },
    {
        "choices": ["Open", "Assigned", "In Progress", "Resolved", "Won`t Do"],
        "internal_type": "string_full_utf8",
        "element": "u_status",
        "max_length": "40",
        "mandatory": "true",
        "column_label": "Status",
        "choice": "3",
    },
    {
        "internal_type": "string",
        "element": "u_affected_resource_types",
        "max_length": "128",
        "column_label": "Affected Resource Types",
    },
    {
        "internal_type": "string",
        "element": "u_affected_aws_account",
        "max_length": "128",
        "column_label": "Affected AWS Account",
    },
    {
        "internal_type": "string",
        "element": "u_vulnerability_impact",
        "max_length": "40",
        "column_label": "Vulnerability Impact",
    },
    {
        "choices": ["Google Cloud", "AWS", "Azure", "Other"],
        "internal_type": "string",
        "element": "u_cloud_environment",
        "max_length": "40",
        "mandatory": "true",
        "column_label": "Cloud Environment",
        "choice": "1",
    },
    {
        "internal_type": "url",
        "element": "u_source_link",
        "max_length": "256",
        "column_label": "Source Link",
    },
    {
        "choices": ["Time Critical", "High", "Medium", "Low"],
        "internal_type": "string",
        "element": "u_priority",
        "max_length": "128",
        "mandatory": "true",
        "column_label": "Priority",
        "default_value": "Medium",
        "choice": "3",
    },
    {
        "internal_type": "string",
        "element": "u_finding_class",
        "max_length": "128",
        "column_label": "Finding Class",
    },
    {
        "internal_type": "glide_date_time",
        "element": "u_due_date",
        "max_length": "40",
        "mandatory": "true",
        "column_label": "Due Date",
    },
    {
        "internal_type": "glide_date_time",
        "element": "u_closed",
        "max_length": "40",
        "read_only": "true",
        "mandatory": "false",
        "column_label": "Closed",
    },
    {
        "internal_type": "string",
        "element": "u_affected_projects",
        "max_length": "128",
        "column_label": "Affected Projects",
    },
]

FORM_SUMMARY_SECTION_FIELDS = [
    "u_ticket_name",
    "u_overview",
    "u_additional_comments",
    {
        "sys_ui_formatter": "Activities (filtered)",
        "element": "activity.xml",
        "type": "formatter",
    },
]

FORM_DETAILS_SECTION_FIELDS = [
    "sys_created_on",
    "u_due_date",
    "sys_created_by",
    "u_assigned_to",
    "u_affected_resource_types",
    "u_affected_projects",
    "sys_updated_on",
    ".split",
    "u_status",
    "u_severity",
    "u_priority",
    "u_cloud_environment",
    "u_finding_count",
    "u_source_link",
    "u_closed",
]

VIEW_SECTIONS_MAPPING = {
    DEFAULT_VIEW: [
        {
            "name": CUSTOM_TICKET_TABLE_NAME,
            "position": "0",
            "fields": FORM_DETAILS_SECTION_FIELDS,
        },
        {"name": "Summary", "position": "1", "fields": FORM_SUMMARY_SECTION_FIELDS},
    ]
}

VIEW_LIST_MAPPING = {
    DEFAULT_VIEW: [
        "u_ticket_name",
        "u_status",
        "u_priority",
        "u_severity",
        "u_assigned_to",
        "u_cloud_environment",
        "u_due_date",
        "sys_created_on",
        "u_finding_count",
    ]
}


BUSINESS_RULES = [
    {
        "action_delete": False,
        "action_insert": True,
        "action_update": True,
        "collection": CUSTOM_TICKET_TABLE_NAME,
        "filter_condition": (
            "u_statusCHANGESTOResolved^ORu_statusCHANGESTOWon`t Do^"
            "u_statusCHANGESFROMAssigned^ORu_statusCHANGESFROMIn Progress^OR"
            "u_statusCHANGESFROMOpen^EQ"
        ),
        "name": "Set Closed",
        "template": "u_closedSAMEASsys_updated_on^EQ",
        "when": "before",
    }
]

ACTIVITY_FORMATTER_FIELDS_EXTRA = (
    "*Attachments*,*EmailCorrespondence*,*Sidebar discussion*,"
    "*EmailAutogenerated*,*Relations*,*Sidebar posted message*"
)
