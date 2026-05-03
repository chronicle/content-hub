from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.JoeSandboxManager import (
    JoeSandboxManager,
    REPORT_WEB_LINK,
    JoeSandboxLimitManagerError,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import dict_to_flat, convert_dict_to_json_result_dict
import base64

SCRIPT_NAME = "JoeSandbox - searchHash"


@output_handler
def main():
    siemplify = SiemplifyAction()
    entities_to_update = []
    result_value = "false"
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("JoeSandbox")
    api_root = conf["Api Root"]
    api_key = conf["Api Key"]
    use_ssl = conf["Use SSL"].lower() == "true"
    joe = JoeSandboxManager(api_root, api_key, use_ssl)

    json_results = {}

    for entity in siemplify.target_entities:
        # Search a file hash in JoeSandbox.
        if entity.entity_type == EntityTypes.FILEHASH:
            try:
                web_ids = joe.search(entity.identifier)
                if web_ids:
                    analysis_info = joe.get_analysis_info(web_ids[0]["webid"])
                    json_results[entity.identifier] = analysis_info

                    # Download analysis
                    full_report = joe.download_report(
                        web_ids[0]["webid"],
                        "pdf"
                    )
                    try:
                        siemplify.result.add_entity_attachment(
                            entity.identifier,
                            f'JoeSandboxReport.{"pdf"}',
                            base64.b64encode(full_report.encode('utf-8')),
                        )
                    except Exception as e:
                        # Attachment cannot be larger than 3 MB
                        siemplify.LOGGER.error(
                            f"Can not add attachment to entity: {entity.identifier}.\n{str(e)}."
                        )

                    siemplify.result.add_entity_link(
                        f"{entity.identifier} - Web Link",
                        REPORT_WEB_LINK.format(analysis_info.get("analysisid")),
                    )

                    # Enrich the entity
                    flat_report = dict_to_flat(analysis_info)
                    entity.additional_properties.update(flat_report)
                    entity.is_enriched = True
                    entities_to_update.append(entity)

                    # Check for detection risk - result 'suspicious'
                    if joe.is_detection_suspicious(analysis_info):
                        result_value = "true"
                        entity.is_suspicious = True
                        siemplify.add_entity_insight(
                            entity,
                            "Found as suspicious by JoeSandbox.",
                            triggered_by="JoeSandbox",
                        )

            except JoeSandboxLimitManagerError as e:
                # Reached max allowed API requests - notify user
                siemplify.LOGGER.error(
                    "The number of allowed submissions (20) "
                    f"per day have been reached. {e}"
                )
                raise
            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER._log.exception(e)

    if entities_to_update:
        siemplify.update_entities(entities_to_update)
        entities_names = [entity.identifier for entity in entities_to_update]
        output_massage = (
            "The following entities were detected by JoeSandbox.\n"
            + "\n".join(entities_names)
        )
    else:
        output_massage = "No entities were detected by JoeSandbox."

    # add json
    siemplify.result.add_result_json(
        convert_dict_to_json_result_dict(json_results)
    )

    siemplify.end(output_massage, result_value)


if __name__ == "__main__":
    main()
