from __future__ import annotations

import base64
import json
import sys
from datetime import datetime, timezone

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.api_manager import APIManager
from ..core.constants import (
    COMMON_ACTION_ERROR_MESSAGE,
    DOWNLOAD_SNAPSHOT_RESULTS_CSV_SCRIPT_NAME,
    FILE_STATE_FAILED,
    FILE_STATE_READY,
    RESULT_VALUE_FALSE,
    RESULT_VALUE_TRUE,
    USER_FILE_TYPE_CSV,
)
from ..core.rubrik_exceptions import (
    ItemNotFoundException,
    RubrikException,
    UnauthorizedErrorException,
)
from ..core.utils import (
    format_authentication_failure_message,
    get_integration_params,
    validate_required_string,
    validate_uuid_format,
)

ACTION_ERROR_PREFIX = "Failed to generate snapshot results CSV"

# RSC names snapshot-results CSV downloads as "<object_name>-violating-files_file_results...".
# Matching on this exact pattern (not just the bare object name) prevents this action from
# ever picking up a concurrent download triggered for a different object.
SNAPSHOT_CSV_FILENAME_SUFFIX = "-violating-files_file_results"


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOAD_SNAPSHOT_RESULTS_CSV_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    output_message = ""
    status = EXECUTION_STATE_INPROGRESS
    result_value = RESULT_VALUE_TRUE
    json_results: dict = {}

    try:
        service_account_json, verify_ssl = get_integration_params(siemplify)

        object_id = siemplify.extract_action_param(
            param_name="Object ID",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )
        violation_id = siemplify.extract_action_param(
            param_name="Violation ID",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )
        snapshot_id = siemplify.extract_action_param(
            param_name="Snapshot ID",
            input_type=str,
            is_mandatory=True,
            print_value=True,
        )
        object_name = siemplify.extract_action_param(
            param_name="Object Name",
            input_type=str,
            is_mandatory=False,
            print_value=True,
        )
        action_context = json.loads(
            siemplify.extract_action_param(
                param_name="additional_data",
                default_value="{}",
                print_value=True,
            )
            or "{}"
        )

        siemplify.LOGGER.info("----------------- Main - Started -----------------")

        object_id = validate_uuid_format(
            validate_required_string(object_id, "Object ID"), "Object ID"
        )
        violation_id = validate_uuid_format(
            validate_required_string(violation_id, "Violation ID"), "Violation ID"
        )
        snapshot_id = validate_uuid_format(
            validate_required_string(snapshot_id, "Snapshot ID"), "Snapshot ID"
        )
        object_name = (object_name or "").strip()

        manager = APIManager(
            service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        if is_first_run:
            # Capture the action start time BEFORE triggering generation. Only files
            # created after this instant are considered ours when locating the
            # externalId — this excludes files from earlier triggers for the same
            # object but a different violation/snapshot.
            action_started_at = datetime.now(timezone.utc)

            # Step 1: fetch violation details and validate the provided inputs against
            # the violation BEFORE triggering any generation. A single Get DSPM
            # Violation Details call supplies the resourceId, snapshotId, and object
            # name used for these checks.
            siemplify.LOGGER.info(
                "Step 1: Fetching violation details to validate inputs before triggering."
            )
            details_data = manager.get_dspm_violation_details(violation_id)
            violation_raw = details_data.get("policyViolation") or {}

            # Validate Object ID matches the violation's resourceId.
            expected_resource_id = violation_raw.get("resourceId") or ""
            if object_id.strip().lower() != expected_resource_id.strip().lower():
                raise ItemNotFoundException(
                    f"Object ID '{object_id}' does not match the resource of violation ID "
                    f"{violation_id} (expected '{expected_resource_id}')."
                )

            # Validate Snapshot ID matches the violation's snapshotId.
            expected_snapshot_id = (violation_raw.get("details") or {}).get("snapshotId") or ""
            if snapshot_id.strip().lower() != expected_snapshot_id.strip().lower():
                raise ItemNotFoundException(
                    f"Snapshot ID '{snapshot_id}' does not match the snapshot of violation ID "
                    f"{violation_id} (expected '{expected_snapshot_id}')."
                )

            # Resolve/validate Object Name from the same response.
            metadata = (violation_raw.get("resourceMetadata") or {}).get("metadata") or {}
            expected_object_name = metadata.get("name") or ""
            if object_name:
                if object_name.strip().lower() != expected_object_name.strip().lower():
                    raise ItemNotFoundException(
                        f"No object found with name: '{object_name}'. "
                        f"Expected object name for violation ID {violation_id}: "
                        f"'{expected_object_name}'."
                    )
            else:
                object_name = expected_object_name

            # Step 2: trigger CSV generation (only after all inputs are validated).
            siemplify.LOGGER.info("Step 2: Triggering snapshot results CSV generation.")
            manager.trigger_snapshot_csv(
                snappable_fid=object_id,
                snapshot_fid=snapshot_id,
                violation_id=violation_id,
            )
            siemplify.LOGGER.info("Step 2 complete: CSV generation triggered.")

            # Step 3: immediately look up the resulting file's externalId via
            # allUserFiles, matched by object name + file type + recency.
            # RSC replaces spaces in the object name with hyphens when naming the
            # download (e.g. "User Action Level" -> "User-Action-Level-violating-...").
            sanitized_object_name = object_name.replace(" ", "-")
            target_file_name = f"{sanitized_object_name}{SNAPSHOT_CSV_FILENAME_SUFFIX}"

            siemplify.LOGGER.info(
                f"Step 3: Locating triggered snapshot results CSV (matching filename "
                f"containing '{target_file_name}')."
            )
            file_entry = manager.find_user_file_by_filename(
                file_type=USER_FILE_TYPE_CSV,
                filename_contains=target_file_name,
                created_after=action_started_at,
            )

            # Step 4: fail fast if the externalId can't be resolved right away.
            external_id = file_entry.get("externalId") if file_entry else None
            if not external_id:
                raise RubrikException(f"Unable to fetch externalId for '{object_name}'.")

            # Step 5: persist the externalId for status polling on the next run.
            action_context["external_id"] = external_id
            siemplify.LOGGER.info(
                f"Step 3 complete: File located (externalId={external_id}). "
                "Stored for status polling on the next run."
            )

            output_message = "Waiting for snapshot results CSV to be generated..."
            status = EXECUTION_STATE_INPROGRESS
            result_value = json.dumps(action_context)
            siemplify.LOGGER.info(output_message)

        else:
            # Subsequent runs: check readiness of the already-located file by its
            # stored externalId, and download once it is READY.
            external_id = action_context.get("external_id")

            siemplify.LOGGER.info(
                f"Step 2: Checking readiness of located file (externalId={external_id})."
            )
            file_entry = manager.get_user_file_by_external_id(external_id)
            file_state = file_entry.get("state") if file_entry else None

            if file_state == FILE_STATE_READY:
                filename = file_entry.get("filename") or "snapshot_results.csv"
                siemplify.LOGGER.info(
                    f"Step 2 complete: File ready. externalId={external_id} filename={filename}"
                )

                # Step 3 — download binary content
                siemplify.LOGGER.info(f"Step 3: Downloading file externalId={external_id}.")
                file_bytes = manager.download_file(external_id)
                siemplify.LOGGER.info(
                    f"Step 3 complete: Downloaded {len(file_bytes)} bytes."
                )

                # Attach to SOAR case
                b64_content = base64.b64encode(file_bytes).decode("utf-8")
                siemplify.result.add_attachment(filename, filename, b64_content)

                output_message = (
                    f"CSV file '{filename}' attached to case. "
                    f"Contains files at risk for violation ID: {violation_id}."
                )
                status = EXECUTION_STATE_COMPLETED
                result_value = RESULT_VALUE_TRUE
                siemplify.LOGGER.info(output_message)

            elif file_state == FILE_STATE_FAILED:
                raise RubrikException(f"File generation failed for type={USER_FILE_TYPE_CSV}.")

            else:
                output_message = "Waiting for snapshot results CSV to be generated..."
                status = EXECUTION_STATE_INPROGRESS
                result_value = json.dumps(action_context)
                siemplify.LOGGER.info(output_message)

    except ValueError as e:
        output_message = str(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)

    except UnauthorizedErrorException as e:
        output_message = format_authentication_failure_message(e)
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except RubrikException as e:
        output_message = f"{ACTION_ERROR_PREFIX}: {e}"
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    except Exception as e:
        output_message = COMMON_ACTION_ERROR_MESSAGE.format(
            DOWNLOAD_SNAPSHOT_RESULTS_CSV_SCRIPT_NAME, e
        )
        result_value = RESULT_VALUE_FALSE
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    finally:
        siemplify.result.add_result_json(json_results)
        siemplify.LOGGER.info("----------------- Main - Finished -----------------")
        siemplify.LOGGER.info(f"Status: {status}")
        siemplify.LOGGER.info(f"result_value: {result_value}")
        siemplify.LOGGER.info(f"Output Message: {output_message}")
        siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
