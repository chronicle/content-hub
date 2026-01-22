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

from abc import ABC, abstractmethod
from datetime import timedelta

from EnvironmentCommon import EnvironmentHandle, GetEnvironmentCommonFactory
from SiemplifyConnectors import SiemplifyConnectorExecution
from SiemplifyConnectorsDataModel import AlertInfo
from SiemplifyLogger import SiemplifyLogger
from SiemplifyUtils import from_unix_time, unix_now, utc_now

from ... import extraction
from ...consts import DATETIME_FORMAT, NONE_VALS, UNIX_FORMAT
from ...data_models import BaseAlert, ConnectorParamTypes, Container
from ...exceptions import ConnectorSetupError
from ...smp_time import get_last_success_time
from ...utils import (
    camel_to_snake_case,
    is_overflowed,
    none_to_default_value,
    platform_supports_db,
)
from ...validation import ParameterValidator
from ..utils import (
    create_params_container,
    create_soar_connector,
    get_param_value_from_vault,
    is_native,
    nativemethod,
)


class BaseConnector(ABC):
    """A Unified Generic infrastructure implementation for Chronicle SOAR
    (Formerly 'Siemplify') Connector development.

    The ``Connector`` base class provides template abstract methods to override
    in the inherited connector classes, generic properties, and general flows
    as methods that will be executed when calling the connector's `start` method.

    Note:
        THIS CLASS IS NOT SUPPORTED WITH PYTHON 2!

    Args:
        script_name (str): The name of the script that is using this connector.
        is_test_run (bool): Whether this is a test run or not.

    Attributes:
        _siemplify (SiemplifyConnectorExecution):
            The Siemplify connector execution object.
        _script_name (str): The name of the script that is using this connector.
        _connector_start_time (int): The time at which the connector started.
        _logger (str): The logger for this connector.
        _is_test_run (bool): Whether this is a test run or not.
        _params (Container): The parameters container for this connector.
        _context (Container): The context data container for this connector.
        _vars (Container): The runtime variables container used by the connector.
        _env_common (str): The environment common handle object.
        _error_msg (str):
            The error message the connector will display in case of a generic failure.

    Properties:
        siemplify (SiemplifyConnectorExecution):
            The Siemplify connector execution object.
        script_name (str): The name of the script that is using this connector.
        connector_start_time (int): The time at which the connector started.
        logger (str): The logger for this connector.
        is_test_run (bool): Whether this is a test run or not.
        params (Container): The parameters container for this connector.
        context (Container): The context data container for this connector.
        vars (Container): The runtime variables container used by the connector.
        env_common (str): The environment common handle object.
        error_msg (str):
            The error message the connector will display in case of a generic failure.

    Abstract Methods:
        - validate_params(self): Validate the parameters for this connector.
        - read_context_data(self): Read the context data for this connector.
        - init_managers(self): Initialize the managers for this connector.
        - store_alert_in_cache(self, alert): Store the alert in the cache.
        - create_alert_info(self, alert): Create an alert info object.

    Additional Methods:
        ** These are methods that are called during the connector execution and affect
        the alerts processing phase, but are not mandatory to override. **

        - get_last_success_time(
                self,
                max_backwards_param_name,
                metric, padding_period_param_name,
                padding_period_metric,
                time_format,
                print_value,
                microtime
            ):
            Calculates the connector last successful timestamp.
        - max_alerts_processed(self, processed_alerts):
            Return True if reached the maximum alerts to process limit in the connector
            execution.
        - pass_filters(self, alert):
            Boolean method to check if alert passes connector filters.
        - filter_alerts(self, alerts):
            Filter alerts from manager and return list of filtered alerts.

    """

    def __init__(self, script_name: str, is_test_run: bool | None = None) -> None:
        self._siemplify = create_soar_connector()
        self._siemplify.script_name = script_name
        self._script_name = script_name
        self._connector_start_time = unix_now()
        self._logger = self._siemplify.LOGGER
        self._is_test_run = none_to_default_value(is_test_run, self.siemplify.is_test_run)
        self.detailed_params = extraction.get_connector_detailed_params(self._siemplify)
        self.param_validator = ParameterValidator(self._siemplify)
        self._params = create_params_container()
        self._context = create_params_container()
        self._vars = create_params_container()
        self._error_msg = "Got exception on main handler."
        self._env_common = None
        self._perspectives()

    # Connector Properties ######################
    @property
    def siemplify(self) -> SiemplifyConnectorExecution:
        return self._siemplify

    @property
    def script_name(self) -> str:
        return self._script_name

    @property
    def connector_start_time(self) -> int:
        return self._connector_start_time

    @property
    def logger(self) -> SiemplifyLogger:
        return self._logger

    @property
    def is_test_run(self) -> bool:
        return self._is_test_run

    @property
    def params(self) -> Container:
        return self._params

    @property
    def context(self) -> Container:
        return self._context

    @property
    def vars(self) -> Container:
        return self._vars

    @property
    def env_common(self) -> EnvironmentHandle:
        if not self._env_common:
            self.load_env_common()
        return self._env_common

    @property
    def error_msg(self) -> str:
        return self._error_msg

    @error_msg.setter
    def error_msg(self, val: str) -> None:
        self._error_msg = val

    # Abstract Methods ######################

    @abstractmethod
    def validate_params(self) -> None:
        """Validate connector parameters.

        Note:
            Use validation `self.param_validator` methods for easier
            one-line validation for connector parameters.

        Examples::

            Class MyConnector(Connector)

                # method override
                def validate_params(self):
                    self.params.user_email = self.param_validator.validate_email(
                        param_name='User Email',
                        email=self.params.user_email
                    )

        Raises:
            ConnectorSetupError: If any of the parameters are invalid.

        """

    @abstractmethod
    def init_managers(self) -> None:
        """Create manager instance objects.

        Examples::

            Class MyConnector(Connector)

                # method override
                def init_managers(self):
                    self.params.manager = MyManager(...)

        Raises:
            ConnectorSetupError: If there is an error creating the manager instance
                objects.

        """

    @abstractmethod
    def create_alert_info(self, alert: BaseAlert) -> AlertInfo:
        """Create alert info object.

        Args:
            alert: The alert to create the alert info object for.

        Raises:
            ConnectorSetupError: If there is an error creating the alert info object.

        """

    # Native Methods ######################
    @nativemethod
    def extract_params(self) -> None:
        """Extracts connector parameters and store them in the `params` container.

        Note:
            Parameter names will be stored in snake_case format.
            For example: `'Max Hours Backwards'` -> `'max_hours_backwards'`

        """
        for param in self.detailed_params:
            if param.type == ConnectorParamTypes.BOOLEAN:
                input_type = bool
            elif param.type == ConnectorParamTypes.INTEGER:
                input_type = int
            else:
                input_type = str
            is_password = param.type == ConnectorParamTypes.PASSWORD
            value = extraction.extract_connector_param(
                siemplify=self.siemplify,
                param_name=param.name,
                input_type=input_type,
                is_mandatory=param.is_mandatory,
                print_value=not is_password,
                remove_whitespaces=not is_password,
            )
            vault_settings = self.siemplify.context.vault_settings
            setattr(
                self.params,
                camel_to_snake_case(
                    " ".join(" ".join(word[0].upper() + word[1:] for word in param.name.split()))
                ),
                input_type(
                    value
                    if vault_settings is None
                    else get_param_value_from_vault(vault_settings, value)
                )
                if value not in NONE_VALS
                else value,
            )

        self.params.whitelist = (
            self.siemplify.whitelist
            if isinstance(self.siemplify.whitelist, list)
            else [self.siemplify.whitelist]
        )

    @nativemethod
    def validate_params_wrapper(self) -> None:
        """Wrapper for validate_params method."""
        self.params.python_process_timeout = self.param_validator.validate_integer(
            param_name="Python Process Timeout", value=self.params.python_process_timeout
        )
        if not is_native(self.validate_params):
            self.logger.info("validating input parameters...")
            self.validate_params()

    @nativemethod
    def read_context_data(self) -> None:
        """Load context data from platform data storage (DB/LFS)
        such as alert ids.

        Examples::

            from TIPCommon import read_ids

            Class MyConnector(Connector):
                # method override
                def read_context_data(self):
                    self.context.ids = TIPCommon.read_ids(self.siemplify)


        Raises:
            ConnectorSetupError: If there is an error loading the context data.

        """

    @nativemethod
    def store_alert_in_cache(self, alert: BaseAlert):
        """Save alert id to `ids.json` or equivalent.

        Args:
            alert: The alert with id to store.

        Examples::

            Class MyConnector(Connector):
                # method override
                def store_alert_in_cache(self, alert):
                    # self.context.alert_ids here is of type list
                    self.context.alert_ids.append(alert.alert_id)

        Raises:
            ConnectorSetupError: If there is an error storing the alert.

        """

    @nativemethod
    def read_context_wrapper(self):
        """Wrapper for read_context_data method."""
        self.context.last_success_timestamp = self.get_last_success_time()
        if not is_native(self.read_context_data):
            self.logger.info(f"Fetching context data from {self.context._location}...")
            self.read_context_data()

    @nativemethod
    def get_last_success_time(
        self,
        max_backwards_param_name=None,
        metric="hours",
        padding_period_param_name=None,
        padding_period_metric="hours",
        time_format=DATETIME_FORMAT,
        print_value=True,
        microtime=False,
        date_time_format=None,
    ):
        """Calculates the connector last successful timestamp
        using "max TIME backwards" and "padding period" connector parameters,
        where TIME is the time metric.

        Args:
            max_backwards_param_name (str):
                Parameter name for alert fetching offset time.
                If ``None`` is provided, will calculate timestamp with offset 0.
                Defaults to ``None``.
            metric (str):
                time metric to use in TIPCommon's 'get_last_success_time'.
                Defaults to "hours".
            padding_period_param_name (str, optional):
                Parameter name for padding period offset time.
                Defaults to ``None``.
            padding_period_metric (str, optional):
                time metric - similar to 'metric' parameter.
                Defaults to "hours".
            time_format (int):
                Which time format to return the last success time in.
                Defaults to DATETIME_FORMAT.
            print_value (bool, optional):
                Whether log the value or not. Defaults to True.
            microtime (bool, optional):
                If time format is UNIX, convert the stored timestamp
                from milliseconds to seconds.
                Defaults to False.
            date_time_format(str, optional):
                Return the last success time as a formatted datetime string.
                If ``time_format`` is not ``DATETIME_FORMAT`` this parameter will
                    be ignored.

        Note:
            This is a special method that needs to be overridden and call to the
            original `get_last_success_time` with the appropriate parameters,
            in case you need to provide different parameters.

        Example::

            # overriden
            def get_last_success_time():
                return super().get_last_success_time(
                    max_backwards_param_name="max_days_backwards",
                    metric="days",
                    padding_period_param_name="padding_period",
                    padding_period_metric="hours",
                )

        Returns:
            (any, int): last success time in DATETIME or UNIX format.

        """
        offset = getattr(self.params, max_backwards_param_name) if max_backwards_param_name else 0
        last_success_time = get_last_success_time(
            siemplify=self.siemplify,
            offset_with_metric={metric: offset},
            time_format=time_format,
            print_value=print_value,
            microtime=microtime,
        )

        if padding_period_param_name:
            padding_time_with_metric = {
                padding_period_metric: getattr(self.params, padding_period_param_name)
            }
            dt_last_success_time = (
                from_unix_time(last_success_time)
                if time_format == UNIX_FORMAT
                else last_success_time
            )
            padding_time = utc_now() - timedelta(**padding_time_with_metric)
            if dt_last_success_time > padding_time:
                last_success_time = padding_time
                self.logger.info(
                    "Last success time is greater than provided padding period: "
                    f"{getattr(self.params, padding_period_param_name)}. "
                    f"{last_success_time} will be used as last success time."
                )

        last_success_time = (
            last_success_time.strftime(date_time_format)
            if time_format == DATETIME_FORMAT and date_time_format is not None
            else last_success_time
        )
        return last_success_time

    @nativemethod
    def load_env_common(self) -> EnvironmentHandle:
        """Loads environment handle object from EnvironmentCommon module
        depending on Siemplify platform deployment.

        Note:
            If needed, override this method to load environment handle object
            from EnvironmentCommon module.

        Raises:
            ConnectorSetupError: if couldn't create environment handle object

        Returns:
            EnvironmentHandle: Environment handle object

        """
        try:
            self._env_common = GetEnvironmentCommonFactory.create_environment_manager(
                self.siemplify,
                self.params.environment_field_name,
                self.params.environment_regex_pattern,
            )
        except Exception as e:
            raise ConnectorSetupError(f"Failed to create environment handle object: {e}") from e

    @nativemethod
    def max_alerts_processed(self, processed_alerts) -> bool:
        """Return True if reached the maximum alerts to process limit in
        the connector execution.

        Args:
            processed_alerts: A list of processed alerts.

        Returns:
            True if the maximum alerts to process limit has been reached,
            False otherwise.

        """
        return False

    @nativemethod
    def pass_filters(self, alert) -> bool:
        """Boolean method to check if alert passes connector filters

        Args:
            alert: The alert to check.

        Returns:
            True if the alert passes the filters, False otherwise.

        """
        return True

    @nativemethod
    def filter_alerts(self, alerts: list[BaseAlert]) -> list[BaseAlert]:
        """Filter alerts from manager and return list of filtered alerts

        Args:
            alerts: A list of alerts.

        Returns:
            A list of filtered alerts.

        """
        return alerts

    @nativemethod
    def _perspectives(self) -> None:
        self.context._location = (
            "DB"
            if platform_supports_db(self.siemplify)
            else f"Local File System: {self.siemplify.run_folder}"
        )

    @nativemethod
    def is_overflow_alert(self, alert_info: AlertInfo) -> bool:
        """Check if the connector alert is overflowed.

        Note:
            To add additional logic for 'Is Overflowed' check, please
            override this method and call super().is_overflow_alert(alert_info)

        Examples:
            def is_overflow_alert(self, alert_info):
                if my_condition_to_not_overflow:
                    return False

                return super().is_overflow_alert(alert_info)

        Args:
            alert_info: AlertInfo obj representing SOAR alert.

        Returns:
            True if alert is overflowed, False otherwise.

        """
        return is_overflowed(self.siemplify, alert_info, self.is_test_run)
