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
from TIPCommon import extract_configuration_param, extract_action_param
from ..core import consts
from ..core.ThreatFuseManager import ThreatFuseManager
from ..core.consts import INTEGRATION_NAME
from ..core.exceptions import (
    ThreatFuseValidationException,
    ThreatFuseInvalidCredentialsException,
    ThreatFuseBadRequestException,
    ThreatFuseStatusCodeException,
)
from ..core.utils import load_csv_to_list, datetime_to_string

SCRIPT_NAME = "Submit Observables"
SUPPORTED_ENTITIES = (
    EntityTypes.FILEHASH,
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EntityTypes.USER,
)


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    web_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Web Root",
        is_mandatory=True,
        print_value=True,
    )

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        print_value=True,
    )

    email_address = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Email Address",
        is_mandatory=True,
    )

    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Key",
        is_mandatory=True,
    )

    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    classification = extract_action_param(
        siemplify,
        param_name="Classification",
        is_mandatory=True,
        print_value=True,
        default_value=consts.DEFAULT_CLASSIFICATION,
    )

    threat_type = extract_action_param(
        siemplify,
        param_name="Threat Type",
        is_mandatory=True,
        print_value=True,
        default_value=consts.DEFAULT_THREAT_TYPE,
    )

    source = extract_action_param(
        siemplify,
        param_name="Source",
        is_mandatory=False,
        print_value=True,
        default_value=consts.DEFAULT_OBSERVABLE_SOURCE,
    )

    expiration_date = extract_action_param(
        siemplify,
        param_name="Expiration Date",
        is_mandatory=False,
        print_value=True,
        input_type=int,
    )

    trusted_circle_ids = extract_action_param(
        siemplify, param_name="Trusted Circle IDs", is_mandatory=False, print_value=True
    )

    tlp = extract_action_param(
        siemplify,
        param_name="TLP",
        is_mandatory=True,
        print_value=True,
        default_value=consts.SELECT_ONE,
    )

    confidence = extract_action_param(
        siemplify,
        param_name="Confidence",
        is_mandatory=False,
        print_value=True,
        input_type=int,
    )

    override_system_confidence = extract_action_param(
        siemplify,
        param_name="Override System Confidence",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=consts.OVERRIDE_SYSTEM_CONFIDENCE,
    )

    anonymous_submission = extract_action_param(
        siemplify,
        param_name="Anonymous Submission",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
        default_value=consts.ANONYMOUS_SUBMISSION_DEFAULT_VALUE,
    )

    tags = extract_action_param(
        siemplify, param_name="Tags", is_mandatory=False, print_value=True
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    job_details = (
        []
    )  # list of dictionaries, each dictionary of format {'id':123, 'entity': <entity.identifier>}
    failed_entities = []  # identifiers of entities that failed to submit as observable
    status = EXECUTION_STATE_COMPLETED

    json_results = {"approved_jobs": [], "jobs_with_excluded_entities": []}

    result_value = "false"

    try:
        classification = consts.CLASSIFICATION_MAPPINGS.get(classification)
        threat_type = consts.THREAT_TYPE_MAPPINGS.get(threat_type)
        tlp = consts.TLP_MAPPINGS.get(tlp)

        tags = load_csv_to_list(tags, param_name="Tags") if tags else []
        trusted_circle_ids = (
            load_csv_to_list(trusted_circle_ids, param_name="Trusted Circle IDs")
            if trusted_circle_ids
            else []
        )

        if expiration_date is not None and expiration_date <= 0:
            raise ThreatFuseValidationException(
                f"'Expiration date' parameter must be a positive number"
            )

        if expiration_date:
            expiration_date = datetime_to_string(
                datetime.datetime.utcnow() + datetime.timedelta(days=expiration_date)
            )

        if confidence and (
            confidence < consts.MIN_CONFIDENCE or confidence > consts.MAX_CONFIDENCE
        ):
            raise ThreatFuseValidationException(
                f"Confidence value should be in range from {consts.MIN_CONFIDENCE} to {consts.MAX_CONFIDENCE}"
            )

        manager = ThreatFuseManager(
            web_root=web_root,
            api_root=api_root,
            api_key=api_key,
            email_address=email_address,
            verify_ssl=verify_ssl,
        )

        for entity in siemplify.target_entities:
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(
                    f"Entity {entity.identifier} is of unsupported type. Skipping."
                )
                continue

            if consts.SPACE_CHARACTER in entity.identifier.strip():
                siemplify.LOGGER.info(
                    "Entity {} contains a ' ' character (space), which is not supported for the action's "
                    "supported entities.".format(entity.identifier)
                )
                continue

            try:
                siemplify.LOGGER.info(f"Submitting job for entity {entity.identifier}")
                # Get job status for submitted observable
                job_status = manager.submit_observable(
                    entity_identifier=entity.identifier.strip(),
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
                    {"id": job_status.import_session_id, "entity": entity.identifier}
                )

            except ThreatFuseBadRequestException as e:
                raise e

            except ThreatFuseInvalidCredentialsException as e:
                raise e

            except (
                ThreatFuseStatusCodeException
            ) as error:  # failed to submit an observable
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(error)

        if job_details:
            for job in job_details:  # get job details for submitted observables
                if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                    siemplify.LOGGER.error(
                        f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
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
                            f"Job {job.get('id')} is not approved. Waiting {consts.JOB_STATUS_WAITING_INTERVAL} seconds.."
                        )
                        time.sleep(consts.JOB_STATUS_WAITING_INTERVAL)
                        job_details = manager.get_job_details(job_id=job.get("id"))

                    siemplify.LOGGER.info(f"Job {job.get('id')} approved")

                    if job_details.numRejected > 0:  # entity in job excluded
                        json_results["jobs_with_excluded_entities"].append(
                            {"id": job.get("id"), "entity": job.get("entity")}
                        )
                    else:  # entity included
                        json_results["approved_jobs"].append(
                            {"id": job.get("id"), "entity": job.get("entity")}
                        )

                except Exception as e:
                    failed_entities.append(job.get("entity"))
                    siemplify.LOGGER.error(
                        f"An error occurred when getting details for job {job.get('id')}"
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

            siemplify.LOGGER.info(
                "Successfully submitted and approved the following entities in {}:\n   {}".format(
                    INTEGRATION_NAME, "\n   ".join(approved_entities)
                )
            )
            output_message = "Successfully submitted and approved the following entities in {}:\n   {}".format(
                INTEGRATION_NAME, "\n   ".join(approved_entities)
            )
            result_value = "true"
        else:
            siemplify.LOGGER.info(
                f"No entities were successfully submitted to {INTEGRATION_NAME}."
            )
            output_message = (
                f"No entities were successfully submitted to {INTEGRATION_NAME}."
            )

        if failed_entities:
            output_message += "\n\n Action was not able to successfully submit and approve the following entities in {}:\n   {}".format(
                INTEGRATION_NAME, "\n   ".join(failed_entities)
            )

    except ThreatFuseValidationException as error:
        siemplify.LOGGER.error(error)
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f"{error}"

    except Exception as error:
        siemplify.LOGGER.error(
            f'Error executing action "{SCRIPT_NAME}". Reason: {error}'
        )
        siemplify.LOGGER.exception(error)
        status = EXECUTION_STATE_FAILED
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {error}'

    siemplify.result.add_result_json(json_results)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
