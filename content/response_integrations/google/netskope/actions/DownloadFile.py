from __future__ import annotations
import base64
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.NetskopeManagerFactory import NetskopeManagerFactory
from TIPCommon import extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

INTEGRATION_NAME = "Netskope"
DOWNLOADFILE_SCRIPT_NAME = f"{INTEGRATION_NAME} - DownloadFile"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = DOWNLOADFILE_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    # Parameters
    use_v2_api = extract_action_param(
        siemplify,
        param_name="Use V2 API",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    file_id = extract_action_param(
        siemplify, param_name="File ID", is_mandatory=True, print_value=True
    )
    quarantine_profile_id = extract_action_param(
        siemplify,
        param_name="Quarantine Profile ID",
        is_mandatory=False,
        print_value=True,
    )

    if not use_v2_api and not quarantine_profile_id:
        raise ValueError("Quarantine Profile ID is mandatory for V1 API.")

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    siemplify.LOGGER.info("Starting to perform the action")
    status = EXECUTION_STATE_FAILED
    result_value = False
    file_name = ""
    output_message = f"File {file_id} was not found in quarantine."
    try:
        netskope_manager = NetskopeManagerFactory.get_manager(
            siemplify, api_version="v2" if use_v2_api else "v1"
        )
        files = netskope_manager.get_quarantined_files()

        file_content = None
        target_file = None

        for file_item in files:
            orig_id = file_item.get("originalResource", {}).get("id")
            quar_id = file_item.get("quarantinedResource", {}).get("id")
            incident_id = file_item.get("file_id") or file_item.get("id")

            if file_id in [orig_id, quar_id, incident_id]:
                if (
                    not use_v2_api
                    and quarantine_profile_id
                    and file_item.get("quarantine_profile_id") != quarantine_profile_id
                ):
                    continue
                target_file = file_item
                break

        if target_file:
            file_name = (
                target_file.get("original_file_name")
                or target_file.get("originalName")
                or target_file.get("file_name")
                or target_file.get("quarantinedName")
            )
            if use_v2_api:
                res = target_file.get("quarantinedResource")
                if res and res.get("app") and res.get("instance"):
                    file_content = netskope_manager.download_file(
                        app=res["app"],
                        instance=res["instance"],
                        file_id=res.get("id") or file_id,
                    )
                else:
                    raise ValueError(
                        "Unable to download file using V2 API: missing app or "
                        "instance information."
                    )
            else:
                file_content = netskope_manager.download_file(
                    file_id, quarantine_profile_id
                )

        if file_name:
            siemplify.result.add_attachment(
                file_name, file_name, base64.b64encode(file_content).decode("ascii")
            )
            output_message = f"Successfully downloaded file {file_id}"
            result_value = True
            siemplify.LOGGER.info("Finished performing the action")
        status = EXECUTION_STATE_COMPLETED

    except Exception as e:
        output_message = f'Error executing action "DownloadFile". Reason: {e}'
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
