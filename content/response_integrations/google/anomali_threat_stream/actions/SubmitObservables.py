from __future__ import annotations
import datetime
import time
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, convert_unixtime_to_datetime, unix_now
from TIPCommon import (
    extract_configuration_param,
    extract_action_param,
    flat_dict_to_csv,
    dict_to_flat,
)
from ..core.AnomaliThreatStreamManager import AnomaliManager
from ..core.constants import (
    INTEGRATION_NAME,
    SUBMIT_OBSERVABLES_SCRIPT_NAME,
    EMAIL_TYPE,
    DEFAULT_CLASSIFICATION,
    DEFAULT_THREAT_TYPE,
    DEFAULT_OBSERVABLE_SOURCE,
    SELECT_ONE,
    CLASSIFICATION_MAPPINGS,
    THREAT_TYPE_MAPPINGS,
    TLP_MAPPINGS,
    MIN_CONFIDENCE,
    MAX_CONFIDENCE,
    SPACE_CHARACTER,
    JOB_STATUS_WAITING_INTERVAL,
)
from ..core.exceptions import (
    AnomaliThreatStreamInvalidCredentialsException,
    AnomaliThreatStreamBadRequestException,
)
from ..core.utils import (
    string_to_multi_value,
    datetime_to_string,
    get_entity_type,
    get_entity_original_identifier,
)

SUPPORTED_ENTITIES = [
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EMAIL_TYPE,
]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SUBMIT_OBSERVABLES_SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    web_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Web Root",
        print_value=True,
    )
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Email Address",
        print_value=True,
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        remove_whitespaces=False,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        print_value=True,
    )

    classification = extract_action_param(
        siemplify,
        param_name="Classification",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_CLASSIFICATION,
    )
    threat_type = extract_action_param(
        siemplify,
        param_name="Threat Type",
        is_mandatory=True,
        print_value=True,
        default_value=DEFAULT_THREAT_TYPE,
    )
    source = extract_action_param(
        siemplify,
        param_name="Source",
        print_value=True,
        default_value=DEFAULT_OBSERVABLE_SOURCE,
    )
    expiration_date = extract_action_param(
        siemplify, param_name="Expiration Date", print_value=True, input_type=int
    )

    trusted_circle_ids = string_to_multi_value(
        extract_action_param(
            siemplify, param_name="Trusted Circle IDs", print_value=True
        )
    )

    tlp = extract_action_param(
        siemplify,
        param_name="TLP",
        is_mandatory=True,
        print_value=True,
        default_value=SELECT_ONE,
    )
    confidence = extract_action_param(
        siemplify, param_name="Confidence", print_value=True, input_type=int
    )

    override_system_confidence = extract_action_param(
        siemplify,
        param_name="Override System Confidence",
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    anonymous_submission = extract_action_param(
        siemplify,
        param_name="Anonymous Submission",
        input_type=bool,
        print_value=True,
        default_value=False,
    )

    tags = string_to_multi_value(
        extract_action_param(siemplify, param_name="Tags", print_value=True)
    )
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if get_entity_type(entity) in SUPPORTED_ENTITIES
    ]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    job_details = (
        []
    )  # list of dictionaries, each dictionary of format {'id':123, 'entity': <entity.identifier>}
    failed_entities = []  # identifiers of entities that failed to submit as observable
    status = EXECUTION_STATE_COMPLETED

    json_results = {"approved_jobs": [], "jobs_with_excluded_entities": []}

    result_value = False

    try:
        classification = CLASSIFICATION_MAPPINGS.get(classification)
        threat_type = THREAT_TYPE_MAPPINGS.get(threat_type)
        tlp = TLP_MAPPINGS.get(tlp)

        if expiration_date is not None and expiration_date <= 0:
            raise Exception(f"'Expiration date' parameter must be a positive number")

        if expiration_date:
            expiration_date = datetime_to_string(
                datetime.datetime.utcnow() + datetime.timedelta(days=expiration_date)
            )

        if confidence and (confidence < MIN_CONFIDENCE or confidence > MAX_CONFIDENCE):
            raise Exception(
                f"Confidence value should be in range from {MIN_CONFIDENCE} to "
                f"{MAX_CONFIDENCE}"
            )

        manager = AnomaliManager(
            web_root=web_root,
            api_root=api_root,
            api_key=api_key,
            username=username,
            verify_ssl=verify_ssl,
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            if SPACE_CHARACTER in entity_identifier.strip():
                siemplify.LOGGER.info(
                    f"Entity {entity_identifier} contains a ' ' character (space), "
                    "which is not supported for the action's supported entities."
                )
                continue

            try:
                siemplify.LOGGER.info(f"Submitting job for entity {entity_identifier}")
                # Get job status for submitted observable
                job_status = manager.submit_observable(
                    entity_identifier=entity_identifier.strip(),
                    classification=classification,
                    tlp=tlp,
                    tags=tags,
                    threat_type=threat_type,
                    confidence=confidence,
                    intelligence_source=source,
                    trusted_circle_ids=trusted_circle_ids,
                    can_override_confidence=override_system_confidence,
                    is_anonymous=anonymous_submission,
                    expiration_ts=expiration_date,
                )
                siemplify.LOGGER.info(
                    f"Submitted job {job_status.import_session_id} for approval"
                )
                job_details.append(
                    {"id": job_status.import_session_id, "entity": entity_identifier}
                )

            except AnomaliThreatStreamBadRequestException as e:
                raise e

            except AnomaliThreatStreamInvalidCredentialsException as e:
                raise e

            except Exception as error:  # failed to submit an observable
                failed_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(error)

        if job_details:
            for job in job_details:  # get job details for submitted observables
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ("
                        f"{convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)})"
                        f" has passed"
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    break
                try:
                    siemplify.LOGGER.info(f"Getting job details of {job.get('id')}")

                    job_details = manager.get_job_details(job_id=job.get("id"))

                    while (
                        not job_details.is_approved
                    ):  # wait until job will be approved
                        siemplify.LOGGER.info(
                            f"Job {job.get('id')} is not approved. Waiting "
                            f"{JOB_STATUS_WAITING_INTERVAL} seconds.."
                        )
                        time.sleep(JOB_STATUS_WAITING_INTERVAL)
                        job_details = manager.get_job_details(job_id=job.get("id"))

                    siemplify.LOGGER.info(f"Job {job.get('id')} approved")

                    if job_details.num_rejected > 0:  # entity in job excluded
                        json_results["jobs_with_excluded_entities"].append(
                            {"id": job.get("id"), "entity": job.get("entity")}
                        )
                    else:  # entity included
                        json_results["approved_jobs"].append(
                            {"id": job.get("id"), "entity": job.get("entity")}
                        )

                    siemplify.result.add_entity_table(
                        job.get("entity"),
                        flat_dict_to_csv(
                            dict_to_flat(
                                {"Link": f"{web_root}/import/review/{job.get('id')}"}
                            )
                        ),
                    )

                except Exception as e:
                    failed_entities.append(job.get("entity"))
                    siemplify.LOGGER.error(
                        "An error occurred when getting details for job "
                        f"{job.get('id')}"
                    )
                    siemplify.LOGGER.exception(e)

        else:
            siemplify.LOGGER.info("No supported entities found")

        if json_results["approved_jobs"] or json_results["jobs_with_excluded_entities"]:
            approved_entities = [
                job.get("entity") for job in json_results["approved_jobs"]
            ] + [
                job.get("entity") for job in json_results["jobs_with_excluded_entities"]
            ]

            output_message = (
                "Successfully submitted and approved the following entities in "
                f"{INTEGRATION_NAME}:\n {', '.join(approved_entities)} \n"
            )
            result_value = True
        else:
            output_message = (
                f"No entities were successfully submitted to {INTEGRATION_NAME}."
            )

        if failed_entities:
            output_message += (
                "Action was not able to successfully submit and approve the following "
                f"entities in {INTEGRATION_NAME}:\n   {', '.join(failed_entities)}"
            )

        if json_results:
            siemplify.result.add_result_json(json_results)

    except Exception as error:
        output_message = (
            f'Error executing action "{SUBMIT_OBSERVABLES_SCRIPT_NAME}". '
            f'Reason: {error}'
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
