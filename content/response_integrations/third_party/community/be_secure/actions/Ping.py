from __future__ import annotations

import json
import re

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

# CONSTS
INTEGRATION_NAME = "beSECURE"


def make_action(siemplify, url, verify_ssl, **kwargs):
    params = dict([(k, v) for k, v in list(kwargs.items())])

    res = requests.get(f"{url}/json.cgi", params=params, verify=verify_ssl)
    res.raise_for_status()

    return res.json()


@output_handler
def main():
    siemplify = SiemplifyAction()

    output_message = "Successful"
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    conf = siemplify.get_configuration(INTEGRATION_NAME)
    api_key = conf["API Key"]
    api_key = re.sub(r"[^A-Z0-9\-]", "", api_key)  # Clean non-API related characters

    url = conf["URL"]
    if not url.startswith("https://") and not url.startswith("http://"):
        url = "https://" + url

    rotation_time = 1
    verify_ssl = conf["Verify SSL Ceritifcate?"].lower() == "true"

    scans = make_action(
        siemplify,
        url,
        verify_ssl,
        primary="admin",
        secondary="networks",
        action="returnnetworks",
        apikey=api_key,
        search_limit=10000,
        search_datelastscanned_value=rotation_time,
        search_datelastscanned_type="minute",
    )

    # raise Exception(json.dumps(scans))
    if "error" in scans:
        output_message = json.dumps(scans, indent=4)
        result_value = "false"
        status = EXECUTION_STATE_FAILED

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
