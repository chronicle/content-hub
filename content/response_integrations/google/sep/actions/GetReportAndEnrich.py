from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import dict_to_flat, add_prefix_to_dict
from ..core.SEPManager import SEP14Manager
from TIPCommon import extract_configuration_param

import json

INTEGRATION_NAME = "SEP"
COMMAND = "_command_id"


@output_handler
def main():
    siemplify = SiemplifyAction()

    conf = siemplify.get_configuration("SEP")
    username = conf["Username"]
    password = conf["Password"]
    domain = conf["Domain"]
    url = conf["Api Root"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )
    command_ids = (
        siemplify.parameters.get("Command IDS", "").split(",")
        if siemplify.parameters.get("Command IDS")
        else []
    )

    sep_manager = SEP14Manager(url, username, password, domain, verify_ssl=verify_ssl)

    enriched_entities = []
    reports = []

    for command_id in command_ids:
        for entity in siemplify.target_entities:
            for key, value in list(entity.additional_properties.items()):
                if COMMAND in key and value == command_id:
                    # The entity is the subject of the given command id
                    report = sep_manager.commandStatusReport(command_id)
                    reports.append(report)

                    flat_report = dict_to_flat(report)
                    flat_report = add_prefix_to_dict(
                        flat_report, f"SEP_{key.split(COMMAND)[0]}_report"
                    )

                    entity.additional_properties.update(flat_report)
                    enriched_entities.append(entity)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = "SEP: The following entities were enriched:\n" + "\n".join(
            entities_names
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "SEP: No entities were enriched."

    siemplify.result.add_result_json(reports)
    siemplify.end(output_message, json.dumps(reports))


if __name__ == "__main__":
    main()
