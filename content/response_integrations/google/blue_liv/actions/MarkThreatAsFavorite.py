from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.BlueLivManager import BlueLivManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.consts import INTEGRATION_NAME, MARK_THREAT_AS_FAVORITE


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = MARK_THREAT_AS_FAVORITE
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="User Name",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        print_value=False,
    )
    organization_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization ID",
        is_mandatory=True,
        print_value=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
        is_mandatory=True,
    )

    status = EXECUTION_STATE_COMPLETED
    result_value = True
    output_message = ""

    try:
        siemplify.LOGGER.info("----------------- Main - Started -----------------")
        module_id = extract_action_param(
            siemplify,
            param_name="Module ID",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        module_type = extract_action_param(
            siemplify,
            param_name="Module Type",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        module_type = module_type.lower()
        threat_id = extract_action_param(
            siemplify,
            param_name="Resource ID",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )
        favorite_status = extract_action_param(
            siemplify,
            param_name="Favorite Status",
            is_mandatory=True,
            print_value=True,
            input_type=str,
        )

        blueliv_manager = BlueLivManager(
            api_root=api_root,
            username=username,
            password=password,
            organization_id=organization_id,
            verify_ssl=verify_ssl,
        )
        blueliv_manager.mark_threat_as_favorite(
            module_id=module_id,
            module_type=module_type,
            threat_id=threat_id,
            status=favorite_status,
        )

        output_message = f"Successfully marked threat ID {threat_id} as favorite."

    except Exception as e:
        output_message += f"Failed to perform action {MARK_THREAT_AS_FAVORITE} {e}"

        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
