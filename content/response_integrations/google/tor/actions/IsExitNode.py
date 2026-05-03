from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.TorManager import TorManager
import json

# This action goes over each ip entity, and for each one does the following:
# THe manager fetches the list of today's exit nodes from
# https://check.torproject.org/exit-addresses
# And checks whether the ip is located in that list. If it does,
# then the ip is an exit node.
# Then the action return the list of the exit node ips as result value
# and prints the ips in the output message.


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("Tor")
    use_ssl = conf.get("Use SSL", "False")

    if use_ssl.lower() == "true":
        use_ssl = True
    else:
        use_ssl = False

    tor_manager = TorManager(use_ssl=use_ssl)

    exit_nodes = []
    json_results = {}

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.ADDRESS:
            try:
                if tor_manager.is_exit_node(entity.identifier):
                    exit_nodes.append(entity)

            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER.exception(e)

    if exit_nodes:
        entities_names = [entity.identifier for entity in exit_nodes]

        output_message = "Tor - The following entities are exit nodes:\n" + "\n".join(
            entities_names
        )
        # add json
        siemplify.result.add_result_json(json.dumps(entities_names))
        siemplify.end(output_message, json.dumps(entities_names))

    else:
        # add json
        siemplify.result.add_result_json(json_results)
        output_message = "Tor - No entities are exit nodes."
        siemplify.end(output_message, json.dumps(exit_nodes))


if __name__ == "__main__":
    main()
