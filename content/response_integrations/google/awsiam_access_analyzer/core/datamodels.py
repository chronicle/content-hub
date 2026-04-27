from __future__ import annotations
import copy
import datetime
import uuid

from TIPCommon import dict_to_flat
from . import consts
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time


class Analyzer:

    def __init__(
        self, arn=None, createdAt=None, name=None, status=None, type=None, **kwargs
    ):
        self.arn = arn
        self.createdAt = createdAt
        self.name = name
        self.status = status
        self.type = type


class Resource:
    def __init__(
        self,
        actions: list,
        analyzedAt: datetime,
        createdAt: datetime.datetime,
        isPublic: bool,
        status: str,
        updatedAt: datetime.datetime,
        resourceArn: str,
        resourceOwnerAccount: str,
        resourceType: str,
        **kwargs,
    ):
        self.actions = actions
        self.analyzedAt = analyzedAt
        self.createdAt = createdAt
        self.isPublic = isPublic
        self.status = status
        self.resourceArn = resourceArn
        self.resourceOwnerAccount = resourceOwnerAccount
        self.resourceType = resourceType
        self.updatedAt = updatedAt

        if self.analyzedAt:
            self.analyzedAt_timestamp = convert_datetime_to_unix_time(self.analyzedAt)
        else:
            self.analyzedAt_timestamp = 1

    def as_json(self):
        return {
            "analyzedAt": self.analyzedAt_timestamp,
            "isPublic": self.isPublic,
            "resourceArn": self.resourceArn,
            "resourceOwnerAccount": self.resourceOwnerAccount,
            "resourceType": self.resourceType,
        }


class Finding:
    def __init__(
        self,
        raw_data,
        action=None,
        analyzedAt=None,
        condition=None,
        createdAt=None,
        id=None,
        isPublic=None,
        principal=None,
        resource=None,
        resourceOwnerAccount=None,
        resourceType=None,
        sources=None,
        status=None,
        updatedAt=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.action = action
        self.analyzed_at = analyzedAt
        self.condition = condition
        self.created_at = createdAt
        self.resource_owner_account = resourceOwnerAccount
        self.id = id
        self.is_public = isPublic
        self.principal = principal
        self.resource = resource
        self.resource_type = resourceType
        self.sources = sources
        self.status = status
        self.updated_at = updatedAt

        try:
            self.created_time_ms = convert_datetime_to_unix_time(self.created_at)
        except Exception:
            self.created_time_ms = 1

        try:
            self.updated_time_ms = convert_datetime_to_unix_time(self.updated_at)
        except Exception:
            self.updated_time_ms = 1

    def as_event(self):
        event = copy.deepcopy(self.raw_data)
        event["createdAt"] = self.created_time_ms
        event["updatedAt"] = self.updated_time_ms
        return dict_to_flat(event)

    def as_alert_info(self, environment_common, severity=None):
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(self.as_event())
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.rule_generator = consts.RULE_GENERATOR_NAME
        alert_info.name = f"Access Analyzer: {self.resource}"
        alert_info.device_vendor = consts.VENDOR
        alert_info.device_product = consts.PRODUCT
        alert_info.priority = (
            consts.SEVERITIES.get(severity.upper(), -1) if severity else -1
        )
        alert_info.start_time = self.updated_time_ms
        alert_info.end_time = self.updated_time_ms
        alert_info.events = [self.as_event()]

        return alert_info
