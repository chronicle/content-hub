# Copyright 2026 Google LLC
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

# pylint: disable=invalid-name
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum  # pylint: disable=no-name-in-module
from typing import Any

from dataclass_wizard import IS
from dataclass_wizard.serial_json import JSONWizard

from .exceptions import GoogleCloudIdentityApiException


class PolicyType(StrEnum):
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class PolicySettingType(StrEnum):
    DLP_RULE = "settings/rule.dlp"
    WORD_LIST_DETECTOR = "settings/detector.word_list"
    REGULAR_EXPRESSION_DETECTOR = "settings/detector.regular_expression"
    URL_LIST_DETECTOR = "settings/detector.url_list"


class PolicySettingState(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PolicySettingTriggers(StrEnum):
    CHROME_FILE_UPLOAD = "google.workspace.chrome.file.v1.upload"
    CHROME_FILE_DOWNLOAD = "google.workspace.chrome.file.v1.download"
    CHROME_WEB_CONTENT_UPLOAD = "google.workspace.chrome.web_content.v1.upload"
    CHROME_PAGE_PRINT = "google.workspace.chrome.page.v1.print"
    CHROME_URL_NAVIGATION = "google.workspace.chrome.url.v1.navigation"
    CHROMEOS_FILE_TRANSFER = "google.workspace.chromeos.file.v1.transfer"
    CHAT_MESSAGE_SEND = "google.workspace.chat.message.v1.send"
    CHAT_ATTACHMENT_UPLOAD = "google.workspace.chat.attachment.v1.upload"
    DRIVE_FILE_SHARE = "google.workspace.drive.file.v1.share"
    GMAIL_EMAIL_SEND = "google.workspace.gmail.email.v1.send"


@dataclass
class PoliciesRequestQuery(JSONWizard):
    page_size: int | None = None
    page_token: str | None = None
    # CommonExpressionLanguage
    # Only supports settings type and customer id
    # https://docs.cloud.google.com/identity/docs/how-to/list-get-policies
    filter: str | None = None


@dataclass
class Policy(JSONWizard):
    # https://docs.cloud.google.com/identity/docs/reference/rest/v1beta1/policies
    class Meta(JSONWizard.Meta):
        """Configuration for Policy serialization."""

        skip_if = IS(None)

    policy_query: dict
    setting: dict | PolicySetting
    type: PolicyType
    customer: str = None
    name: str | None = None

    def get_id(self) -> str:
        """Get the ID of the policy.

        Returns:
            The policy ID.

        Raises:
            GoogleCloudIdentityApiException: If the policy has not been created yet.

        """
        if self.name:
            return self.name.rsplit("/", maxsplit=1)[-1]
        msg = "Policy not created yet."
        raise GoogleCloudIdentityApiException(msg)

    def get_customer_id(self) -> str:
        """Get the customer ID of the policy.

        Returns:
            The customer ID.

        """
        return self.customer.rsplit("/", maxsplit=1)[-1]

    def get_org_unit_id(self) -> str:
        """Get the organizational unit ID of the policy.

        Returns:
            The organizational unit ID.

        """
        return self.policy_query.get("orgUnit", "").rsplit("/", maxsplit=1)[-1]

    def get_display_name(self) -> str:
        """Get the display name of the policy setting.

        Returns:
            The display name.

        """
        if isinstance(self.setting, PolicySetting):
            return self.setting.value.display_name
        return self.setting.get("value", {}).get("displayName", None)

    def match_setting_model(self) -> None:
        """Cast in place the policy's setting to a specific PolicySettingValue subclass."""
        self.setting = PolicySetting.from_setting_value_dict(self.setting)


@dataclass
class PolicySettingValue(JSONWizard):
    display_name: str
    description: str = field(default=None)


@dataclass
class DLPRulePolicySettingValue(PolicySettingValue):
    triggers: list[PolicySettingTriggers | str] = field(default_factory=list)
    state: PolicySettingState = PolicySettingState.ACTIVE
    action: dict = field(default_factory=dict)
    condition: dict = field(default_factory=dict)


@dataclass
class WordListDetectorPolicySettingValue(PolicySettingValue):
    word_list: dict = field(default_factory=dict)

    @staticmethod
    def from_list_of_words(
        words: list[str], **kwargs: object
    ) -> WordListDetectorPolicySettingValue:
        """Create a WordListDetectorPolicySettingValue from a list of words.

        Args:
            words: A list of words to detect.
            **kwargs: Additional keyword arguments for PolicySettingValue.

        Returns:
            A new WordListDetectorPolicySettingValue instance.

        """
        return WordListDetectorPolicySettingValue(word_list={"words": words}, **kwargs)


@dataclass
class RegularExpressionDetectorPolicySettingValue(PolicySettingValue):
    regular_expression: dict = field(default_factory=dict)

    @staticmethod
    def from_regular_expression(
        regexp: str, **kwargs: object
    ) -> RegularExpressionDetectorPolicySettingValue:
        """Create a RegularExpressionDetectorPolicySettingValue from a regular expression.

        Args:
            regexp: The regular expression to detect.
            **kwargs: Additional keyword arguments for PolicySettingValue.

        Returns:
            A new RegularExpressionDetectorPolicySettingValue instance.

        """
        return RegularExpressionDetectorPolicySettingValue(
            regular_expression={"expression": regexp}, **kwargs
        )


@dataclass
class URLListDetectorPolicySettingValue(PolicySettingValue):
    url_list: dict = field(default_factory=dict)

    @staticmethod
    def from_list_of_words(
        urls: list[str], **kwargs: object
    ) -> URLListDetectorPolicySettingValue:
        """Create a URLListDetectorPolicySettingValue from a list of URLs.

        Args:
            urls: A list of URLs to detect.
            **kwargs: Additional keyword arguments for PolicySettingValue.

        Returns:
            A new URLListDetectorPolicySettingValue instance.

        """
        return URLListDetectorPolicySettingValue(url_list={"urls": urls}, **kwargs)


@dataclass
class PolicySetting:
    type: PolicySettingType
    value: PolicySettingValue

    @staticmethod
    def _class_to_setting_type(value: PolicySettingValue) -> PolicySettingType:
        if isinstance(value, DLPRulePolicySettingValue):
            return PolicySettingType.DLP_RULE
        if isinstance(value, WordListDetectorPolicySettingValue):
            return PolicySettingType.WORD_LIST_DETECTOR
        if isinstance(value, RegularExpressionDetectorPolicySettingValue):
            return PolicySettingType.REGULAR_EXPRESSION_DETECTOR
        if isinstance(value, URLListDetectorPolicySettingValue):
            return PolicySettingType.URL_LIST_DETECTOR

        msg = f"Unknown PolicySettingValue type: {type(value)}"
        raise TypeError(msg)

    @staticmethod
    def _setting_type_to_class(
        setting_type: PolicySettingType | str,
    ) -> type[PolicySettingValue]:
        mapping = {
            PolicySettingType.DLP_RULE: DLPRulePolicySettingValue,
            PolicySettingType.WORD_LIST_DETECTOR: WordListDetectorPolicySettingValue,
            PolicySettingType.REGULAR_EXPRESSION_DETECTOR:
                RegularExpressionDetectorPolicySettingValue,
            PolicySettingType.URL_LIST_DETECTOR: URLListDetectorPolicySettingValue,
        }
        if isinstance(setting_type, str):
            setting_type = PolicySettingType(setting_type)

        if setting_type not in mapping:
            msg = f"Unknown PolicySettingType: {setting_type}"
            raise TypeError(msg)
        return mapping[setting_type]

    @staticmethod
    def from_setting_value(value: PolicySettingValue) -> PolicySetting:
        """Create a PolicySetting from a PolicySettingValue.

        This factory method infers the policy setting type from the value's type.

        Args:
            value: The policy setting value.

        Returns:
            A new PolicySetting instance.

        """
        return PolicySetting(
            type=PolicySetting._class_to_setting_type(value), value=value
        )

    @classmethod
    def from_setting_value_dict(cls, policy_setting: dict[str, Any]) -> PolicySetting:
        """Create a PolicySetting from a dictionary representation of its value.

        This factory method uses the provided setting_type to determine the correct
        PolicySettingValue subclass and then deserializes the dictionary into it.

        Args:
            policy_setting: A dictionary representing the policy setting's value.

        Returns:
            A new PolicySetting instance.

        """
        constructor = cls._setting_type_to_class(policy_setting.get("type"))
        setting = constructor.from_dict(policy_setting.get("value", {}))
        return PolicySetting.from_setting_value(setting)


@dataclass
class OrgUnit(JSONWizard):
    # https://developers.google.com/workspace/admin/directory/reference/rest/v1/orgunits
    class Meta(JSONWizard.Meta):
        """Configuration for OrgUnit serialization."""

        skip_if = IS(None)
        recursive_classes = True

    name: str = None
    kind: str | None = None
    description: str | None = None
    etag: str | None = None
    block_inheritance: bool | None = None
    org_unit_id: str | None = None
    org_unit_path: str | None = None
    parent_org_unit_id: str | None = None
    parent_org_unit_path: str | None = None
    organization_units: list[OrgUnit] = None

    def get_org_unit_id(self) -> str:
        """Get the organizational unit ID.

        The ID is cleaned of any prefixes.

        Returns:
            The organizational unit ID.

        """
        return self.org_unit_id.replace("orgUnits/", "").replace("id:", "")


@dataclass
class User(JSONWizard):
    # Incomplete model all fields available at
    # https://developers.google.com/workspace/admin/directory/reference/rest/v1/users
    class Meta(JSONWizard.Meta):
        """Configuration for User serialization."""

        skip_if = IS(None)

    id: str
    customer_id: str


class Code(Enum):
    # https://github.com/googleapis/googleapis/blob/master/google/rpc/code.proto
    OK = 0
    CANCELLED = 1
    UNKNOWN = 2
    INVALID_ARGUMENT = 3
    DEADLINE_EXCEEDED = 4
    NOT_FOUND = 5
    ALREADY_EXISTS = 6
    PERMISSION_DENIED = 7
    RESOURCE_EXHAUSTED = 8
    FAILED_PRECONDITION = 9
    ABORTED = 10
    OUT_OF_RANGE = 11
    UNIMPLEMENTED = 12
    INTERNAL = 13
    UNAVAILABLE = 14
    DATA_LOSS = 15
    UNAUTHENTICATED = 16


@dataclass
class Status(JSONWizard):
    # Shared modification result response
    # https://docs.cloud.google.com/identity/docs/reference/rest/Shared.Types/Operation
    class Meta(JSONWizard.Meta):
        """Configuration for Status serialization."""

        skip_if = IS(None)

    code: Code | int
    message: str | None = None

    def validate(self) -> None:
        """Validate the operation.

        Raises:
            GoogleCloudIdentityApiException: If the operation code is not OK.

        """
        if self.code != Code.OK:
            msg = f"Operation failed: {self.message}"
            raise GoogleCloudIdentityApiException(msg)


@dataclass
class Operation(JSONWizard):
    # Shared modification result response
    # https://docs.cloud.google.com/identity/docs/reference/rest/Shared.Types/Operation
    class Meta(JSONWizard.Meta):
        """Configuration for Operation serialization."""

        skip_if = IS(None)

    done: bool
    error: Status | None = None
    name: str | None = None
    response: Any | None = None

    def validate(self) -> Operation:
        """Validate the operation.

        Returns:
            The valid operation.

        Raises:
            GoogleCloudIdentityApiException: If the operation is not done.

        """
        if not self.done:
            msg = f"Operation not done: {self.name}"
            raise GoogleCloudIdentityApiException(msg)
        if self.error:
            self.error.validate()
        return self
