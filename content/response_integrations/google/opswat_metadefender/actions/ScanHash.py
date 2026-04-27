from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.OpswatMetadefenderManager import OpswatMetadefenderManager

FILEHASH = EntityTypes.FILEHASH


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("OpswatMetadefender")
    verify_ssl = conf.get("Verify SSL", "false").lower() == "true"

    op_manager = OpswatMetadefenderManager(
        conf["ApiRoot"], api_key=conf["ApiKey"], verify_ssl=verify_ssl
    )
    scope_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == FILEHASH
    ]
    output_message = "No entities to scan"
    result_value = "false"

    for entity in scope_entities:
        if entity.entity_type == FILEHASH:
            print(entity.identifier)
            report = op_manager.find_hash_reputation(entity.identifier)
            if report:
                if report["scan_results"]["scan_all_result_a"] == "Infected":
                    entity.is_suspicious = True
                    siemplify.update_entities([entity])
                    siemplify.add_entity_insight(entity, "Found suspicious in Opswat")
                    result_value = "true"
                csv_table = op_manager.report_to_csv(report)
                siemplify.result.add_data_table(entity.identifier, csv_table)
                print(csv_table)
                output_message = "Scan results added to table"
            else:
                output_message = "No Scan Results"

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
