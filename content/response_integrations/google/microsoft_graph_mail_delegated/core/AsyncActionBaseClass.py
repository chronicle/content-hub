from __future__ import annotations

from typing import Any, NoReturn

from collections.abc import Mapping, MutableMapping, MutableSequence

import abc
import dataclasses
import requests

from soar_sdk.SiemplifyAction import SiemplifyAction

from TIPCommon.base.action.data_models import ExecutionState
from TIPCommon.data_models import Container
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.smp_time import is_approaching_action_timeout
from TIPCommon.validation import ParameterValidator
from . import AuthenticationManager as auth_manager
from . import constants
from . import datamodels
from . import exceptions
from . import MicrosoftGraphMailDelegatedManager


ActionDataJson = MutableMapping[str, MutableSequence[str] | Mapping[str, Any]]


@dataclasses.dataclass(slots=True)
class ActionResult:
    status: ExecutionState
    result_value: bool | str


class AsyncActionBaseClass(abc.ABC):
    """AsyncActionBaseClass class with methods to extract configuration/action
    parameters for Async Action with initializing MicrosoftGraphMailDelegatedManager.
    """

    def __init__(self, siemplify: SiemplifyAction):
        """Base constructor. It should trigger load of entire integration
           configuration and configuration specific to the current action.

        Args:
            script_name (str): Name of the current action.
        """
        self.siemplify = siemplify
        self.output_messages = []
        self.logger = self.siemplify.LOGGER
        self._params = Container()

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
        specific Microsoft Graph Mail Action.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _perform_action(
        self,
        manager: MicrosoftGraphMailDelegatedManager.ApiManager,
    ) -> ActionResult:
        """Main method to perform async action.

        Args:
            manager (MicrosoftGraphMailDelegatedManager): Instance of
            MicrosoftGraphMailDelegatedManager.

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
        azure_ad_endpoint = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Microsoft Entra ID Endpoint",
            is_mandatory=True,
            print_value=True,
        )
        microsoft_graph_endpoint = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Microsoft Graph Endpoint",
            is_mandatory=True,
            print_value=True,
        )

        client_id = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client ID",
            is_mandatory=True,
            print_value=True,
        )
        secret_id = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Client Secret Value",
            is_mandatory=True,
            remove_whitespaces=False,
        )
        tenant = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Microsoft Entra ID Directory ID",
            is_mandatory=True,
            print_value=True,
        )
        refresh_token = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Refresh Token",
            is_mandatory=True,
        )
        self.params.mail_field_source = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Mail Field Source",
            input_type=bool,
        )
        private_key_b64 = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Base64 Encoded Private Key",
        )
        certificate_b64 = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Base64 Encoded Certificate",
        )
        ca_certificate_b64 = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Base64 Encoded CA certificate",
        )
        self.params.smime_auth = datamodels.SmimeAuth(
            private_key_b64=private_key_b64,
            certificate_b64=certificate_b64,
            ca_certificate_b64=ca_certificate_b64,
        )
        verify_ssl = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="Verify SSL",
            input_type=bool,
            default_value=True,
            print_value=True,
        )
        mail_address = extract_configuration_param(
            siemplify=self.siemplify,
            provider_name=constants.INTEGRATION_NAME,
            param_name="User Mailbox",
            is_mandatory=True,
            print_value=True,
        )
        self.params.session_auth_params = auth_manager.SessionAuthenticationParameters(
            azure_ad_endpoint=azure_ad_endpoint,
            client_id=client_id,
            client_secret=secret_id,
            tenant=tenant,
            refresh_token=refresh_token,
            verify_ssl=verify_ssl,
        )

        self.params.api_params = MicrosoftGraphMailDelegatedManager.ApiParameters(
            api_root=microsoft_graph_endpoint,
            client_id=client_id,
            client_secret=secret_id,
            tenant=tenant,
            mail_address=mail_address,
        )

    def _get_api_manager(self) -> MicrosoftGraphMailDelegatedManager.ApiManager:
        """Initializing MicrosoftGraphMailDelegatedManager ApiManager.

        Returns:
            MicrosoftGraphMailDelegatedManager.ApiManager: ApiManager instance.
        """
        session = self._get_authenticated_session()
        return MicrosoftGraphMailDelegatedManager.ApiManager(
            session=session,
            api_parameters=self.params.api_params,
            mail_field_source=self.params.mail_field_source,
            logger=self.siemplify.LOGGER,
        )

    def _get_authenticated_session(self) -> requests.Session:
        return auth_manager.get_authenticated_session(self.params.session_auth_params)

    def _construct_output_message(self) -> str:
        self.output_messages = [message for message in self.output_messages if message]
        return "\n\n".join(self.output_messages)

    def validate_mailbox(self) -> None:
        if not self.params.results.pending_mailboxes:
            raise exceptions.MicrosoftGraphMailManagerError(
                "The provided mailbox(es) doesn't exist."
            )

    def run(self) -> NoReturn:
        """
        Main Microsoft Graph Mail action method. It wraps some common logic for actions.
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
