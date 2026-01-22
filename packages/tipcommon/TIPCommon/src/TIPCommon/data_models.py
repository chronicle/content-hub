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

"""data_models
===========

This module contains data classes for representing:
- Data model
- Alerts
- Variable containers
- General parameters
- Connector parameters.

"""

from __future__ import annotations

import dataclasses
import email
import json
from enum import Enum
from typing import Any, Generic, Self, TypeVar

import SiemplifyVault
from SiemplifyConnectorsDataModel import ConnectorContext

from TIPCommon.types import SingleJson

T = TypeVar("T")


class TypedContainer(Generic[T]):
    """Container for a specific type that provides type intellisense"""

    def __init__(self) -> None:
        self._params: dict[str, T] = {}

    def __get__(self, service_name: str, _=None) -> T:
        return self._params.get(service_name)

    def __set__(self, service_name: str, service: T) -> None:
        self._params[service_name] = service

    def __contains__(self, item: Any) -> bool:
        return item in self._params


class BaseDataModel:
    """Represents a base data model. It has the following properties:

    Attributes:
        raw_data: The raw data for the alert.

    The `to_json` method converts the raw data to JSON format as returned from
    `json.loads()`.

    Example:
        >>> from data_models import BaseDataModel
        >>> data = BaseDataModel({"foo": "bar"})
        >>> data.raw_data
        {'foo': 'bar'}
        >>> data.to_json()
        {'foo': 'bar'}

    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def __repr__(self):
        return str(self.raw_data)

    def to_json(self):
        return self.raw_data


class BaseAlert:
    """Represents a base alert. It has the following properties:

    Attributes:
        raw_data: The raw data for the alert.
        alert_id: The ID of the alert.

    The `to_json` method converts the alert to JSON format as returned from
    `json.loads()`.

    Example:
        >>> from data_models import BaseAlert
        >>> alert = BaseAlert({"foo": "bar"}, 100)
        >>> alert.raw_data
        {'foo': 'bar'}
        >>> alert.alert_id
        100
        >>> alert.to_json()
        {'foo': 'bar'}

    """

    def __init__(self, raw_data, alert_id):
        self.raw_data = raw_data
        self.alert_id = alert_id

    def to_json(self):
        return self.raw_data


class Container:
    """Represents a container for variables.

    Examples:
        >>> from data_models import Container
        >>> container = Container()
        >>> container.one = 1
        >>> container.one
        1

    """

    def __init__(self):
        self._params = {}

    def __get__(self, ins, instype=None):
        return self._params.get(ins)

    def __set__(self, ins, value):
        self._params[ins] = value


class Parameter:
    """A Parent class representing a parameter.

    It has the following properties:

    raw_data: The raw data for the parameter.

    Example:
        >>> from data_models import Parameter
        >>> p = Parameter({"foo": "bar"})
        >>> print(p)
        Parameter(raw_data={'foo': 'bar'})

    """

    def __init__(self, raw_param):
        self._raw_data = raw_param

    @property
    def raw_data(self):
        return self._raw_data


class ConnectorParameter(Parameter):
    """Represents a connector parameter. It has the following properties:

    name: The name of the parameter.
    value: The value of the parameter.
    type: The type of the parameter (according to `ConnectorParamTypes`).
    mode: The mode of the parameter.
    is_mandatory: Whether the parameter is mandatory.

    Example:
        >>> from data_models import ConnectorParameter, ConnectorParamTypes
        >>> p = ConnectorParameter({
            'param_name': 'api_root',
            'type': ConnectorParamTypes.STRING,
            'param_value': 'http://foo.bar',
            'is_mandatory': True,
            'mode': 0
            })
        >>> print(p)
        ConnectorParameter(name='api_root', value='http://foo.bar', type=2, mode=0, is_mandatory=True)

    """

    def __init__(self, raw_param):
        super().__init__(raw_param)
        self._name = raw_param.get("param_name", "")
        self._value = raw_param.get("param_value", "")
        self._type = ConnectorParamTypes(raw_param.get("type", -1))
        self._mode = raw_param.get("mode", "")
        self._is_mandatory = raw_param.get("is_mandatory", "")

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    @property
    def type(self):
        return self._type

    @property
    def mode(self):
        return self._mode

    @property
    def is_mandatory(self):
        return self._is_mandatory


class ConnectorParamTypes(Enum):
    """Represents the types of connector parameters. The possible values are:

    * BOOLEAN: A Boolean parameter.
    * INTEGER: An integer parameter.
    * STRING: A string parameter.
    * PASSWORD: A password parameter.
    * IP: An IP address parameter.
    * HOST: A host name parameter.
    * URL: A URL parameter.
    * DOMAIN: A domain name parameter.
    * EMAIL: An email address parameter.
    * SCRIPT: Script parameter (legacy).
    * NULL: Invalid parameter type.
    """

    BOOLEAN = 0
    INTEGER = 1
    STRING = 2
    PASSWORD = 3
    IP = 4
    HOST = 5
    URL = 6
    DOMAIN = 7
    EMAIL = 8

    # TODO: (b/288932557)
    # This is workaround for SDK legacy code and should be removed when fixed
    SCRIPT = 12

    NULL = -1


class JobParamType(Enum):
    BOOLEAN = 0
    INTEGER = 1
    STRING = 2
    PASSWORD = 3
    IP = 4
    HOST = 5
    URL = 6
    DOMAIN = 7
    EMAIL = 8
    NULL = -1


class CaseDataStatus(Enum):
    NEW = 0
    OPENED = 1
    CLOSED = 2
    ALL = 3
    MERGED = 4
    CREATION_PENDING = 5

    @classmethod
    def _missing_(cls, value):
        """Custom method to handle missing values when trying to create
        an enum member. This supports direct integer values,
        'Priority' prefixed strings, and exact enum names as strings.
        """
        if isinstance(value, str):
            candidate_name = value.replace(" ", "_").upper()
            if candidate_name in cls.__members__:
                return cls.__members__[candidate_name]

        raise ValueError(f"'{value}' is not a valid {cls.__name__}")


CASE_DATA_STATUS_VAL_NAME_MAP = {
    CaseDataStatus.NEW: "New",
    CaseDataStatus.OPENED: "Opened",
    CaseDataStatus.CLOSED: "Closed",
    CaseDataStatus.ALL: "All",
    CaseDataStatus.MERGED: "Merged",
    CaseDataStatus.CREATION_PENDING: "Creation Pending",
}


class CasePriority(Enum):
    INFORMATIVE = -1
    UNCHANGED = 0
    LOW = 40
    MEDIUM = 60
    HIGH = 80
    CRITICAL = 100

    @classmethod
    def _missing_(cls, value):
        """Custom method to handle missing values when trying to create
        an enum member. This supports direct integer values,
        'Priority' prefixed strings, and exact enum names as strings.
        """
        if isinstance(value, str):
            candidate_name = value[len("Priority") :].replace("Info", "Informative").upper()
            candidate_name = candidate_name.replace("UNSPECIFIED", "UNCHANGED")
            if candidate_name in cls.__members__:
                return cls.__members__[candidate_name]

        raise ValueError(f"'{value}' is not a valid {cls.__name__}")


CASE_PRIORITY_VAL_NAME_MAP = {
    CasePriority.INFORMATIVE: "Informative",
    CasePriority.UNCHANGED: "Unchanged",
    CasePriority.LOW: "Low",
    CasePriority.MEDIUM: "Medium",
    CasePriority.HIGH: "High",
    CasePriority.CRITICAL: "Critical",
}


class AlertPriority(Enum):
    INFORMATIVE = -1
    UNCHANGED = 0
    LOW = 40
    MEDIUM = 60
    HIGH = 80
    CRITICAL = 100


ALERT_PRIORITY_VAL_NAME_MAP = {
    AlertPriority.INFORMATIVE: "Informative",
    AlertPriority.UNCHANGED: "Unchanged",
    AlertPriority.LOW: "Low",
    AlertPriority.MEDIUM: "Medium",
    AlertPriority.HIGH: "High",
    AlertPriority.CRITICAL: "Critical",
}


class ConnectorConnectivityStatusEnum(Enum):
    LIVE = 0
    NO_CONNECTIVITY = 1


class DatabaseContextType(Enum):
    GLOBAL = 0
    CASE = 1
    ALERT = 2
    JOB = 3
    CONNECTOR = 4


@dataclasses.dataclass
class ScriptContext:
    target_entities: str = ""
    case_id: int | str | None = None
    alert_id: str = ""
    environment: str = ""
    workflow_id: str = ""
    workflow_instance_id: str | None = None
    parameters: SingleJson = dataclasses.field(default_factory=dict)
    integration_identifier: str = ""
    integration_instance: str = ""
    action_definition_name: str = ""
    original_requesting_user: str = ""
    execution_deadline_unix_time_ms: int = 0
    async_polling_interval_in_sec: int = 0
    async_total_duration_deadline: int = 0
    script_timeout_deadline: int = 0
    default_result_value: str = ""
    use_proxy_settings: bool = False
    max_json_result_size: int = 15
    vault_settings: SiemplifyVault | None = None
    environment_api_key: str | None = None
    unique_identifier: str = ""
    job_api_key: str = ""
    connector_context: ConnectorContext | None = None

    def __post_init__(self) -> None:
        if self.connector_context is None:
            self.connector_context: ConnectorContext = ConnectorContext({
                "params": [],
                "allow_list": [],
            })

    def update(self, attributes: SingleJson) -> None:
        vars(self).update(attributes)

    def to_json(self) -> SingleJson:
        return {
            "target_entities": self.target_entities,
            "case_id": self.case_id,
            "alert_id": self.alert_id,
            "environment": self.environment,
            "workflow_id": self.workflow_id,
            "workflow_instance_id": self.workflow_instance_id,
            "parameters": self.parameters,
            "integration_identifier": self.integration_identifier,
            "integration_instance": self.integration_instance,
            "action_definition_name": self.action_definition_name,
            "original_requesting_user": self.original_requesting_user,
            "execution_deadline_unix_time_ms": self.execution_deadline_unix_time_ms,
            "async_polling_interval_in_sec": self.async_polling_interval_in_sec,
            "async_total_duration_deadline": self.async_total_duration_deadline,
            "script_timeout_deadline": self.script_timeout_deadline,
            "default_result_value": self.default_result_value,
            "use_proxy_settings": self.use_proxy_settings,
            "max_json_result_size": self.max_json_result_size,
            "vault_settings": (
                self.vault_settings
                if self.vault_settings is None
                else {
                    "vault_api_root": self.vault_settings.api_root,
                    "vault_verify_ssl": self.vault_settings.verify_ssl,
                    "vault_username": self.vault_settings.username,
                    "vault_password": self.vault_settings.password,
                    "vault_client_ca_certificate": (self.vault_settings.client_ca_certificate),
                    "vault_client_certificate": self.vault_settings.client_certificate,
                    "vault_client_certificate_passphrase": (
                        self.vault_settings.client_certificate_passphrase
                    ),
                }
            ),
            "environment_api_key": self.environment_api_key,
            "unique_identifier": self.unique_identifier,
            "job_api_key": self.job_api_key,
            "connector_info": {
                "environment": self.connector_context.connector_info.environment,
                "integration": self.connector_context.connector_info.integration,
                "connector_definition_name": (
                    self.connector_context.connector_info.connector_definition_name
                ),
                "identifier": self.connector_context.connector_info.identifier,
                "display_name": self.connector_context.connector_info.display_name,
                "description": self.connector_context.connector_info.description,
                "result_data_type": (self.connector_context.connector_info.result_data_type),
                "params": self.connector_context.connector_info.params,
                "allow_list": self.connector_context.connector_info.white_list,
            },
        }


class FieldItem:
    def __init__(self, original_name, name, value):
        # type: (str, str, str) -> None
        self.original_name = original_name
        self.name = name
        self.value = value

    @classmethod
    def from_json(cls, field_json):
        # type: (SingleJson) -> FieldItem
        return cls(
            original_name=field_json["originalName"],
            name=field_json["name"],
            value=field_json["value"],
        )


class EventPropertyField:
    def __init__(self, order, group_name, is_integration, is_highlight, items):
        # type: (int, str, bool, bool, list[FieldItem]) -> None
        self.order = order
        self.group_name = group_name
        self.is_integration = is_integration
        self.is_highlight = is_highlight
        self.items = items

    @classmethod
    def from_json(cls, event_property_field):
        # type: (SingleJson) -> EventPropertyField
        return cls(
            order=event_property_field["order"],
            group_name=event_property_field["groupName"],
            is_integration=event_property_field["isIntegration"],
            is_highlight=event_property_field["isHighlight"],
            items=[FieldItem.from_json(item) for item in event_property_field["items"]],
        )


class AlertEvent:
    def __init__(
        self,
        fields,
        identifier,
        case_id,
        alert_identifier,
        name,
        product,
        port,
        source_system_name,
        outcome,
        time,
        type_,
        artifact_entities,
    ):
        # type: (list[EventPropertyField], str, int, str, str, str, str | None, str, str | None, int, str, list[str]) -> None
        self.fields = fields
        self.identifier = identifier
        self.case_id = case_id
        self.alert_identifier = alert_identifier
        self.name = name
        self.product = product
        self.port = port
        self.source_system_name = source_system_name
        self.outcome = outcome
        self.time = time
        self.type_ = type_
        self.artifact_entities = artifact_entities

    @classmethod
    def from_json(cls, event_json):
        # type: (SingleJson) -> AlertEvent
        return cls(
            fields=[EventPropertyField.from_json(field) for field in event_json["fields"]],
            identifier=event_json["identifier"],
            case_id=event_json["caseId"],
            alert_identifier=event_json["alertIdentifier"],
            name=event_json["name"],
            product=event_json["product"],
            port=event_json["port"],
            source_system_name=event_json["sourceSystemName"],
            outcome=event_json["outcome"],
            time=event_json["time"],
            type_=event_json["type"],
            artifact_entities=event_json["artifactEntities"],
        )


class FieldGroupItem:
    def __init__(self, original_name, name, value):
        # type: (str, str, str) -> None
        self.original_name = original_name
        self.name = name
        self.value = value

    @classmethod
    def from_json(cls, field_group_json):
        # type: (SingleJson) -> FieldGroupItem
        return cls(
            original_name=field_group_json["originalName"],
            name=field_group_json["name"],
            value=field_group_json["value"],
        )

    def to_json(self) -> SingleJson:
        return {
            "originalName": self.original_name,
            "name": self.name,
            "value": self.value,
        }


class FieldsGroup:
    def __init__(self, order, group_name, is_integration, is_highlight, hide_options, items):
        self.order = order
        self.group_name = group_name
        self.is_integration = is_integration
        self.is_highlight = is_highlight
        self.hide_options = hide_options
        self.items = items

    @classmethod
    def from_json(cls, field_group_json):
        return cls(
            order=field_group_json.get("order"),
            group_name=field_group_json.get("groupName", field_group_json.get("displayName")),
            is_integration=field_group_json.get("isIntegration"),
            is_highlight=field_group_json.get("isHighlight", field_group_json.get("highlighted")),
            hide_options=field_group_json.get("hideOptions", field_group_json.get("hidden")),
            items=[FieldGroupItem.from_json(item_json) for item_json in field_group_json["items"]],
        )

    def to_json(self) -> SingleJson:
        items_json = [item.to_json() for item in self.items] if self.items else []
        return {
            "order": self.order,
            "groupName": self.group_name,
            "isIntegration": self.is_integration,
            "isHighlight": self.is_highlight,
            "hideOptions": self.hide_options,
            "items": items_json,
        }


class SLA:
    def __init__(
        self,
        sla_expiration_time,
        critical_expiration_time,
        expiration_status,
        remaining_time_since_last_pause,
    ):
        # type: (int | None, int | None, int, int | None) -> None
        self.sla_expiration_time = sla_expiration_time
        self.critical_expiration_time = critical_expiration_time
        self.expiration_status = expiration_status
        self.remaining_time_since_last_pause = remaining_time_since_last_pause

    @classmethod
    def from_json(cls, sla_json):
        # type: (SingleJson) -> SLA
        return cls(
            sla_expiration_time=sla_json.get(
                "expirationTime", sla_json.get("slaExpirationTime", -1)
            ),
            critical_expiration_time=sla_json.get("criticalExpirationTime", -1),
            expiration_status=sla_json.get("expirationStatus", -1),
            remaining_time_since_last_pause=sla_json.get("remainingTimeSinceLastPause", -1),
        )

    def to_json(self) -> SingleJson:
        """Converts the SLA object to a JSON-serializable dictionary."""
        return {
            "slaExpirationTime": self.sla_expiration_time,
            "criticalExpirationTime": self.critical_expiration_time,
            "expirationStatus": self.expiration_status,
            "remainingTimeSinceLastPause": self.remaining_time_since_last_pause,
        }


class AlertCard:
    def __init__(
        self,
        id_: int,
        creation_time_unix_time_ms: int,
        modification_time_unix_time_ms: int,
        identifier: str,
        status: int,
        name: str,
        priority: AlertPriority | int | None,
        workflow_status: int | None,
        sla_expiration_unix_time: int | None,
        sla_critical_expiration_unix_time: int | None,
        start_time: int,
        end_time: int,
        alert_group_identifier: str,
        events_count: int,
        title: str,
        rule_generator: str,
        device_product: str,
        device_vendor: str,
        playbook_attached: bool | None,
        playbook_run_count: int | None,
        is_manual_alert: bool | None,
        sla: SLA | None,
        fields_groups: list[FieldsGroup],
        source_url: str | None,
        source_rule_url: str | None,
        siem_alert_id: str | None,
        additional_properties: str | None,
        case_id: int | None,
        ticket_id: str | None,
        closure_details: SingleJson | None,
        event_count: int | None = None,
        product_families: list[str] | None = None,
        entity_cards: list[SingleJson] | None = None,
        security_event_cards: list[SingleJson] | None = None,
        involved_relations: list[SingleJson] | None = None,
    ):
        self.id_ = id_
        self.creation_time_unix_time_ms = creation_time_unix_time_ms
        self.modification_time_unix_time_ms = modification_time_unix_time_ms
        self.identifier = identifier
        self.status = status
        self.name = name
        self.priority = priority
        self.workflow_status = workflow_status
        self.sla_expiration_unix_time = sla_expiration_unix_time
        self.sla_critical_expiration_unix_time = sla_critical_expiration_unix_time
        self.start_time = start_time
        self.end_time = end_time
        self.alert_group_identifier = alert_group_identifier
        self.events_count = events_count
        self.title = title
        self.rule_generator = rule_generator
        self.device_product = device_product
        self.device_vendor = device_vendor
        self.playbook_attached = playbook_attached
        self.playbook_run_count = playbook_run_count
        self.is_manual_alert = is_manual_alert
        self.sla = sla
        self.fields_groups = fields_groups
        self.source_url = source_url
        self.source_rule_url = source_rule_url
        self.siem_alert_id = siem_alert_id
        self.additional_properties = additional_properties
        self.case_id = case_id
        self.ticket_id = ticket_id
        self.closure_details = closure_details
        self.event_count = event_count
        self.product_families = product_families or []
        self.entity_cards = entity_cards or []
        self.security_event_cards = security_event_cards or []
        self.involved_relations = involved_relations or []

    @classmethod
    def from_json(cls, alert_card_json):

        raw_priority = alert_card_json.get("priority")
        priority = raw_priority
        if isinstance(raw_priority, str) and raw_priority.isdigit():
            priority = int(raw_priority)

        add_props = alert_card_json.get("additionalProperties")
        if isinstance(add_props, dict):
            add_props = json.dumps(add_props)

        return cls(
            id_=alert_card_json.get("id", 0),
            creation_time_unix_time_ms=alert_card_json.get("creationTimeUnixTimeInMs", 0),
            modification_time_unix_time_ms=alert_card_json.get("modificationTimeUnixTimeInMs", 0),
            identifier=alert_card_json.get("identifier", ""),
            status=alert_card_json.get("status", 0),
            name=alert_card_json.get("displayName", alert_card_json.get("name", "")),
            priority=priority,
            workflow_status=alert_card_json.get(
                "workflowsStatus", alert_card_json.get("playbookStatus")
            ),
            sla_expiration_unix_time=alert_card_json.get("slaExpirationUnixTime"),
            sla_critical_expiration_unix_time=alert_card_json.get("slaCriticalExpirationUnixTime"),
            start_time=alert_card_json.get(
                "startTime", alert_card_json.get("startTimeUnixTimeInMs", 0)
            ),
            end_time=alert_card_json.get("endTime", 0),
            alert_group_identifier=alert_card_json.get("alertGroupIdentifier", ""),
            events_count=alert_card_json.get("eventsCount", alert_card_json.get("eventCount", 0)),
            title=(alert_card_json.get("title") or alert_card_json.get("displayName", "")),
            rule_generator=alert_card_json.get("ruleGenerator", ""),
            device_product=alert_card_json.get("product", alert_card_json.get("deviceProduct")),
            device_vendor=alert_card_json.get("vendor", alert_card_json.get("deviceVendor")),
            playbook_attached=alert_card_json.get("playbookAttached"),
            playbook_run_count=(
                alert_card_json.get("playbookRunCount") or alert_card_json.get("playbook_run_count")
            ),
            is_manual_alert=alert_card_json.get("isManualAlert", alert_card_json.get("manual")),
            sla=SLA.from_json(alert_card_json.get("sla")) if alert_card_json.get("sla") else None,
            fields_groups=[
                FieldsGroup.from_json(x)
                for x in alert_card_json.get("fieldsGroups", alert_card_json.get("fields", []))
            ],
            source_url=alert_card_json.get("sourceUrl"),
            source_rule_url=alert_card_json.get("sourceRuleUrl"),
            siem_alert_id=alert_card_json.get("siemAlertId"),
            additional_properties=add_props,
            case_id=alert_card_json.get("caseId"),
            ticket_id=alert_card_json.get("ticketId"),
            closure_details=alert_card_json.get("closureDetails"),
            event_count=alert_card_json.get("eventCount"),
            product_families=alert_card_json.get("productFamilies", []),
            entity_cards=alert_card_json.get("entityCards", []),
            security_event_cards=alert_card_json.get("securityEventCards", []),
            involved_relations=alert_card_json.get("involvedRelations", []),
        )

    def to_json(self) -> SingleJson:
        """Converts the AlertCard object to a JSON-serializable dictionary."""
        priority_value = self.priority.value if isinstance(self.priority, Enum) else self.priority
        return {
            "id": self.id_,
            "creationTimeUnixTimeInMs": self.creation_time_unix_time_ms,
            "modificationTimeUnixTimeInMs": self.modification_time_unix_time_ms,
            "identifier": self.identifier,
            "status": self.status,
            "name": self.name,
            "priority": priority_value,
            "workflowsStatus": self.workflow_status,
            "slaExpirationUnixTime": self.sla_expiration_unix_time,
            "slaCriticalExpirationUnixTime": self.sla_critical_expiration_unix_time,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "alertGroupIdentifier": self.alert_group_identifier,
            "eventsCount": self.events_count,
            "title": self.title,
            "ruleGenerator": self.rule_generator,
            "deviceProduct": self.device_product,
            "deviceVendor": self.device_vendor,
            "caseId": self.case_id,
            "playbookAttached": self.playbook_attached,
            "playbookRunCount": self.playbook_run_count,
            "isManualAlert": self.is_manual_alert,
            "sla": self.sla.to_json() if self.sla else None,
            "fieldsGroups": [fg.to_json() for fg in self.fields_groups],
            "sourceUrl": self.source_url,
            "sourceRuleUrl": self.source_rule_url,
            "siemAlertId": self.siem_alert_id,
            "additionalProperties": self.additional_properties,
            "ticketId": self.ticket_id,
            "closureDetails": self.closure_details,
            "productFamilies": self.product_families,
            "entityCards": self.entity_cards,
            "securityEventCards": self.security_event_cards,
            "involvedRelations": self.involved_relations,
        }


class CaseDetails:
    def __init__(
        self,
        id_,
        creation_time_unix_time_ms,
        modification_time_unix_time_ms,
        name,
        priority,
        is_important,
        is_incident,
        start_time_unix_time_ms,
        end_time_unix_time_ms,
        assigned_user,
        description,
        is_test_case,
        type_,
        stage,
        environment,
        status,
        score,
        involved_suspicious_entity,
        workflow_status,
        source,
        products,
        tasks,
        incident_id,
        last_modifying_user_id,
        tags,
        related_alerts,
        alert_count,
        alerts,
        wall_data,
        entity_cards,
        entities,
        is_overflow_case,
        is_manual_case,
        sla_expiration_unix_time,
        sla_critical_expiration_unix_time,
        stage_sla_expiration_unix_time_ms,
        stage_sla__critical_expiration_unix_time_in_ms,
        can_open_incident,
        sla,
        stage_sla,
        alerts_sla,
    ):
        # type: (int, int, int, str, CasePriority, bool, bool, int, int, str, str | None, bool, int, str, str, CaseDataStatus, int | None, list[str], list[AlertCard], bool, bool, int | None, int | None, int | None, int | None, bool, SLA, SLA) -> None
        self.id_ = id_
        self.creation_time_unix_time_ms = creation_time_unix_time_ms
        self.modification_time_unix_time_ms = modification_time_unix_time_ms
        self.name = name
        self.priority = priority
        self.is_important = is_important
        self.is_incident = is_incident
        self.start_time_unix_time_ms = start_time_unix_time_ms
        self.end_time_unix_time_ms = end_time_unix_time_ms
        self.assigned_user = assigned_user
        self.description = description
        self.is_test_case = is_test_case
        self.type_ = type_
        self.stage = stage
        self.environment = environment
        self.score = score
        self.involved_suspicious_entity = involved_suspicious_entity
        self.workflow_status = workflow_status
        self.source = source
        self.products = products
        self.tasks = tasks
        self.status = status
        self.incident_id = incident_id
        self.last_modifying_user_id = last_modifying_user_id
        self.tags = tags
        self.related_alerts = related_alerts
        self.alert_count = alert_count
        self.alerts = alerts
        self.wall_data = wall_data
        self.entity_cards = entity_cards
        self.entities = entities
        self.is_overflow_case = is_overflow_case
        self.is_manual_case = is_manual_case
        self.sla_expiration_unix_time = sla_expiration_unix_time
        self.sla_critical_expiration_unix_time = sla_critical_expiration_unix_time
        self.stage_sla_expiration_unix_time_ms = stage_sla_expiration_unix_time_ms
        self.stage_sla__critical_expiration_unix_time_in_ms = (
            stage_sla__critical_expiration_unix_time_in_ms
        )
        self.can_open_incident = can_open_incident
        self.sla = sla
        self.stage_sla = stage_sla
        self.alerts_sla = alerts_sla

    @property
    def is_open(self):
        # type: () -> bool
        return self.status == CaseDataStatus.OPENED

    @property
    def is_closed(self):
        # type: () -> bool
        return self.status == CaseDataStatus.CLOSED

    @classmethod
    def from_json(cls, case_details_json):
        # type: (SingleJson) -> CaseDetails
        return cls(
            id_=case_details_json.get("id"),
            creation_time_unix_time_ms=(
                case_details_json.get("creationTimeUnixTimeInMs")
                or case_details_json.get("createTime")
            ),
            modification_time_unix_time_ms=(
                case_details_json.get("modificationTimeUnixTimeInMs")
                or case_details_json.get("updateTime")
            ),
            name=case_details_json.get("displayName", case_details_json.get("name")),
            priority=CasePriority(case_details_json.get("priority", 0)),
            is_important=case_details_json.get(
                "important",
                case_details_json.get("isImportant", False),
            ),
            is_incident=case_details_json.get(
                "incident",
                case_details_json.get("isIncident", False),
            ),
            start_time_unix_time_ms=(
                case_details_json.get("startTimeUnixTimeInMs")
                or case_details_json.get("createTime")
            ),
            end_time_unix_time_ms=(
                case_details_json.get("endTimeUnixTimeInMs") or case_details_json.get("endTime")
            ),
            assigned_user=(
                case_details_json.get("assignedUser") or case_details_json.get("assignee")
            ),
            description=case_details_json.get("description", ""),
            is_test_case=case_details_json.get("type", case_details_json.get("isTestCase", False))
            in [True, "Test"],
            type_=case_details_json.get("type"),
            stage=case_details_json.get("stage"),
            tags=case_details_json.get("tags", []),
            environment=case_details_json.get("environment"),
            status=CaseDataStatus(case_details_json.get("status", 0)),
            score=case_details_json.get("score", 0),
            involved_suspicious_entity=case_details_json.get("involvedSuspiciousEntity", False),
            workflow_status=case_details_json.get("workflowStatus"),
            source=case_details_json.get("source"),
            products=case_details_json.get("products", []),
            tasks=case_details_json.get("tasks", []),
            incident_id=case_details_json.get("incidentId", ""),
            last_modifying_user_id=case_details_json.get("lastModifyingUserId"),
            related_alerts=case_details_json.get("relatedAlerts", []),
            alert_count=case_details_json.get("alertCount", 0),
            alerts=[
                AlertCard.from_json(alert_card_json)
                for alert_card_json in (
                    case_details_json.get("alertCards", case_details_json.get("alerts", []))
                )
            ],
            wall_data=[
                WallData.from_json(alert_card_json)
                for alert_card_json in case_details_json.get("wallData", {})
            ],
            entity_cards=[
                EntityCard.from_json(alert_card_json)
                for alert_card_json in case_details_json.get("entityCards", {})
            ],
            entities=[
                Entity.from_json(alert_card_json)
                for alert_card_json in (
                    case_details_json.get("involvedEntities", case_details_json.get("entities", []))
                )
            ],
            is_overflow_case=case_details_json.get(
                "overflowCase",
                case_details_json.get("isOverflowCase", False),
            ),
            is_manual_case=case_details_json.get("isManualCase", False),
            sla_expiration_unix_time=case_details_json.get("slaExpirationUnixTime"),
            sla_critical_expiration_unix_time=(
                case_details_json.get("slaCriticalExpirationUnixTime")
            ),
            stage_sla_expiration_unix_time_ms=(
                case_details_json.get("stageSlaExpirationUnixTimeInMs")
            ),
            stage_sla__critical_expiration_unix_time_in_ms=(
                case_details_json.get("stageSlaCriticalExpirationUnixTimeInMs")
            ),
            can_open_incident=case_details_json.get("canOpenIncident", False),
            sla=SLA.from_json(case_details_json.get("sla", {})),
            stage_sla=(
                SLA.from_json(case_details_json.get("stageSla", case_details_json.get("sla", {})))
            ),
            alerts_sla=SLA.from_json(case_details_json.get("alertsSla", {})),
        )

    def to_json(self, include_activities: bool = False) -> SingleJson:
        """Converts the CaseDetails object to a JSON-serializable dictionary."""
        priority_value = self.priority.value
        status_value = self.status.value

        alerts_json = [alert.to_json() for alert in self.alerts]
        wall_data_json = [wdata.to_json() for wdata in self.wall_data]
        entity_cards_json = [entity_card.to_json() for entity_card in self.entity_cards]
        entities_json = [entity.to_json() for entity in self.entities]
        sla_json = self.sla.to_json()
        stage_sla_json = self.stage_sla.to_json()
        tags = [tag["displayName"] if "displayName" in tag else tag for tag in self.tags]

        case_data = {
            "id": self.id_,
            "creationTimeUnixTimeInMs": self.creation_time_unix_time_ms,
            "modificationTimeUnixTimeInMs": self.modification_time_unix_time_ms,
            "createTime": self.creation_time_unix_time_ms,
            "updateTime": self.modification_time_unix_time_ms,
            "name": self.name,
            "displayName": self.name,
            "priority": priority_value,
            "important": self.is_important,
            "incident": self.is_incident,
            "isImportant": self.is_important,
            "isIncident": self.is_incident,
            "startTimeUnixTimeInMs": self.start_time_unix_time_ms,
            "endTimeUnixTimeInMs": self.end_time_unix_time_ms,
            "assignedUser": self.assigned_user,
            "assignee": self.assigned_user,
            "description": self.description,
            "isTestCase": self.is_test_case,
            "type": self.type_,
            "stage": self.stage,
            "environment": self.environment,
            "status": status_value,
            "products": self.products,
            "score": self.score,
            "involvedSuspiciousEntity": self.involved_suspicious_entity,
            "workflowStatus": self.workflow_status,
            "source": self.source,
            "tasks": self.tasks,
            "incidentId": self.incident_id,
            "lastModifyingUserId": self.last_modifying_user_id,
            "tags": tags,
            "relatedAlerts": self.related_alerts,
            "alertCount": self.alert_count,
            "alertCards": alerts_json,
            "wallData": wall_data_json,
            "entityCards": entity_cards_json,
            "entities": entities_json,
            "isOverflowCase": self.is_overflow_case,
            "overflowCase": self.is_overflow_case,
            "isManualCase": self.is_manual_case,
            "manualCase": self.is_manual_case,
            "slaExpirationUnixTime": self.sla_expiration_unix_time,
            "slaCriticalExpirationUnixTime": self.sla_critical_expiration_unix_time,
            "stageSlaExpirationUnixTimeInMs": self.stage_sla_expiration_unix_time_ms,
            "stageSlaCriticalExpirationUnixTimeInMs": (
                self.stage_sla__critical_expiration_unix_time_in_ms
            ),
            "canOpenIncident": self.can_open_incident,
            "sla": sla_json,
            "stageSla": stage_sla_json,
            "alertSla": self.alerts_sla.to_json(),
        }

        if include_activities:
            case_data["activities"] = case_data.pop("wallData")

        return case_data


@dataclasses.dataclass(slots=True)
class Insight:
    raw_data: SingleJson

    @classmethod
    def from_json(cls, insights_response: SingleJson):
        if "activityDataJson" in insights_response:
            insights_response = json.loads(insights_response["activityDataJson"])

        return cls(raw_data=insights_response)

    def to_json(self):
        """Converts the Insight object to a JSON-serializable dictionary"""
        entity_data: SingleJson | None = self.raw_data.pop(
            "entityData", self.raw_data.pop("entity", None)
        )
        if entity_data is not None:
            entity_data["fields"] = entity_data.pop("fieldsGroups", entity_data.pop("fields", []))

        return {
            "alertIdentifier": self.raw_data.pop("alertIdentifier", None),
            "caseId": self.raw_data.pop("caseId", -1),
            "triggeredBy": self.raw_data.pop("triggeredBy", None),
            "title": self.raw_data.pop("title", ""),
            "content": self.raw_data.pop("title", ""),
            "entity": entity_data,
            "severity": self.raw_data.pop("severity", None),
            "type": self.raw_data.pop("type", None),
            "additionalDataType": self.raw_data.pop("additionalDataType", None),
            "additionalData": self.raw_data.pop("additionalData", None),
            "additionalDataTitle": self.raw_data.pop("additionalDataTitle", None),
            "creatorUserName": self.raw_data.pop(
                "creatorFullName", self.raw_data.pop("creatorUserName", None)
            ),
            **self.raw_data,
        }


class UserProfileCard:
    def __init__(
        self,
        raw_data,
        first_name,
        last_name,
        user_name,
        account_state,
    ):
        # type: (dict, str, str, str, int) -> None
        self.raw_data = raw_data
        self.first_name = first_name
        self.last_name = last_name
        self.user_name = user_name
        self.account_state = account_state

    @classmethod
    def from_json(cls, user_profile_card_response):
        # type: (dict) -> UserProfileCard
        return cls(
            raw_data=user_profile_card_response,
            first_name=user_profile_card_response["firstName"],
            last_name=user_profile_card_response["lastName"],
            user_name=user_profile_card_response.get(
                "userName",
                user_profile_card_response.get("displayName"),
            ),
            account_state=user_profile_card_response["accountState"],
        )


class ConnectorCard:
    def __init__(
        self,
        integration: str,
        display_name: str,
        identifier: str,
        is_enabled: bool,
        is_remote: bool,
        status: ConnectorConnectivityStatusEnum,
    ) -> None:
        self.integration = integration
        self.display_name = display_name
        self.identifier = identifier
        self.is_enabled = is_enabled
        self.is_remote = is_remote
        self.status = status

    @classmethod
    def from_json(cls, connector_card_json: SingleJson) -> ConnectorCard:
        return cls(
            integration=connector_card_json["integration"],
            display_name=connector_card_json.get("display_name")
            or connector_card_json.get("displayName"),
            identifier=connector_card_json["identifier"],
            is_enabled=(
                connector_card_json.get("is_enabled") or connector_card_json.get("enabled")
            ),
            is_remote=connector_card_json.get("is_remote") or connector_card_json.get("remote"),
            status=ConnectorConnectivityStatusEnum(connector_card_json.get("status", 1)),
        )


class InstalledIntegrationInstance:
    def __init__(
        self,
        instance: SingleJson,
        identifier: str,
        integration_identifier: str,
        environment_identifier: str,
        instance_name: str,
    ) -> None:
        self.instance = instance
        self.identifier = identifier
        self.integration_identifier = integration_identifier
        self.environment_identifier = environment_identifier
        self.instance_name = instance_name

    @classmethod
    def from_json(
        cls,
        integration_env_json: SingleJson,
    ) -> InstalledIntegrationInstance:
        """Parses JSON data into an IntegrationEnvironment object.

        Args:
            integration_env_json (SingleJson): JSON data containing integration
                environment information.

        Returns:
            InstalledIntegrationInstance: An instance of the specified class
            initialized with data from `raw_data`.

        """
        return cls(
            instance=integration_env_json,
            identifier=integration_env_json["identifier"],
            integration_identifier=integration_env_json["integrationIdentifier"],
            environment_identifier=(
                integration_env_json.get("environmentIdentifier")
                or integration_env_json.get("environment")
            ),
            instance_name=(
                integration_env_json.get("instanceName") or integration_env_json.get("displayName")
            ),
        )

    def to_json(self) -> SingleJson:
        """Serializes data model into dict.

        Returns:
            Service Account Json dict

        """
        return {
            "environmentIdentifier": self.instance.get(
                "environmentIdentifier", self.instance.get("environment")
            ),
            "identifier": self.instance.get("identifier"),
            "instanceDescription": self.instance.get(
                "instanceDescription", self.instance.get("displayName")
            ),
            "instanceName": self.instance.get("instanceName", self.instance.get("displayName")),
            "integrationIdentifier": self.instance.get(
                "integrationIdentifier", self.instance.get("integration")
            ),
            "isConfigured": self.instance.get("isConfigured", self.instance.get("configured")),
            "isRemote": self.instance.get("isRemote", None),
            "isSystemDefault": self.instance.get(
                "isSystemDefault", self.instance.get("systemDefault")
            ),
        }


class GoogleServiceAccount:
    def __init__(
        self,
        account_type,
        project_id,
        private_key_id,
        private_key,
        client_email,
        client_id,
        auth_uri,
        token_uri,
        auth_provider_x509_url,
        client_x509_cert_url,
    ):
        # type: (str, str, str, str, str, str, str, str, str, str) -> None
        self.account_type = account_type
        self.project_id = project_id
        self.private_key_id = private_key_id
        self.private_key = private_key
        self.client_email = client_email
        self.client_id = client_id
        self.auth_uri = auth_uri
        self.token_uri = token_uri
        self.auth_provider_x509_url = auth_provider_x509_url
        self.client_x509_cert_url = client_x509_cert_url

    def to_dict(self):
        # type: () -> dict
        """Serializes data model into dict.

        Returns:
            Service Account Json dict

        """
        return {
            "account_type": self.account_type,
            "project_id": self.project_id,
            "private_key_id": self.private_key_id,
            "private_key": self.private_key,
            "client_email": self.client_email,
            "client_id": self.client_id,
            "auth_uri": self.auth_uri,
            "token_uri": self.token_uri,
            "auth_provider_x509_cert_url": self.auth_provider_x509_url,
            "client_x509_cert_url": self.client_x509_cert_url,
        }


@dataclasses.dataclass(slots=True)
class CaseWallAttachment:
    name: str
    file_type: str
    base64_blob: str
    is_important: bool
    case_id: int | None = None
    description: str | None = None


class CustomFieldScope(Enum):
    CASE = "Case"
    ALERTS = "Alert"

    def build_parent_path(self, identifier: int) -> str:
        if self == CustomFieldScope.CASE:
            return f"cases/{identifier}"
        return f"cases/-/alerts/{identifier}"


@dataclasses.dataclass(slots=True)
class CustomField:
    id: int
    display_name: str
    description: str
    type: str
    scopes: list[CustomFieldScope]

    @classmethod
    def from_json(cls, json_data: SingleJson) -> CustomField:
        return cls(
            id=json_data["id"],
            display_name=json_data["displayName"],
            description=json_data["description"],
            type=json_data["type"],
            scopes=[CustomFieldScope(sc.strip()) for sc in json_data["scopes"].split(",")],
        )


@dataclasses.dataclass(slots=True)
class CustomFieldValue:
    custom_field_id: int
    values: list[str]
    scope: CustomFieldScope
    identifier: int

    @classmethod
    def from_json(cls, json_data: SingleJson) -> CustomFieldValue:
        return cls(
            custom_field_id=json_data["customFieldId"],
            values=json_data["values"],
            scope=CustomFieldScope(json_data["scope"]),
            identifier=json_data["identifier"],
        )


class SmimeType(Enum):
    ENCRYPTED = "encrypted"
    SIGNED = "signed"


@dataclasses.dataclass(slots=True)
class SmimeEmailConfig:
    email: email.message.Message
    private_key_b64: str
    certificate_b64: str
    ca_certificate_b64: str


@dataclasses.dataclass(slots=True)
class DynamicParameter:
    key: str
    value: str

    @classmethod
    def from_json(cls, json_data: SingleJson) -> DynamicParameter:
        return cls(
            key=json_data["key"],
            value=json_data["value"],
        )


@dataclasses.dataclass(slots=True)
class EnvironmentData:
    environment: str
    dynamic_parameters: list[DynamicParameter] = dataclasses.field(default_factory=list)
    base64_image: str | None = None
    platform: int | None = None

    @classmethod
    def from_json(cls, json_data: SingleJson) -> EnvironmentData:
        return cls(
            environment=json_data["environment"],
            dynamic_parameters=[
                DynamicParameter.from_json(p) for p in json_data.get("dynamicParameters", [])
            ],
            base64_image=json_data.get("base64Image"),
            platform=json_data.get("platform"),
        )


@dataclasses.dataclass(slots=True)
class CaseSLAInfo:
    expiration_time_ms: int | None = None
    critical_expiration_time_ms: int | None = None
    expiration_status: int | None = None
    last_pause_remaining_time_ms: int | None = None

    @classmethod
    def from_json(cls, json_data: SingleJson) -> CaseSLAInfo:
        return cls(
            expiration_time_ms=json_data.get("expirationTimeMs"),
            critical_expiration_time_ms=json_data.get("criticalExpirationTimeMs"),
            expiration_status=json_data.get("expirationStatus"),
            last_pause_remaining_time_ms=json_data.get("lastPauseRemainingTimeMs"),
        )


@dataclasses.dataclass(slots=True)
class CaseOverviewInfo:
    id: int
    create_time_ms: int
    update_time_ms: int
    display_id: str
    display_name: str
    alert_count: int
    stage: str
    priority: CasePriority
    important: bool
    description: str | None = None
    type: int | None = None
    assignee_full_name: str | None = None
    environment_data: EnvironmentData | None = None
    status: CaseDataStatus | None = None
    score: int | None = None
    case_sla: CaseSLAInfo | None = None
    alerts_sla: CaseSLAInfo | None = None
    incident: bool | None = None
    has_suspicious_entity: bool | None = None
    workflow_status: int | None = None
    tags: list[str] = dataclasses.field(default_factory=list)
    products: list[str] = dataclasses.field(default_factory=list)
    touched: bool | None = None
    merged: bool | None = None
    has_incident: bool | None = None
    alert_names: list[str] = dataclasses.field(default_factory=list)

    @classmethod
    def from_json(cls, json_data: SingleJson) -> CaseOverviewInfo:
        env_data_json = json_data.get("environmentData")
        case_sla_json = json_data.get("caseSla")
        alerts_sla_json = json_data.get("alertsSla")

        return cls(
            id=json_data["id"],
            create_time_ms=json_data["createTimeMs"],
            update_time_ms=json_data["updateTimeMs"],
            display_id=json_data["displayId"],
            display_name=json_data["displayName"],
            alert_count=json_data["alertCount"],
            stage=json_data["stage"],
            priority=CasePriority(json_data["priority"]),
            important=json_data["important"],
            description=json_data.get("description"),
            type=json_data["type"],
            assignee_full_name=json_data.get("assigneeFullName"),
            environment_data=(EnvironmentData.from_json(env_data_json) if env_data_json else None),
            status=CaseDataStatus(json_data["status"]),
            score=json_data.get("score"),
            case_sla=CaseSLAInfo.from_json(case_sla_json) if case_sla_json else None,
            alerts_sla=(CaseSLAInfo.from_json(alerts_sla_json) if alerts_sla_json else None),
            incident=json_data.get("incident"),
            has_suspicious_entity=json_data.get("hasSuspiciousEntity"),
            workflow_status=json_data.get("workflowStatus"),
            tags=json_data.get("tags", []),
            products=json_data.get("products", []),
            touched=json_data.get("touched"),
            merged=json_data.get("merged"),
            has_incident=json_data.get("hasIncident"),
            alert_names=json_data.get("alertNames", []),
        )


@dataclasses.dataclass(slots=True)
class EventCard:
    case_id: int
    alert_identifier: str
    event_id: str
    name: str
    time: int
    product: str
    port: str
    outcome: str
    artifact_entities: list[SingleJson]
    fields: list[SingleJson]

    @classmethod
    def from_json(cls, event_data: SingleJson) -> EventCard:
        return cls(
            case_id=event_data.get("caseId", event_data.get("case_id")),
            alert_identifier=event_data.get("alertIdentifier", event_data.get("alert_identifier")),
            event_id=event_data.get("identifier", event_data.get("event_id")),
            name=event_data.get("name", event_data.get("eventName")),
            time=event_data["time"],
            product=event_data["product"],
            port=event_data["port"],
            outcome=event_data["outcome"],
            artifact_entities=event_data.get("artifactEntities", [])
            or event_data.get("artificats"),
            fields=event_data.get("fields", []),
        )

    def to_json(self) -> SingleJson:
        return {
            "caseId": self.case_id,
            "alertIdentifier": self.alert_identifier,
            "eventId": self.event_id,
            "name": self.name,
            "time": self.time,
            "product": self.product,
            "artifactEntities": self.artifact_entities,
        }


@dataclasses.dataclass(slots=True)
class Entity:
    raw_data: SingleJson
    case_id: int
    entity_type: str | None

    enriched: bool
    artifact: bool
    vulnerable: bool
    suspicious: bool
    attacker: bool
    pivot: bool
    internal: bool
    manually_created: bool

    fields: list[SingleJson]

    @classmethod
    def from_json(cls, entity_response: SingleJson) -> Entity:
        if isinstance(entity_response, str):
            raw_data = json.loads(entity_response)
        else:
            raw_data = entity_response

        return cls(
            raw_data=raw_data,
            case_id=raw_data.get("caseId", raw_data.get("case_id", -1)),
            entity_type=raw_data.get("entityType", raw_data.get("type")),
            enriched=raw_data.get("isEnriched", raw_data.get("enriched", False)),
            artifact=raw_data.get("isArtifact", raw_data.get("artifact", False)),
            vulnerable=raw_data.get("isVulnerable", raw_data.get("vulnerable", False)),
            suspicious=raw_data.get("isSuspicious", raw_data.get("suspicious", False)),
            attacker=raw_data.get("isAttacker", raw_data.get("attacker", False)),
            pivot=raw_data.get("isPivot", raw_data.get("pivot", False)),
            internal=raw_data.get("isInternal", raw_data.get("internal", False)),
            manually_created=raw_data.get(
                "isManuallyCreated", raw_data.get("manuallyCreated", False)
            ),
            fields=raw_data.get("fieldsGroups", raw_data.get("fields", [])),
        )

    def to_json(self) -> SingleJson:
        entity_json = {
            "caseId": self.raw_data.pop("caseId", self.case_id),
            "type": self.raw_data.pop("entityType", self.raw_data.pop("type", self.entity_type)),
            "enriched": self.raw_data.pop("isEnriched", self.enriched),
            "artifact": self.raw_data.pop("isArtifact", self.artifact),
            "vulnerable": self.raw_data.pop("isVulnerable", self.vulnerable),
            "suspicious": self.raw_data.pop("isSuspicious", self.suspicious),
            "attacker": self.raw_data.pop("isAttacker", self.attacker),
            "pivot": self.raw_data.pop("isPivot", self.pivot),
            "internal": self.raw_data.pop("isInternal", self.internal),
            "manuallyCreated": self.raw_data.pop("isManuallyCreated", self.manually_created),
            "fields": self.raw_data.pop("fieldsGroups", self.raw_data.pop("fields", self.fields)),
        }

        return {
            **entity_json,
            **self.raw_data,
        }


@dataclasses.dataclass(slots=True)
class WallData:
    raw_data: SingleJson
    case_id: int
    activity_kind: str | int | None
    activity_data_json: str | None
    favorite: bool

    @classmethod
    def from_json(cls, data: SingleJson) -> WallData:
        if isinstance(data, str):
            raw_data = json.loads(data)
        else:
            raw_data = data

        legacy_kind = raw_data.get("activityKind")
        converted_kind = None
        if isinstance(legacy_kind, int):
            kind_map = {
                6: "CaseUpdated",
                1: "CaseComment",
                2: "CaseInsight",
            }
            converted_kind = kind_map.get(legacy_kind, legacy_kind)

        activity_data_json = raw_data.get("activityDataJson")
        if not activity_data_json:
            activity_data_json = json.dumps({
                "kind": raw_data.get("type"),
                "comment": raw_data.get("description"),
                "skipComment": None,
                "newValueJson": raw_data.get("newValue"),
                "activityDescription": None,
            })

        return cls(
            raw_data=raw_data,
            case_id=raw_data.get("caseId", -1),
            activity_kind=raw_data.get("activityKind", converted_kind),
            activity_data_json=activity_data_json,
            favorite=raw_data.get("isFavorite", raw_data.get("favorite", False)),
        )

    def to_json(self) -> SingleJson:
        wall_json = {
            "caseId": self.raw_data.pop("caseId", self.case_id),
            "activityKind": self.raw_data.pop("activityKind", self.activity_kind),
            "activityDataJson": self.raw_data.pop("activityDataJson", self.activity_data_json),
            "favorite": self.raw_data.pop("isFavorite", self.favorite),
        }

        return {
            **wall_json,
            **self.raw_data,
        }


@dataclasses.dataclass(slots=True)
class EntityCard:
    identifier: str
    entity_type: str
    is_suspicious: str
    linked_entities: list[str]

    @classmethod
    def from_json(cls, entity_data: SingleJson) -> EntityCard:
        return cls(
            identifier=entity_data["identifier"],
            entity_type=entity_data.get("type", entity_data.get("entity_type")),
            is_suspicious=entity_data.get("suspicious", entity_data.get("is_suspicious")),
            linked_entities=entity_data.get("linkedEntities", entity_data.get("linked_entities")),
        )

    def to_json(self) -> SingleJson:
        return {
            "identifier": self.identifier,
            "type": self.entity_type,
            "suspicious": self.is_suspicious,
            "linkedEntities": self.linked_entities,
        }


class DataAccessContext:
    def __init__(self, global_access: bool, assigned_scopes: list[Any]):
        # type: (bool, List[Any]) -> None
        self.global_access = global_access
        self.assigned_scopes = assigned_scopes

    @classmethod
    def from_json(cls, json_data: SingleJson) -> DataAccessContext:
        return cls(
            global_access=json_data.get("globalAccess", False),
            assigned_scopes=json_data.get("assignedScopes", []),
        )

    def to_json(self) -> dict:
        return {
            "globalAccess": self.global_access,
            "assignedScopes": self.assigned_scopes,
        }


class UserDetails:
    def __init__(
        self,
        id_: int,
        creation_time_unix_time_in_ms: int,
        modification_time_unix_time_in_ms: int,
        permission_group: str,
        permission_groups: list[str],
        soc_roles: list[str],
        is_disabled: bool,
        login_identifier: str,
        first_name: str,
        last_name: str,
        permission_type: int,
        role: int,
        soc_role_id: int,
        soc_role_ids: list[int],
        email: str,
        user_name: str,
        user_type: int,
        identity_provider: int,
        provider_name: str,
        advanced_reports_access: int,
        account_state: int,
        last_login_time: int,
        previous_login_time: int,
        last_password_change_time: int,
        last_password_change_notification_time: int,
        login_wrong_password_count: int,
        is_deleted: bool,
        deletion_time_unix_time_in_ms: int,
        environments: list[str],
        allowed_platforms: list[int],
        data_access_context: DataAccessContext,
        soc_role: str | None,
        image_base64: str | None,
    ):
        self.id_ = id_
        self.creation_time_unix_time_in_ms = creation_time_unix_time_in_ms
        self.modification_time_unix_time_in_ms = modification_time_unix_time_in_ms
        self.permission_group = permission_group
        self.permission_groups = permission_groups
        self.soc_role = soc_role
        self.soc_roles = soc_roles
        self.is_disabled = is_disabled
        self.login_identifier = login_identifier
        self.first_name = first_name
        self.last_name = last_name
        self.permission_type = permission_type
        self.role = role
        self.soc_role_id = soc_role_id
        self.soc_role_ids = soc_role_ids
        self.email = email
        self.user_name = user_name
        self.image_base64 = image_base64
        self.user_type = user_type
        self.identity_provider = identity_provider
        self.provider_name = provider_name
        self.advanced_reports_access = advanced_reports_access
        self.account_state = account_state
        self.last_login_time = last_login_time
        self.previous_login_time = previous_login_time
        self.last_password_change_time = last_password_change_time
        self.last_password_change_notification_time = last_password_change_notification_time
        self.login_wrong_password_count = login_wrong_password_count
        self.is_deleted = is_deleted
        self.deletion_time_unix_time_in_ms = deletion_time_unix_time_in_ms
        self.environments = environments
        self.allowed_platforms = allowed_platforms
        self.data_access_context = data_access_context

    @classmethod
    def from_json(cls, user_details_json: SingleJson) -> UserDetails:
        data_access_context_json = user_details_json.get("dataAccessContext", {})
        data_access_context = DataAccessContext.from_json(data_access_context_json)

        return cls(
            id_=user_details_json.get("id"),
            creation_time_unix_time_in_ms=user_details_json.get("creationTimeUnixTimeInMs", 0),
            modification_time_unix_time_in_ms=user_details_json.get(
                "modificationTimeUnixTimeInMs", 0
            ),
            permission_group=user_details_json.get("permissionGroup", ""),
            permission_groups=user_details_json.get("permissionGroups", []),
            soc_role=user_details_json.get("socRole", None),
            soc_roles=user_details_json.get("socRoles", []),
            is_disabled=user_details_json.get("isDisabled", False),
            login_identifier=user_details_json.get("loginIdentifier"),
            first_name=user_details_json.get("firstName"),
            last_name=user_details_json.get("lastName"),
            permission_type=user_details_json.get("permissionType", 0),
            role=user_details_json.get("role", None),
            soc_role_id=user_details_json.get("socRoleId", None),
            soc_role_ids=user_details_json.get("socRoleIds", []),
            email=user_details_json.get("email"),
            user_name=user_details_json.get("userName", user_details_json.get("displayName")),
            image_base64=user_details_json.get("imageBase64", None),
            user_type=user_details_json.get("userType", None),
            identity_provider=user_details_json.get("identityProvider", None),
            provider_name=user_details_json.get("providerName"),
            advanced_reports_access=user_details_json.get("advancedReportsAccess", 0),
            account_state=user_details_json.get("accountState"),
            last_login_time=user_details_json.get("lastLoginTime"),
            previous_login_time=user_details_json.get("previousLoginTime", None),
            last_password_change_time=user_details_json.get("lastPasswordChangeTime", None),
            last_password_change_notification_time=user_details_json.get(
                "lastPasswordChangeNotificationTime", None
            ),
            login_wrong_password_count=user_details_json.get("loginWrongPasswordCount", None),
            is_deleted=user_details_json.get("isDeleted", False),
            deletion_time_unix_time_in_ms=user_details_json.get("deletionTimeUnixTimeInMs", None),
            environments=user_details_json.get("environments", []),
            allowed_platforms=user_details_json.get("allowedPlatforms", []),
            data_access_context=data_access_context,
        )

    def to_json(self) -> SingleJson:
        return {
            "id": self.id_,
            "creationTimeUnixTimeInMs": self.creation_time_unix_time_in_ms,
            "modificationTimeUnixTimeInMs": self.modification_time_unix_time_in_ms,
            "permissionGroup": self.permission_group,
            "permissionGroups": self.permission_groups,
            "socRole": self.soc_role,
            "socRoles": self.soc_roles,
            "isDisabled": self.is_disabled,
            "loginIdentifier": self.login_identifier,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "permissionType": self.permission_type,
            "role": self.role,
            "socRoleId": self.soc_role_id,
            "socRoleIds": self.soc_role_ids,
            "email": self.email,
            "userName": self.user_name,
            "imageBase64": self.image_base64,
            "userType": self.user_type,
            "identityProvider": self.identity_provider,
            "providerName": self.provider_name,
            "advancedReportsAccess": self.advanced_reports_access,
            "accountState": self.account_state,
            "lastLoginTime": self.last_login_time,
            "previousLoginTime": self.previous_login_time,
            "lastPasswordChangeTime": self.last_password_change_time,
            "lastPasswordChangeNotificationTime": (self.last_password_change_notification_time),
            "loginWrongPasswordCount": self.login_wrong_password_count,
            "isDeleted": self.is_deleted,
            "deletionTimeUnixTimeInMs": self.deletion_time_unix_time_in_ms,
            "environments": self.environments,
            "allowedPlatforms": self.allowed_platforms,
            "dataAccessContext": self.data_access_context.to_json(),
        }


class InternalDomain:
    def __init__(
        self,
        alias_name: str,
        id_: int,
        domain_display_name: str,
        environments_json: str,
        creation_time_unix_time_in_ms: int,
        modification_time_unix_time_in_ms: int,
    ):
        self.alias_name = alias_name
        self.id_ = id_
        self.domain_display_name = domain_display_name
        self.environments_json = environments_json
        self.creation_time_unix_time_in_ms = creation_time_unix_time_in_ms
        self.modification_time_unix_time_in_ms = modification_time_unix_time_in_ms

    @classmethod
    def from_json(cls, json_data: SingleJson) -> InternalDomain:
        """Creates an InternalDomain object from a JSON dictionary.

        Args:
            json_data (SingleJson):  A dictionary containing the internal domain data.

        Returns:
            An InternalDomain object.

        """
        return cls(
            alias_name=json_data.get("name", json_data.get("alias")),
            id_=json_data.get("id"),
            domain_display_name=json_data.get("displayName", json_data.get("domain")),
            environments_json=json_data.get("environmentsJson", json_data.get("environments", [])),
            creation_time_unix_time_in_ms=json_data.get("creationTimeUnixTimeInMs", 0),
            modification_time_unix_time_in_ms=json_data.get("modificationTimeUnixTimeInMs", 0),
        )

    def to_json(self) -> SingleJson:
        """Converts the InternalDomain object to a JSON-serializable dictionary."""
        return {
            "alias": self.alias_name,
            "id": self.id_,
            "domain": self.domain_display_name,
            "environments": self.environments_json,
            "creationTimeUnixTimeInMs": self.creation_time_unix_time_in_ms,
            "modificationTimeUnixTimeInMs": self.modification_time_unix_time_in_ms,
        }


@dataclasses.dataclass(slots=True)
class EmailTemplate:
    """Represents an email template."""

    template_type: int | str
    name: str
    content: str
    creator_user_name: str
    for_migration: bool
    environments: list[str]
    _id: int
    creation_time_unix_time_in_ms: int
    modification_time_unix_time_in_ms: int

    def to_json(self) -> dict:
        """Converts the EmailTemplate object to a JSON-serializable dictionary."""
        return {
            "type": self.template_type,
            "name": self.name,
            "content": self.content,
            "creatorUserName": self.creator_user_name,
            "forMigration": self.for_migration,
            "environments": self.environments,
            "id": self._id,
            "creationTimeUnixTimeInMs": self.creation_time_unix_time_in_ms,
            "modificationTimeUnixTimeInMs": self.modification_time_unix_time_in_ms,
        }

    @classmethod
    def from_json(cls, data: SingleJson) -> EmailTemplate:
        """Creates an EmailTemplate object from a JSON dictionary.

        Args:
            data (SingleJson): A dictionary containing the email template data.

        Returns:
            An EmailTemplate object.

        """
        return cls(
            template_type=data.get("type", data.get("templateType")),
            name=data.get("displayName", data.get("name")),
            content=data.get("content", "{}"),
            creator_user_name=data.get("creatorUserName", data.get("author")),
            for_migration=data.get("forMigration", False),
            environments=data.get("environments", []),
            _id=data.get("id"),
            creation_time_unix_time_in_ms=data.get("creationTimeUnixTimeInMs"),
            modification_time_unix_time_in_ms=data.get("modificationTimeUnixTimeInMs"),
        )


@dataclasses.dataclass(slots=True)
class AttachmentMetadata:
    raw_data: SingleJson

    @classmethod
    def from_json(cls, result_data: SingleJson) -> Self:
        """Creates an AttachmentMetadata object from a JSON dictionary.

        Args:
            data (SingleJson): A dictionary containing the attachment metadata.

        Returns:
            An AttachmentMetadata object.

        """
        return cls(raw_data=result_data)

    def to_json(self) -> SingleJson:
        """Converts the AttachmentMetadata object to a JSON-serializable dictionary."""
        id_ = self.raw_data.pop("id", None)
        type_ = self.raw_data.pop("type", 4)
        description = self.raw_data.pop("comment", self.raw_data.pop("description", ""))
        evidence_thumbnail_base64 = self.raw_data.pop("evidence_thumbnail_base64", None)
        creator_user_id = self.raw_data.pop("user", self.raw_data.pop("creator_user_id", None))
        case_id = self.raw_data.pop("case", self.raw_data.pop("case_id", -1))
        is_favorite = self.raw_data.pop("isFavorite", self.raw_data.pop("is_favorite", False))
        update_time = self.raw_data.pop(
            "updateTime", self.raw_data.pop("modification_time_unix_time_in_ms", -1)
        )
        create_time = self.raw_data.pop(
            "createTime", self.raw_data.pop("creation_time_unix_time_in_ms", -1)
        )
        attachment_data = self.raw_data.pop("caseAttachment", {})
        evidence_name = attachment_data.pop("fileName", self.raw_data.pop("evidence_name", None))
        evidence_id = attachment_data.pop("attachmentId", self.raw_data.pop("evidence_id", 0))
        file_type = attachment_data.pop("fileType", self.raw_data.pop("file_type", None))
        alert_identifier = self.raw_data.pop(
            "alertIdentifier", self.raw_data.pop("alert_identifier", None)
        )

        return {
            "caseId": case_id,
            "id": id_,
            "type": type_,
            "description": description,
            "evidenceName": evidence_name,
            "fileType": file_type,
            "alertIdentifier": alert_identifier,
            "comment": description,
            "commentForClient": description,
            "creationTimeUnixTimeInMs": create_time,
            "modificationTimeUnixTimeInMs": update_time,
            "modificationTimeUnixTimeInMsForClient": update_time,
            "isFavorite": is_favorite,
            "evidenceThumbnailBase64": evidence_thumbnail_base64,
            "evidenceId": evidence_id,
            "creatorUserId": creator_user_id,
        }


@dataclasses.dataclass(slots=True)
class CreateEntity:
    case_id: int
    alert_identifier: str
    entity_type: str
    entity_identifier: str
    entity_to_connect_regex: str
    types_to_connect: list[str] | None = None
    is_primary_link: bool = False
    is_directional: bool = False

    def to_json(self) -> SingleJson:
        """Converts the CreateEntity object to a JSON-serializable dictionary"""
        return {
            "caseId": f"{self.case_id}",
            "alertIdentifier": self.alert_identifier,
            "entityType": self.entity_type,
            "entityIdentifier": self.entity_identifier,
            "entityToConnectRegEx": self.entity_to_connect_regex,
            "typesToConnect": self.types_to_connect or [],
            "isPrimaryLink": self.is_primary_link,
            "isDirectional": self.is_directional,
        }
