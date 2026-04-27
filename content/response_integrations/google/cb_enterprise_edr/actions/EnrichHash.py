from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.CBEnterpriseEDRManager import (
    CBEnterpriseEDRManager,
    CBEnterpriseEDRUnauthorizedError,
    CBEnterpriseEDRNotFoundError,
)
from TIPCommon import extract_configuration_param

INTEGRATION_NAME = "CBEnterpriseEDR"
SCRIPT_NAME = "Enrich Hash"
SUPPORTED_ENTITIES = [EntityTypes.FILEHASH]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    org_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization Key",
        is_mandatory=True,
        input_type=str,
    )
    api_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API ID",
        is_mandatory=True,
        input_type=str,
    )
    api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret Key",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    json_results = {}
    failed_entities = []
    missing_entities = []
    partially_enriched_entities = []
    output_message = ""

    try:
        cb_edr_manager = CBEnterpriseEDRManager(
            api_root, org_key, api_id, api_secret_key, verify_ssl
        )

        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                if len(entity.identifier) != 64:
                    siemplify.LOGGER.info(
                        f"Hash {entity.identifier} is not of type sha256. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")

                not_found = False
                failed = False
                hash_metadata = {}
                hash_summary = {}

                try:
                    siemplify.LOGGER.info(
                        f"Fetching hash metadata for entity {entity.identifier}"
                    )
                    hash_metadata = cb_edr_manager.get_filehash_metadata(
                        entity.identifier
                    )
                    siemplify.LOGGER.info(
                        f"Hash metadata was found for entity {entity.identifier}"
                    )
                    entity.additional_properties.update(
                        hash_metadata.as_enrichment_data()
                    )
                    entity.is_enriched = True

                except CBEnterpriseEDRNotFoundError:
                    not_found = True
                    siemplify.LOGGER.info(
                        f"No metadata was found for hash {entity.identifier}"
                    )

                except CBEnterpriseEDRUnauthorizedError as e:
                    # Unauthorized - invalid credentials were passed. Terminate action
                    siemplify.LOGGER.error(
                        f"Failed to execute Enrich Entities action! Error is {e}"
                    )
                    siemplify.end(
                        f"Failed to execute Enrich Entities action! Error is {e}",
                        "false",
                        EXECUTION_STATE_FAILED,
                    )

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Unable to fetch metadata for hash {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)
                    failed = True

                try:
                    siemplify.LOGGER.info(
                        f"Trying to get hash summary for entity {entity.identifier}"
                    )
                    hash_summary = cb_edr_manager.get_filehash_summary(
                        entity.identifier
                    )
                    siemplify.LOGGER.info(
                        f"Hash summary was found for entity {entity.identifier}"
                    )
                    entity.additional_properties.update(
                        hash_summary.as_enrichment_data()
                    )
                    entity.is_enriched = True

                except CBEnterpriseEDRNotFoundError:
                    not_found = True
                    siemplify.LOGGER.info(
                        f"No summary was found for hash {entity.identifier}"
                    )

                except CBEnterpriseEDRUnauthorizedError as e:
                    # Unauthorized - invalid credentials were passed. Terminate action
                    siemplify.LOGGER.error(
                        f"Failed to execute Enrich Entities action! Error is {e}"
                    )
                    siemplify.end(
                        f"Failed to execute Enrich Entities action! Error is {e}",
                        "false",
                        EXECUTION_STATE_FAILED,
                    )
                    failed = True

                except Exception as e:
                    siemplify.LOGGER.error(
                        f"Unable to fetch summary for hash {entity.identifier}"
                    )
                    siemplify.LOGGER.exception(e)

                if not (hash_metadata or hash_summary):
                    if not_found:
                        missing_entities.append(entity)
                    elif failed:
                        failed_entities.append(entity)

                else:
                    if hash_summary and hash_metadata:
                        successful_entities.append(entity)

                    else:
                        # Entity got enriched by at least one request
                        partially_enriched_entities.append(entity)

                    json_results[entity.identifier] = {}

                    if hash_metadata:
                        json_results[entity.identifier].update(hash_metadata.raw_data)

                    if hash_summary:
                        json_results[entity.identifier].update(hash_summary.raw_data)

                siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

            except CBEnterpriseEDRUnauthorizedError as e:
                # Unauthorized - invalid credentials were passed. Terminate action
                siemplify.LOGGER.error(
                    f"Failed to execute Enrich Entities action! Error is {e}"
                )
                siemplify.end(
                    f"Failed to execute Enrich Entities action! Error is {e}",
                    "false",
                    EXECUTION_STATE_FAILED,
                )

            except Exception as e:
                failed_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += "Successfully enriched entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in successful_entities])
            )
            siemplify.update_entities(successful_entities)
            result_value = "true"

        else:
            output_message += "No entities were enriched."
            result_value = "false"

        if partially_enriched_entities:
            output_message += "\n\nThe following entities were partially enriched because of the errors getting entity data:\n   {}".format(
                "\n   ".join(
                    [entity.identifier for entity in partially_enriched_entities]
                )
            )

        if missing_entities:
            output_message += "\n\nAction was not able to find VMware Carbon Black Enterprise EDR info to enrich the following entities\n   {}".format(
                "\n   ".join([entity.identifier for entity in missing_entities])
            )

        if failed_entities:
            output_message += (
                "\n\nFailed enriching the following entities:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in failed_entities])
                )
            )

    except Exception as e:
        siemplify.LOGGER.error(
            f"Failed to execute Enrich Entities action! Error is {e}"
        )
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to execute Enrich Entities action! Error is {e}"

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
