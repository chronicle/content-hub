from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TenableManager import TenableSecurityCenterManager

SCRIPT_NAME = "TenableSecurityCenter - GetReport"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("TenableSecurityCenter")
    server_address = conf["Server Address"]
    username = conf.get("Username")
    password = conf.get("Password")
    access_key = conf.get("Access Key")
    secret_key = conf.get("Secret Key")
    use_ssl = conf["Use SSL"].lower() == "true"

    report_id = siemplify.parameters.get("Report ID")
    report_name = siemplify.parameters.get("Report Name")

    tenable_manager = TenableSecurityCenterManager(
        server_address,
        username,
        password,
        access_key,
        secret_key,
        use_ssl,
    )
    try:
        if report_id:
            siemplify.LOGGER.info(f"Fetching report by ID: {report_id}")
            report = tenable_manager.get_report_by_id(report_id)
        elif report_name:
            siemplify.LOGGER.info(f"Fetching report by name: {report_name}")
            report = tenable_manager.get_report_by_name(report_name)
        else:
            raise Exception("One of Report ID or Report name must be inserted.")
    except Exception as err:
        siemplify.LOGGER.error(f"Failed fetching report, ERROR: {err}")
        siemplify.LOGGER.exception(err)
        raise

    if report:
        siemplify.result.add_result_json(report)
        output_message = "Report found."
        result_value = "true"
    else:
        output_message = "Report not found."
        result_value = "false"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
