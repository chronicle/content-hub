from __future__ import annotations

import requests
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "SOAR - PING"
    provider_name = "Resolution Intelligence Cloud"
    webhook_url = siemplify.extract_configuration_param(
        provider_name=provider_name, param_name="RI Inbound Webhook URL"
    )

    token = siemplify.extract_configuration_param(
        provider_name=provider_name, param_name="Token"
    )

    verify_ssl = siemplify.extract_configuration_param(
        provider_name=provider_name,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )

    if not webhook_url:
        raise Exception("Missing required configuration parameter: ri_inbound_webhook")
    try:
        response = requests.post(
            url=webhook_url.replace("{token}", token), json={}, verify=verify_ssl
        )

        if response.status_code == 200 or response.status_code == 400:
            siemplify.end("Ping successful. API is reachable.", True)
        else:
            siemplify.result.add_result_json({"status_code": response.status_code})

            siemplify.end(
                f"Ping failed. HTTP Status Code: {response.status_code}", False
            )

    except Exception as e:
        siemplify.result.add_result_json({"error": str(e)})
        siemplify.end(f"Ping failed with error: {str(e)}", False)


if __name__ == "__main__":
    main()
