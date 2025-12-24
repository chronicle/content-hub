from __future__ import annotations

import requests
import xmltodict
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

# Consts:
INTEGRATION_NAME = "PhishTank"
SCRIPT_NAME = "Check Url"
SCORE_MODIFIER = 50.0

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "phishtank/Siemplify",
}


def get_entity_original_identifier(entity):
    """Helper function for getting entity original identifier
    :param entity: entity from which function will get original identifier
    :return: {str} original identifier
    """
    return entity.additional_properties.get("OriginalIdentifier", entity.identifier)


@output_handler
def main():
    siemplify = SiemplifyAction()
    service_url = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Service Url",
    )
    try:
        status = EXECUTION_STATE_COMPLETED
        output_message = "No URL's were found in the current scope"
        result_value = 0
        failed_entities = []
        successfull_entities = []
        not_in_db_entities = []
        suspicious_entities = []

        result_json = {}
        for entity in siemplify.target_entities:
            if entity.entity_type == EntityTypes.URL:
                try:
                    siemplify.LOGGER.info(f"Processing: {entity.identifier}")
                    orig_url = entity.additional_properties.get(
                        "OriginalIdentifier",
                        entity.identifier,
                    )

                    payload = {"url": orig_url, "format": "json"}
                    res = requests.post(service_url, headers=HEADERS, params=payload)
                    res.raise_for_status()
                    data = xmltodict.parse(res.content)
                    result_json[entity.identifier] = data.get("response", {}).get(
                        "results",
                    )

                    score = 0
                    # print(data)
                    if (
                        str(
                            data.get("response", {})
                            .get("results")
                            .get("url0", {})
                            .get("in_database"),
                        ).lower()
                        == "true"
                    ):
                        url_data = data.get("response", {}).get("results").get("url0")
                        message = "URL found with the following properties:\nLink: {phish_detail_page}\nVerified: {verified}\nValid: {valid}".format(
                            phish_detail_page=url_data.get("phish_detail_page", "None"),
                            verified=url_data.get("verified", "None"),
                            valid=url_data.get("valid", "None"),
                        )
                        score = SCORE_MODIFIER
                        successfull_entities.append(entity)

                        # mark suspicious if verified:
                        if (
                            data.get("response", {})
                            .get("results")
                            .get("url0")
                            .get("verified")
                            .lower()
                            == "true"
                        ):
                            entity.is_suspicious = True
                            suspicious_entities.append(entity)

                    else:
                        message = "URL not found in Phishtank's database"
                        not_in_db_entities.append(entity)

                    result_json[entity.identifier]["score"] = score
                    siemplify.add_entity_insight(
                        entity,
                        message,
                        triggered_by="Phishing",
                    )
                except Exception as e:
                    failed_entities.append(
                        f'Failed for "{entity.identifier}" with error {e}',
                    )
                    raise Exception(data.get("response", {}).get("results").get("url0"))

        if (
            successfull_entities
            or suspicious_entities
            or not_in_db_entities
            or failed_entities
        ):
            output_message = ""

        if successfull_entities:
            result_value = len(successfull_entities)
            output_message += (
                "Found data in PhishTank database for {} URLs:\n{}".format(
                    len(successfull_entities),
                    "\n".join([x.identifier for x in successfull_entities]),
                )
            )
        if suspicious_entities:
            siemplify.update_entities(suspicious_entities)
            output_message += "\n" + "Out of which {} are verified:\n{}".format(
                len(suspicious_entities),
                "\n".join([x.identifier for x in suspicious_entities]),
            )

        if not_in_db_entities:
            output_message += (
                "\n\n\n"
                + "Following URLs do not appear in PhishTank database:\n{}".format(
                    "\n".join([x.identifier for x in not_in_db_entities]),
                )
            )

        if failed_entities:
            output_message += "\n\n" + "Errors:\n{}".format("\n".join(failed_entities))

        if result_json:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(result_json),
            )
    except Exception as e:
        siemplify.LOGGER.error(f"General error performing action {SCRIPT_NAME}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += "\n unknown failure"
        raise

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
