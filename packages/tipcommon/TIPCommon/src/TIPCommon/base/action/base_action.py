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

import sys
from abc import ABC, abstractmethod
from typing import Callable, Generic, NoReturn, Union

from SiemplifyAction import SiemplifyAction
from SiemplifyDataModel import CustomList
from SiemplifyUtils import output_handler, unix_now
from . import consts
from .action_parser import parse_case_attachment, parse_case_comment
from .data_models import (
    Attachment,
    CaseAttachment,
    CaseComment,
    CaseInsight,
    CasePriority,
    Content,
    DataTable,
    EntityInsight,
    EntityTypesEnum,
    ExecutionState,
    HTMLReport,
    Markdown,
    Link,
)
from ..interfaces import ApiClient, ScriptLogger
from ..utils import (
    create_logger,
    create_params_container,
    create_soar_action,
    is_native,
    nativemethod,
)
from ...data_models import Container
from ...exceptions import (
    ActionSetupError,
    CaseResultError,
    GeneralActionException,
    ParameterExtractionError,
    SDKWrapperError,
)
from ...filters import filter_list_by_type
from ...smp_time import is_approaching_action_timeout
from ...transformation import convert_dict_to_json_result_dict
from ...types import Contains, Entity, JSON, SingleJson
from ...utils import get_entity_original_identifier, is_first_run


PerformAction = Callable[[Union[Entity, None]], None]


class Action(ABC, Generic[ApiClient]):
    """A Unified Generic infrastructure implementation for Chronicle SOAR
    (Formerly known as 'Siemplify') Action development.

    The `Action` base class provides template abstract methods to override
    in the inherited action classes, generic properties, and general flows
    as methods that will be executed when calling the action's `run`
    method.

    Note:
        THIS CLASS IS NOT SUPPORTED WITH PYTHON 2!

    Args:
        name (str): The action's script name

    Attributes:
        _soar_action (SiemplifyAction): The SiemplifyAction SDK object.
        _api_client (Apiable): The api client of the integration
        _name (str): The name of the script that is using this action.
        _action_start_time (int): The starting time of the action
        _logger (SiemplifyLogger): The logger object used for logging in actions.
        _params (Container): The parameters container for this connector.

        global_context (dict): Dictionary to store context if needed.
        _entity_types (list[EntityTypesEnum]): The entity types supported by the action.
        _entities_to_update (list[Entity]): The entities to update when the action ends.

        json_results (JSON): The action's JSON results.
        _attachments (list[Attachment]): Case result attachments to add.
        _contents (list[Content]): Case result contents to add.
        _data_tables (list[DataTable]): Case result data tables to add.
        _html_reports (list)[HTMLReport]: Case result HTML reports to add.
        _links (list[Link]): Case result links to add.
        _markdowns (list[Markdown]): Case result markdowns to add.

        _entity_insights (list[EntityInsight]): Case entity insights to add.
        _case_insights (list[CaseInsight]): Case insights to add.

        _execution_state (ExecutionState): The action's final execution state.
        _result_value (bool): The action final result value.
        _output_message (str): The action's output message in case of success.
        _error_output_message (str): The action's output message in case of failure.

    Properties:
        soar_action (SiemplifyAction): The SiemplifyAction SDK object.
        api_client (Apiable): The api client of the integration
        name (str): The name of the script that is using this action.
        action_start_time (int): The starting time of the action
        logger (SiemplifyLogger): The logger object used for logging in actions.
        params (Container): The parameters container for this connector.

        entity_types (list[EntityTypesEnum]): The entity types supported
        by the action.
        entities_to_update (list[Entity]): The entities to update when the action ends.

        json_results (JSON): The action's JSON results.
        attachments (list[Attachment]): Case result attachments to add.
        contents (list[Content]): Case result contents to add.
        data_tables (list[DataTable]): Case result data tables to add.
        html_reports (list)[HTMLReport]: Case result HTML reports to add.
        links (list[Link]): Case result links to add.
        markdowns (list[Markdown]): Case result markdowns to add.

        entity_insights (list[EntityInsight]): Case entity insights to add.
        case_insights (list[CaseInsight]): Case insights to add.

        execution_state (ExecutionState): The action's final execution state.
        result_value (bool): The action final result value.
        output_message (str): The action's output message in case of success.
        error_output_message (str): The action's output message in case of failure.

    Methods:
        - run(): Runs the action execution.
        - _get_adjusted_json_results(): Adjust the JSON result to a
            particular structure.

    Abstract Methods:
        - _validate_params(): Validate the parameters for this action.
        - _init_api_clients(): Initialize the api clients of the action.
        - _perform_action(): Perform the action's main logic.

    Additional Methods:
        These are methods that are called during the action execution and
        affect the alerts processing phase, but are not mandatory to override.

        - _get_entity_types()
        - _finalize_action_on_success()
        - _finalize_action_on_failure()
        - _on_entity_failure()
        - _handle_timeout()
        - _extract_action_parameters()
        - _finalize()

    SDK Wrapper Methods:
        - _add_attachment_to_current_case()
        - _get_current_case_attachments()
        - _add_comment_to_case()
        - _get_current_case_comments()
        - _assign_case_to_user()
        - _add_tag_to_case()
        - _attach_playbook_to_current_alert()
        - _get_similar_cases_to_current_case()
        - _get_alerts_ticket_ids_from_cases_closed_since_timestamp()
        - _change_current_case_stage()
        - _change_current_case_priority()
        - _close_current_case()
        - _close_alert()
        - _escalate_case()
        - _mark_case_as_important()
        - _raise_incident()
        - _add_entity_to_case()
        - _update_alerts_additional_data()
        - _get_current_integration_configuration()
        - _any_alert_entities_in_custom_list()
        - _add_alert_entities_to_custom_list()
        - _remove_alert_entities_from_custom_list()

    Examples::

        from TIPCommon.base.actions.action_base import Action
        from TIPCommon.validation import ParameterValidator


        SOME_ACTION_SCRIPT_NAME = 'Some Integration - Some Action'


        class SomeAction(Action):

            def _validate_params(self) -> None:
                validator = ParameterValidator(self.soar_action)
                ...  # validation logic

            def _perform_action(self, entity: Entity) -> None:
                try:
                    self.logger.info('Querying Api client')
                    data = self.api_client.do_something(
                        param=self.params.query,
                        entity=entity.original_identifier
                    )

                    ...  # Some logic to process the data

                except SomeCustomException as err:
                    self.error_output_message = (
                        "Action wasn't able to successfully do its thing."\n
                    )
                    raise err from err


        def main() -> None:
            SomeAction(SEARCH_GRAPHS_SCRIPT_NAME).run()


        if __name__ == '__main__':
            main()
    """

    __slots__ = (
        "_name",
        "_soar_action",
        "_logger",
        "_params",
        "_api_client",
        "_action_start_time",
        "global_context",
        "_entity_types",
        "_entities_to_update",
        "_json_results",
        "_attachments",
        "_contents",
        "_data_tables",
        "_html_reports",
        "_links",
        "_markdowns",

        "_entity_insights",
        "_case_insights",
        "_execution_state",
        "_result_value",
        "_output_message",
        "_error_output_message",
        "_is_first_run",
    )

    def __init__(self, name: str) -> None:
        self._name: str = name
        self._soar_action: SiemplifyAction = create_soar_action()
        self._logger: ScriptLogger = create_logger(self._soar_action)
        self._params: Container = create_params_container()
        self._api_client: Contains[ApiClient] | None = None
        self._is_first_run: bool = is_first_run(sys.argv)

        self._action_start_time: int = -1

        self.global_context: dict = {}
        self._entity_types: list[EntityTypesEnum] = []
        self._entities_to_update: list[Entity] = []

        self._json_results: SingleJson = {}
        self._attachments: list[Attachment] = []
        self._contents: list[Content] = []
        self._data_tables: list[DataTable] = []
        self._html_reports: list[HTMLReport] = []
        self._links: list[Link] = []
        self._markdowns: list[Markdown] = []
        self._entity_insights: list[EntityInsight] = []
        self._case_insights: list[CaseInsight] = []

        self._execution_state: ExecutionState = ExecutionState.COMPLETED
        self._result_value: bool = True
        self._output_message: str = f"Successfully executed action {self._name}"
        self._error_output_message: str = f'Error executing action "{self._name}"'

        self._soar_action.script_name = self._name

    # ==================== Abstract Method ==================== #

    @abstractmethod
    def _init_api_clients(self) -> Contains[ApiClient]:
        """Initiate and return all the API clients used by the action"""
        raise NotImplementedError

    @abstractmethod
    def _perform_action(self, current_entity: Entity | None) -> None:
        """Perform the action's main logic"""
        raise NotImplementedError

    # ==================== Native Methods ==================== #

    @nativemethod
    def _validate_params(self) -> None:
        """Validate the parameters' values

        Raises:
            ActionSetupError: If any of the parameters are invalid.
        """

    @nativemethod
    def _extract_action_parameters(self) -> None:
        """Extract the integration and action's parameters"""

    @nativemethod
    def _get_entity_types(self) -> list[EntityTypesEnum]:
        """Get which entity types does the action work on"""

    @nativemethod
    def _finalize_action_on_success(self) -> None:
        """Perform finalize steps right before the action ends in success.

        You can have logic to determine output message and result value
        after collecting data from all entities in the action for example.
        """

    @nativemethod
    def _finalize_action_on_failure(self, error: Exception) -> None:
        """Perform finalize steps right before the action ends in failure.

        You can have logic to determine the output message and result value
        after collecting data from all entities in the action for example.

        Args:
            error: The last exception that was caught
        """

    @nativemethod
    def _on_entity_failure(self, current_entity: Entity, error: Exception) -> None:
        """Callback function that will be called when
        an error is raised during an entity loop

        Args:
            current_entity: the current entity that failed
            error: The last exception that was caught
        """

    @nativemethod
    def _handle_entity_loop_timeout(self, current_entity: Entity) -> None:
        """Function that is

        Args:
            current_entity: the current entity that failed
        """

    @nativemethod
    def _finalize(self) -> None:
        """Perform finalize steps before the action script ends"""

    # ==================== Action Methods ==================== #

    @output_handler
    def run(self) -> NoReturn:
        """run the action script.

        Use the run() method on instance of this class
        (after overriding the abstract methods) in the main function
        of the action's script in order to run the action.

        Action steps:
        1) Extract configuration and action parameters and store them in the
            'params' container descriptor
        2) Validate the parameters
        3) Run the action's main logic on each of the supported entities
            if the action supports entities. If not, run the action's main logic
        4) Send all case result objects
        5) Terminate the entity script

        Examples::

            class SomeAction(Action):
                def __init__(...) -> None:
                    ...


            def _perform_action(...) -> None:
                ...


            ...


            def main() -> None:
                SomeAction(...).run()


            if __name__ == '__main__':
                main()
        """
        self._start_action_clock()
        self.logger.info(
            f"==================== Starting Action - {self.name} - "
            "Execution ===================="
        )

        self.logger.info("-------------------- Main - Param Init --------------------")
        try:
            if not is_native(self._extract_action_parameters):
                self._extract_action_parameters()

        except Exception as e:
            raise ParameterExtractionError(
                f"Failed during parameter extraction, Error: {e}\n"
            ) from e

        self.logger.info("-------------------- Main - Started --------------------")
        try:
            try:
                self._api_client: Contains[ApiClient] = self._init_api_clients()

                if not is_native(self._validate_params):
                    self.logger.info("Validating input parameters")
                    self._validate_params()

            except Exception as e:
                raise ActionSetupError(e) from e

            if not is_native(self._get_entity_types):
                self.logger.info("Setting entity types")
                self.entity_types = self._get_entity_types()

            if self.entity_types:
                self.__entities_main_loop(
                    perform_action_fn=self._perform_action,
                )

            else:
                self.__no_entities_action(perform_action_fn=self._perform_action)

            self.__create_entity_insights()
            self.__create_case_insights()

            self.__send_json_results()

        except Exception as error:
            self.logger.info("-------------------- Main - Failed --------------------")
            self.logger.info(f"Action {self.name} failed due to unhandled exception")

            if not is_native(self._finalize_action_on_failure):
                self.logger.info("Starting action failure finalizing steps")
                self._finalize_action_on_failure(error)

            self.__set_action_to_failure_state(error)

        else:
            if not is_native(self._finalize_action_on_success):
                self.logger.info("Starting action success finalizing steps")
                self._finalize_action_on_success()

        finally:
            if not is_native(self._finalize):
                self.logger.info("Starting action finalizing steps")
                self._finalize()

        self.logger.info("-------------------- Main - Finished --------------------")
        self.__end_action_script()

    def _start_action_clock(self) -> None:
        if self.action_start_time == -1:
            self._action_start_time = unix_now()

    def _get_adjusted_json_results(self) -> JSON:
        """Get an adjusted JSON result

        Use this method to change the structure of the default/raw structure
        that comes from the action. This method is called before the JSON result
        is sent to the platform and only if there is JSON result, so it contains
        all the results that the action has added.

        By default, this checks if the action uses entities, if so, it adjusts it
        to the Entity/EntityResults list format.

        Returns:
            The adjusted JSON result.
        """
        if self.entity_types and isinstance(self.json_results, dict):
            return convert_dict_to_json_result_dict(self.json_results)

        return self.json_results

    # ==================== Private Methods ==================== #

    def __send_case_wall_results(self, entity: Entity | None = None) -> None:
        """Send all case results back to the platform

        Args:
            entity: the current entity if there is one. Defaults to None.
        """
        self.__send_data_tables(entity)
        self.__send_attachments(entity)
        self.__send_contents(entity)
        self.__send_links(entity)
        self.__send_html_reports(entity)
        self.__send_markdowns(entity)

    def __no_entities_action(self, perform_action_fn: PerformAction) -> None:
        """Perform the specified action when no supported entity types
        are detected.

        Args:
            perform_action_fn: The function that performs the action.
        """
        self.logger.info("No supported entity types detected for this action")
        self.logger.info("Starting to perform the action")
        perform_action_fn(None)
        self.logger.info("\nFinished performing the action")

        self.logger.info("Sending script result items")
        self.__send_case_wall_results()

    def __entities_main_loop(self, perform_action_fn: PerformAction) -> None:
        """Main loop for iterating over entities and performing actions.

        Args:
            perform_action_fn: The function that performs the action.
        """
        action_name = self.soar_action.action_definition_name

        registered_entities = ", ".join(str(et) for et in self.entity_types)
        self.logger.info(
            f"Detected {len(self.entity_types)} supported entity "
            "types:\n"
            f"{registered_entities}"
        )

        entities = self.soar_action.target_entities
        for i, entity in enumerate(entities, start=1):
            self.logger.info(f'\n==> Processing entity "{entity.identifier}"')

            # Checking timeout
            self.logger.info("Checking timeout")
            approaching_timeout = is_approaching_action_timeout(
                self.soar_action.execution_deadline_unix_time_ms
            )
            if approaching_timeout:
                self.logger.info(
                    f"Action {action_name} is approaching time out. "
                    "Stopping execution gracefully"
                )
                if not is_native(self._handle_entity_loop_timeout):
                    self.logger.info("Handling time out")
                    self._handle_entity_loop_timeout(entity)

                self.logger.info("Setting action to timeout state")
                self.result_value = False
                self.execution_state = ExecutionState.TIMED_OUT
                break

            self.logger.info("Action does not approach timeout")

            entity_type = next(
                (
                    et for et in EntityTypesEnum
                    if et.value.casefold() == entity.entity_type.casefold()
                ),
                EntityTypesEnum.GENERIC
            )
            if entity_type not in self.entity_types:
                self.logger.info(
                    f"\nEntity {entity.identifier} has type {entity_type} "
                    "and is not one of the registered entity types "
                    f"for this action as mentioned above.\n"
                    "Continuing to the next entity."
                )
                self.logger.info(
                    f"Finished processing {i} out of {len(entities)} entities <=="
                )
                continue

            setattr(
                entity, consts.ENTITY_OG_ID_ATTR, get_entity_original_identifier(entity)
            )
            self.logger.info(
                "Added the entity original identifier attribute, "
                f"original identifier: {entity.original_identifier}"
            )

            try:
                self.logger.info("Starting to perform the action")
                perform_action_fn(entity)
                self.logger.info("\nFinished performing the action")

            except Exception as e:
                self.logger.info(f"---- Error with entity {entity.identifier} ----")

                self.logger.error(
                    "An error occurred on entity "
                    f"{entity.original_identifier}\n"
                    f"Error: {e}"
                )

                self.logger.exception(e)

                self.logger.info("\nAdding error message to json result")
                self.json_results[entity.original_identifier] = {
                    "execution_status": str(e)
                }

                if not is_native(self._on_entity_failure):
                    self.logger.info("Calling on entity failure method")
                    self._on_entity_failure(entity, e)

                self.logger.info("Continuing to the next entity")

            self.logger.info(f"Sending script result items for entity {entity}")
            self.__send_case_wall_results(entity)

            self.logger.info(
                f"Finished processing {i} out of {len(entities)} entities <=="
            )
        self.__update_entities()
        self.logger.info(f"Finished iterating over all {len(entities)} " "entities")

    def __set_action_to_failure_state(self, error: Exception) -> None:
        """Set the action's properties into a 'failure state'.

        Setting an action to that state includes:
            output_message - An error message with the error itself\n
            result_value - False\n
            execution_state - 2 (represents a failure state)

            logging the output message and the errors

        Args:
            error: The exception object which is caught in the exception
        """
        self.logger.error(f"{self.error_output_message}")
        self.logger.exception(error)

        self.logger.info("Setting the action to failure state")
        self.result_value = False
        self.output_message = f"{self.error_output_message}\nReason: {error}"
        self.execution_state = ExecutionState.FAILED

    def __end_action_script(self) -> None:
        """End an action execution.

        Create the end state of an action run.
        Write logs with the result action properties,
        Send the result properties to the platform.
        """
        self.logger.info("Starting action end phase")
        self.logger.info(f"Result Value: {self.result_value}")
        self.logger.info(f"Output Message: {self.output_message}")
        self.logger.info(
            f"Execution State: {self.execution_state} - "
            f"{consts.EXECUTION_STATE[self.execution_state]}"
        )

        self.soar_action.end(
            message=self.output_message,
            result_value=self.result_value,
            execution_state=self.execution_state.value,
        )

    def __send_json_results(self, entity: Entity | None = None) -> None:
        """Sends the JSON results to the case result.

        Args:
            entity: The entity to associate the JSON results with. If `None`,
            the JSON results will not be associated with any entity.

        Raises:
            CaseResultError: If the JSON results could not be sent
                to the case result.
        """
        action_type = "json results"
        try:
            if not self.json_results:
                return

            self.logger.info("Setting the adjusting json result")
            self.json_results = self._get_adjusted_json_results()

            if entity is None:
                self.logger.info(
                    consts.ADD_TO_CASE_RESULT_MSG.format(action_type=f"{action_type}")
                )
                self.soar_action.result.add_result_json(self.json_results)

            else:
                self.logger.info(
                    consts.ADD_TO_CASE_RESULT_MSG.format(
                        action_type=f"{action_type} - specific entity"
                    )
                )
                self.soar_action.result.add_entity_json(
                    entity_identifier=entity.identifier,
                    json_data=self.json_results,
                    entity_type=entity.entity_type,
                )

        except Exception as e:
            raise CaseResultError(
                consts.ADD_TO_CASE_RESULT_ERR_MSG.format(
                    action_type=action_type,
                    error=e,
                )
            ) from e

    def __send_data_tables(self, entity: Entity | None = None) -> None:
        """Sends the data tables to the case result.

        Args:
            entity: The entity to associate the data tables with. If `None`,
                the data tables will not be associated with any entity.

        Raises:
            CaseResultError: If the data tables could not be sent
                to the case result.
        """
        action_type = "data tables"

        try:
            if not self.data_tables:
                return

            self.logger.info(
                consts.ADD_TO_CASE_RESULT_MSG.format(action_type=action_type)
            )
            for data_table in self.data_tables:
                self.soar_action.result.add_entity_table(
                    entity_identifier=(
                        data_table.title
                        if data_table.title or entity is None
                        else entity.identifier
                    ),
                    data_table=data_table.data_table,
                    entity_type=None if entity is None else entity.entity_type,
                )

        except Exception as e:
            raise CaseResultError(
                consts.ADD_TO_CASE_RESULT_ERR_MSG.format(
                    action_type=action_type,
                    error=e,
                )
            ) from e

    def __send_attachments(self, entity: Entity | None = None) -> None:
        """Sends the attachments to the case result.

        Args:
            entity: The entity to associate the attachments with. If `None`,
            the data tables will not be associated with any entity.

        Raises:
            CaseResultError: If the attachments could not be sent
                to the case result.
        """
        action_type = "attachments"

        try:
            if not self.attachments:
                return

            self.logger.info(
                consts.ADD_TO_CASE_RESULT_MSG.format(action_type=action_type)
            )
            for attachment in self.attachments:
                if entity is None:
                    self.soar_action.result.add_attachment(
                        title=attachment.title,
                        filename=attachment.filename,
                        file_contents=attachment.file_contents,
                        additional_data=attachment.additional_data,
                    )

                else:
                    self.soar_action.result.add_entity_attachment(
                        entity_identifier=(
                            attachment.title if attachment.title else entity.identifier
                        ),
                        filename=attachment.filename,
                        file_contents=attachment.file_contents,
                        additional_data=attachment.additional_data,
                        entity_type=entity.entity_type,
                    )

        except Exception as e:
            raise CaseResultError(
                consts.ADD_TO_CASE_RESULT_ERR_MSG.format(
                    action_type=action_type,
                    error=e,
                )
            ) from e

    def __send_contents(self, entity: Entity | None = None) -> None:
        """Sends the content to the case result.

        Args:
            entity: The entity to associate the content with. If `None`,
            the data tables will not be associated with any entity.

        Raises:
            CaseResultError: If the content could not be sent
                to the case result.
        """
        action_type = "content"

        try:
            if not self.contents:
                return

            self.logger.info(
                consts.ADD_TO_CASE_RESULT_MSG.format(action_type=action_type)
            )
            for content in self.contents:
                self.soar_action.result.add_content(
                    entity_identifier=(
                        content.title
                        if content.title or entity is None
                        else entity.identifier
                    ),
                    content=content.content,
                    entity_type=None if entity is None else entity.entity_type,
                )

        except Exception as e:
            raise CaseResultError(
                consts.ADD_TO_CASE_RESULT_ERR_MSG.format(
                    action_type=action_type,
                    error=e,
                )
            ) from e

    def __send_html_reports(self, entity: Entity | None = None) -> None:
        """Sends the HTML reports to the case result.

        Args:
            entity: The entity to associate the HTML reports with. If `None`,
            the data tables will not be associated with any entity.

        Raises:
            CaseResultError: If the HTML reports could not be sent
                to the case result.
        """
        action_type = "HTML reports"

        try:
            if not self.html_reports:
                return

            self.logger.info(
                consts.ADD_TO_CASE_RESULT_MSG.format(action_type=action_type)
            )
            for html_report in self.html_reports:
                self.soar_action.result.add_entity_html_report(
                    entity_identifier=(
                        html_report.title
                        if html_report.title or entity is None
                        else entity.identifier
                    ),
                    report_name=html_report.report_name,
                    report_contents=html_report.report_contents,
                    entity_type=None if entity is None else entity.entity_type,
                )

        except Exception as e:
            raise CaseResultError(
                consts.ADD_TO_CASE_RESULT_ERR_MSG.format(
                    action_type=action_type,
                    error=e,
                )
            ) from e

    def __send_markdowns(self, entity: Entity | None = None) -> None:
        """Sends the markdowns to the case result.

        Args:
            entity: The entity to associate the markdowns with. If `None`, the data
              tables will not be associated with any entity.

        Raises:
            CaseResultError: If the markdowns could not be sent
                to the case result.
        """

        action_type = "markdowns"

        try:
            if not self.markdowns:
                return

            self.logger.info(
                consts.ADD_TO_CASE_RESULT_MSG.format(action_type=action_type)
            )
            for markdown in self.markdowns:
                self.soar_action.result.add_entity_markdown(
                    entity_identifier=(
                        markdown.title
                        if markdown.title or entity is None
                        else entity.identifier
                    ),
                    markdown_name=markdown.markdown_name,
                    markdown_content=markdown.markdown_content,
                    entity_type=None if entity is None else entity.entity_type,
                )

        except Exception as e:
            raise CaseResultError(
                consts.ADD_TO_CASE_RESULT_ERR_MSG.format(
                    action_type=action_type,
                    error=e,
                )
            ) from e

    def __send_links(self, entity: Entity | None = None) -> None:
        """Sends the links to the case result.

        Args:
            entity: The entity to associate the links with. If `None`,
            the data tables will not be associated with any entity.

        Raises:
            CaseResultError: If the links could not be sent
                to the case result.
        """
        action_type = "links"

        try:
            if not self.links:
                return

            self.logger.info(
                consts.ADD_TO_CASE_RESULT_MSG.format(action_type=action_type)
            )
            for link in self.links:
                self.soar_action.result.add_link(
                    title=(
                        link.title
                        if link.title or entity is None
                        else entity.identifier
                    ),
                    link=link.link,
                    entity_type=None if entity is None else entity.entity_type,
                )

        except Exception as e:
            raise CaseResultError(
                consts.ADD_TO_CASE_RESULT_ERR_MSG.format(
                    action_type=action_type,
                    error=e,
                )
            ) from e

    def __update_entities(self) -> None:
        """Updates the entities using the provided list of entities to update.

        This method triggers the update of entities by calling the
        `update_entities` method of the `soar_action` object with the list
        of entities to update.
        If there are no entities to update, the method returns immediately.

        Raises:
            GeneralActionException: If an error occurs while
                updating the entities.
        """
        try:
            if not self.entities_to_update:
                return

            self.logger.info("Updating entities")
            self.soar_action.update_entities(self.entities_to_update)

        except Exception as e:
            raise GeneralActionException(
                f"Failed to update entities, Error: {e}"
            ) from e

    def __create_entity_insights(self) -> None:
        """Creates entity insights.

        Raises:
            CaseResultError: If there is an error while creating
                entity insights.
        """
        action_type = "entity insights"

        try:
            if not self.entity_insights:
                return

            self.logger.info(
                consts.ADD_TO_CASE_RESULT_MSG.format(action_type=action_type)
            )
            for entity_insight in self.entity_insights:
                self.soar_action.add_entity_insight(
                    domain_entity_info=entity_insight.entity,
                    message=entity_insight.message,
                    triggered_by=entity_insight.triggered_by,
                    original_requesting_user=entity_insight.original_requesting_user,
                )

        except Exception as e:
            raise CaseResultError(
                consts.ADD_TO_CASE_RESULT_ERR_MSG.format(
                    action_type=action_type,
                    error=e,
                )
            ) from e

    def __create_case_insights(self) -> None:
        """Creates case insights.

        Raises:
            CaseResultError: If there is an error while creating case insights.
        """
        action_type = "case insights"

        try:
            if not self.case_insights:
                return

            self.logger.info(
                consts.ADD_TO_CASE_RESULT_MSG.format(action_type=action_type)
            )
            for case_insight in self.case_insights:
                self.soar_action.create_case_insight(
                    triggered_by=case_insight.triggered_by,
                    title=case_insight.title,
                    content=case_insight.content,
                    entity_identifier=case_insight.entity_identifier,
                    severity=case_insight.severity,
                    insight_type=case_insight.insight_type,
                    additional_data=case_insight.additional_data,
                    additional_data_type=case_insight.additional_data_type,
                    additional_data_title=case_insight.additional_data_title,
                )

        except Exception as e:
            raise CaseResultError(
                consts.ADD_TO_CASE_RESULT_ERR_MSG.format(
                    action_type=action_type,
                    error=e,
                )
            ) from e

    # ==================== SDK Wrapper Methods ==================== #

    def _add_attachment_to_current_case(self, file_path: str) -> int:
        """Add an attachment to the current case.

        Args:
            file_path: The attachment's file path

        Returns:
            The number of attachments case has (e.g. 6)

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info(f"Adding an attachment from {file_path}")
            return self.soar_action.add_attachment(file_path)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _get_current_case_attachments(self) -> list[CaseAttachment]:
        """Get the attachments from the current case

        Returns:
            List of CaseAttachment objects

        Raises:
            SDKWrapperError: if the file does not exist or if the
                file's size is bigger than 5MB after encoding
        """
        try:
            self.logger.info("Getting attachments")
            attachments: list[SingleJson] = self.soar_action.get_attachments()
            return [parse_case_attachment(attachment) for attachment in attachments]

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _add_comment_to_case(
        self,
        comment: str,
        case_id: int | str | None = None,
        alert_identifier: str | None = None,
    ) -> None:
        """Add a comment to case case_id that alert alert_id is grouped to.

        Args:
            comment: The comment to add - cannot be empty
            case_id: Case identifier (e.g. 5 or '7'),
                defaults to the current case
            alert_identifier: Alert Name_Alert ID
                (e.g.
                ACCESS DISABLED ACCOUNTS_8642BD99-2CCB-43F4-83ED-5248F56931E8)
                defaults to the current alert

        Raises:
            SDKWrapperError: if the comment is an empty string or
                if the alert id wasn't found in the case with ID case_id
        """
        try:
            self.logger.info(f'Adding a comment "{comment}" to case {case_id}')
            self.soar_action.add_comment(comment, case_id, alert_identifier)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _get_current_case_comments(self) -> list[CaseComment]:
        """Get the case's comments.

        Returns:
            list of CaseComment objects

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info("Getting case comments")
            comments: list[SingleJson] = self.soar_action.get_case_comments()
            return [parse_case_comment(comment) for comment in comments]

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _assign_case_to_user(
        self,
        user: str,
        case_id: int | str | None = None,
        alert_identifier: str | None = None,
    ) -> None:
        """Assign case to specific user or user group.

        Args:
            user: user_id | user group - role
                (e.g. b9f72ed5-0276-465e-b7ef-053ba8906900, @Tier1, @CISO)
            case_id: Case identifier (e.g. 5 or '7'),
                defaults to the current case
            alert_identifier: Alert Name_Alert ID
                (e.g.
                ACCESS DISABLED ACCOUNTS_8642BD99-2CCB-43F4-83ED-5248F56931E8)
                defaults to the current alert

        Raises:
            SDKWrapperError: if the user/role doesn't exist or
                if the alert id wasn't found in the case with ID case_id

        """
        try:
            self.logger.info(f"Assigning case {case_id} to {user}")
            self.soar_action.assign_case(user, case_id, alert_identifier)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _add_tag_to_case(
        self,
        tag: str,
        case_id: int | str | None = None,
        alert_identifier: str | None = None,
    ) -> None:
        """Add given tag to case case_id that alert_id is grouped to.

        Args:
            tag: Tag to be added - has to be at least 2 characters long
            case_id: Case identifier (e.g. 5 or '7'),
                defaults to the current case
            alert_identifier: Alert Name_Alert ID
                (e.g.
                ACCESS DISABLED ACCOUNTS_8642BD99-2CCB-43F4-83ED-5248F56931E8)
                defaults to the current alert

        Raises:
            SDKWrapperError: if the tag has less than 2 characters or
                if the alert id wasn't found in the case with ID case_id
        """
        try:
            self.logger.info(f'Adding a tag "{tag}" to case {case_id}')
            self.soar_action.add_tag(tag, case_id, alert_identifier)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _attach_playbook_to_current_alert(self, playbook_name: str) -> bool:
        """Attach a specific playbook to the case the current
        alert os grouped to.

        Args:
            playbook_name: The playbook's name

        Returns:
            True if the playbook was attached, else False

        Raises:
            SDKWrapperError: if the provided playbook_name does not exist
        """
        try:
            self.logger.info(f"Attaching playbook {playbook_name} to alert")
            return self.soar_action.attach_workflow_to_case(playbook_name)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _get_similar_cases_to_current_case(
        self,
        consider_ports: bool = False,
        consider_category_outcome: bool = False,
        consider_rule_generator: bool = False,
        consider_entity_identifiers: bool = False,
        days_to_look_back: int = 1,
        end_time_unix_ms: int | None = None,
    ) -> list[int]:
        """Search for similar cases to the current case, and return their Ids.

        All the boolean search criteria are joined using logical 'AND'
        condition and will be used in the same search.

        Args:
            consider_ports: Search for similar cases by the same Port number
            consider_category_outcome: Search for similar cases
                by the same Category Outcome
            consider_rule_generator: Search for similar cases
                by the same Rule Generator
            consider_entity_identifiers: Search for similar cases
                containing the same Entity Identifier
            days_to_look_back: Defines how many days back the search
                should look for similar cases (e.g. 365)
            end_time_unix_ms: End time (e.g. 16000491293y7)

        Returns:
            list of similar cases IDs (e.g. [20, 11, 36])

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info("Getting similar cases")
            return self.soar_action.get_similar_cases(
                consider_ports,
                consider_category_outcome,
                consider_rule_generator,
                consider_entity_identifiers,
                days_to_look_back,
                end_time_unix_ms,
            )

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _get_alerts_ticket_ids_from_cases_closed_since_timestamp(
        self,
        timestamp_unix_ms: int,
        rule_generator: str,
    ) -> list[str | None]:
        """Get alerts from cases that were closed since timestamp.

        Args:
            timestamp_unix_ms: Time stamp (e.g. 1550409785000)
            rule_generator: Rule generator (e.g. 'Phishing email detector')

        Returns:
            The list of alerts ticket IDs for alerts with the
            same rule_generate. (e.g. ['aa305953-86f2-4f79-8b3e-e1d003'])

            If the rule generator was not found an empty list [] will be
            returned

            If the rule generator was found but no cases were closed with that
            particular rule generator, a list containing null value [None]
            will be returned.

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info("Getting alerts' ticket IDs from closed cases")
            return (
                self.soar_action
                .get_alerts_ticket_ids_from_cases_closed_since_timestamp(
                    timestamp_unix_ms, rule_generator
                )
            )

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _change_current_case_stage(self, stage: str) -> None:
        """Change the current case's stage.

        For the default stages you can use TIPCommon.CaseStage enum to access
        its string values e.g. CaseStage.TRIAGE.value

        Args:
            stage: The stage to change to (e.g. INCIDENT | TRIAGE)

        Raises:
            SDKWrapperError: if the stage wasn't found
        """
        try:
            self.logger.info(f"Changing the case's stage to {stage}")
            return self.soar_action.change_case_stage(stage)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _change_current_case_priority(self, priority: CasePriority) -> None:
        """Change the current case's priority.

        Args:
            priority: The cases priority to change to.
                Priorities: INFORMATIONAL, LOW, MEDIUM, HIGH or CRITICAL

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info(f"Changing the case priority to {priority}")
            return self.soar_action.change_case_priority(priority.value)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _close_current_case(
        self,
        reason: int | str,
        root_cause: str,
        comment: str,
    ) -> None:
        """Close the current case.

        For the default reasons and root cause values you can use
        TIPCommon.CloseCaseOrAlertReasons
        TIPCommon.CloseCaseOrAlertMaliciousRootCauses
        TIPCommon.CloseCaseOrAlertNotMaliciousRootCauses
        TIPCommon.CloseCaseOrAlertMaintenanceRootCauses
        TIPCommon.CloseCaseOrAlertInconclusiveRootCauses
        enums to access its string values
        e.g. CloseCaseOrAlertReasons.MALICIOUS.value

        Args:
            reason: Close case reason
            root_cause: Close case root cause
            comment: Comment

        Raises:
            SDKWrapperError: if root_case does not correspond to its particular
                reason, or if the case is already closed
        """
        try:
            self.logger.info("Closing the current case")
            self.soar_action.close_case(root_cause, comment, reason)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _close_alert(
        self,
        reason: int | str,
        root_cause: str,
        comment: str,
    ) -> JSON:
        """Closes the current alert.

        For the default reasons and root cause values you can use
        TIPCommon.CloseCaseOrAlertReasons
        TIPCommon.CloseCaseOrAlertMaliciousRootCauses
        TIPCommon.CloseCaseOrAlertNotMaliciousRootCauses
        TIPCommon.CloseCaseOrAlertMaintenanceRootCauses
        TIPCommon.CloseCaseOrAlertInconclusiveRootCauses
        enums to access its string values
        e.g. CloseCaseOrAlertReasons.MALICIOUS.value

        Args:
            reason: Close alert reason
            root_cause: Close alert root cause
            comment: Comment

        Returns:
            Json response
            E.g.
            {
                'is_request_valid': True,
                'errors': [],
                'new_case_id': None
            }

        Raises:
            SDKWrapperError: if root_case does not correspond to its particular
                reason, or if the alert is already closed
        """
        try:
            self.logger.info("Closing the current alert")
            return self.soar_action.close_alert(root_cause, comment, reason)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _escalate_case(self, comment: str) -> None:
        """Escalate the case.

        Args:
            comment: Escalate comment

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info("Escalating the case")
            self.soar_action.escalate_case(comment)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _mark_case_as_important(self) -> None:
        """Mark the case as important

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info("Marking the case as important")
            self.soar_action.mark_case_as_important()

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _raise_incident(self) -> None:
        """Raise incident

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info("Raising incident")
            self.soar_action.raise_incident()

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _add_entity_to_case(
        self,
        entity_identifier: str,
        entity_type: EntityTypesEnum,
        is_internal: bool,
        is_suspicious: bool,
        is_enriched: bool,
        is_vulnerable: bool,
        properties: SingleJson,
    ) -> None:
        """Add an entity to the case.

        Args:
            entity_identifier: The entity identifier (e.g. 1.1.1.1, google.com)
            entity_type: Entity type
            is_internal: Whether the entity is internal/external
            is_suspicious: Whether the entity is suspicious or not
            is_enriched: Is the entity already enriched
            is_vulnerable: Is the entity vulnerable
            properties: Additional properties to add

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info(f"Adding entity {entity_identifier} to the case")
            self.soar_action.add_entity_to_case(
                entity_identifier,
                entity_type.value,
                is_internal,
                is_suspicious,
                is_enriched,
                is_vulnerable,
                properties,
            )

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _update_alerts_additional_data(
        self,
        alerts_additional_data: dict,
    ) -> None:
        """Update alerts additional data.

        Args:
            alerts_additional_data: Additional data to update

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            # dictionary of indicatorIdentifier - string data
            self.logger.info("Updating the alert's additional data")
            self.soar_action.update_alerts_additional_data(alerts_additional_data)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _get_current_integration_configuration(
        self,
        fallback_integration_identifier: str = "",
    ) -> SingleJson:
        """Get an integration configuration.

        Args:
            fallback_integration_identifier: The integration's identifier
                (e.g. VirusTotalV3) in case the call is not from an integration

        Returns:
            Json response
            E.g.
            {
                'API Key': '46c89...',
                'Verify SSL': 'True',
                'AgentIdentifier': None
            }

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info("Getting current integration configuration")
            return self.soar_action.get_configuration(fallback_integration_identifier)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _any_alert_entities_in_custom_list(self, category_name: str) -> bool:
        """Check whether an Entity Identifier is part of a predefined dynamic
        categorized Custom List

        Args:
            category_name: Custom list category

        Returns:
            True if there's at least one entity in the alert that has a custom
            list record with the given category, else False

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info(
                f"Checking if any alerts entities in custom list {category_name}"
            )
            return self.soar_action.any_alert_entities_in_custom_list(category_name)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _add_alert_entities_to_custom_list(
        self,
        category_name: str,
    ) -> list[CustomList]:
        """Add an Entity Identifier to a categorized Custom List,
        in order to perform future comparisons in other actions.

        Args:
            category_name: Custom list category to be used

        Returns:
            A list of all CustomList objects

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info(f"Adding entities of alert to custom list {category_name}")
            return self.soar_action.add_alert_entities_to_custom_list(category_name)

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    def _remove_alert_entities_from_custom_list(
        self,
        category_name: str,
    ) -> list[CustomList]:
        """Remove an Entity Identifier from a categorized Custom List,
        in order to perform future comparisons in other actions.

        Args:
            category_name: Custom list category to be used

        Returns:
            A list of all CustomList objects

        Raises:
            SDKWrapperError: if an error occurs
        """
        try:
            self.logger.info(
                f"Removing entities of alerts to custom list {category_name}"
            )
            return self.soar_action.remove_alert_entities_from_custom_list(
                category_name
            )

        except Exception as e:
            raise SDKWrapperError(consts.SDK_WRAPPER_ERR_MSG.format(error=e)) from e

    # ==================== Properties Definitions ==================== #

    @property
    def soar_action(self) -> SiemplifyAction:
        """Returns the SDK SiemplifyAction object.

        Returns:
            A `SiemplifyAction` SDK object.
        """
        return self._soar_action

    @property
    def api_client(self) -> Contains[ApiClient]:
        """Returns the aAPI client of the integration.

        Returns:
            An Apiable object
        """
        return self._api_client

    @property
    def name(self) -> str:
        """Returns the script name of the action.

        Returns:
            A `str` representing the action's script name.
        """
        return self._name

    @property
    def action_start_time(self) -> int:
        """Returns the action start time in unix.

        Returns:
            An `int` representing the action's starting time in unix.
        """
        return self._action_start_time

    @property
    def logger(self) -> ScriptLogger:
        """Returns a NewLineLogger object for actions.

        Returns:
            A `NewLineLogger` object.
        """
        return self._logger

    @property
    def params(self) -> Container:
        """Returns the action's parameters descriptor.

        Returns:
            A `Container` object with the action's parameters (in snake_case)
            as its attributes
        """
        return self._params

    @property
    def json_results(self) -> JSON:
        """Returns the action's JSON results.

        Returns:
            The action's JSON result that will be sent to the case wall.
        """
        return self._json_results

    @property
    def is_first_run(self) -> bool:
        """Returns the action's JSON results.

        Returns:
            The action's JSON result that will be sent to the case wall.
        """
        return self._is_first_run

    @property
    def entity_types(self) -> list[EntityTypesEnum]:
        """Returns the entity types that are supported by the action.

        If the action work with entities, the action will only process entities
        that their type is in the entity_types list. If not, it will skip the
        entity.

        Returns:
            A list of `EntityTypesEnum` objects representing the entity types
            the action can process.
        """
        return self._entity_types

    @property
    def entities_to_update(self) -> list[Entity]:
        """Returns the entities that should be updated in the platform.

        All the entities in the list will be sent to be updated in the platform.

        Returns:
            A list of `Entity` objects representing the entities that should
            be updated in the case.
        """
        return self._entities_to_update

    @property
    def data_tables(self) -> list[DataTable]:
        """Returns the case result data tables associated with this object.

        All the data tables in the list will be sent to the case result by
        default.

        Returns:
            A list of `DataTable` objects representing the insights
            for this case.
        """
        return self._data_tables

    @property
    def attachments(self) -> list[Attachment]:
        """Returns the case result attachments associated with this object.

        All the attachments in the list will be sent to the case result by
        default.

        Returns:
            A list of `Attachment` objects representing the insights
            for this case.
        """
        return self._attachments

    @property
    def contents(self) -> list[Content]:
        """Returns the case result contents associated with this object.

        All the contents in the list will be sent to the case result by
        default.

        Returns:
            A list of `Content` objects representing the insights for this case.
        """
        return self._contents

    @property
    def html_reports(self) -> list[HTMLReport]:
        """Returns the case result HTML reports associated with this object.

        All the HTML reports in the list will be sent to the case result by
        default.

        Returns:
            A list of `HTMLReport` objects representing the insights
            for this case.
        """
        return self._html_reports

    @property
    def links(self) -> list[Link]:
        """Returns the case result links associated with this object.

        All the links in the list will be sent to the case result by
        default.

        Returns:
            A list of `Link` objects representing the insights for this case.
        """
        return self._links

    @property
    def markdowns(self) -> list[Markdown]:
        """Returns the case result markdowns associated with this object.

        All the markdowns in the list will be sent to the case result by
        default.

        Returns:
            A list of `Markdown` objects representing the insights for this case.
        """
        return self._markdowns

    @property
    def entity_insights(self) -> list[EntityInsight]:
        """Returns the entity insights associated with this object.

        All the entity insights in the list will be sent to the case result by
        default.

        Returns:
            A list of `EntityInsight` objects representing the insights
            for this case.
        """
        return self._entity_insights

    @property
    def case_insights(self) -> list[CaseInsight]:
        """Returns the case insights associated with this object.

        All the case insights in the list will be sent to the case result by
        default.

        Returns:
            A list of `CaseInsight` objects representing the insights
            for this case.
        """
        return self._case_insights

    @property
    def execution_state(self) -> ExecutionState:
        """The action's execution state.

        Status indicator, represented by an integer,
        to pass back to the platform.

        - ExecutionState.COMPLETED = 0
        - ExecutionState.IN_PROGRESS = 1
        - ExecutionState.FAILED = 2
        - ExecutionState.TIMED_OUT = 3

        Returns:
            The `ExecutionState`object representing the current execution state.
        """
        return self._execution_state

    @property
    def result_value(self) -> bool:
        """The action's result value.

        The action's result value that will be passed back to the platform.

        True - Action Succeeded\n
        False - Action Failed
        """
        return self._result_value

    @property
    def output_message(self) -> str:
        """The action's output message in case of a successful run.

        A short descriptive message to pass back as the output message
        of the action.
        """
        return self._output_message

    @property
    def error_output_message(self) -> str:
        """The action's output message in case of a failed run.

        An output message that should appear in case of a failure during the
        action's run-time.
        Default value: "Action '{name}' failed"
        """
        return self._error_output_message

    # ==================== Properties Setters ==================== #

    @json_results.setter
    def json_results(self, value: JSON) -> None:
        """Sets the JSON results.

        Sets the value only if it's an instance of either `list` or `dict`.

        Args:
            value: The JSON value to set.
        """
        if isinstance(value, (list, dict)):
            self._json_results = value

    @entity_types.setter
    def entity_types(self, value: list[EntityTypesEnum]) -> None:
        """Sets the entity types.

        Sets the value only if it's an instance of `list`,
        filters out duplicate values
        and filters the list by type `EntityTypesEnum`.

        Args:
            value: The entity types list to set.
        """
        if isinstance(value, list):
            self._entity_types = list(set(filter_list_by_type(value, EntityTypesEnum)))

    @entities_to_update.setter
    def entities_to_update(self, value: list[Entity]) -> None:
        """Sets the entity to update.

        Sets the value only if it's an instance of `list`,
        filters out duplicate values and filters the list by type `Entity`.

        Args:
            value: The entities-to-update list to set.
        """
        if isinstance(value, list):
            self._entities_to_update = list(set(filter_list_by_type(value, Entity)))

    @data_tables.setter
    def data_tables(self, value: list[DataTable]) -> None:
        """Sets the data tables.

        Sets the value only if it's an instance of `list`
        and filters the list by type `DataTable`.

        Args:
            value: The data tables list to set.
        """
        if isinstance(value, list):
            self._data_tables = filter_list_by_type(value, DataTable)

    @attachments.setter
    def attachments(self, value: list[Attachment]) -> None:
        """Sets the attachments.

        Sets the value only if it's an instance of `list`
        and filters the list by type `Attachment`.

        Args:
            value: The attachments list to set.
        """
        if isinstance(value, list):
            self._attachments = filter_list_by_type(value, Attachment)

    @contents.setter
    def contents(self, value: list[Content]) -> None:
        """Sets the contents.

        Sets the value only if it's an instance of `list`
        and filters the list by type `Content`.

        Args:
            value: The contents list to set.
        """
        if isinstance(value, list):
            self._contents = filter_list_by_type(value, Content)

    @html_reports.setter
    def html_reports(self, value: list[HTMLReport]) -> None:
        """Sets the HTML reports.

        Sets the value only if it's an instance of `list`
        and filters the list by type `HTMLReport`.

        Args:
            value: The HTML reports list to set.
        """
        if isinstance(value, list):
            self._html_reports = filter_list_by_type(value, HTMLReport)

    @links.setter
    def links(self, value: list[Link]) -> None:
        """Sets the links.

        Sets the value only if it's an instance of `list`
        and filters the list by type `Link`.

        Args:
            value: The links list to set.
        """
        if isinstance(value, list):
            self._links = filter_list_by_type(value, Link)

    @markdowns.setter
    def markdowns(self, value: list[Markdown]) -> None:
        """Sets the markdowns.

        Sets the value only if it's an instance of `list`
        and filters the list by type `Markdown`.

        Args:
            value: The markdowns list to set.
        """
        if isinstance(value, list):
            self._markdowns = filter_list_by_type(value, Markdown)

    @entity_insights.setter
    def entity_insights(self, value: list[EntityInsight]) -> None:
        """Sets the entity insights.

        Sets the value only if it's an instance of `list`
        and filters the list by type `EntityInsight`.

        Args:
            value: The entity insights list to set.
        """
        if isinstance(value, list):
            self._entity_insights = filter_list_by_type(value, EntityInsight)

    @case_insights.setter
    def case_insights(self, value: list[CaseInsight]) -> None:
        """Sets the case insights.

        Sets the value only if it's an instance of `list`
        and filters the list by type `CaseInsight`.

        Args:
            value: The case insights list to set.
        """
        if isinstance(value, list):
            self._case_insights = filter_list_by_type(value, CaseInsight)

    @execution_state.setter
    def execution_state(self, value: ExecutionState) -> None:
        """Sets the execution state.

        Sets the value only if it's an instance of `ExecutionState`.

        Args:
            value: The execution state to set.
        """
        if isinstance(value, ExecutionState):
            self._execution_state = value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        """Sets the result value.

        Sets the value only if it's an instance of `bool`.

        Args:
            value: The result value to set.
        """
        if isinstance(value, bool):
            self._result_value = value

    @output_message.setter
    def output_message(self, value: str) -> None:
        """Sets the output message.

        Sets the value only if it's an instance of `str`.

        Args:
            value: The output message to set.
        """
        if isinstance(value, str):
            self._output_message = value

    @error_output_message.setter
    def error_output_message(self, value: str) -> None:
        """Sets the error output message.

        Sets the value only if it's an instance of `str`.

        Args:
            value: The error output message to set.
        """
        if isinstance(value, str):
            self._error_output_message = value
