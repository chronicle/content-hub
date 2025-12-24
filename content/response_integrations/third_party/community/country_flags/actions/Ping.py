from __future__ import annotations

import base64
import json
import os

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

# Consts:
SCRIPT_NAME = "GetCountryFlag"
FLAGS_FILE = "flags.json"
FLAGS_URL = "https://www.countryflags.io/{}/flat/64.png"

SHOULD_UPDATE_FILE = False


def get_base64_flag_data(country_code, flags_data, siemplify):
    if country_code in flags_data:
        siemplify.LOGGER.info(f"Country flag found in cache. Country - {country_code}")
    else:
        siemplify.LOGGER.info(
            f"Country flag not found in cache. Country - {country_code}",
        )
        flag_res = requests.get(FLAGS_URL.format(country_code))
        flag_res.raise_for_status()
        base64_flag = base64.b64encode(flag_res.content).decode("utf-8")
        flags_data[country_code] = base64_flag
        SHOULD_UPDATE_FILE = True

    return flags_data[country_code]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("Attempting to open cache file")
    try:
        with open(os.path.join(siemplify.run_folder, FLAGS_FILE)) as f:
            data = f.read()
    except:
        siemplify.LOGGER.info("Cache file not found, defaulting to empty cache")
        data = {}

    try:
        flags_data = json.loads(data)
    except:
        siemplify.LOGGER.info(
            "Cache file does not represent a JSON. Creating an empty JSON instead",
        )
        flags_data = {}

    country_code = "us"

    if country_code:
        b64_flag = get_base64_flag_data(country_code, flags_data, siemplify)
        if b64_flag:
            siemplify.end("Successful", "True")

    siemplify.end("Faild", False, EXECUTION_STATE_FAILED)


if __name__ == "__main__":
    main()
