from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import dict_to_flat, add_prefix_to_dict, get_domain_from_entity
from soar_sdk.SiemplifyDataModel import EntityTypes
from ..core.ProofPointPSManager import ProofPointPSManager
import re


PROVIDER = "ProofPointPS"
ACTION_NAME = "ProofPoint - Enriched Entities"


def is_valid_email(email):
    return (
        re.match(
            "^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$",
            email,
        )
        is not None
    )


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.action_definition_name = ACTION_NAME
    conf = siemplify.get_configuration(PROVIDER)
    verify_ssl = conf.get("Verify SSL").lower() == "true"
    proofpoint_manager = ProofPointPSManager(
        server_address=conf.get("Api Root"),
        username=conf.get("Username"),
        password=conf.get("Password"),
        verify_ssl=verify_ssl,
    )

    entities_to_enrich = []

    for entity in siemplify.target_entities:
        try:
            records = []

            if entity.entity_type == EntityTypes.HOSTNAME:
                records.extend(
                    proofpoint_manager.search(
                        sender=f"@{get_domain_from_entity(entity)}"
                    )
                )
                records.extend(
                    proofpoint_manager.search(
                        recipient=f"@{get_domain_from_entity(entity)}"
                    )
                )

            elif entity.entity_type == EntityTypes.USER and is_valid_email(
                entity.identifier
            ):
                records.extend(proofpoint_manager.search(sender=entity.identifier))
                records.extend(proofpoint_manager.search(recipient=entity.identifier))

            if records:
                for index, record in enumerate(records):
                    # Delete from enrichment the unuseful data
                    if "dlpviolation" in record:
                        del record["dlpviolation"]

                    if "messagestatus" in record:
                        del record["messagestatus"]

                    flat_record = dict_to_flat(record)
                    flat_record = add_prefix_to_dict(flat_record, index)
                    flat_record = add_prefix_to_dict(flat_record, "ProofPointPS")
                    entity.additional_properties.update(flat_record)

                entities_to_enrich.append(entity)

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER.exception(e)

    if entities_to_enrich:
        entities_names = [entity.identifier for entity in entities_to_enrich]
        output_message = "The following entities were enriched:\n" + "\n".join(
            entities_names
        )
        siemplify.update_entities(entities_to_enrich)

    else:
        output_message = "No entities were enriched."

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
