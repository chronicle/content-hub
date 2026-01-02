from __future__ import annotations

import abc
import dataclasses
import traceback
from typing import NoReturn

from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED


@dataclasses.dataclass
class ActionResult:
    status: int
    result_value: bool


class Container:
    """Represents a container for variables.

    Examples:
        >>> from data_models import Container
        >>> container = Container()
        >>> container.one = 1
        >>> container.one
        1

    """

    def __init__(self):
        self._params = {}

    def __get__(self, ins, instype=None):
        return self._params.get(ins)

    def __set__(self, ins, value):
        self._params[ins] = value


class ActionBaseClass(abc.ABC):
    """ActionBaseClass class with methods to extract configuration/action
    parameters for Actions in ChronicleSupportTools.
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

    @abc.abstractmethod
    def _extract_action_configuration(self) -> None:
        """Protected method, which should extract configuration."""
        raise NotImplementedError

    def load_base_integration_configuration(self) -> None:
        """Loads base integration configuration, which is used by all async
        integration actions.
        """
        raise NotImplementedError

    @property
    def params(self) -> Container:
        """Returns the action's parameters descriptor.

        Returns:
            A `Container` object with the action's parameters (in snake_case)
            as its attributes

        """
        return self._params

    def _construct_output_message(self):
        self.output_messages = [message for message in self.output_messages if message]
        return "\n\n".join(self.output_messages)

    @abc.abstractmethod
    def _perform_action(self) -> ActionResult:
        """Main method to perform async action.

        Args:
            None

        Returns:
            ActionResult: ActionResult instance to get the action status and result.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.

        """
        raise NotImplementedError

    def run(self) -> NoReturn:
        """Main ChronicleSupportTools action method. It wraps some common logic for actions."""
        try:
            self.logger.info(f"{'Main - Param Init':-^80}")
            self._extract_action_configuration()
            self.logger.info(f"{'Main - Started':-^80}")
            result = self._perform_action()

        # pylint: disable=broad-exception-caught
        except Exception as e:
            result = ActionResult(EXECUTION_STATE_FAILED, False)
            message = f"Failed to execute action. Error: {e}"
            self.logger.error(message)
            self.output_messages.append(message)
            self.output_messages.append(traceback.format_exc())
            self.logger.exception(e)

        output_message = self._construct_output_message()
        self.logger.info(f"{'Main - Finished':-^80}")
        self.siemplify.LOGGER.info(
            f"\n  status: {result.status}"
            f"\n  result_value: {result.result_value}"
            f"\n  output_message: {output_message}",
        )
        self.siemplify.end(output_message, result.result_value, result.status)
