from __future__ import annotations

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, unix_now


class BaseEmailAction:
    """Abstract class for Email actions"""

    # Constants related to Email integration config
    INTEGRATION_NAME = "SendGrid"
    JOIN_DELIMITER = ", "
    MAX_IDS_PRINT = 100

    def __init__(self, script_name):
        """Base constructor. It should trigger load of entire integration configuration
        and configuration specific to the current action.
        :param script_name: {str} Name of the current action
        """
        self.siemplify = SiemplifyAction()
        self.siemplify.script_name = script_name
        self.logger = self.siemplify.LOGGER

        self.logger.info("================= Main - Param Init =================")

        self.load_integration_configuration()

    def load_integration_configuration(self):
        """Protected method, which should load configuration, specific to entire Email configuration"""
        # Load Email integration configuration
        self.load_base_integration_configuration()

    # noinspection PyAttributeOutsideInit
    def load_base_integration_configuration(self):
        """Loads base integration configuration, which is used by all Email integration actions"""
        configurations = self.siemplify.get_configuration("SendGrid")
        self.api_token = configurations["API Token"]

        self.email_from = self.siemplify.parameters.get("Email From")
        self.email_to = self.siemplify.parameters.get("Email To")
        self.subject = self.siemplify.parameters.get("Subject")
        self.content = self.siemplify.parameters.get("Content")
        self.return_message_status = self.siemplify.parameters.get(
            "Return Message Status",
        )

    def load_action_configuration(self):
        """Protected method, which should load configuration, specific to the specific Email Action"""
        raise NotImplementedError

    def run(self):
        """Main Email action method. It wraps some common logic for actions"""
        self.logger.info("----------------- Main - Started -----------------")

        try:
            status = EXECUTION_STATE_COMPLETED  # Used to flag back to Siemplify system, the action final status
            output_messages = [
                "Output messages:\n",
            ]  # Human-readable message, showed in UI as the action result
            result_value = False  # Set a simple result value, used for playbook if\else and placeholders.
            failed_entities = []  # If this action contains entity based logic, collect failed entity.identifiers
            successful_entities = []  # If this action contains entity based logic, collect successful entity.identifiers

            status, result_value = self.execute_action(
                output_messages,
                successful_entities,
                failed_entities,
            )

        except Exception as e:
            self.logger.error(f"General error performing action {self.SCRIPT_NAME}")
            self.logger.exception(e)
            raise  # used to return entire error details - including stacktrace back to client UI. Best for most use cases

        all_messages = "\n  ".join(output_messages)
        self.logger.info("----------------- Main - Finished -----------------")
        self.logger.info(
            f"status: {status}\n  result_value: {result_value}\n  output_message: {all_messages}",
        )
        self.siemplify.end(all_messages, result_value, status)

    def execute_action(self, output_messages, successful_entities, failed_entities):
        """This abstract method should be implemented to reflect actual behavior to process an entity
        :param output_messages: {list} Mutable list of output messages (str) to form audit trail for this action
        :param successful_entities: {list} List of entity.identifier's, which have been processed successfully
        :param failed_entities: {list} List of entity.identifier's, which have been failed during processing
        :return: {tuple} 1st value - Status of the operation: {int} 0 - success, 1 - failed, 2 - timed out; 2nd value - Success flag: {bool} True - success, False - failure.
        """
        status = EXECUTION_STATE_COMPLETED  # Used to flag back to Siemplify system, the action final status

        for entity in self.siemplify.target_entities:
            self.logger.info(f"Started processing entity: {entity.identifier}")

            if unix_now() >= self.siemplify.execution_deadline_unix_time_ms:
                self.logger.error(
                    "Timed out. execution deadline ({}) has passed".format(
                        convert_unixtime_to_datetime(
                            self.siemplify.execution_deadline_unix_time_ms,
                        ),
                    ),
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                self.execute_action_per_entity(entity, output_messages)

                successful_entities.append(entity.identifier)
                self.logger.info(f"Finished processing entity {entity.identifier}")

            except Exception as e:
                failed_entities.append(entity.identifier)
                self.logger.error(f"An error occurred on entity {entity.identifier}")
                self.logger.exception(e)

        if successful_entities:
            output_messages.append(
                "Successfully processed entities:\n{}".format(
                    "\n  ".join(successful_entities),
                ),
            )
        else:
            output_messages.append("No entities where processed.")

        if failed_entities:
            output_messages.append(
                "Failed processing entities:{}\n".format("\n  ".join(failed_entities)),
            )
            status = EXECUTION_STATE_FAILED

        return status

    def execute_action_per_entity(self, entity, output_messages):
        """Abstract method, which should do something per each entity
        :param entity: {AlertInfo} Actual entity instance along with all related information
        :param output_messages: {list} Mutable list of output messages (str) to form audit trail for this action
        """
        raise NotImplementedError
