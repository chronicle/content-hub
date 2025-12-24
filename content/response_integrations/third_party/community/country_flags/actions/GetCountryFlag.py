from __future__ import annotations

import base64
import json
import os

import requests
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

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

    country_code = siemplify.parameters.get("Country Code Two Digit")
    country_code_entities_raw = siemplify.parameters.get(
        "Country Code From Entity Field",
    )

    result_json = {}

    for entity in siemplify.target_entities:
        ent_country_code = None
        if country_code_entities_raw:
            country_code_entities = [
                x.strip() for x in country_code_entities_raw.split(",")
            ]
            for field in country_code_entities:
                if field in entity.additional_properties:
                    ent_country_code = entity.additional_properties.get(field)
                if ent_country_code:
                    try:
                        b64_flag = get_base64_flag_data(
                            ent_country_code,
                            flags_data,
                            siemplify,
                        )
                        result_json[entity.identifier] = {"b64_flag": b64_flag}
                        break
                    except Exception as e:
                        siemplify.LOGGER.exception(e)
                        siemplify.LOGGER.error(
                            f'Failed processing entity {entity.identifier} with country code "{ent_country_code}"',
                        )

    if country_code:
        b64_flag = get_base64_flag_data(country_code, flags_data, siemplify)
        result_json[country_code] = b64_flag

    if result_json:
        siemplify.result.add_result_json(convert_dict_to_json_result_dict(result_json))

    if SHOULD_UPDATE_FILE:
        siemplify.LOGGER.info(f"Updating flags file with new flag ({country_code})")
        with open(os.path.join(siemplify.run_folder, FLAGS_FILE), "w") as f:
            f.write(json.dumps(flags_data))

    siemplify.end(
        "Fetched flag from countryflags.io for countries",
        True,
        EXECUTION_STATE_COMPLETED,
    )


if __name__ == "__main__":
    main()
