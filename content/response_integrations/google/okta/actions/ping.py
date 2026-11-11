from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from okta.core.OktaManager import OktaManager, OktaException


PROVIDER = "Okta"


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration(PROVIDER)
    api_root = conf.get("Api Root")
    api_token = conf.get("Api Token")
    client_id = conf.get("Client ID")
    use_oauth_authentication = (
        str(conf.get("Use Oauth Authentication", "false")).lower() == "true"
    )
    key_id = conf.get("Key ID")
    private_key = conf.get("Private Key")
    verify_ssl = str(conf.get("Verify SSL", "false")).lower() == "true"

    try:
        okta = OktaManager(
            api_root=api_root,
            api_token=api_token,
            client_id=client_id,
            use_oauth_authentication=use_oauth_authentication,
            key_id=key_id,
            private_key=private_key,
            verify_ssl=verify_ssl,
            logger=siemplify.LOGGER,
        )
        okta.test_connectivity()
        output_message = "Connection Established Successfully"
        result = True
        status = EXECUTION_STATE_COMPLETED
    except OktaException as err:
        output_message = f"Connection Failed: {err}"
        result = False
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(err)

    siemplify.end(output_message, result, status)


if __name__ == "__main__":
    main()
