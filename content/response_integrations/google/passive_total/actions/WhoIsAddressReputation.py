from __future__ import annotations
from soar_sdk.SiemplifyDataModel import EntityTypes

# Imports
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict
from ..core.PassiveTotalManager import PassiveTotal

# Consts
ADDRESS = EntityTypes.ADDRESS

@output_handler
def main():
    # Action Content
    siemplify = SiemplifyAction()

    configuration = siemplify.get_configuration("PassiveTotal")
    passive_total = PassiveTotal(
        user=configuration["Username"], key=configuration["Api_Key"]
    )
    scope_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type == ADDRESS and not entity.is_internal
    ]
    entities_to_update = []
    json_result = {}
    output_message = ""
    result_value = False

    for entity in scope_entities:
        report = passive_total.get_dns_report(entity.identifier)
        if report:
            json_result[entity.identifier] = report
            whois_dict = passive_total.dns_report_to_dict(report)
            whois_csv = passive_total.dns_report_to_csv(report)
            # Enrich entity with the scan result.
            if whois_dict and not len(whois_dict) == 0:
                entity.additional_properties.update(whois_dict)
                entities_to_update.append(entity)
                result_value = True
                siemplify.result.add_entity_table(entity.identifier, whois_csv)

    # Update Entities
    siemplify.update_entities(entities_to_update)
    # Arrange Action Output.
    if len(scope_entities) == 0:
        output_message = "No entities for scan."
    else:
        if len(entities_to_update) == 0:
            output_message = "No entities were enriched."
        else:
            for entity in entities_to_update:
                if len(output_message) == 0:
                    output_message = entity.identifier
                else:
                    output_message += f", {entity.identifier}"
            output_message += " enriched by WhoIs RISKIQ."

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_result))
    siemplify.end(output_message, result_value)

if __name__ == "__main__":
    main()
