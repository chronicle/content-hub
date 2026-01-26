# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any

from ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_TIMEDOUT,
)
from SiemplifyDataModel import EntityTypes, InsightSeverity, InsightType

from ...types import Entity


class EntityTypesEnum(Enum):
    ADDRESS = EntityTypes.ADDRESS
    ALERT = EntityTypes.ALERT
    APPLICATION = EntityTypes.APPLICATION
    CHILD_HASH = EntityTypes.CHILDHASH
    CHILD_PROCESS = EntityTypes.CHILDPROCESS
    CLUSTER = EntityTypes.CLUSTER
    CONTAINER = EntityTypes.CONTAINER
    CREDIT_CARD = EntityTypes.CREDITCARD
    CVE = EntityTypes.CVE
    CVE_ID = EntityTypes.CVEID
    DATABASE = EntityTypes.DATABASE
    DEPLOYMENT = EntityTypes.DEPLOYMENT
    DESTINATION_DOMAIN = EntityTypes.DESTINATIONDOMAIN
    DOMAIN = EntityTypes.DOMAIN
    EMAIL_MESSAGE = EntityTypes.EMAILMESSAGE
    EVENT = EntityTypes.EVENT
    FILE_HASH = EntityTypes.FILEHASH
    FILE_NAME = EntityTypes.FILENAME
    GENERIC = EntityTypes.GENERIC
    HOST_NAME = EntityTypes.HOSTNAME
    IP_SET = EntityTypes.IPSET
    MAC_ADDRESS = EntityTypes.MACADDRESS
    PARENT_HASH = EntityTypes.PARENTHASH
    PARENT_PROCESS = EntityTypes.PARENTPROCESS
    PHONE_NUMBER = EntityTypes.PHONENUMBER
    POD = EntityTypes.POD
    PROCESS = EntityTypes.PROCESS
    SERVICE = EntityTypes.SERVICE
    SOURCE_DOMAIN = EntityTypes.SOURCEDOMAIN
    THREAT_ACTOR = EntityTypes.THREATACTOR
    THREAT_CAMPAIGN = EntityTypes.THREATCAMPAIGN
    THREAT_SIGNATURE = EntityTypes.THREATSIGNATURE
    URL = EntityTypes.URL
    USB = EntityTypes.USB
    USER = EntityTypes.USER


class CaseStage(Enum):
    TRIAGE = "Triage"
    ASSESSMENT = "Assessment"
    INVESTIGATION = "Investigation"
    INCIDENT = "Incident"
    IMPROVEMENT = "Improvement"
    RESEARCH = "Research"


class CasePriority(Enum):
    INFORMATIONAL = 0
    LOW = 40
    MEDIUM = 60
    HIGH = 80
    CRITICAL = 100


class CloseCaseOrAlertReasons(Enum):
    MALICIOUS = 0
    NOT_MALICIOUS = 1
    MAINTENANCE = 2
    INCONCLUSIVE = 3


class CloseCaseOrAlertMaliciousRootCauses(Enum):
    EXTERNAL_ATTACK = "External attack"
    INFRASTRUCTURE_ISSUE = "Infrastructure issue"
    IRRELEVANT_TCP_UDP_PORT = "Irrelevant TCP/UDP port"
    MISCONFIGURED_SYSTEM = "Misconfigured system"
    OTHER = "Other"
    SIMILAR_CASE_IS_ALREADY_UNDER_INVESTIGATION = "Similar case is already under investigation"
    SYSTEM_CLOCKED_THE_ATTACK = "System blocked the attack"
    SYSTEM_APPLICATION_MALFUNCTION = "System/application malfunction"
    UNFORESEEN_EFFECTS_OF_CHANGE = "Unforeseen effects of change"
    UNKNOWN = "Unknown"


class CloseCaseOrAlertNotMaliciousRootCauses(Enum):
    EMPLOYEE_ERROR = "Employee error"
    HUMAN_ERROR = "Human error"
    LAB_TEST = "Lab test"
    LEGIT_ACTION = "Legit action"
    MISCONFIGURED_SYSTEM = "Misconfigured system"
    NONE = "None"
    NORMAL_BEHAVIOR = "Normal behavior"
    OTHER = "Other"
    PENETRATION_TEST = "Penetration test"
    RULE_UNDER_CONSTRUCTION = "Rule under construction"
    SIMILAR_CASE_IS_ALREADY_UNDER_INVESTIGATION = "Similar case is already under investigation"
    UNKNOWN = "Unknown"
    USER_MISTAKE = "User mistake"


class CloseCaseOrAlertMaintenanceRootCauses(Enum):
    LAB_TEST = "Lab test"
    OTHER = "Other"
    RULE_UNDER_CONSTRUCTION = "Rule under construction"


class CloseCaseOrAlertInconclusiveRootCauses(Enum):
    NO_CLEAR_CONCLUSION = "No clear conclusion"


class ExecutionState(Enum):
    COMPLETED = EXECUTION_STATE_COMPLETED
    IN_PROGRESS = EXECUTION_STATE_INPROGRESS
    FAILED = EXECUTION_STATE_FAILED
    TIMED_OUT = EXECUTION_STATE_TIMEDOUT


class IntegrationParamType(Enum):
    BOOLEAN = 0
    INTEGER = 1
    STRING = 2
    PASSWORD = 3
    IP = 4
    EMAIL = 8
    NULL = -1


class ActionParamType(Enum):
    STRING = 0
    BOOLEAN = 1
    PLAYBOOK_NAME = 2
    USER = 3
    STAGE = 4
    CLOSE_CASE_REASONS = 5
    CLOSE_ROOT_CAUSE = 6
    CASE_PRIORITIES = 7
    EMAIL_CONTENT = 10
    CONTENT = 11
    PASSWORD = 12
    ENTITY_TYPE = 13
    MULTI_VALUES = 14
    DDL = 15
    CODE = 20
    NULL = -1


class ScriptParameter:
    """A general script parameter object.

    Attributes:
        full_dict (dict[str, Any]): The original dict received from the API.
        id (int | None): The parameter's ID.
        creation_time (int): The parameter's creation time.
        modification_time (int): The parameter's last modification time.
        custom_action_id (int | None): The action's ID.
        is_mandatory (bool): Whether the parameter is mandatory or not.
        default_value (Any): The parameter's default value
            (prioritized over 'value' in playbooks).
        description (str | None): The parameter's description.
        name (str | None): The parameter's name.
        value (Any): The default value of the parameter
            (prioritized over 'default_value' in manual actions).
        type (ActionParamType): The type of the parameter.
        optional_values (list): DDL of optional values for type DDL.

    """

    def __init__(self, input_dict: dict[str, Any]) -> None:
        self.full_dict: dict[str, Any] = input_dict
        self.id: int | None = input_dict.get("id")
        self.creation_time: int = input_dict.get("creationTimeUnixTimeInMs", -1)
        self.modification_time: int = input_dict.get("modificationTimeUnixTimeInMs", -1)
        self.custom_action_id: int | None = input_dict.get("customActionId")
        self.is_mandatory: bool = input_dict.get("isMandatory", False)
        self.default_value: Any = input_dict.get("defaultValue")
        self.description: str | None = input_dict.get("description")
        self.name: str = input_dict.get("name", "No name found!")
        self.value: Any = input_dict.get("value")
        self.type = ActionParamType(input_dict.get("type", -1))
        self.optional_values: list | None = input_dict.get("optionalValues")


class FullDetailsConfigurationParameter:
    """A general script parameter object.

    Attributes:
        full_dict (dict[str, Any]): The original dict received from the API.
        id (int | None): The parameter's ID.
        integration_identifier (str): The integration's identifier
            (e.g. VirusTotalV3).
        creation_time (int): The parameter's creation time.
        modification_time (int): The parameter's last modification time.
        is_mandatory (bool): Whether the parameter is mandatory or not.
        description (str | None): The parameter's description.
        name (str): The parameter's name.
        display_name (str): The parameter's display name.
        value (Any): The default value of the parameter.
        type (IntegrationParamType): The type of the parameter.
        optional_values (list): DDL of optional values for type DDL.

    """

    def __init__(self, input_dict: dict[str, Any]) -> None:
        self.full_dict: dict[str, Any] = input_dict
        self.id: int | None = input_dict.get("id")
        self.integration_identifier: str = input_dict.get("integrationIdentifier")
        self.creation_time: int = input_dict.get("creationTimeUnixTimeInMs", -1)
        self.modification_time: int = input_dict.get("modificationTimeUnixTimeInMs", -1)
        self.is_mandatory: bool = input_dict.get("isMandatory", False)
        self.description: str | None = input_dict.get("propertyDescription")
        self.name: str = input_dict.get("propertyName", "No name found!")
        self.display_name: str = input_dict.get("propertyDisplayName", "No display name found!")
        self.value: Any = input_dict.get("value")
        self.type = IntegrationParamType(input_dict.get("propertyType", -1))
        self.optional_values: list | None = input_dict.get("optionalValues")


@dataclasses.dataclass(frozen=True, eq=True)
class DataTable:
    """An action script-result data table.

    This class is immutable, after assigning values and creating the object,
    new values cannot be assigned to the attributes.
    The class supports hashing (store in a set or as a dict key) and `==`
    operator.

    Attributes:
        title (str | None): The table's title.
        data_table (list[str)]): A list of csv rows that construct the table.

    """

    data_table: list[str]
    title: str = "Script Result Data Table"


@dataclasses.dataclass(frozen=True, eq=True)
class Attachment:
    """An action script-result attachment.

    This class is immutable, after assigning values and creating the object,
    new values cannot be assigned to the attributes.
    The class supports hashing (store in a set or as a dict key) and `==`
    operator.

    Attributes:
        title (str | None): The attachment's title.
        filename (str): The attachment's file name.
        file_contents (bytes): The attachment's file content.
        additional_data (dict | None): Additional data(?)

    """

    filename: str
    file_contents: bytes
    title: str = "Script Result Attachment"
    additional_data: dict | None = None


@dataclasses.dataclass(frozen=True, eq=True)
class Content:
    """An action script-result content.

    This class is immutable, after assigning values and creating the object,
    new values cannot be assigned to the attributes.
    The class supports hashing (store in a set or as a dict key) and `==`
    operator.

    Attributes:
        title (str | None): The content's title.
        content (str): The content to add to the script results.

    """

    content: str
    title: str = "Script Result Content"


@dataclasses.dataclass(frozen=True, eq=True)
class Link:
    """An action script-result link.

    This class is immutable, after assigning values and creating the object,
    new values cannot be assigned to the attributes.
    The class supports hashing (store in a set or as a dict key) and `==`
    operator.

    Attributes:
        title (str | None): The link's title.
        link (str): The link.

    """

    link: str
    title: str = "Script Result Link"


@dataclasses.dataclass(frozen=True, eq=True)
class HTMLReport:
    """An action script-result link.

    This class is immutable, after assigning values and creating the object,
    new values cannot be assigned to the attributes.
    The class supports hashing (store in a set or as a dict key) and `==`
    operator.

    Attributes:
        title (str | None): The link's title.
        report_name (str): The report's name.
        report_contents (str): The report's HTML content.

    """

    report_name: str
    report_contents: str
    title: str = "Script Result HTML Report"


@dataclasses.dataclass(frozen=True, eq=True)
class Markdown:
    """An action script-result markdown.

    This class is immutable, after assigning values and creating the object,
    new values cannot be assigned to the attributes.
    The class supports hashing (store in a set or as a dict key) and `==`
    operator.

    Attributes:
        title (str | None): The markdown's title.
        markdown_content (str): The markdown's content.
        markdown_name (str): The markdown's name.

    """

    markdown_name: str
    markdown_content: str
    title: str = "Script Result Markdown"


@dataclasses.dataclass(frozen=True, eq=True)
class EntityInsight:
    """An entity insight.

    This class is immutable, after assigning values and creating the object,
    new values cannot be assigned to the attributes.
    The class supports hashing (store in a set or as a dict key) and `==`
    operator.

    Attributes:
        entity (Entity): The entity object.
        message (str): The insight's message.
        triggered_by (str | None): The integration's name.
        original_requesting_user (str | None): The original user.

    """

    entity: Entity
    message: str
    triggered_by: str | None = None
    original_requesting_user: str | None = None


@dataclasses.dataclass(frozen=True)
class CaseInsight:
    """A case insight.

    This class is immutable, after assigning values and creating the object,
    new values cannot be assigned to the attributes.
    The class supports hashing (store in a set or as a dict key) and `==`
    operator.

    Attributes:
        title (str): The insight's title.
        triggered_by (str): The integration's name/ID (e.g. VirusTotalV3).
        content (str): The insight message.
        severity (InsightSeverity): Insight severity => info | warning | error.
        insight_type (InsightType): Insight type => general | entity.
        entity_identifier (str | None): The entity's identifier.
        additional_data (Any | None): Additional data
        additional_data_type (Any | None): The additional data's type
        additional_data_title (str | None): The additional data's title

    """

    triggered_by: str
    title: str
    content: str
    severity: InsightSeverity
    insight_type: InsightType
    entity_identifier: str = ""
    additional_data: Any | None = None
    additional_data_type: Any | None = None
    additional_data_title: str | None = None


@dataclasses.dataclass(frozen=True, eq=True)
class CaseAttachment:
    """A case attachment

    This class is immutable, after assigning values and creating the object,
    new values cannot be assigned to the attributes.
    The class supports hashing (store in a set or as a dict key) and `==`
    operator.

    Attributes:
        attachment_id (int): The attachment's ID (e.g. 10).
        attachment_type (str): The attachment's type (e.g. `.txt`).
        description (str): The attachment's description.
        is_favorite (bool): Whether the attachment is marked as favorite.

    """

    attachment_id: int
    attachment_type: str
    description: str
    is_favorite: bool


@dataclasses.dataclass(frozen=True, eq=True)
class CaseComment:
    """A case comment

    This class is immutable, after assigning values and creating the object,
    new values cannot be assigned to the attributes.
    The class supports hashing (store in a set or as a dict key) and `==`
    operator.

    Attributes:
        comment (str): The comment
        comment_for_client (str | None): the comment for the client
        modification_time_unix_time_in_ms_for_client (int):
            The modification time for the comment_for_client
        last_editor (str):
            The ID of the last editor
            (e.g. `77bdb7a4-8484-481d-9482-2449e33f9518`)
        last_editor_full_name (str):
            The full name name of the last editor's user (e.g. `admin admin`)
        is_deleted (bool): Whether the comment is already deleted
        creator_user_id (str):
            The creator user ID (e.g. `77bdb7a4-8484-481d-9482-2449e33f9518`)
        creator_full_name (str): The creator's full name (e.g. `System`)
        comment_id (int): The comment's ID (e.g. `1`)
        comment_type (int): The comment's type (e.g. `5`)
        case_id (int): The case ID (e.g. `7`)
        is_favorite (bool): Whether the comment is marked as favorite.
        modification_time_unix_time_in_ms (int):
        The comment's last modification time in unix (e.g. `1686040471269`)
        creation_time_unix_time_in_ms (int):
            The comment's creation time in unix (e.g. `1686040471269`)
        alert_identifier (str):
            The alert's identifier (e.g.
            `SUSPICIOUS PHISHING EMAIL_83765943-9437-4771-96F6-BD0FB291384E`)

    """

    comment: str
    creator_user_id: str
    comment_id: int
    comment_type: int
    case_id: int
    is_favorite: bool
    modification_time_unix_time_in_ms: int
    creation_time_unix_time_in_ms: int
    alert_identifier: str
    creator_full_name: str | None = None
    is_deleted: bool | None = None
    last_editor: str | None = None
    last_editor_full_name: str | None = None
    modification_time_unix_time_in_ms_for_client: int | None = None
    comment_for_client: str | None = None
