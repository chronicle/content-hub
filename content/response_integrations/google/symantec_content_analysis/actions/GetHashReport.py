from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import construct_csv, dict_to_flat, output_handler

from ..core.SymantecContentAnalysisManager import SymantecContentAnalysisManager

INTEGRATION_PROVIDER = "SymantecContentAnalysis"
ACTION_NAME = "SymantecContentAnalysis_Get Hash Report"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME
    conf = siemplify.get_configuration(INTEGRATION_PROVIDER)

    verify_ssl = conf.get("Verify SSL").lower() == "true"
    symantec_manager = SymantecContentAnalysisManager(
        conf.get("API Root"), conf.get("API Key"), verify_ssl
    )

    # Variables
    success_entities = []
    errors = []
    result_value = False

    target_entities = [
        entity for entity in siemplify.target_entities if entity.entity_type == EntityTypes.FILEHASH
    ]

    for entity in target_entities:
        try:
            report = symantec_manager.get_file_samples(entity.identifier)

            if report:
                result_value = True
                success_entities.append(entity)
                report_csv = construct_csv(report)
                siemplify.result.add_entity_table(entity.identifier, report_csv)
                # Enrich entity.
                entity.additional_properties.update(dict_to_flat({"res": report}))

        except Exception as err:
            error_message = f'Error fetching report for "{entity.identifier}", ERROR: {str(err)}'
            siemplify.LOGGER.error(error_message)
            siemplify.LOGGER.exception(err)
            errors.append(error_message)

    if result_value:
        output_message = (
            f"{', '.join([entity.identifier for entity in success_entities])} were enriched."
        )
        siemplify.update_entities(success_entities)
    else:
        output_message = "No target entities were enriched."

    if errors:
        output_message = "{0} \n Errors: \n \n  {1}".format(output_message, " \n ".join(errors))

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
