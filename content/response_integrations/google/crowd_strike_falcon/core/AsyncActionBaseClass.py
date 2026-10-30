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

from typing import NoReturn
import abc
import dataclasses

from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.data_models import Container
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.smp_time import is_approaching_action_timeout
from TIPCommon.validation import ParameterValidator
from crowd_strike_falcon.core import constants
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.exceptions import ODSDetectionLevelError, ODSInvalidFilePathError


@dataclasses.dataclass
class ActionResult:
    status: int
    result_value: bool


@dataclasses.dataclass
class IntegrationConfig:
    api_root: str
    client_id: str
    client_secret: str
    verify_ssl: bool
    customer_id: str


class AsyncActionBaseClass(abc.ABC):
    """AsyncActionBaseClass class with methods to extract configuration/action
    parameters for Async Action with initializing CrowdStrikeManager.
    """

    def __init__(self, siemplify: str):
        """Base constructor. It should trigger load of entire integration
           configuration and configuration specific to the current action.

        Args:
            script_name (str): Name of the current action.
        """
        self.siemplify = siemplify
        self.output_messages = []
        self.logger = self.siemplify.LOGGER
        self._params = Container()
        self.config = IntegrationConfig(
            api_root=constants.API_ROOT_DEFAULT,
            client_id="",
            client_secret="",
            verify_ssl=False,
            customer_id="",
        )

    @abc.abstractmethod
    def _validate_params(self, validator: ParameterValidator) -> None:
        """Validate the parameters' values

        Args:
            ParameterValidator: ParameterValidator class instance to validate different
                types of parameters.
        Examples::

        class MyAction(Action):
            ...

            def _validate_params(self, validator: ParameterValidator) -> None:
                self.params.max_graphs_to_return = validator.validate_positive(
                    param_name='A Name',
                    value=self.params.a_name,
                )

            ...
        Raises:
            NotImplementedError: If any of the parameters are invalid.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _extract_action_configuration(self) -> None:
        """Protected method, which should extract configuration, specific to the
        specific CrowdStrikeFalcon Action.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _perform_action(self, manager: CrowdStrikeManager) -> ActionResult:
        """Main method to perform async action.

        Args:
            manager (CrowdStrikeManager): CrowdStrikeManager instance.

        Returns:
            ActionResult: ActionResult instance to get the action status and result.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _log_messages(self) -> None:
        """Log all the messages for the action script to write to the SiemplifyLogger.

        This method should be implemented by subclasses to define the
        logic for logging messages.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _finalize_action(self) -> ActionResult:
        """Finalize the action based on the current state of the operation.

        This method checks the state of the operation and calls the appropriate
            finalization method based on the following conditions:

        Returns:
            ActionResult: An object containing the final execution state and a boolean
                indicating whether the operation was successful or not.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _finalize_action_on_timeout(self) -> ActionResult:
        """Finalize action when it times out.

        Returns:
            ActionResult: ActionResult instance to get the action status and result.

        Raises:
            NotImplementedError: If not overridden.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _finalize_action_on_inprogress(self) -> ActionResult:
        """Finalize action during asynchronous processing.

        Returns:
            ActionResult: ActionResult instance to get the action status and result.

        Raises:
            NotImplementedError: If not overridden.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _finalize_action_on_failure(self) -> ActionResult:
        """Finalize action when it action fails to delete emails.

        Returns:
            ActionResult: ActionResult instance to get the action status and result.

        Raises:
            NotImplementedError: If not overridden.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _finalize_action_on_success(self) -> ActionResult:
        """Finalize action when it succeeds.

        Returns:
            ActionResult: ActionResult instance to get the action status and result.

        Raises:
            NotImplementedError: If not overridden.
        """
        raise NotImplementedError

    def _is_timeout(self) -> bool:
        """Check if script timeout is approached for gracefully termination.

        Returns:
            bool: True is timeout is approached otherwise False.
        """
        return is_approaching_action_timeout(
            self.siemplify.execution_deadline_unix_time_ms,
            timeout_threshold_in_sec=constants.ASYNC_TIMEOUT_THRESHOLD_IN_MS,
        )

    def load_base_integration_configuration(self) -> None:
        """Loads base integration configuration, which is used by all async
        integration actions.
        """
        api_root = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="API Root",
            default_value=constants.API_ROOT_DEFAULT,
            print_value=True,
        )

        client_id = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client API ID",
            print_value=True,
        )

        client_secret = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client API Secret",
            remove_whitespaces=False,
        )

        verify_ssl = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
            is_mandatory=True,
            print_value=True,
        )

        customer_id = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Customer ID",
            print_value=True,
        )


        self.config = IntegrationConfig(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            verify_ssl=verify_ssl,
            customer_id=customer_id,
        )

    def _get_api_manager(self) -> CrowdStrikeManager:
        """Initializing CrowdStrikeManager.

        Returns:
            CrowdStrikeManager: CrowdStrikeManager instance.
        """
        return CrowdStrikeManager(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
            use_ssl=self.config.verify_ssl,
            api_root=self.config.api_root,
            logger=self.siemplify.LOGGER,
            customer_id=self.config.customer_id,
        )

    def _construct_output_message(self):
        self.output_messages = [message for message in self.output_messages if message]
        return "\n\n".join(self.output_messages)

    def run(self) -> NoReturn:
        """
        Main CrowdStrikeFalcon action method. It wraps some common logic for actions.
        """
        try:
            self.logger.info(f'{"Main - Param Init":-^80}')
            self.load_base_integration_configuration()
            self._extract_action_configuration()
            self.logger.info(f'{"Main - Started":-^80}')
            validator = ParameterValidator(self.siemplify)
            self._validate_params(validator=validator)
            manager = self._get_api_manager()
            result = self._perform_action(manager)

        except ODSDetectionLevelError as e:
            result = ActionResult(ExecutionState.FAILED, False)
            self.logger.error(str(e))
            self.output_messages.append(str(e))
            self.logger.exception(e)

        except ODSInvalidFilePathError as e:
            result = ActionResult(ExecutionState.FAILED, False)
            self.logger.error(str(e))
            self.output_messages.append(str(e))
            self.logger.exception(e)

        # pylint: disable=broad-exception-caught
        except Exception as e:
            result = ActionResult(ExecutionState.FAILED, False)
            message = f"Failed to execute action. Error: {e}"
            self.logger.error(message)
            self.output_messages.append(message)
            self.logger.exception(e)

        output_message = self._construct_output_message()
        self.logger.info(f'{"Main - Finished":-^80}')
        self.siemplify.LOGGER.info(
            f"\n  status: {result.status.value}"
            f"\n  result_value: {result.result_value}"
            f"\n  output_message: {output_message}"
        )
        self.siemplify.end(output_message, result.result_value, result.status.value)

    @property
    def params(self) -> Container:
        """Returns the action's parameters descriptor.

        Returns:
            A `Container` object with the action's parameters (in snake_case)
            as its attributes
        """
        return self._params
