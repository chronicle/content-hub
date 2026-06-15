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

import base64
import os
from enum import Enum
from typing import Any

import requests
from soar_sdk.SiemplifyDataModel import Attachment
from TIPCommon.rest.soar_api import (
    add_attachment_to_case_wall,
    get_attachments_metadata,
)
from TIPCommon.types import SingleJson

ORIG_EMAIL_DESCRIPTION = "This is the original message as EML"


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


class AttachmentsManager:
    def __init__(self, siemplify):
        self.siemplify = siemplify
        self.logger = siemplify.LOGGER
        self.alert_entities = self.get_alert_entities()
        self.attachments = self._get_attachments()

    def get_alert_entities(self):
        execution_scope = getattr(
            self.siemplify, "execution_scope", ExecutionScope.Alert
        )
        if execution_scope.value == ExecutionScope.Alert.value:
            alerts = [self.siemplify.current_alert]
        else:
            alerts = getattr(
                self.siemplify.case, "open_alerts", None
            ) or getattr(self.siemplify.case, "alerts", [])
        entities = []
        for alert in alerts:
            try:
                for entity in alert.entities:
                    entities.append(entity)
            except Exception as e:
                self.logger.error(
                    "Failed to retrieve entities for alert "
                    f"{alert.identifier}: {e}"
                )
        return entities

    def get_attachments(self):
        attachments = []
        for wall_item in self.attachments:
            if wall_item["type"] == 4:
                if not wall_item["alertIdentifier"]:
                    attachments.append(wall_item)

        return attachments

    def get_alert_attachments(self, alert_identifier: str):
        attachments = []
        for wall_item in self.attachments:
            if wall_item["type"] == 4:
                if alert_identifier == wall_item["alertIdentifier"]:
                    attachments.append(wall_item)
        return attachments

    def get_target_alerts(self) -> list[Any]:
        """Get the target alerts based on the execution scope.

        Returns:
            The target alerts.
        """
        execution_scope: Any = getattr(
            getattr(self.siemplify, "soar_action", self.siemplify),
            "execution_scope",
            ExecutionScope.Alert,
        )
        if execution_scope.value == ExecutionScope.Alert.value:
            return [self.siemplify.current_alert]

        return getattr(
            self.siemplify.case,
            "open_alerts",
            None,
        ) or getattr(self.siemplify.case, "alerts", [])

    def get_attachments_for_target_alerts(self) -> list[SingleJson]:
        """Get attachments for the target alerts.

        Returns:
            The list of attachments.
        """
        target_alerts: list[Any] = self.get_target_alerts()
        target_alert_ids: set[str] = {alert.identifier for alert in target_alerts}

        return [
            wall_item
            for wall_item in self.attachments
            if wall_item["type"] == 4
            and wall_item.get("alertIdentifier") in target_alert_ids
        ]

    def _get_attachments(self) -> list[SingleJson]:
        """Get attachments metadata from case wall and alert wall.

        Returns:
            list[SingleJson]: List of attachments metadata
        """
        return [
            attachment.to_json()
            for attachment in get_attachments_metadata(
                self.siemplify, self.siemplify.case.identifier
            )
        ]

    def add_attachment(
        self,
        filename,
        base64_blob,
        case_id,
        alert_identifier,
        description=None,
        is_favorite=False,
    ):
        """Add attachment
        :param file_path: {string} file path
        :param case_id: {string} case identifier
        :param alert_identifier: {string} alert identifier
        :param description: {string} attachment description
        :param is_favorite: {boolean} is attachment favorite
        :return: {dict} attachment_id
        """
        name, attachment_type = os.path.splitext(os.path.split(filename)[1])
        if not attachment_type:
            attachment_type = ".noext"
        attachment = Attachment(
            case_id,
            alert_identifier,
            base64_blob,
            attachment_type,
            name,
            description,
            is_favorite,
            len(base64.b64decode(base64_blob)),
            len(base64_blob),
        )
        attachment.case_identifier = case_id
        attachment.alert_identifier = alert_identifier
        result = None
        try:
            result = add_attachment_to_case_wall(self.siemplify, attachment)

        except requests.HTTPError as e:
            if "Attachment size" in str(e):
                raise ValueError(
                    "Attachment size should be < 5MB. Original file size: "
                    f"{attachment.orig_size}. Size after encoding: {attachment.size}.",
                ) from e

        return result
