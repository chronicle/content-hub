from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from TIPCommon import extract_configuration_param
from ..core.MSSQLManager import MSSQLManager


INTEGRATION_NAME = "MSSQL"
SCRIPT_NAME = "Ping"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    server_addr = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Server Address"
    )
    username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Username"
    )
    password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Password"
    )
    port = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Port", input_type=int
    )
    database = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Database Name For Testing",
    )
    win_auth = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Windows Authentication",
        default_value=False,
        input_type=bool,
    )
    use_kerberos = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use Kerberos Authentication",
        default_value=False,
        input_type=bool,
    )
    kerberos_realm = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Kerberos Realm"
    )
    kerberos_username = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Kerberos Username"
    )
    kerberos_password = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Kerberos Password"
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        print_value=True,
        input_type=bool,
        is_mandatory=False,
        default_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        sql_manager = MSSQLManager(
            username=username,
            password=password,
            server=server_addr,
            database=database,
            port=port,
            trusted=win_auth,
            use_kerberos=use_kerberos,
            kerberos_realm=kerberos_realm,
            kerberos_username=kerberos_username,
            kerberos_password=kerberos_password,
            siemplify=siemplify,
            verify_ssl=verify_ssl,
        )

        siemplify.LOGGER.info(
            f"Connecting to SQL Server instance {server_addr}:{port}."
        )
        sql_manager.connect()

        # If no exception occur - then connection is successful
        siemplify.LOGGER.info("Connected successfully.")
        status = EXECUTION_STATE_COMPLETED
        output_message = (
            f"Successfully connected to {database} at {server_addr}:{port}."
        )
        result_value = "true"

    except Exception as e:
        siemplify.LOGGER.error(
            f"General error performing action {SCRIPT_NAME}. Error: {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"General error performing action {SCRIPT_NAME}. Error: {e}"

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
