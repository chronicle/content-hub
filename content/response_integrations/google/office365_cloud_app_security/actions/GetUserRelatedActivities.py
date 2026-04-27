from __future__ import annotations
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.Office365CloudAppSecurityManager import (
    Office365CloudAppSecurityManager,
    Office365CloudAppSecurityConfigurationError,
)
from ..core.Office365CloudAppSecurityCommon import Office365CloudAppSecurityCommon
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyDataModel import EntityTypes
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv

# =====================================
#             CONSTANTS               #
# =====================================
INTEGRATION_NAME = "Office365CloudAppSecurity"
SCRIPT_NAME = "Office365CloudAppSecurity - Get User Related Activities"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    result_value = "true"
    output_message = ""
    json_results = {}

    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="portal URL",
        input_type=str,
    )

    api_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API token",
        input_type=str,
    )

    # INIT ACTION PARAMETERS:
    activity_display_limit = extract_action_param(
        siemplify,
        param_name="Activity Display Limit",
        is_mandatory=False,
        print_value=False,
        input_type=int,
    )
    time_frame = extract_action_param(
        siemplify,
        param_name="Time Frame",
        is_mandatory=True,
        print_value=True,
        input_type=int,
    )
    product_name = extract_action_param(
        siemplify,
        param_name="Product Name",
        is_mandatory=False,
        print_value=True,
        input_type=str,
    )

    cloud_app_manager = Office365CloudAppSecurityManager(
        api_root=api_root, api_token=api_token
    )
    cloud_app_common = Office365CloudAppSecurityCommon(siemplify.LOGGER)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        status = EXECUTION_STATE_COMPLETED
        failed_entities = []
        successfull_entities = []
        no_activities = []

        for entity in siemplify.target_entities:
            if entity.entity_type == EntityTypes.USER:
                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break
                try:
                    activities = cloud_app_manager.get_user_related_activities(
                        entity.additional_properties.get(
                            "OriginalIdentifier", entity.identifier.lower()
                        ),
                        time_frame,
                        product_name,
                        activity_display_limit,
                    )

                    if not activities:
                        no_activities.append(entity.identifier)
                        siemplify.LOGGER.error(
                            f"No alert related activities were found: {entity.identifier} "
                        )
                    else:
                        json_results[entity.identifier] = [
                            activity.to_json() for activity in activities
                        ]

                        activity_table = construct_csv(
                            [activity.to_table_data() for activity in activities]
                        )
                        siemplify.result.add_data_table(
                            title=f"{entity.identifier} Related Activity Table ",
                            data_table=activity_table,
                        )

                        output_message += f"User related activities for the following user were fetched:{entity.identifier}. \n"

                    successfull_entities.append(entity)
                    siemplify.LOGGER.info(
                        f"Finished processing entity {entity.identifier}"
                    )

                except Office365CloudAppSecurityConfigurationError as e:
                    raise

                except Exception as e:
                    failed_entities.append(entity)
                    siemplify.LOGGER.error(
                        f"An error occurred on entity {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)
            else:
                siemplify.LOGGER.info(
                    f"The entity {entity.identifier} is not a type of USER, skipping..."
                )

        if no_activities:
            output_message += f"\n No activities related to these users: {', '.join([entity for entity in no_activities])} were found.\n"

        if not successfull_entities:
            siemplify.LOGGER.info("\n No entities where processed.")
            output_message = "No entities where processed."
            result_value = "false"

        if failed_entities:
            result_value = "false"
            output_message = "No entities where processed."
            siemplify.LOGGER.info(
                "\n Failed processing entities:\n   {}".format(
                    "\n".join([entity.identifier for entity in failed_entities])
                )
            )

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = (
            f'Error executing action "Get User Related Activities". Reason: {e}'
        )

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
