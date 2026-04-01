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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction

if TYPE_CHECKING:
    import logging
    from collections.abc import Callable
    from enum import Enum

    from TIPCommon.base.action import EntityTypesEnum


@dataclass
class ActionResult:
    """Dataclass to store the result of an action.

    Attributes:
        output_message: The output message to be displayed to the user.
        value: The boolean result of the action.
        json_result: A JSON serializable dictionary to be returned as the
            action's result.
        status: The execution status of the action (e.g., COMPLETED, FAILED).

    """

    output_message: str
    value: bool
    json_result: dict[str, Any] | None
    status: str

    def set_action_complete(self) -> None:
        """Set the action status to completed."""
        self.status = EXECUTION_STATE_COMPLETED

    def set_action_failed(self) -> None:
        """Set the action status to failed."""
        self.status = EXECUTION_STATE_FAILED


class ActionContext:
    """Context object for an action.

    Provides access to Siemplify functionality and parameters.

    Attributes:
        action_name: The name of the action.
        integration_name: The name of the integration.
        action_parameters: A dictionary of action parameters.
        integration_parameters: A dictionary of integration parameters.

    """

    def __init__(
        self,
        integration_name: str,
        action_name: str,
    ) -> None:
        """Initialize the ActionContext.

        Args:
            integration_name: The name of the integration.
            action_name: The name of the action.

        """
        self.action_name = action_name
        self.integration_name = integration_name
        self._siemplify_action = SiemplifyAction()
        self._siemplify_action.script_name = action_name
        self._status = EXECUTION_STATE_COMPLETED
        self._supported_entities = []
        self.action_parameters = self.siemplify.parameters or {}
        self.integration_parameters = (
            self._siemplify_action.get_configuration(integration_name) or {}
        )

    def get_logger(self) -> logging.Logger:
        """Get the Siemplify logger.

        Returns:
            The logger instance.

        """
        return self._siemplify_action.LOGGER

    def get_entities(self) -> list[Any]:
        """Get the target entities for the action, filtered by supported entity types.

        Returns:
            A list of target entities.

        """
        logger = self.get_logger()
        entities = []
        for entity in self._siemplify_action.target_entities:
            if entity.entity_type in self._supported_entities:
                entities.append(entity)
            else:
                msg = (
                    f"Entity: {entity.identifier} -> {entity.entity_type} "
                    f"not in {self._supported_entities}"
                )
                logger.debug(msg)
        return entities

    @staticmethod
    def _normalize_entity_type(ent: str | Enum) -> str:
        """Normalize entity type to string.

        Args:
            ent: The entity type to normalize.

        Returns:
            The normalized entity type as a string.

        """
        if isinstance(ent, str):
            return ent
        return ent.value

    def set_supported_entities(self, supported_entities: list[EntityTypesEnum]) -> None:
        """Set the supported entity types for the action.

        Args:
            supported_entities: A list of supported entity types.

        """
        self._supported_entities = list(
            map(ActionContext._normalize_entity_type, supported_entities)
        )

    def print_param_values(self) -> None:
        """Print the action parameter values to the log."""
        for param_name, value in self.action_parameters.items():
            self.get_logger().info(f"{param_name}: {value}")

    def process_action_parameters(
        self, param_mappers_config: dict[str, list[Callable[[Any], Any]]]
    ) -> None:
        """Process action parameters using the provided mappers.

        Args:
            param_mappers_config: A dictionary mapping parameter names to a list of
                mapper functions.

        """
        self.get_logger().info("Processing action parameters...")
        self._process_parameters(self.action_parameters, param_mappers_config, "action")

    def process_integration_parameters(
        self, param_mappers_config: dict[str, list[Callable[[Any], Any]]]
    ) -> None:
        """Process integration parameters using the provided mappers.

        Args:
            param_mappers_config: A dictionary mapping parameter names to a list of
                mapper functions.

        """
        self.get_logger().info("Processing integration parameters...")
        self._process_parameters(
            self.integration_parameters, param_mappers_config, "integration"
        )

    def _process_parameters(
        self,
        result_placeholder: dict[str, Any],
        param_mappers_config: dict[str, list[Callable[[Any], Any]]],
        param_context_name: str,
    ) -> None:
        """Process parameters using the provided mappers.

        Args:
            result_placeholder: The dictionary of parameters to process.
            param_mappers_config: The configuration for mapping parameters.
            param_context_name: The name of the parameter context (e.g.,
                'action', 'integration').

        Raises:
            ValueError: If an invalid parameter is encountered.

        """
        for param_name, mappers in param_mappers_config.items():
            if param_name not in result_placeholder:
                self.get_logger().info(
                    f"No parameter {param_name} found in {param_context_name} context"
                )
                continue
            for mapper in mappers:
                try:
                    result_placeholder[param_name] = mapper(
                        result_placeholder[param_name]
                    )
                except Exception as e:  # pylint: disable=broad-exception-caught
                    msg = f"Invalid parameter '{param_name}' reason: {e}"
                    self.get_logger().exception(msg)
                    raise ValueError(msg) from e

    @property
    def siemplify(self) -> SiemplifyAction:
        """Get the SiemplifyAction object.

        Returns:
            The SiemplifyAction instance.

        """
        return self._siemplify_action


class ActionRunner:
    """A wrapper for Siemplify actions to simplify action development.

    This class handles common action boilerplate, such as parameter processing,
    error handling, and logging.
    """

    def __init__(  # noqa: PLR0913
        self,
        function: Callable[[Any, Any, dict[str, Any]], None],
        integration_name: str,
        action_name: str,
        *,
        print_params: bool = False,
        enable_default_error_handling: bool = True,
        error_message_format: str = (
            "{integration_name} - {action_name} failed. Reason: {error}"
        ),
        supported_entities: list[EntityTypesEnum] | None = None,
        action_param_mappers: dict[str, list[Callable[[Any], Any]]] | None = None,
        integration_param_mappers: dict[str, list[Callable[[Any], Any]]] | None = None,
        injectables: dict[str, Any | Callable[[ActionContext], Any]] | None = None,
    ) -> None:
        """Initialize the ActionRunner.

        Args:
            function: The main function of the action.
            integration_name: The name of the integration.
            action_name: The name of the action.
            print_params: Whether to print action parameters at the start.
            enable_default_error_handling: Whether to use the default error
                handling.
            error_message_format: The format string for error messages.
            supported_entities: A list of supported entity types for the action.
            action_param_mappers: Mappers for processing action parameters.
            integration_param_mappers: Mappers for processing integration
                parameters.
            injectables: A dictionary of dependencies to inject into the action
                function.

        """
        self._function = function
        self._integration_name = integration_name
        self._action_name = action_name
        self._print_params = print_params
        self._enable_default_error_handling = enable_default_error_handling
        self._error_message_format = error_message_format
        self._supported_entities = supported_entities
        self._action_param_mappers = action_param_mappers or {}
        self._integration_param_mappers = integration_param_mappers or {}
        self._injectables = injectables or {}

    def register_injectable(
        self, injectable_name: str, injectable_builder: Callable[[ActionContext], Any]
    ) -> None:
        """Register an injectable dependency.

        Args:
            injectable_name: The name of the dependency.
            injectable_builder: A function that builds the dependency, taking an
                ActionContext as input.

        """
        self._injectables[injectable_name] = injectable_builder

    def run(self, context: ActionContext | None = None) -> ActionResult:
        """Run the action.

        This method sets up the action context, processes parameters,
        handles dependency injection, executes the main action logic,
        and finalizes the action with Siemplify.

        Args:
            context: An optional ActionContext. If not provided, a new one will be
                created.

        Returns:
            The result of the action.

        """
        context = context or ActionContext(self._integration_name, self._action_name)
        if self._supported_entities is not None:
            context.set_supported_entities(self._supported_entities)
        logger = context.get_logger()
        logger.info("----------------- Main - Init -----------------")
        context.process_integration_parameters(self._integration_param_mappers)
        context.process_action_parameters(self._action_param_mappers)
        result = ActionResult("", value=True, json_result=None, status=EXECUTION_STATE_COMPLETED)
        if self._print_params:
            logger.info("Printing action param values...")
            context.print_param_values()

        dependencies_to_inject = self._process_injectables(context)

        logger.info("----------------- Main - Started -----------------")
        if self._enable_default_error_handling:
            try:
                self._function(context, result, **dependencies_to_inject)
            except Exception as error:
                result.output_message = self._error_message_format.format(
                    action_name=self._action_name,
                    integration_name=self._integration_name,
                    error=error,
                )
                logger.exception(result.output_message)
                result.set_action_failed()
                result.value = False
        else:
            self._function(context, result, **dependencies_to_inject)

        logger.info("----------------- Main - Finished -----------------")
        msg_status = f"Status: {result.status}"
        logger.info(msg_status)
        msg_value = f"Result Value: {result.value}"
        logger.info(msg_value)
        msg_output = f"Output Message: {result.output_message}"
        logger.info(msg_output)

        if result.json_result:
            context.siemplify.result.add_result_json(result.json_result)

        context.siemplify.end(result.output_message, result.value, result.status)
        return result

    def _process_injectables(self, context: ActionContext) -> dict[str, Any]:
        """Process and build the injectable dependencies.

        Args:
            context: The current ActionContext.

        Returns:
            A dictionary of built dependencies.

        """
        context.get_logger().info("Processing injectables...")
        for k, v in self._injectables.items():
            if callable(v):
                self._injectables[k] = v(context)
        return self._injectables
