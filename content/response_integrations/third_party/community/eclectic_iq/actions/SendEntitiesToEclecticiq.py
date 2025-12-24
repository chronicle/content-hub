from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.EclecticIQManager import EclecticIQManager

INTEGRATION_NAME = "EclecticIQ"
ACTION_NAME = "Send Entities to EclecticIQ"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.LOGGER.info("================= Main - Param Init =================")

    configs = siemplify.get_configuration(INTEGRATION_NAME)

    eiq_url = configs["EclecticIQ URL"]
    api_token = configs["API Token"]
    verify_ssl = configs["Verify SSL"]
    group_name = siemplify.extract_action_param("Group Name")
    create_indicator = siemplify.extract_action_param(
        "Create Indicator",
        print_value=True,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = None

    try:
        eiq_manager = EclecticIQManager(eiq_url, api_token, verify_ssl)
        result = eiq_manager.create_entities(
            siemplify.case,
            siemplify.target_entities,
            group_name,
            create_indicator,
        )
        siemplify.add_comment("Entities are successfully created in EclecticIQ.")
        indicator_id = result.get("data")[0]["id"]
        siemplify.result.add_entity_link(
            "EclecticIQ Platform Link",
            f"{eiq_url}/entity/{indicator_id}",
        )

        output_message = "Entities are successfully created in EclecticIQ."
        result_value = "Success"

    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {ACTION_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += "\n unknown failure"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
