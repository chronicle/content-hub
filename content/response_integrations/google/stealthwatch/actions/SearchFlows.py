from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import utc_now
from ..core.StealthwatchManager import StealthwatchManager
import datetime
import json
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "Stealthwatch"


@output_handler
def main():
    siemplify = SiemplifyAction()
    configurations = siemplify.get_configuration("Stealthwatch")
    server_address = configurations["Api Root"]
    username = configurations["Username"]
    password = configurations["Password"]
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        default_value=False,
    )

    time_delta = int(siemplify.parameters["Timeframe"])
    limit = int(siemplify.parameters["Limit"])

    end_time = utc_now().strftime("%Y-%m-%dT%H:%M:00.000%z")
    start_time = (utc_now() - datetime.timedelta(hours=time_delta)).strftime(
        "%Y-%m-%dT%H:%M:00.000%z"
    )

    stealthwatch_manager = StealthwatchManager(
        server_address, username, password, verify_ssl
    )

    enriched_entities = []

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:

            # Get the domain id of the entity
            domain_id = stealthwatch_manager.get_domain_id_by_ip(entity.identifier)

            if domain_id:
                results = stealthwatch_manager.search_flows(
                    domain_id,
                    start_time,
                    end_time,
                    limit,
                    source_ips=[entity.identifier],
                )

                results.extend(
                    stealthwatch_manager.search_flows(
                        domain_id,
                        start_time,
                        end_time,
                        limit,
                        destination_ips=[entity.identifier],
                    )
                )

                if results:
                    # Attach all data as JSON
                    siemplify.result.add_json(entity.identifier, json.dumps(results))

                    # Attach filtered data as csv
                    filtered_results = stealthwatch_manager.filter_flow_results(results)
                    csv_output = stealthwatch_manager.construct_csv(filtered_results)
                    siemplify.result.add_entity_table(entity.identifier, csv_output)

                    enriched_entities.append(entity)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = "Flows were found for the following entities:\n" + "\n".join(
            entities_names
        )

        siemplify.end(output_message, "true")

    else:
        output_message = "No flows were found."
        # No flows found and action is completed
        siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
