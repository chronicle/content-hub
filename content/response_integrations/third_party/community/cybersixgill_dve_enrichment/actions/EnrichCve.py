from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import add_prefix_to_dict, output_handler

from ..core.CybersixgillManager import PROVIDER, SixgillEnrichManager
from ..core.CybersixgillResultProcessor import SixgillActionResultProcessor


@output_handler
def main():
    siemplify = SiemplifyAction()
    client_id = siemplify.extract_configuration_param(PROVIDER, "Client Id")
    client_secret = siemplify.extract_configuration_param(PROVIDER, "Client Secret")

    sixgill_manager = SixgillEnrichManager(client_id, client_secret)
    sixgill_process = SixgillActionResultProcessor(siemplify, sixgill_manager)
    entity_dict = sixgill_process.entity_enrich()
    enriched_entities = []
    try:
        for entity in siemplify.target_entities:
            entity_dict = add_prefix_to_dict(entity_dict, "Cybersixgill")
            entity.additional_properties.update(entity_dict)
            enriched_entities.append(entity)
            entity.is_enriched = True
        siemplify.update_entities(enriched_entities)
    except Exception as err:
        self.siemplify.LOGGER.error(err)
    sixgill_process.enrich()


if __name__ == "__main__":
    main()
