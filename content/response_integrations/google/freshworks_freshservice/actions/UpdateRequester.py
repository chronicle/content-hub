from __future__ import annotations
from TIPCommon import extract_configuration_param, extract_action_param

from ..core.FreshworksFreshserviceManager import FreshworksFreshserviceManager
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.consts import (
    INTEGRATION_IDENTIFIER,
    INTEGRATION_DISPLAY_NAME,
    UPDATE_REQUESTER_SCRIPT_NAME,
    PARAMETERS_DEFAULT_DELIMITER,
)
from ..core.exceptions import (
    FreshworksFreshserviceValidationError,
    FreshworksFreshserviceDuplicateValueError,
    FreshworksFreshserviceNotFoundError,
    FreshworksFreshserviceNegativeValueException,
)
from ..core.utils import (
    load_csv_to_list,
    load_json_string_to_dict,
    remove_none_dictionary_values,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_IDENTIFIER} - {UPDATE_REQUESTER_SCRIPT_NAME}"
    siemplify.LOGGER.info("=================== Main - Param Init ===================")

    # Integration configuration
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="API Key",
        is_mandatory=True,
        print_value=False,
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_IDENTIFIER,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=True,
        print_value=True,
    )

    # Action configuration
    primary_email = extract_action_param(
        siemplify, param_name="Email", print_value=True, is_mandatory=False
    )
    job_title = extract_action_param(
        siemplify, param_name="Job Title", print_value=True, is_mandatory=False
    )
    first_name = extract_action_param(
        siemplify, param_name="First Name", print_value=True, is_mandatory=False
    )
    last_name = extract_action_param(
        siemplify, param_name="Last Name", print_value=True, is_mandatory=False
    )
    can_see_all_tickets_from_associated_departments = extract_action_param(
        siemplify,
        param_name="Can See All Tickets From Associated Departments",
        print_value=True,
        input_type=bool,
        default_value=False,
        is_mandatory=False,
    )
    departments = extract_action_param(
        siemplify, param_name="Departments", print_value=True, is_mandatory=False
    )
    location = extract_action_param(
        siemplify, param_name="Location", print_value=True, is_mandatory=False
    )
    custom_fields = extract_action_param(
        siemplify, param_name="Custom Fields", print_value=True, is_mandatory=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    # Action results
    status = EXECUTION_STATE_COMPLETED
    result_value = False

    try:
        requester_id = extract_action_param(
            siemplify,
            param_name="Requester ID",
            print_value=True,
            input_type=int,
            is_mandatory=True,
        )
        if requester_id < 0:
            raise FreshworksFreshserviceNegativeValueException(
                '"Requester ID" should be a positive number.'
            )
        departments = (
            load_csv_to_list(departments, "Departments") if departments else None
        )
        custom_fields = (
            load_json_string_to_dict(custom_fields, "Custom Fields")
            if custom_fields
            else None
        )

        manager = FreshworksFreshserviceManager(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
            force_test_connectivity=True,
        )

        departments_to_ids, location_id = {}, None

        # Lookup department ids
        if departments:
            all_departments = manager.get_departments()
            departments_to_ids = {}
            invalid_departments = []
            for param_department in departments:
                for department in all_departments:
                    if department.name == param_department:
                        departments_to_ids[department.name] = department.id
                if param_department not in departments_to_ids:
                    invalid_departments.append(param_department)
            if invalid_departments:
                raise FreshworksFreshserviceValidationError(
                    f"Failed to find the following departments in {INTEGRATION_DISPLAY_NAME}: "
                    f"{PARAMETERS_DEFAULT_DELIMITER.join(invalid_departments)}"
                )

        # Lookup location id
        if location:
            all_locations = manager.get_locations()
            for freshservice_location in all_locations:
                if location == freshservice_location.name:
                    location_id = freshservice_location.id
            if location_id is None:
                raise FreshworksFreshserviceValidationError(
                    f"Failed to find location in {INTEGRATION_DISPLAY_NAME}."
                )

        try:
            requester = manager.update_requester(
                **remove_none_dictionary_values(
                    requester_id=requester_id,
                    first_name=first_name,
                    last_name=last_name,
                    primary_email=primary_email,
                    job_title=job_title,
                    location_id=location_id,
                    department_ids=list(departments_to_ids.values()) or None,
                    can_see_all_tickets_from_associated_departments=can_see_all_tickets_from_associated_departments,
                    custom_fields=custom_fields,
                )
            )
            if location and isinstance(requester.location_id, int):
                requester.set_location_name(location)
            if departments_to_ids and requester.department_ids:
                requester.set_department_names(list(departments_to_ids.keys()))

            siemplify.result.add_result_json({"requester": requester.to_json()})
            output_message = f"{INTEGRATION_DISPLAY_NAME} requester is updated."
            result_value = True
        except FreshworksFreshserviceNotFoundError as error:
            output_message = (
                f"Failed to update requester {requester_id}"
                " with the provided parameters! "
                f"Error is: Requester {requester_id} was not "
                f"found in {INTEGRATION_DISPLAY_NAME}."
            )
            siemplify.LOGGER.error(output_message)
            siemplify.LOGGER.exception(error)

    except (
        FreshworksFreshserviceValidationError,
        FreshworksFreshserviceDuplicateValueError,
    ) as error:
        output_message = f"Failed to update {INTEGRATION_DISPLAY_NAME} requester with the provided parameters! Error is: {error}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    except Exception as error:
        output_message = (
            f'Error executing action "{UPDATE_REQUESTER_SCRIPT_NAME}". Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
