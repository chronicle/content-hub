from __future__ import annotations

from shlex import quote

from anyrun import RunTimeException
from anyrun.connectors import FeedsConnector
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param

from ..core.config import Config


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{Config.INTEGRATION_NAME} - Ping"

    feeds_token = extract_configuration_param(
        siemplify,
        Config.INTEGRATION_NAME,
        param_name="ANYRUN TI Feeds Basic token",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify, Config.INTEGRATION_NAME, param_name="Verify SSL", input_type=bool
    )

    try:
        if extract_configuration_param(
            siemplify, Config.INTEGRATION_NAME, param_name="Enable proxy", input_type=bool
        ):
            check_proxy(siemplify, feeds_token, verify_ssl)

        with FeedsConnector(
            api_key=feeds_token, integration=Config.VERSION, verify_ssl=verify_ssl
        ) as connector:
            connector.check_authorization()

    except RunTimeException as exception:
        output_message = str(exception)
        siemplify.LOGGER.error(output_message)
        status = EXECUTION_STATE_FAILED
        is_succes = False
    else:
        output_message = (
            f"[ANY.RUN] Successful connection to the {Config.INTEGRATION_NAME} services!"
        )
        siemplify.LOGGER.info(output_message)
        status = EXECUTION_STATE_COMPLETED
        is_succes = True

    siemplify.end(output_message, is_succes, status)


def check_proxy(siemplify: SiemplifyAction, token: str, verify_ssl: bool) -> None:
    try:
        host = quote(
            extract_configuration_param(siemplify, Config.INTEGRATION_NAME, param_name="Proxy host")
        )
        port = quote(
            extract_configuration_param(siemplify, Config.INTEGRATION_NAME, param_name="Proxy port")
        )

        with FeedsConnector(
            api_key=token, proxy=f"https://{host}:{port}", verify_ssl=verify_ssl
        ) as connector:
            connector.check_proxy()

    except TypeError:
        raise RunTimeException(
            "[ANY.RUN] The proxy request failed. Check the proxy settings are correct"
        )


if __name__ == "__main__":
    main()
