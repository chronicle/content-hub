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

import json
import os
import pathlib
import re
from abc import ABC, abstractmethod
from typing import Any


def platform_supports_db(siemplify: object) -> bool:
    """Check whether the platform supports using DB or on prem.

    Args:
        siemplify (SiemplifyAction | SiemplifyJob | SiemplifyConnectorExecution):
            The SOAR SDK object instance

    Returns:
        bool: True if the platform supports DB, False otherwise

    """
    return bool(hasattr(siemplify, "set_connector_context_property"))


def validate_map_file_exists(map_file_path: str, logger: Any) -> None:
    try:
        if not pathlib.Path(map_file_path).exists():
            with pathlib.Path(map_file_path).open("w+", encoding="utf-8") as map_file:
                map_file.write(
                    json.dumps({
                        "Original environment name": "Desired environment name",
                        "Env1": "MyEnv1",
                    })
                )
                logger.info(f"Mapping file was created at {map_file}")
    except Exception as e:
        logger.error(f"Unable to create mapping file: {e}")
        logger.exception(e)


class GetEnvironmentCommonFactory:
    @staticmethod
    def create_environment_manager(
        siemplify: Any,
        environment_field_name: str,
        environment_regex_pattern: str,
        map_file: str = "map.json",
    ) -> EnvironmentHandle:
        """Get environment common
        :param siemplify: {siemplify} Siemplify object
        :param environment_field_name: {string} The environment field name
        :param environment_regex_pattern: {string} The environment regex pattern
        :param map_file: {string} The map file
        :return: {EnvironmentHandle}
        """
        if platform_supports_db(siemplify):
            return EnvironmentHandleForDBSystem(
                logger=siemplify.LOGGER,
                environment_field_name=environment_field_name,
                environment_regex=environment_regex_pattern,
                default_environment=siemplify.context.connector_info.environment,
            )

        map_file_path: str = os.path.join(siemplify.run_folder, map_file)
        validate_map_file_exists(map_file_path, siemplify.LOGGER)

        return EnvironmentHandleForFileSystem(
            map_file_path=map_file_path,
            logger=siemplify.LOGGER,
            environment_field_name=environment_field_name,
            environment_regex=environment_regex_pattern,
            default_environment=siemplify.context.connector_info.environment,
        )


class EnvironmentHandle(ABC):
    def __init__(
        self,
        logger: Any,
        environment_field_name: str,
        environment_regex: str,
        default_environment: str,
    ) -> None:
        self.logger = logger
        self.environment_field_name = environment_field_name
        self.environment_regex = environment_regex or ".*"
        self.default_environment = default_environment

    @abstractmethod
    def get_environment(self, data: dict[str, str]) -> str:
        """Get environment using all reoccurring environment logic
        environment_field_name + environment_regex + environment map.json
        first check if the user entered environment_field_name (from where to fetch)
        Then, if regex pattern given - extract environment
        In the end, try to resolve the found environment to its mapped alias - using the map file
        If nothing supply, return the default connector environment
        :param data: {dict} fetch the environment value from this data field (can be the alert or the event)
        :return: {string} environment
        """


class EnvironmentHandleForFileSystem(EnvironmentHandle):
    """handle environment logic
    environment_field_name + environment_regex + environment map.json
    """

    def __init__(
        self,
        map_file_path: str,
        logger: Any,
        environment_field_name: str,
        environment_regex: str,
        default_environment: str,
    ) -> None:
        super().__init__(logger, environment_field_name, environment_regex, default_environment)
        self.map_file_path = map_file_path

    def get_environment(self, data: dict[str, str]) -> str:
        """Get environment using all reoccurring environment logic
        environment_field_name + environment_regex + environment map.json
        first check if the user entered environment_field_name (from where to fetch)
        Then, if regex pattern given - extract environment
        In the end, try to resolve the found environment to its mapped alias - using the map file
        If nothing supply, return the default connector environment
        :param data: {dict} fetch the environment value from this data field (can be the alert or the event)
        :return: {string} environment
        """
        # Check first if map.json exists, and if not, create it.

        if self.environment_field_name and data.get(self.environment_field_name):
            # Get the environment from the given field
            environment = data.get(self.environment_field_name, "")

            if self.environment_regex and self.environment_regex != ".*":
                # If regex pattern given - extract environment
                match = re.search(self.environment_regex, environment)

                if match:
                    # Get the first matching value to match the pattern
                    environment = match.group()

            # Try to resolve the found environment to its mapped alias.
            # If the found environment / extracted environment is empty
            # use the default environment
            return (
                self._get_mapped_environment(environment)
                if environment
                else self.default_environment
            )

        return self.default_environment

    def _get_mapped_environment(self, original_env: str) -> str:
        """Get mapped environment alias from mapping file
        :param original_env: {str} The environment to try to resolve
        :return: {str} The resolved alias (if no alias - returns the original env)
        """
        try:
            with pathlib.Path(self.map_file_path).open("r+", encoding="utf-8") as map_file:
                mappings = json.loads(map_file.read())
        except Exception as e:
            self.logger.error(f"Unable to read environment mappings: {e}")
            mappings = {}

        if not isinstance(mappings, dict):
            self.logger.LOGGER.error(
                "Mappings are not in valid format. Environment will not be mapped."
            )
            return original_env

        return mappings.get(original_env, original_env)


class EnvironmentHandleForDBSystem(EnvironmentHandle):
    """handle environment logic
    environment_field_name + environment_regex + environment map.json
    """

    def __init__(
        self,
        logger: Any,
        environment_field_name: str,
        environment_regex: str,
        default_environment: str,
    ) -> None:
        super().__init__(logger, environment_field_name, environment_regex, default_environment)

    def get_environment(self, data: dict[str, str]) -> str:
        """Get environment using all reoccurring environment logic
        environment_field_name + environment_regex + environment map.json
        first check if the user entered environment_field_name (from where to fetch)
        Then, if regex pattern given - extract environment
        In the end, try to resolve the found environment to its mapped alias - using the map file
        If nothing supply, return the default connector environment
        :param data: {dict} fetch the environment value from this data field (can be the alert or the event)
        :return: {string} environment
        """
        if self.environment_field_name and data.get(self.environment_field_name):
            # Get the environment from the given field
            environment = data.get(self.environment_field_name, "")

            if self.environment_regex and self.environment_regex != ".*":
                # If regex pattern given - extract environment
                match = re.search(self.environment_regex, environment)

                if match:
                    # Get the first matching value to match the pattern
                    environment = match.group()

            # Try to resolve the found environment to its mapped alias.
            # If the found environment / extracted environment is empty
            # use the default environment
            return environment or self.default_environment

        return self.default_environment
