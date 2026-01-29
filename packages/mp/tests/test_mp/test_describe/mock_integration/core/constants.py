from __future__ import annotations

import datetime
from enum import Enum
from typing import TYPE_CHECKING

from TIPCommon.base.action import EntityTypesEnum

if TYPE_CHECKING:
    from collections.abc import Mapping


# Integration Identifiers
INTEGRATION_IDENTIFIER: str = "SampleIntegration"
INTEGRATION_DISPLAY_NAME: str = "Sample Integration"

# Script Identifiers
PING_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Ping"
SIMPLE_ACTION_EXAMPLE_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Simple Action Example"
ENRICH_ENTITY_ACTION_EXAMPLE_SCRIPT_NAME: str = (
    f"{INTEGRATION_IDENTIFIER} - Enrich Entity Action Example"
)
ASYNC_ACTION_EXAMPLE_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Async Action Example"
CONNECTOR_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Simple Connector Example"
JOB_SCRIPT_NAME: str = f"{INTEGRATION_IDENTIFIER} - Simple Job Example"

# Default Configuration Parameter Values
DEFAULT_API_ROOT: str = "https://api.vatcomply.com"
DEFAULT_VERIFY_SSL: bool = True

# API Constants
ENDPOINTS: Mapping[str, str] = {
    "ping": "/rates",
    "get-base-rate": "/rates",
}

# Timeouts
REQUEST_TIMEOUT: int = 30
ASYNC_ACTION_TIMEOUT_THRESHOLD_SEC: int = 60


# Parameter Values
class DDLEnum(Enum):
    @classmethod
    def values(cls) -> list[str]:
        return [item.value for item in cls]


class CurrenciesDDLEnum(DDLEnum):
    SELECT_ONE = "Select One"
    USD = "USD"
    EUR = "EUR"
    CAD = "CAD"


class TimeFrameDDLEnum(DDLEnum):
    TODAY = "Today"
    LAST_WEEK = "Last 7 Days"
    CUSTOM = "Custom"

    def to_start_date(self) -> datetime.date:
        match self:
            case TimeFrameDDLEnum.TODAY:
                return datetime.date.today()
            case TimeFrameDDLEnum.LAST_WEEK:
                return datetime.date.today() - datetime.timedelta(days=7)
            case _:
                raise ValueError(
                    f"Cannot convert object {self} to Date object",
                )


class SupportedEntitiesEnum(DDLEnum):
    ALL = "All Entities"
    IP = "IP"
    HASH = "Hash"
    USER = "User"

    def to_entity_type_enum_list(self) -> list[EntityTypesEnum]:
        match self:
            case SupportedEntitiesEnum.IP:
                return [EntityTypesEnum.ADDRESS]
            case SupportedEntitiesEnum.HASH:
                return [
                    EntityTypesEnum.FILE_HASH,
                    EntityTypesEnum.CHILD_HASH,
                    EntityTypesEnum.PARENT_HASH,
                ]
            case SupportedEntitiesEnum.USER:
                return [EntityTypesEnum.USER]
            case SupportedEntitiesEnum.ALL:
                return list(EntityTypesEnum)
            case _:
                raise ValueError("Unfamiliar Entity type")


class AlertSeverityEnum(DDLEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"

    @property
    def severity(self) -> int:
        return ALERT_SEVERITY_MAP[self]


ALERT_SEVERITY_MAP: Mapping[AlertSeverityEnum, int] = {
    AlertSeverityEnum.CRITICAL: 100,
    AlertSeverityEnum.HIGH: 80,
    AlertSeverityEnum.MEDIUM: 60,
    AlertSeverityEnum.LOW: 40,
    AlertSeverityEnum.INFORMATIONAL: -1,
}

DEFAULT_VENDOR: str = "Sample Project"
DEFAULT_PRODUCT: str = "Exchange"
ALERT_NAME_FORMAT: str = "{date} : {base}"
ALERT_NAME_EXCHANGE_FORMAT: str = "{date} : {base} - {currency}"
DISPLAY_ID_FORMAT: str = "Sample_Project_{date}_{base}"
DISPLAY_ID_EXCHANGE_FORMAT: str = "Sample_Project_{date}_{base}_{currency}"
ATTACHMENT_FILE_NAME_FORMAT: str = "{date}_{base}.json"
ATTACHMENT_FILE_NAME_EXCHANGE_FORMAT: str = "{date}_{base}_{currency}.json"
REASON: str = "This is a sample Alert reason."
DESCRIPTION: str = "This is a sample Alert description."
RULE_GENERATOR: str = "This is a sample Rule Generator."
SOURCE_GROUPING_IDENTIFIER_FORMAT: str = "{date}:{base}"
PROCESSED_CASES_LIMIT: int = 100
MIN_DAYS_BACKWARDS: int = 1
MAX_DAYS_BACKWARDS: int = 30
DATE_KEY: str = "date"
CASES_WITH_COMMENT_KEY: str = "cases_with_comment"
COMMENT_PREFIX: str = "Job Added a comment: Exchange Rate:"
CURRENCY_PAIR: str = "USD - EUR"
SIMPLE_JOB_CONTEXT_KEY: str = "simple_job_context"
CLOSED_CASE_TAG: str = "Closed"
CURRENCY_TAG: str = "Currency"
ROOT_CAUSE: str = "Other"
CLOSE_CASE_REASON: str = "Maintenance"
CLOSE_CASE_COMMENT: str = "Closed by Sample Integration Job"
