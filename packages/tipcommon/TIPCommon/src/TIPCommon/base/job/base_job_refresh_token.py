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

import collections
import csv
import re
from abc import abstractmethod
from io import StringIO
from typing import Generic

from .base_job import Job
from ..interfaces import ApiClient
from ...data_models import ConnectorCard, InstalledIntegrationInstance
from ...exceptions import RefreshTokenRenewalJobException
from ...rest.soar_api import (
    get_connector_cards,
    get_installed_integrations_of_environment,
)
from ...types import Contains


INTEGRATION_KEY = "integration"
SUPPORTED_PLATFORM_VERSION = "6.2.35.0"


SuccessFailureTuple = collections.namedtuple(
    "SuccessFailureTuple", ["success_list", "failure_list"]
)


class RefreshTokenRenewalJob(Job, Generic[ApiClient]):

    def __init__(self, name: str, integration_identifier: str) -> None:
        super().__init__(name)
        self.integration_identifier = integration_identifier

    @property
    def api_client(self) -> Contains[ApiClient]:
        return self._api_client

    @api_client.setter
    def api_client(self, value: Contains[ApiClient]) -> None:
        self._api_client = value

    @abstractmethod
    def _get_integration_envs(self) -> list[str]:
        """Gets the names of environments to refresh token for.

        Examples::

            Class MyJob(Job)
                ...

                # method override
                def _get_integration_envs(self) -> str:
                    return self.params.integration_environments
        Raises:
            NotImplementedError: If not overridden_

        Returns:
            str: Environment names.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_connector_names(self) -> list[str]:
        """Get the names of connectors to refresh the token.

        Examples::

            Class MyJob(Job)
                ...

                # method override
                def _get_connector_names(self) -> str:
                    return self.params.connector_names
        Raises:
            NotImplementedError: If not overridden_

        Returns:
            str: Connector names.
        """
        raise NotImplementedError

    @abstractmethod
    def _refresh_integration_token(self, instance_identifier: str) -> None:
        """Renew Refresh token and set it in integration configuration.

        Args:
            instance_identifier (str): integration instance identifier.
                e.g.: "ce0027a2-2b53-4cce-ad08-430df6d002f3"

        Raises:
            NotImplementedError: If not overridden

        Returns:
            None
        """
        raise NotImplementedError

    @abstractmethod
    def _refresh_connector_token(self, instance_identifier: str) -> None:
        """Renew Refresh token and set it in connector instance configuration.

        Args:
            instance_identifier (str): connector instance identifier.
                e.g.: "Test_OauthConnector_75098aae-de81-44cc-a807-4843d5ae7ea5"

        Raises:
            NotImplementedError: If not overridden

        Returns:
            None
        """
        raise NotImplementedError

    @abstractmethod
    def _build_manager_for_instance(
        self,
        instance_settings: dict[str, str],
    ) -> ApiClient | None:
        """Create manager instance objects.

        Examples::

            Class MyJob(Job)
                ...

                # method override
                def _build_manager_for_instance(
                    self,
                    instance_settings
                ) -> IntegrationManager:
                    return MyManager(...)
        Returns:
            The integration's manager

        Raises:
            NotImplementedError: If not overridden
        """
        raise NotImplementedError

    def _perform_job(self) -> None:
        """main method to get the instance settings and set the renewed refresh
        token in the configuration.

        Raises:
            Exception: exception to be raised if anything fails during execution
        """
        self._verify_platform_version()
        self.logger.info("Platform version validated.")
        integrations_result = self._fetch_integrations_to_update(
            environments=self._get_integration_envs(),
            integration_identifier=self.integration_identifier,
        )
        connectors_result = self._fetch_connectors_to_update(
            connector_names=self._get_connector_names(),
            integration_identifier=self.integration_identifier,
        )
        self._check_and_raise_if_instances_not_found(
            failed_to_find_environments=integrations_result.failure_list,
            failed_to_find_connectors=connectors_result.failure_list,
        )

        self._refresh_integrations_instance_token(integrations_result.success_list)
        self._refresh_connectors_token(connectors_result.success_list)

    def _verify_platform_version(self) -> None:
        """Verify SOAR platform version and compare with supported version for this
        job to run.

        Raises:
            RefreshTokenRenewalJobException: exception to be raised in case of
                version not supported.
        """
        supported_version_tuple = _version_string_to_tuple(SUPPORTED_PLATFORM_VERSION)
        current_version_str = self.soar_job.get_system_version()
        current_version_tuple = _version_string_to_tuple(current_version_str)

        if current_version_tuple < supported_version_tuple:
            raise RefreshTokenRenewalJobException(
                f"{self.error_msg} its supported on SOAR Platform version "
                f"{SUPPORTED_PLATFORM_VERSION} and higher."
            )

    def _fetch_integrations_to_update(
        self,
        environments: list[str],
        integration_identifier: str,
    ) -> SuccessFailureTuple:
        """Fetch all integrations installed for provided environments.

        Args:
            environments (list): instance environments list.
            integration_identifier (str): integration identifier.

        Returns:
            SuccessFailureTuple:
                success_list - A list of dictionary objects representing fetched
                    integration instances.
                failure_list - A list of environment names for which integrations
                    were not found.
        """
        fetched_integrations = []
        failed_to_find_environments = []

        for environment in environments:
            env_instances = get_installed_integrations_of_environment(
                chronicle_soar=self.soar_job,
                environment=environment,
                integration_identifier=integration_identifier,
            )

            if not env_instances:
                failed_to_find_environments.append(environment)
                continue

            fetched_integrations.extend(
                [
                    instance
                    for instance in env_instances
                    if instance.integration_identifier == integration_identifier
                ]
            )

        return SuccessFailureTuple(
            success_list=fetched_integrations,
            failure_list=failed_to_find_environments,
        )

    def _fetch_connectors_to_update(
        self,
        connector_names: list[str],
        integration_identifier: str,
    ) -> SuccessFailureTuple:
        """Fetch connector instances list for provided connector names.

        Args:
            connector_names (list[str]): connector names from parameter.
            integration_identifier (str): integration identifier

        Returns:
            SuccessFailureTuple:
                success_list - List of connector cards found for the provided connector
                    names.
                failure_list - List of connector names not found in the fetched
                    connector cards.
        """
        if not connector_names:
            return SuccessFailureTuple(
                success_list=[],
                failure_list=[],
            )

        response_json = get_connector_cards(
            self.soar_job,
            integration_name=integration_identifier,
        )
        connector_cards = [
            cards_json
            for cards_json in response_json
            if cards_json.integration == integration_identifier
        ]
        connector_display_names = [
            connector_card.display_name for connector_card in connector_cards
        ]
        not_found_connectors = set(connector_names).difference(connector_display_names)

        connectors_found = [
            connector_card
            for connector_card in connector_cards
            if connector_card.display_name in connector_names
        ]

        return SuccessFailureTuple(
            success_list=connectors_found,
            failure_list=list(not_found_connectors),
        )

    def _check_and_raise_if_instances_not_found(
        self,
        failed_to_find_environments: list[str],
        failed_to_find_connectors: list[str],
    ) -> None:
        """Check if instances (environments or connectors) failed to be found,
        and raise an exception with an error message if any instance is not found.

        Args:
            failed_to_find_environments (list[str]): A list of environment names that
                failed to be found.
            failed_to_find_connectors (list[str]): A list of connector names that failed
                to be found.

        Raises:
            RefreshTokenRenewalJobException: If any instance (environment or connector)
                is not found.
        """
        if failed_to_find_environments or failed_to_find_connectors:
            failed_instances = failed_to_find_environments + failed_to_find_connectors
            error_msg = (
                f"{self.error_msg} the specified instances "
                f'were not found: {", ".join(failed_instances)}'
            )
            raise RefreshTokenRenewalJobException(error_msg)

    def _refresh_integrations_instance_token(
        self,
        integrations: list[InstalledIntegrationInstance],
    ) -> None:
        """Refreshes the tokens for integration instances.

        Args:
            integrations (list[SingleJson]): A list of dictionaries representing
                integration instances.Each dictionary should have keys 'instanceName'
                and 'identifier'.

        Returns:
            None: This function does not return anything. It updates the tokens for
                integration instances.
        """
        for integration_payload in integrations:
            instance_name = integration_payload.instance_name
            identifier = integration_payload.identifier
            self.logger.info(
                f'Processing integration instance "{instance_name}" - "{identifier}"'
            )

            parameters = self._get_integration_configuration_params(identifier)
            self.api_client = self._build_manager_for_instance(parameters)
            self._refresh_integration_token(identifier)
            self._log_refresh_token_result(instance_name=instance_name)

    def _refresh_connectors_token(
        self,
        connector_cards: list[ConnectorCard],
    ) -> None:
        """Refreshes the tokens for connector instances.

        Args:
            connector_cards (list[ConnectorCard]): A list of dictionaries representing
                connector instances.Each dictionary should have keys 'displayName' and
                'identifier'.

        Returns:
            None: This function does not return anything. It updates the tokens for
                connector instances.
        """
        for connector_card in connector_cards:
            connector_name = connector_card.display_name
            identifier = connector_card.identifier
            self.logger.info(
                f'Processing connector "{connector_name}" instance - "{identifier}"'
            )

            parameters = self._get_connector_configuration_params(identifier)
            self.api_client = self._build_manager_for_instance(parameters)
            self._refresh_connector_token(identifier)
            self._log_refresh_token_result(
                instance_name=connector_card.display_name,
                instance_key="connector",
            )

    def _get_integration_configuration_params(
        self,
        integration_instance_identifier: str,
    ) -> dict[str, str]:
        return self.soar_job.get_configuration(
            provider=self.integration_identifier,
            integration_instance=integration_instance_identifier,
        )

    def _get_connector_configuration_params(
        self,
        connector_identifier: str,
    ) -> dict[str, str]:
        """Get connector configuration parameters.

        Args:
            connector_identifier (str): connector instance identifier.

        Returns:
            dict: dict of configuration details for connector instance.
        """
        params_list = self.soar_job.get_connector_parameters(connector_identifier)
        return {
            param_dict["paramName"]: param_dict["paramValue"]
            for param_dict in params_list
        }

    def _log_refresh_token_result(
        self,
        instance_name: str,
        instance_key: str = INTEGRATION_KEY,
    ) -> None:
        """Log the result of setting a refresh token for an instance.

        Args:
            instance_name (str): The name of the instance.
            instance_key (str): The key indicating the type of instance
                (e.g., 'integration' or 'connector').
        """
        self.logger.info(
            f"New refresh token is set for {instance_key} instance "
            f'"{instance_name}".'
        )

    def _init_api_clients(self) -> None:
        return


def validate_param_csv_to_multi_value(
    param_name: str,
    param_csv_value: str | None,
    delimiter: str = ",",
) -> list[str]:
    """Validate job parameters and return all values as a list.

    This function parses a comma-separated parameter value into a list of
    unique elements. If a single value is provided without double quotes and
    contains commas, it is considered a single value. If multiple values are
    provided enclosed in double quotes and separated by commas, each value
    will be returned as a list of unique elements.

    Args:
        param_name (str): The parameter key.
        param_csv_value (str | None): The parameter value provided in the
            job parameter. If None, an empty list is returned.

    Raises:
        ValueError: If the double quotes count is invalid or if some values
            are invalid or have mismatched double quotes.

    Returns:
        list[str]: A list of unique values provided in the job parameters.
            If no valid values are found, an empty list is returned.
    """
    if not param_csv_value:
        return []

    param_value = param_csv_value.strip()
    _validate_double_quotes_count(param_name, param_value)

    if '"' in param_value:
        param_value = re.sub(r'"\s+,', '",', param_value)
        param_value = re.sub(r',\s+"', ',"', param_value)
        csv_values = _get_parsed_csv_values(param_value, delimiter)
        param_values = _validate_values(
            param_name=param_name,
            param_value_str=param_value,
            csv_values=csv_values,
        )
    else:
        param_values = [param_value]

    return list(set(param_values))


def _validate_double_quotes_count(param_name: str, param_value: str) -> None:
    if param_value.count('"') % 2 == 1:
        raise ValueError(
            "Invalid input values: Unmatched double quotes for parameter "
            f'"{param_name}".'
        )


def _get_parsed_csv_values(
    param_csv_value: str,
    delimiter: str,
) -> list[str]:
    csv_file = StringIO(param_csv_value)
    csv_reader = csv.reader(csv_file, delimiter=delimiter)

    return next(csv_reader)


def _validate_values(
    param_name: str,
    param_value_str: str,
    csv_values: list[str],
) -> list[str]:
    """Validate the values for proper double quotes usage.

    Args:
        param_name (str): The parameter key.
        param_value_str (str): The parameter value.
        csv_values (list[str]): The list of parameter values.

    Raises:
        ValueError: If some values are invalid or have mismatched double quotes.
    """
    valid_values = []
    invalid_values = []
    for value in csv_values:
        if f'"{value}"' in param_value_str:
            valid_values.append(value)

        else:
            invalid_values.append(value)

    if invalid_values:
        raise ValueError(
            f'Parameter "{param_name}" values not provided in '
            f'double-quotes or incorrect: "{", ".join(invalid_values)}"'
        )

    return valid_values


def _version_string_to_tuple(version: str) -> tuple[int, ...]:
    return tuple(map(int, version.split(".")))
