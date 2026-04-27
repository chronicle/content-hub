from __future__ import annotations
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyUtils import unix_now, convert_dict_to_json_result_dict
from time import sleep
from string import Formatter
from .utils import get_entity_original_identifier


IN_PROGRESS_MSG = 2
ALL_FAILED_MSG = 3
SOME_COMPLETED_MSG = 4
SOME_FAILED_MSG = 5
TIMEOUT_REACHED_MSG = 6

OUTPUT_MESSAGE_BEFORE = 1
OUTPUT_MESSAGE_AFTER = 2

ENTITY_FILENAME_CONCAT_CHAR = "|||"

ENTITY_KEY_FOR_FORMAT = "et"
STEP_KEY_FOR_FORMAT = "st"
ENTITY_STATE_KEY = "state"
ENTITY_DATA_KEY = "data"
ENTITY_REASON_KEY = "reason"

DEFAULT_OUTPUT_MESSAGES = {
    IN_PROGRESS_MSG: f"The following entities are in progress to {{{STEP_KEY_FOR_FORMAT}}}: {{{ENTITY_KEY_FOR_FORMAT}}}",
    ALL_FAILED_MSG: "All entities are failed.",
    SOME_COMPLETED_MSG: f"The following entities are successful to {{{STEP_KEY_FOR_FORMAT}}}: {{{ENTITY_KEY_FOR_FORMAT}}}.",
    SOME_FAILED_MSG: f"The following entities are failed to {{{STEP_KEY_FOR_FORMAT}}}: {{{ENTITY_KEY_FOR_FORMAT}}}",
    TIMEOUT_REACHED_MSG: f"Action reached timeout in {{{STEP_KEY_FOR_FORMAT}}} waiting for results for the following entities: {{{ENTITY_KEY_FOR_FORMAT}}}",
}

ENTITY_MAPPING = "EM"
DUPLICATED_DEVICES = "DUP"
FOUNDED_DEVICES = "FD"
STEP = "STEP"
CUSTOM_VARIABLE = "CV"
DEFAULT_TIMEOUT = 300
RETRY = "RT"

FAILED_ENTITY_STATE = "failed"
IN_PROGRESS_ENTITY_STATE = "in_progress"
COMPLETED_ENTITY_STATE = "completed"
GLOBAL_TIMEOUT_THRESHOLD_IN_MIN = 1


class AsyncActionStepHandlerException(Exception):
    pass


class TimeOutReachedException(AsyncActionStepHandlerException):
    pass


class ActionStep:
    def __init__(
        self,
        step_id,
        step_label,
        method_name,
        only_success_required=False,
        retry=1,
        wait_before_retry=0,
        variables=None,
    ):
        self.step_id = step_id
        self.step_label = step_label
        self.method_name = method_name
        self.only_success_required = only_success_required
        self.retry = retry
        self.wait_before_retry = wait_before_retry
        self.variables = variables or {}


class AsyncActionStepHandler:
    def __init__(
        self,
        siemplify,
        manager,
        action_steps,
        result_value,
        action_global,
        action_start_time=None,
        output_message_collection=None,
    ):
        self.siemplify = siemplify
        self.manager = manager
        self.action_steps = action_steps
        self.action_start_time = action_start_time or unix_now()
        self.result_value = result_value
        self.output_message_collection = output_message_collection or {}
        self.addition_output_message_before = {}
        self.addition_output_message_after = {}
        self.starting_step_index = 0
        self.set_initial_step()
        self.action_global = action_global
        self.timeout_reached = False
        self.logger = self.siemplify.LOGGER
        self.iteration_completed = False
        self.output_message_variables = {}
        self.json_result = {}

    def execute_steps(self):
        self.validate_configs()
        result_value, status, retry_count = None, None, self.get_retry()
        try:
            for index, action_step in self.action_steps.items():
                if index < self.starting_step_index:
                    continue
                self.start_step(action_step)
                while True:
                    if self.is_approaching_timeout():
                        raise TimeOutReachedException

                    self.wait_if_needed(retry_count, action_step)
                    self.action_global[action_step.method_name](
                        self, **action_step.variables
                    )
                    result_value, status = self.step_finalizer()

                    if self.is_step_finished(action_step, index, status, retry_count):
                        break
                    retry_count += 1
                    self.process_max_retry(retry_count, action_step)
                self.finish_step(action_step)
                self.update_iteration_status(status)
                retry_count = 0
                if self.iteration_completed:
                    self.logger.info("Iteration completed!")
                    break
        except TimeOutReachedException:
            self.set_retry(retry_count)
            if self.is_approaching_global_timeout():
                self.logger.info("Timeout reached!")
                status = EXECUTION_STATE_FAILED
                result_value = False
        self.update_iteration_status(status)
        return self.finish_execution(result_value, status)

    def finish_execution(self, result_value, status):
        json_result = self.build_json_result(self.json_result)
        if json_result:
            self.siemplify.result.add_result_json(json_result)
        return self.return_action_results(result_value, status)

    def add_output_messages(self, output_messages):
        self.output_message_collection[self.get_current_step()] = output_messages

    def is_step_complete(self):
        return not bool(self.get_entities_by_state(IN_PROGRESS_ENTITY_STATE))

    def step_finalizer(self):
        if self.is_all_entities_in_state(FAILED_ENTITY_STATE):
            self.logger.info(f"All entities are failed.")
            return False, EXECUTION_STATE_COMPLETED
        if self._should_change_step():
            self.logger.info("Moving to the next step")
            return self.go_to_next_step()
        self.logger.info(
            "There are still in progress items. Executing step one more time."
        )
        return self.result_value, EXECUTION_STATE_INPROGRESS

    def _should_change_step(self):
        return not bool(self.get_entities_by_state(IN_PROGRESS_ENTITY_STATE))

    def get_entity_mapping(self):
        if not self.result_value.get(ENTITY_MAPPING):
            self.result_value[ENTITY_MAPPING] = {}
        return self.result_value[ENTITY_MAPPING]

    def get_current_step(self):
        return self.result_value.get(STEP)

    def set_current_step(self, step):
        self.result_value[STEP] = step

    def get_entity_mapping_values(self):
        return self.get_entity_mapping().values()

    def get_full_entity_data(self, entity):
        return self.get_entity_mapping().get(entity, {})

    def get_entity_data(self, entity, step=None):
        return self.get_full_entity_data_for_step(entity, step).get(ENTITY_DATA_KEY)

    def get_full_entity_data_for_step(self, entity, step=None):
        return self.get_full_entity_data(entity).get(self.get_step_or_current(step), {})

    def is_entity_in_state(self, step, entity, state):
        return state == self.get_full_entity_data_for_step(entity, step).get(
            ENTITY_STATE_KEY, IN_PROGRESS_ENTITY_STATE
        )

    def get_all_entities(self):
        return self.get_entity_mapping().keys()

    def get_entities_by_state(self, state, step=None):
        return [
            entity
            for entity in self.get_all_entities()
            if self.is_entity_in_state(self.get_step_or_current(step), entity, state)
        ]

    def get_step_data_by(self, index=None, step_id=None):
        if index is not None:
            return self.action_steps[index]
        if step_id is not None:
            for index, step_data in self.action_steps.items():
                if step_data.step_id == step_id:
                    return step_data
            raise Exception(f"Unable to find step data with step_id {step_id}")
        return self.action_steps[self.get_step_index()]

    def failed_on_step(self, step=None):
        step = self.get_step_or_current(step)
        step_index = self.get_step_index(step)
        failed_entities = self.get_entities_by_state(FAILED_ENTITY_STATE, step)
        if step_index == 0:
            return failed_entities

        previously_failed_entities = self.get_entities_by_state(
            FAILED_ENTITY_STATE, self.get_step_data_by(index=(step_index - 1)).step_id
        )
        return list(set(failed_entities) - set(previously_failed_entities))

    def get_step_or_current(self, step=None):
        return step or self.get_current_step()

    def is_all_entities_in_state(self, state, step=None):
        return len(self.get_all_entities()) == len(
            self.get_entities_by_state(state, step)
        )

    def get_step_index(self, step=None):
        step_for_search = self.get_step_or_current(step)
        for index, action_step in self.action_steps.items():
            if action_step.step_id == step_for_search:
                return index

    def go_to_next_step(self):
        next_step_index = self.get_step_index() + 1

        if not self.is_step_exists(next_step_index):
            return True, EXECUTION_STATE_COMPLETED

        self.init_state(next_step_index)
        return self.result_value, EXECUTION_STATE_INPROGRESS

    def is_last_step(self):
        return self.get_step_index() + 1 == self.get_steps_count()

    def is_step_exists(self, step_index):
        return bool(self.action_steps.get(step_index))

    def get_output_message_for_id(
        self, output_message_id, variables_for_format, step=None
    ):
        output_message = self.output_message_collection.get(
            self.get_step_or_current(step), {}
        ).get(output_message_id, DEFAULT_OUTPUT_MESSAGES[output_message_id])
        variables_for_format.update(
            {STEP_KEY_FOR_FORMAT: self.get_step_data_by(step_id=step).step_label}
        )
        existing_variables_for_format = {}
        for _, fn, _, _ in Formatter().parse(output_message):
            if variables_for_format.get(fn):
                existing_variables_for_format[fn] = variables_for_format.get(fn)
            if self.output_message_variables.get(fn):
                existing_variables_for_format[fn] = self.output_message_variables.get(
                    fn
                )

            existing_variables_for_format[fn] = existing_variables_for_format.get(
                fn, fn
            )
        return (
            f"{output_message.format(**existing_variables_for_format)}\n"
            if output_message
            else ""
        )

    def format_output_message(self, output_message):
        return output_message[:-1]

    def get_output_message(self):
        current_step = self.get_current_step()
        output_message = ""
        if self.timeout_reached:
            return self.get_output_message_for_id(
                TIMEOUT_REACHED_MSG,
                {
                    ENTITY_KEY_FOR_FORMAT: ", ".join(
                        self.get_entities_by_state(IN_PROGRESS_ENTITY_STATE)
                    )
                },
            )

        if self.addition_output_message_before.get(current_step):
            output_message += (
                f"{self.addition_output_message_before.get(current_step)}\n"
            )

        output_message += self.build_entity_output_message()

        if self.addition_output_message_after.get(current_step):
            output_message += (
                f"{self.addition_output_message_after.get(current_step)}\n"
            )

        return output_message

    def get_action_step_by(self):
        step_index = self.get_step_index()

        if self.is_step_exists(step_index):
            return self.action_steps.get(step_index)

        raise Exception(
            f"Step with index {step_index} does not exist. Available indexes are "
            f"{self.action_steps.keys()}"
        )

    def get_updated_entity_mapping(
        self, entity_identifier, key, entity_data, step=None
    ):
        entity_mapping = self.get_entity_mapping()
        entity_mapping[entity_identifier] = entity_mapping.get(entity_identifier, {})

        entity_mapping[entity_identifier][self.get_step_or_current(step)] = (
            entity_mapping[entity_identifier].get(self.get_step_or_current(step), {})
        )

        entity_mapping[entity_identifier][self.get_step_or_current(step)][
            key
        ] = entity_data
        return entity_mapping

    def add_entity_data_to_step(
        self, entity_identifier, entity_data, step=None, mark_as_completed=True
    ):
        self.update_entity_mapping(
            self.get_updated_entity_mapping(
                entity_identifier, ENTITY_DATA_KEY, entity_data, step
            )
        )
        if mark_as_completed:
            self.set_entity_state(entity_identifier, COMPLETED_ENTITY_STATE, step)

    def set_entity_state(self, entity_identifier, state, step=None):
        self.update_entity_mapping(
            self.get_updated_entity_mapping(
                entity_identifier, ENTITY_STATE_KEY, state, step
            )
        )

    def fail_entity(self, entity_identifier, step=None, reason=None):
        self.set_entity_state(entity_identifier, FAILED_ENTITY_STATE, step)
        if reason:
            self.update_entity_mapping(
                self.get_updated_entity_mapping(
                    entity_identifier, ENTITY_REASON_KEY, reason, step
                )
            )

    def update_entity_mapping(self, entity_mapping):
        self.result_value[ENTITY_MAPPING] = entity_mapping

    def update_entity_mapping_with_dict(self, entity_data):
        entity_mapping = self.get_entity_mapping()
        entity_mapping.update(entity_data)

    def set_initial_step(self):
        self.set_current_step(self.get_current_step() or self.action_steps[0].step_id)
        self.starting_step_index = self.get_step_index()

    def init_state(self, next_step_index):
        failed_entities = self.get_entities_by_state(FAILED_ENTITY_STATE)
        self.set_current_step(self.action_steps[next_step_index].step_id)
        self.mark_entities_as_failed(failed_entities)
        self.set_retry(0)
        self.add_output_messages({})

    def mark_entities_as_failed(self, failed_entities):
        for failed_entity in failed_entities:
            self.set_entity_state(failed_entity, FAILED_ENTITY_STATE)

    def is_approaching_timeout(self):
        return (
            self.is_approaching_iteration_timeout()
            or self.is_approaching_global_timeout()
        )

    def is_approaching_global_timeout(self):
        self.timeout_reached = (
            self.siemplify.execution_deadline_unix_time_ms - unix_now()
            < GLOBAL_TIMEOUT_THRESHOLD_IN_MIN * 60000
        )
        return self.timeout_reached

    def is_approaching_iteration_timeout(self):
        return unix_now() - self.action_start_time > int(DEFAULT_TIMEOUT * 1000 * 0.7)

    def validate_configs(self):
        if not self.action_steps:
            raise Exception("No Action steps provided.")

    def return_action_results(self, result_value, status):
        if None in [result_value, status]:
            raise Exception("Unable to get data from execution.")
        return (
            self.format_output_message(self.get_output_message()),
            self.get_final_result_value(result_value),
            status,
        )

    def get_custom_variable(self, variable_name):
        if not self.result_value.get(CUSTOM_VARIABLE):
            self.result_value[CUSTOM_VARIABLE] = {}
        return self.result_value[CUSTOM_VARIABLE].get(variable_name)

    def add_custom_variable(self, variable_name, data):
        if not self.result_value.get(CUSTOM_VARIABLE):
            self.result_value[CUSTOM_VARIABLE] = {}
        self.result_value[CUSTOM_VARIABLE][variable_name] = data

    def set_retry(self, count):
        self.result_value[RETRY] = count

    def get_retry(self):
        return self.result_value.get(RETRY, 0)

    def fail_all_in_progress_entities(self, reason):
        for entity in self.get_entities_by_state(IN_PROGRESS_ENTITY_STATE):
            self.fail_entity(entity, reason=reason)

    def is_step_finished(self, action_step, index, status, retry_count):
        return (
            self.get_step_index() != index
            or status != EXECUTION_STATE_INPROGRESS
            or action_step.retry < retry_count
        )

    def get_steps_count(self):
        return len(self.action_steps.keys())

    def add_addition_output_message(
        self, message, step=None, position=OUTPUT_MESSAGE_AFTER
    ):
        (
            self.addition_output_message_after
            if position == OUTPUT_MESSAGE_AFTER
            else self.addition_output_message_before
        )[self.get_step_or_current(step)] = message

    def build_entity_output_message(self):
        output_message = ""
        in_progress_items = self.get_entities_by_state(IN_PROGRESS_ENTITY_STATE)
        completed_items = self.get_entities_by_state(COMPLETED_ENTITY_STATE)
        if completed_items:
            output_message += self.get_output_message_for_id(
                SOME_COMPLETED_MSG, {ENTITY_KEY_FOR_FORMAT: ", ".join(completed_items)}
            )

        output_message += self.add_failed_entities_output_message()

        if in_progress_items:
            output_message += self.get_output_message_for_id(
                IN_PROGRESS_MSG, {ENTITY_KEY_FOR_FORMAT: ", ".join(in_progress_items)}
            )

        return output_message

    def update_iteration_status(self, status):
        self.iteration_completed = status not in [None, EXECUTION_STATE_INPROGRESS]
        return self.iteration_completed

    def add_failed_entities_output_message(self):
        all_failed_output_message = self.build_all_failed_output_message()
        if all_failed_output_message:
            return all_failed_output_message

        output_message, not_handled_failed_entities = (
            self.get_failed_output_message_for_previous_steps()
        )

        if not_handled_failed_entities:
            output_message += self.get_output_message_for_id(
                SOME_FAILED_MSG,
                {
                    ENTITY_KEY_FOR_FORMAT: ", ".join(
                        list(
                            set(
                                [
                                    self.extract_entities_from_item(item)
                                    for item in list(not_handled_failed_entities)
                                ]
                            )
                        )
                    )
                },
            )

        return output_message

    def build_all_failed_output_message(self):
        if self.is_last_step() and (
            len(self.get_all_entities()) == len(self.failed_on_step())
        ):
            return self.get_output_message_for_id(
                ALL_FAILED_MSG,
                {
                    ENTITY_KEY_FOR_FORMAT: ", ".join(
                        self.get_entities_by_state(FAILED_ENTITY_STATE)
                    )
                },
            )

    def get_failed_output_message_for_previous_steps(self):
        output_message, not_handled_failed_entities, current_step_index = (
            "",
            set(),
            self.get_step_index(),
        )
        for index, action_step in self.action_steps.items():
            if index > current_step_index:
                break
            output_message_for_step = self.output_message_collection.get(
                action_step.step_id, {}
            )
            failed_items = self.failed_on_step(action_step.step_id)

            if not output_message_for_step.get(SOME_FAILED_MSG):
                not_handled_failed_entities.update(set(failed_items))
                continue

            if failed_items:
                output_message += self.get_output_message_for_id(
                    SOME_FAILED_MSG,
                    {
                        ENTITY_KEY_FOR_FORMAT: ", ".join(
                            list(
                                set(
                                    [
                                        self.extract_entities_from_item(item)
                                        for item in failed_items
                                    ]
                                )
                            )
                        )
                    },
                    step=action_step.step_id,
                )

        return output_message, not_handled_failed_entities

    def wait_if_needed(self, retry_count, action_step):
        if retry_count > 0 and retry_count != action_step.retry:
            self.logger.info(f"Retrying {retry_count} out of {action_step.retry}")
            self.logger.info(f"Waiting {action_step.wait_before_retry} seconds...")
            sleep(action_step.wait_before_retry)

    def process_max_retry(self, retry_count, action_step):
        if retry_count >= action_step.retry:
            self.logger.info(
                f"Max retry count {action_step.retry} reached. "
                f"Marking in progress entities as failed"
            )
            self.fail_all_in_progress_entities(
                reason=f"Max retry for {self.get_step_data_by().step_label} reached."
            )

    def finish_step(self, action_step):
        self.logger.info(f'*** Finishing step "{action_step.step_label}" ***')
        self.logger.info(
            f"Successful items are: {self.get_entities_by_state(COMPLETED_ENTITY_STATE, action_step.step_id)}"
        )

    def start_step(self, action_step):
        self.logger.info(f'\n *** Starting step "{action_step.step_label}" ***')

    def get_final_result_value(self, result_value):
        for index, action_step in self.action_steps.items():
            if action_step.only_success_required and self.failed_on_step(
                action_step.step_id
            ):
                result_value = False
                break
        return result_value

    def remove_entity(self, entity):
        entity_mapping = self.get_entity_mapping()
        if not entity_mapping.get(entity):
            self.logger.info(f"Entity {entity} does not exists")
            return False
        del entity_mapping[entity]
        self.logger.info(f"Entity {entity} removed successfully")
        self.update_entity_mapping(entity_mapping)
        return True

    def build_json_result(
        self,
        successful_json_result,
        include_failed_json=True,
        include_timed_out_entities=True,
    ):
        if include_failed_json:
            for index, action_step in self.action_steps.items():
                for entity in self.failed_on_step(action_step.step_id):
                    successful_json_result[entity] = {
                        "step": action_step.step_label,
                        "reason": self.get_reason(entity, action_step.step_id),
                        "is_success": False,
                    }
        if include_timed_out_entities and self.timeout_reached:
            for entity in self.get_all_entities():
                successful_json_result[entity] = {
                    "step": self.get_step_data_by().step_label,
                    "reason": "Timeout reached!",
                    "is_success": False,
                }
        return convert_dict_to_json_result_dict(successful_json_result)

    def get_reason(self, entity, step=None):
        return self.get_full_entity_data_for_step(
            entity, self.get_step_or_current(step)
        ).get(ENTITY_REASON_KEY)

    def get_entity(self, entity_identifier):
        return [
            entity
            for entity in self.siemplify.target_entities
            if get_entity_original_identifier(entity) == entity_identifier
        ][0]

    def add_output_message_variable(self, key, value):
        self.output_message_variables[key] = value

    def extract_entities_from_item(self, item, position=0):
        all_entities = item.split(ENTITY_FILENAME_CONCAT_CHAR)
        return all_entities[position] if position >= 0 else all_entities
