from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED)

from ..core.PortnoxManager import (PortnoxManager, PortnoxAuthError,
                            flatten_device_for_enrichment, normalize_mac)

INTEGRATION_NAME = "PortnoxCloud"
SCRIPT_NAME = "Enrich Entities"

SUPPORTED_ENTITIES = [EntityTypes.MACADDRESS, EntityTypes.HOSTNAME, EntityTypes.ADDRESS]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "{0} - {1}".format(INTEGRATION_NAME, SCRIPT_NAME)
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    api_root = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="API Root",
        default_value="https://clear.portnox.com:8081/CloudPortalBackEnd/")
    api_token = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="API Token", is_mandatory=False)
    username = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="Username", is_mandatory=False)
    password = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="Password", is_mandatory=False)
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name="Verify SSL",
        input_type=bool, default_value=True)

    max_pages = siemplify.extract_action_param(
        param_name="Max Pages To Scan", input_type=int, default_value=10,
        is_mandatory=False, print_value=True)
    create_insight = siemplify.extract_action_param(
        param_name="Create Insight", input_type=bool, default_value=True,
        is_mandatory=False, print_value=True)

    enriched, failed, json_results = [], [], {}
    updated_entities = []

    try:
        manager = PortnoxManager(
            api_root=api_root, api_token=api_token, username=username,
            password=password, verify_ssl=verify_ssl, logger=siemplify.LOGGER)

        scope = [e for e in siemplify.target_entities
                 if e.entity_type in SUPPORTED_ENTITIES]

        for entity in scope:
            siemplify.LOGGER.info("Looking up {0}".format(entity.identifier))
            try:
                if entity.entity_type == EntityTypes.MACADDRESS:
                    devices = manager.find_devices_by_mac(
                        entity.identifier, max_pages=max_pages)
                else:
                    devices = manager.find_devices_by_text(
                        entity.identifier, max_pages=max_pages)

                if not devices:
                    failed.append(entity.identifier)
                    continue

                device = devices[0]
                json_results[entity.identifier] = device

                enrichment = flatten_device_for_enrichment(device)
                entity.additional_properties.update(enrichment)
                entity.is_enriched = True

                if enrichment.get("Portnox_IsBlockedByAdmin") in (True, "True", "true"):
                    entity.is_suspicious = True

                if create_insight:
                    siemplify.add_entity_insight(
                        entity,
                        "Portnox device {0}\nAccount: {1}\nMACs: {2}\nIPs: {3}\nBlocked: {4}".format(
                            enrichment.get("Portnox_DeviceId", "n/a"),
                            enrichment.get("Portnox_AccountName", "n/a"),
                            enrichment.get("Portnox_MacAddresses", "n/a"),
                            enrichment.get("Portnox_IpAddresses", "n/a"),
                            enrichment.get("Portnox_IsBlockedByAdmin", False)),
                        triggered_by=INTEGRATION_NAME)

                updated_entities.append(entity)
                enriched.append(entity.identifier)

            except Exception as entity_error:
                siemplify.LOGGER.error("Failed on {0}: {1}".format(
                    entity.identifier, entity_error))
                failed.append(entity.identifier)

        if updated_entities:
            siemplify.update_entities(updated_entities)
        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results))

        status = EXECUTION_STATE_COMPLETED
        result_value = str(bool(enriched))
        parts = []
        if enriched:
            parts.append("Enriched from Portnox Cloud: {0}".format(", ".join(enriched)))
        if failed:
            parts.append("Not found in Portnox Cloud: {0}".format(", ".join(failed)))
        output_message = "\n".join(parts) or "No supported entities in scope."

    except PortnoxAuthError as error:
        siemplify.LOGGER.error(str(error))
        status = EXECUTION_STATE_FAILED
        result_value = "False"
        output_message = "Authentication to Portnox Cloud failed. {0}".format(error)

    except Exception as error:
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        result_value = "False"
        output_message = "Enrichment failed. Error: {0}".format(error)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
