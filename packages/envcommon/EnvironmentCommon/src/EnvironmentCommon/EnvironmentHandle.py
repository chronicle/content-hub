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

import json
import os
import re
from abc import ABC, abstractmethod


def platform_supports_db(siemplify):
    if hasattr(siemplify, 'set_connector_context_property'):
        return True
    return False


def validate_map_file_exists(map_file_path, logger):
    try:
        if not os.path.exists(map_file_path):
            with open(map_file_path, 'w+') as map_file:
                map_file.write(json.dumps(
                    {"Original environment name": "Desired environment name",
                     "Env1": "MyEnv1"}))
                logger.info("Mapping file was created at {}".format(map_file))
    except Exception as e:
        logger.error("Unable to create mapping file: {}".format(e))
        logger.exception(e)


class GetEnvironmentCommonFactory(object):
    @staticmethod
    def create_environment_manager(siemplify, environment_field_name, environment_regex_pattern, map_file='map.json'):
        """
            Get environment common
            :param siemplify: {siemplify} Siemplify object
            :param environment_field_name: {string} The environment field name
            :param environment_regex_pattern: {string} The environment regex pattern
            :param map_file: {string} The map file
            :return: {EnvironmentHandle}
            """
        if platform_supports_db(siemplify):
            return EnvironmentHandleForDBSystem(logger=siemplify.LOGGER,
                                                environment_field_name=environment_field_name,
                                                environment_regex=environment_regex_pattern,
                                                default_environment=siemplify.context.connector_info.environment)

        map_file_path = os.path.join(siemplify.run_folder, map_file)
        validate_map_file_exists(map_file_path, siemplify.LOGGER)

        return EnvironmentHandleForFileSystem(map_file_path=map_file_path,
                                              logger=siemplify.LOGGER,
                                              environment_field_name=environment_field_name,
                                              environment_regex=environment_regex_pattern,
                                              default_environment=siemplify.context.connector_info.environment)


class EnvironmentHandle(ABC):
    """
    handle environment logic
    environment_field_name + environment_regex + environment map.json
    """

    def __init__(self, logger, environment_field_name, environment_regex, default_environment):
        self.logger = logger
        self.environment_field_name = environment_field_name
        # if environment_regex is null or empty, turn it into ".*" (aka: select everything)
        self.environment_regex = environment_regex if environment_regex else ".*"
        self.default_environment = default_environment

    @abstractmethod
    def get_environment(self, data):
        """
        Get environment using all reoccurring environment logic
        environment_field_name + environment_regex + environment map.json
        first check if the user entered environment_field_name (from where to fetch)
        Then, if regex pattern given - extract environment
        In the end, try to resolve the found environment to its mapped alias - using the map file
        If nothing supply, return the default connector environment
        :param data: {dict} fetch the environment value from this data field (can be the alert or the event)
        :return: {string} environment
        """
        ...


class EnvironmentHandleForFileSystem(EnvironmentHandle):
    """
    handle environment logic
    environment_field_name + environment_regex + environment map.json
    """

    def __init__(self, map_file_path, logger, environment_field_name, environment_regex, default_environment):
        super().__init__(logger, environment_field_name,
                         environment_regex, default_environment)
        self.map_file_path = map_file_path

    def get_environment(self, data):
        """
        Get environment using all reoccurring environment logic
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
            mapped_environment = self._get_mapped_environment(
                environment) if environment else self.default_environment
            return mapped_environment

        return self.default_environment

    def _get_mapped_environment(self, original_env):
        """
        Get mapped environment alias from mapping file
        :param original_env: {str} The environment to try to resolve
        :return: {str} The resolved alias (if no alias - returns the original env)
        """
        try:
            with open(self.map_file_path, 'r+') as map_file:
                mappings = json.loads(map_file.read())
        except Exception as e:
            self.logger.error(
                "Unable to read environment mappings: {}".format(e))
            mappings = {}

        if not isinstance(mappings, dict):
            self.logger.LOGGER.error(
                "Mappings are not in valid format. Environment will not be mapped.")
            return original_env

        return mappings.get(original_env, original_env)


class EnvironmentHandleForDBSystem(EnvironmentHandle):
    """
    handle environment logic
    environment_field_name + environment_regex + environment map.json
    """

    def __init__(self, logger, environment_field_name, environment_regex, default_environment):
        super().__init__(logger, environment_field_name,
                         environment_regex, default_environment)

    def get_environment(self, data):
        """
        Get environment using all reoccurring environment logic
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
            return environment if environment else self.default_environment

        return self.default_environment
