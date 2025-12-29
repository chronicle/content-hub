from __future__ import annotations

import re

from marketorestpython.client import MarketoClient
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler

INTEGRATION = "Marketo"

SCRIPT_NAME = "Get Lead By Entity Email"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION PARAMETERS:
    client_id = siemplify.extract_configuration_param(
        provider_name=INTEGRATION,
        param_name="Client Id",
    )
    client_secret = siemplify.extract_configuration_param(
        provider_name=INTEGRATION,
        param_name="Client Secret",
    )
    munchkin_id = siemplify.extract_configuration_param(
        provider_name=INTEGRATION,
        param_name="Munchkin Id",
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = ""  # human readable message, showed in UI as the action result
    result_value = (
        False  # Set a simple result value, used for playbook if\else and placeholders.
    )
    failed_entities = []  # In case this actions contains entity based logic, collect failed entity.identifiers
    successfull_entities = []  # In case this reactions contains entity based logic, collect successfull entity.identifiers

    mc = MarketoClient(munchkin_id, client_id, client_secret, None, None)
    enriched_entities = []
    json_result = {}
    json_result_enities = {}
    leads_count = 0
    try:
        for ent in siemplify.target_entities:
            if re.match(r"[^@]+@[^@]+\.[^@]+", ent.identifier):
                valid_email = ent.identifier
                valid_email = valid_email.lower()
            else:
                valid_email = None
                output_message += (
                    "\n entity: {}, is not a valid email address. Skipping entity."
                )
            if ent.entity_type == EntityTypes.USER and valid_email is not None:
                lead_details = mc.execute(
                    method="get_multiple_leads_by_filter_type",
                    filterType="email",
                    filterValues=str(valid_email),
                )
                if lead_details is not None and len(lead_details) > 0:
                    enrichments = lead_details
                    enrichment_json = {
                        "Marketo_firstName": enrichments[0]["firstName"],
                        "Marketo_lastName": enrichments[0]["lastName"],
                        "Marketo_email": enrichments[0]["email"],
                        "LeadID": enrichments[0]["id"],
                    }
                    ent.is_enriched = True

                    ent.additional_properties.update(enrichment_json)

                    json_result_enities[ent.identifier] = enrichment_json
                    enriched_entities.append(ent)
                    leads_count += 1
                    output_message += (
                        f"The entity <{valid_email}> was enriched successfully."
                    )
                    result_value = True
                else:
                    output_message += f"\n failed to find lead for: {valid_email!s}"
                    result_value = False

    except Exception as e:
        output_message += f"\n failed to find lead for: {valid_email!s}"
        result_value = False
        raise Exception(f"Some error occured: {e}")
    if len(enriched_entities) > 0:
        siemplify.update_entities(enriched_entities)
        siemplify.LOGGER.info(f"\n Enriched entities: {enriched_entities}")
    else:
        siemplify.LOGGER.info(f"\n Did not enrich any entity. {enriched_entities}")
    json_result_enities = convert_dict_to_json_result_dict(json_result_enities)
    json_result["entites"] = json_result_enities
    json_result["leads_count"] = leads_count

    siemplify.result.add_result_json(json_result)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
