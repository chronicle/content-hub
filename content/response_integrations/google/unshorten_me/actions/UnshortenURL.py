from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.UnshortenMeManager import UnshortenMeManager, UnshortenMeLimitManagerError
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict

SCRIPT_NAME = "UnshortenMe - UnshortenURL"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("UnshortenMe")
    use_ssl = conf.get("Use SSL", "False").lower() == "true"

    unshortenme_manager = UnshortenMeManager(use_ssl=use_ssl)

    enriched_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.URL:
            try:
                long_url = unshortenme_manager.unshorten_url(entity.identifier)
                if long_url:
                    entity.additional_properties.update({"long_url": long_url})
                    json_results[entity.identifier] = long_url
                    entity.is_enriched = True
                    enriched_entities.append(entity)

            except UnshortenMeLimitManagerError:
                # Reached max allowed API requests - notify user
                raise
            except Exception as e:
                # An error occurred - skip entity and continue
                siemplify.LOGGER.error(
                    f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
                )
                siemplify.LOGGER._log.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]

        output_message = (
            "Unshorten.me: The following urls were unshortened:\n"
            + "\n".join(entities_names)
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "Unshorten.me: No urls were unshortened."

    # add json
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
