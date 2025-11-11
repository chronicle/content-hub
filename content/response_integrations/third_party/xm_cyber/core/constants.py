"""Define the constants used in the integration."""

from __future__ import annotations

from soar_sdk.SiemplifyDataModel import EntityTypes

INTEGRATION_NAME = "XM Cyber"
SUPPORTED_ENTITY_TYPES = [EntityTypes.USER, EntityTypes.HOSTNAME]
# Action Names
PING_SCRIPT_NAME = f"{INTEGRATION_NAME} - Ping"

# Endpoints
PING_ENDPOINT = "/api/auth/"
PUSH_BREACH_POINT_ENDPOINT = "/api/entityInventory/applyImportedLabelsOnEntities"
ENRICH_ENTITIES_ENDPOINT = "/api/secopsPublisher/entities"

# Errors
ERRORS = {
    "API": {
        "INVALID_AUTHENTICATION": "Please check the provided Base URL or API Key and Try again.",
        "CONNECTION_ERROR": f"Connection Error - Unable to reach the {INTEGRATION_NAME} instance.",
        "UNKNOWN_ERROR": "Something went wrong - Please try again. Error: {}",
    },
    "VALIDATIONS": {
        "EMPTY_VALUE": "Value field cannot be empty.",
        "INCORRECT_PARAMETER": (
            "Parameter: {} not present in the current possible set of parameters."
        ),
        "INCORRECT_OPERATOR": "Operator: {} not allowed.",
        "ENTITY_ID_INCORRECT_OPERATOR": (
            "For entityID parameter, operator must always be 'Equals' or 'Not equal to'"
        ),
        "CONTAINS_INCORRECT_PARAMETER": (
            "For {} parameter, operator must be 'Contains' or 'Not Contains'"
        ),
        "CONTAINS_INCORRECT_OPERATOR": (
            "For {} parameter, operator cannot be 'Contains' or 'Not Contains'"
        ),
        "INCORRECT_VALUE_FOR_LIST": "For {} parameter, value must be one of {}",
        "INVALID_DATE_FORMAT": (
            "Value: {} is not a valid date format. Example date: Sat Mar 15 2025 14:55:48 GMT+0000"
        ),
        "INCORRECT_VALUE_TYPE": (
            "For boolean and string values, operator must always be 'Equals' or 'Not equal to'"
        ),
    },
    "PUSH_BREACH_POINT": {
        "MISSING_ENTITY_ID": (
            "{}: {} does not have {} field that stores the entity ID. Skipping...\n"
        ),
        "MISSING_PARAMETER": "{}: {} does not have parameter: {} . Skipping...\n",
        "TYPE_MISMATCH": (
            "Type mismatch found between values for event: {}. Actual value: {}, "
            "Expected value: {}. "
        )
        + "Skipping...\n",
        "CRITERIA_MISMATCH": (
            "{}: {} does not match the criteria. Current value: ({}). Skipping...\n"
        ),
        "FAILED": f"Failed to push attributes to the {INTEGRATION_NAME} server! Error:",
    },
    "ACTION": {
        "FAILED": f"Failed to connect to the {INTEGRATION_NAME} Integration! Error:",
    },
}
# Lists
POSSIBLE_LIST_PARAM_VALUES = {"Is Critical Asset": {"TRUE", "FALSE"}}
EXTRA_PARAMETERS = {"All", "entityID"}
ENRICHED_PARAMETERS = {
    "Affected Entities",
    "Affected Critical Assets",
    "Compromise Risk Score",
    "Is Critical Asset",
    "Choke Point Score",
    "Attacked By Techniques",
    "Labels",
    "Domain Name",
    "Enabled",
    "AD Risk to Domain",
    "AD Risky Principals",
    "AD Admins And DCs",
    "Account ID",
    "User without MFA",
    "Highly Privileged",
    "Last Activity Date",
    "Predefined Admin",
    "ARN",
    "Is External",
    "Tenant ID",
    "Tenant Name",
}
POSSIBLE_PARAMETERS = {*EXTRA_PARAMETERS, *ENRICHED_PARAMETERS}
STRINGIFIED_LIST_PARAMETERS = {"Attacked By Techniques", "Labels"}
DATE_PARAMETERS = {"Last Activity Date"}
POSSIBLE_OPERATORS = {
    "Less than": "__lt__",
    "Greater than": "__gt__",
    "Less than equal to": "__le__",
    "Greater than equal to": "__ge__",
    "Equals": "__eq__",
    "Not equal to": "__ne__",
    "Contains": "__contains__",
    "Not Contains": "__contains__",
}
CHOKE_POINT_SCORE_FIELD_NAME = "Choke Point Score Level"
COMPROMISE_RISK_SCORE_FIELD_NAME = "Compromise Risk Score Level"
# Others
ATTRIBUTE_NAME = "Google_SecOps_BP"

ENTITY_ID_FIELD = "event_principal_{}_productObjectId"
PREFIX_PARAMETER_FOR_LABELS = "event_principal_{}_attribute_labels_XM Cyber - {}"
ENRICHMENT_PREFIX = "XMC"
ENRICHED_ENTITY_ID_FIELD = f"{ENRICHMENT_PREFIX}_product_object_id"
PREFIX_PARAMETER_FOR_ENTITY_ID = ENRICHMENT_PREFIX + "_{}"
