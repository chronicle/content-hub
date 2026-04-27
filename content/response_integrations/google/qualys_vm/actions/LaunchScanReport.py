from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import (
    extract_action_param,
    convert_comma_separated_to_list,
)
from ..core.manager_factory import create_qualys_manager_from_action
from ..core.constants import INTEGRATION_NAME, LAUNCH_SCAN_REPORT_SCRIPT_NAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LAUNCH_SCAN_REPORT_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # INIT INTEGRATION CONFIGURATION:

    # INIT ACTION PARAMETERS:
    report_title = extract_action_param(
        siemplify, param_name="Report Title", is_mandatory=True, print_value=True
    )
    template_name = extract_action_param(
        siemplify, param_name="Report Type", is_mandatory=True, print_value=True
    )
    output_format = extract_action_param(
        siemplify, param_name="Output Format", is_mandatory=True, print_value=True
    )
    ips = extract_action_param(siemplify, param_name="IPs/Ranges", print_value=True)
    asset_group_names = extract_action_param(
        siemplify, param_name="Asset Groups", default_value="", print_value=True
    )
    asset_group_names = convert_comma_separated_to_list(asset_group_names)
    report_refs = extract_action_param(
        siemplify, param_name="Scan Reference", print_value=False
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    asset_group_ids = []

    try:
        qualys_manager = create_qualys_manager_from_action(siemplify)

        for asset_group_name in asset_group_names:
            matching_asset_groups = qualys_manager.list_asset_groups(
                title=asset_group_name
            )
            if matching_asset_groups:
                asset_group_ids.append(matching_asset_groups[0].get("ID"))

        template_id = qualys_manager.get_template_id_by_name(template_name)

        report_id = qualys_manager.launch_scan_report(
            report_title=report_title,
            template_id=template_id,
            output_format=output_format,
            ips=ips,
            asset_group_ids=asset_group_ids,
            report_refs=report_refs,
        )
        output_message = f"Scan report was initialized. Report ID: {report_id}."

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {LAUNCH_SCAN_REPORT_SCRIPT_NAME}"
        )
        siemplify.LOGGER.exception(e)
        report_id = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f'Error executing action "{LAUNCH_SCAN_REPORT_SCRIPT_NAME}". Reason: {e}'
        )

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {report_id}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, report_id, status)


if __name__ == "__main__":
    main()
