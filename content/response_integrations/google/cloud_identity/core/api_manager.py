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

from __future__ import annotations

import logging
from enum import StrEnum  # pylint: disable=no-name-in-module
from typing import TYPE_CHECKING, Any

from .consts import DEFAULT_API_ROOT
from .datamodels import (
    DLPRulePolicySettingValue,
    OrgUnit,
    PoliciesRequestQuery,
    Policy,
    PolicySetting,
    PolicySettingTriggers,
    PolicySettingType,
    PolicySettingValue,
    PolicyType,
    URLListDetectorPolicySettingValue,
)
from .exceptions import (
    GoogleCloudAuthenticationError,
    GoogleCloudIdentityApiEntityNotFoundException,
    GoogleCloudIdentityApiException,
)
from .orgunits_api_resource import OrgUnitsApiResource
from .policies_api_resource import PoliciesApiResource

if TYPE_CHECKING:
    from collections.abc import Iterable

    from google.auth.transport.requests import AuthorizedSession


# pylint: disable=invalid-name
class _Prefix(StrEnum):
    POLICIES = "policies/"
    CUSTOMERS = "customers/"
    ORGANIZATION_UNITS = "orgUnits/"


class GoogleCloudIdentityApiManager:
    """Manager for interacting with the Google Cloud Identity Policies API."""

    def __init__(self, session: AuthorizedSession, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize the GoogleCloudIdentityApiManager.

        Args:
            session: The authorized session for API requests.
            **kwargs: Additional keyword arguments.

        """
        self._session = session
        self._logger = kwargs.get("logger", logging.getLogger(__name__))
        self._api_root = kwargs.get("api_root", DEFAULT_API_ROOT)
        self._policies_resource = kwargs.get(
            "policies_resource",
            PoliciesApiResource(self._session, self._api_root, logger=self._logger),
        )
        self._org_units_resource = kwargs.get(
            "orgunits_resource", OrgUnitsApiResource(self._session, logger=self._logger)
        )

    def test_connectivity(self) -> None:
        """Tests connectivity to the Google Cloud Identity Policies API.

        Raises:
            GoogleCloudIdentityApiException: If the test connectivity fails.

        """
        query = PoliciesRequestQuery(page_size=1)
        try:
            next(iter(self._policies_resource.list(query)))
        except StopIteration as e:
            msg = "Test connectivity failed."
            raise GoogleCloudIdentityApiException(msg) from e

    def fetch_policies_by_setting_type(
        self, setting_type: PolicySettingType
    ) -> Iterable[Policy]:
        """Fetch policies filtered by the specified setting type.

        Args:
            setting_type: The type of policy setting to filter by.

        Yields:
            Policies matching the setting type.

        """
        query = PoliciesRequestQuery(filter=f'setting.type.matches("{setting_type}")')
        yield from self._policies_resource.list(query)

    def fetch_policy(self, policy_id: str) -> Policy:
        """Fetch a single policy by its ID.

        Args:
            policy_id: The ID of the policy to fetch.

        Returns:
            The fetched policy.

        """
        policy_id = _remove_prefix(policy_id)
        return self._policies_resource.get(policy_id)

    def create_policy(self, policy: Policy) -> Policy:
        """Create a new policy.

        Args:
            policy: The policy to create.

        Returns:
            The created policy.

        """
        return self._policies_resource.create(policy)

    def list_policies(
        self,
        organization_unit_id: str,
        display_names: list[str],
        policy_type: PolicyType,
        setting_type: PolicySettingType | str,
    ) -> Iterable[Policy]:
        """Find the policies matching the specified criteria.

        Args:
            organization_unit_id: The organizational unit ID.
            display_names: The display names list of the policy to match.
            policy_type: The policy type: ADMIN or SYSTEM.
            setting_type: The setting type of the policy to match.

        Yields:
            The matching policy if found.

        """
        if not setting_type:
            self._logger.info("No setting type selected.")
            setting_type = ".*"

        query = PoliciesRequestQuery(
            filter=f'setting.type.matches("{setting_type}")', page_size=100
        )
        results = self._policies_resource.list(query)

        def _predicate(v: Policy) -> bool:
            if policy_type and v.type != policy_type:
                return False

            if organization_unit_id and v.get_org_unit_id() != organization_unit_id:
                return False

            if display_names and v.get_display_name() not in display_names:
                return False

            self._logger.info("Found policy: %s", v.get_id())
            return True

        results = filter(_predicate, results)

        yield from results

    def create_chrome_dlp_policy(
        self,
        organization_unit_id: str,
        rule_name: str,
        description: str,
        html_message_body: str,
        cel_condition: str,
    ) -> Policy:
        """Create a Chrome Data Loss Prevention (DLP) policy.

        Args:
            organization_unit_id: The organizational unit ID.
            rule_name: The name of the DLP rule.
            description: A description for the DLP rule.
            html_message_body: The custom end user message to display upon blocking.
            cel_condition: The CEL condition expression determining when to block.

        Returns:
            The created policy.

        """
        setting = DLPRulePolicySettingValue(
            display_name=rule_name,
            description=description,
            triggers=[PolicySettingTriggers.CHROME_URL_NAVIGATION],
            condition={"contentCondition": cel_condition},
            action={
                "chromeAction": {
                    "blockContent": {
                        "actionParams": {
                            "customEndUserMessage": {
                                "unsafeHtmlMessageBody": html_message_body
                            }
                        }
                    }
                },
            },
        )
        return self.create_policy_for_org_unit(
            organization_unit_id=organization_unit_id,
            setting=setting,
        )

    def create_url_list_detector_policy(
        self,
        organization_unit_id: str,
        rule_name: str,
        description: str,
        urls: list[str],
    ) -> Policy:
        """Create a URL list detector policy for URL navigation tracking/blocking.

        Args:
            organization_unit_id: The organizational unit ID.
            rule_name: The name of the detector rule.
            description: A description for the detector rule.
            urls: A list of words or URLs to match against.

        Returns:
            The created policy.

        """
        setting = URLListDetectorPolicySettingValue.from_list_of_words(
            display_name=rule_name, description=description, urls=urls
        )
        return self.create_policy_for_org_unit(
            organization_unit_id=organization_unit_id,
            setting=setting,
        )

    def update_url_list_detector_policy(
        self,
        policy_id: str,
        urls: list[str],
    ) -> Policy:
        """Update a URL list detector policy by appending to URL list.

        Args:
            policy_id: The ID of the policy to update.
            urls: A list of words or URLs to add to the detector rule.

        Returns:
            The updated policy.

        Raises:
            TypeError: If the setting type of the policy is not URL_LIST_DETECTOR.
            GoogleCloudAuthenticationError: If no URLs are found in the policy.

        """
        policy: Policy = self.fetch_policy(policy_id)
        policy.match_setting_model()
        if policy.setting.type != PolicySettingType.URL_LIST_DETECTOR:
            msg = (
                f"Setting type of policy {policy_id} "
                f"is not {PolicySettingType.URL_LIST_DETECTOR}"
            )
            raise TypeError(msg)
        policy_setting: URLListDetectorPolicySettingValue = policy.setting.value
        existing_urls = policy_setting.url_list.get("urls")
        if existing_urls:
            existing_urls.extend(urls)
        else:
            msg = "No URLs found in the policy."
            raise GoogleCloudAuthenticationError(msg)

        return self._policies_resource.patch(policy)

    def create_policy_for_org_unit(
        self, organization_unit_id: str, setting: PolicySettingValue
    ) -> Policy:
        """Create a policy specifically targeted at a given organizational unit.

        Args:
            organization_unit_id: The organizational unit ID.
            setting: The setting values for the policy.

        Returns:
            The created policy.

        """
        policy = Policy(
            type=PolicyType.ADMIN,
            policy_query={
                "query": f"entity.org_units.exists("
                f"org_unit, "
                f"org_unit.org_unit_id == orgUnitId('{organization_unit_id}')"
                f")",
                "orgUnit": _organization_unit_prefix(organization_unit_id),
                "sortOrder": 1,
            },
            setting=PolicySetting.from_setting_value(setting),
        )
        return self.create_policy(policy)

    def fetch_org_unit(self, directory_path_or_name: str = "/") -> OrgUnit:
        """Fetch an organizational unit by its directory path or name.

        Args:
            directory_path_or_name: The full path of the
                organizational unit or its name.

        Returns:
            The found organizational unit.

        Raises:
            GoogleCloudIdentityApiEntityNotFoundException: If the org unit is not found.

        """
        if directory_path_or_name.startswith("/"):
            org_units = self._org_units_resource.list(
                org_unit_path=directory_path_or_name
            ).organization_units
            org_unit = filter(
                lambda ou: ou.org_unit_path == directory_path_or_name, org_units
            )
        else:
            org_units = self._org_units_resource.list().organization_units
            org_unit = filter(lambda ou: ou.name == directory_path_or_name, org_units)

        org_unit = next(org_unit, None)
        if not org_unit:
            msg = f"OrgUnit not found at path: {directory_path_or_name}"
            raise GoogleCloudIdentityApiEntityNotFoundException(msg)
        return org_unit


def _customers_prefix(customer_id: str) -> str:
    return _prefix(customer_id, _Prefix.CUSTOMERS)


def _policies_prefix(policy_id: str) -> str:
    return _prefix(policy_id, _Prefix.POLICIES)


def _organization_unit_prefix(org_unit_id: str) -> str:
    return _prefix(org_unit_id, _Prefix.ORGANIZATION_UNITS)


def _remove_prefix(value: str) -> str:
    for prefix in [e.value for e in _Prefix]:
        if value.startswith(prefix):
            return value.rsplit("/", maxsplit=1)[-1]
    return value


def _prefix(value: str, prefix: _Prefix) -> str:
    if value and not value.startswith(prefix):
        value = prefix + value
    return value
