from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from ..core.ThreatExchangeManager import ThreatExchangeManager
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import construct_csv, dict_to_flat
from soar_sdk.SiemplifyAction import SiemplifyAction


SUSPICIOUS_STATUSES = ["SUSPICIOUS", "MALICIOUS"]
SUSPICIOUS_SEVERITY = ["SUSPICIOUS", "SEVERE", "APOCALYPSE"]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "ThreatExchange - GetFileReputation"

    conf = siemplify.get_configuration("ThreatExchange")
    server_addr = conf["Api Root"]
    app_id = conf["App ID"]
    app_secret = conf["App Secret"]
    api_version = conf["API Version"]
    use_ssl = conf["Use SSL"].lower() == "true"

    threat_exchange_manager = ThreatExchangeManager(
        server_addr, app_id, app_secret, api_version, use_ssl
    )

    enriched_entities = []

    for entity in siemplify.target_entities:
        try:
            reputations = []

            if entity.entity_type == EntityTypes.FILEHASH:
                reputations = threat_exchange_manager.get_file_reputation(
                    entity.identifier
                )
            elif entity.entity_type == EntityTypes.HOSTNAME:
                reputations = threat_exchange_manager.get_domain_reputation(
                    entity.identifier
                )
            elif entity.entity_type == EntityTypes.ADDRESS:
                reputations = threat_exchange_manager.get_ip_reputation(
                    entity.identifier
                )
            elif entity.entity_type == EntityTypes.URL:
                reputations = threat_exchange_manager.get_url_reputation(
                    entity.identifier
                )

            if reputations:
                reputations = list(map(dict_to_flat, reputations))
                csv_output = construct_csv(reputations)

                # Attach reputations as csv
                siemplify.result.add_entity_table(
                    f"{entity.identifier} - Reputations", csv_output
                )

                enriched_entities.append(entity)

                for reputation in reputations:
                    # Check whether the entity is suspicious
                    if (
                        reputation.get("status") in SUSPICIOUS_STATUSES
                        or reputation.get("severity") in SUSPICIOUS_SEVERITY
                    ):
                        entity.is_suspicious = True

        except Exception as e:
            # An error occurred - skip entity and continue
            siemplify.LOGGER.error(
                f"An error occurred on entity: {entity.identifier}.\n{str(e)}."
            )
            siemplify.LOGGER._log.exception(e)

    if enriched_entities:
        entities_names = [entity.identifier for entity in enriched_entities]
        output_message = (
            "Threat Exchange - Found reputations for the following entities\n"
            + "\n".join(entities_names)
        )

        siemplify.update_entities(enriched_entities)

    else:
        output_message = "No reputations were found.\n"

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
