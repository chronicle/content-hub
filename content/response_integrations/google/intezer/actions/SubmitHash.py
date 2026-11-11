from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import (
    dict_to_flat,
    flat_dict_to_csv,
    add_prefix_to_dict,
    convert_dict_to_json_result_dict,
)
from intezer.core.IntezerManager import IntezerManager, MALICIOUS_VERDICTS
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
import json
import sys

SCRIPT_NAME = "Intezer - Submit Hash"


def get_entity_by_identifier(target_entities, entity_identifier):
    for entity in target_entities:
        if entity.identifier == entity_identifier:
            return entity

    raise Exception(f"Entity with identifier {entity_identifier} was not found.")


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    conf = siemplify.get_configuration("Intezer")
    api_root = conf["API Root"]
    api_key = conf["API key"]
    verify_ssl = conf.get("Verify SSL", "False").lower() == "true"

    intezer_manager = IntezerManager(
        api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
    )

    scanned_hashes = {"existing_hashes": [], "new_hashes": []}

    submitted_hashes = []
    error_msg = ""
    errors = []

    for entity in siemplify.target_entities:
        if entity.entity_type == EntityTypes.FILEHASH:
            try:
                existing_results = intezer_manager.get_existing_analysis(
                    entity.identifier
                )

                if existing_results:
                    siemplify.LOGGER.info(
                        f"Hash {entity.identifier} was already analyzed. Fetching report."
                    )
                    scanned_hashes["existing_hashes"].append(
                        (entity.identifier, existing_results)
                    )

                else:
                    siemplify.LOGGER.info(f"Submitting {entity.identifier}.")
                    results_url = intezer_manager.submit_hash(entity.identifier)
                    scanned_hashes["new_hashes"].append(
                        (entity.identifier, results_url)
                    )

                submitted_hashes.append(entity.identifier)

            except Exception as e:
                errors.append(entity.identifier)
                siemplify.LOGGER.error(f"Unable to submit {entity.identifier}")
                siemplify.LOGGER.exception(e)

    if errors:
        error_msg = f"\nErrors occurred on the following hashes: {', '.join(errors)}.\nCheck logs for details."

    siemplify.end(
        f"The following hashes were submitted to scan: {', '.join(submitted_hashes)}.{error_msg}.",
        json.dumps(scanned_hashes),
        EXECUTION_STATE_INPROGRESS,
    )


def async_analysis():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("Start async")

    enriched_entities = []

    try:
        conf = siemplify.get_configuration("Intezer")
        api_root = conf["API Root"]
        api_key = conf["API key"]
        verify_ssl = conf.get("Verify SSL", "False").lower() == "true"

        intezer_manager = IntezerManager(
            api_root=api_root, api_key=api_key, verify_ssl=verify_ssl
        )
        siemplify.LOGGER.info("Connected to Intezer")

        scanned_hashes = json.loads(siemplify.parameters["additional_data"])

        if all(
            [
                intezer_manager.is_analysis_completed(results_url)
                for file_hash, results_url in scanned_hashes["new_hashes"]
            ]
        ):
            siemplify.LOGGER.info("All scans completed.")

            results_json = {}

            reports = scanned_hashes["existing_hashes"]
            errors = []
            error_msg = ""

            for file_hash, results_url in scanned_hashes["new_hashes"]:
                try:
                    siemplify.LOGGER.info(f"Fetching report for {file_hash}")
                    report = intezer_manager.get_results(results_url)
                    reports.append((file_hash, report))
                except Exception as e:
                    errors.append(file_hash)
                    siemplify.LOGGER.error(f"Unable to get report of {file_hash}")
                    siemplify.LOGGER.exception(e)

            verdicts = []

            for file_hash, report in reports:
                if report:
                    entity = get_entity_by_identifier(
                        siemplify.target_entities, file_hash
                    )
                    results_json[entity.identifier] = report

                    flat_report = dict_to_flat(report)
                    flat_report = add_prefix_to_dict(flat_report, "Intezer")
                    entity.additional_properties.update(flat_report)
                    enriched_entities.append(entity)
                    entity.is_enriched = True

                    verdicts.append(report.get("verdict", "no_verdict").lower())

                    if report.get("verdict") in MALICIOUS_VERDICTS:
                        entity.is_suspicious = True

                    siemplify.LOGGER.info(f"Attaching report for {file_hash}")
                    csv_output = flat_dict_to_csv(flat_report)

                    siemplify.result.add_entity_table(entity.identifier, csv_output)

            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(results_json)
            )
            siemplify.update_entities(enriched_entities)

            if errors:
                error_msg = f"\nErrors occurred on the following hashes: {', '.join(errors)}.\nCheck logs for details."

            siemplify.end(
                f"Analysis completed for all hashes.{error_msg}",
                ",".join(verdicts),
                EXECUTION_STATE_COMPLETED,
            )

        else:
            siemplify.end(
                "Analysis is still in progress.",
                json.dumps(scanned_hashes),
                EXECUTION_STATE_INPROGRESS,
            )

    except Exception as e:
        siemplify.LOGGER.exception(e)
        raise


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        async_analysis()
