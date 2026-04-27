from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from ..core.ArcsightManager import ArcsightManager
from TIPCommon import extract_configuration_param, extract_action_param
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from ..core.exceptions import ArcsightInvalidParamError
from ..core.constants import INTEGRATION_NAME, ADD_ENTRIES_TO_ACTIVE_LIST_SCRIPT_NAME
import json


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ADD_ENTRIES_TO_ACTIVE_LIST_SCRIPT_NAME
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    ca_certificate_file = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="CA Certificate File"
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    columns_string = extract_action_param(
        siemplify, param_name="Columns", print_value=True
    )
    entries_string = extract_action_param(
        siemplify, param_name="Entries", print_value=True
    )
    list_uuid = extract_action_param(
        siemplify, param_name="Active List UUID", print_value=True
    )
    activelist_name = extract_action_param(
        siemplify, param_name="Active list name", print_value=True
    )
    json_entities = extract_action_param(
        siemplify, param_name="Entries JSON", print_value=True
    )

    entries = {"columns": [], "entry_list": []}
    fetched_by_uuid = bool(list_uuid)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    try:
        if json_entities:
            json_entities = json.loads(json_entities)

        if not list_uuid and not activelist_name:
            raise ArcsightInvalidParamError(
                "either 'Active list UUID' or 'Active list name' should be provided."
            )

        if not json_entities and (not columns_string and not entries_string):
            raise ArcsightInvalidParamError(
                "either 'Entries JSON' or 'Columns' + 'Entries' should be provided."
            )

        if columns_string and entries_string:
            entries["columns"] = columns_string.split(";")
            entries["entry_list"] = [
                entry.split("|") for entry in entries_string.split(";")
            ]

        elif json_entities:
            json_entities = (
                json_entities if isinstance(json_entities, list) else [json_entities]
            )
            for json_entry in json_entities:
                entries["columns"] += [
                    name for name in json_entry.keys() if name not in entries["columns"]
                ]
                entries["entry_list"].append(
                    [json_entry.get(name, "") for name in entries["columns"]]
                )
        else:
            # case when provided ONLY columns_string OR entries_string
            raise ArcsightInvalidParamError(
                "both 'Columns' and 'Entries' should be provided."
            )

        arcsight_manager = ArcsightManager(
            server_ip=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
            ca_certificate_file=ca_certificate_file,
            logger=siemplify.LOGGER,
        )

        arcsight_manager.login()

        if not list_uuid:
            list_uuid = arcsight_manager.get_activelist_uuid(activelist_name)

        arcsight_manager.add_entries_to_activelist_uuid(
            entries=entries, list_uuid=list_uuid
        )
        status = EXECUTION_STATE_COMPLETED
        result_value = True
        output_message = ""

        if fetched_by_uuid:
            output_message = f"Successfully added entries to the active list with UUID '{list_uuid}' in ArcSight."
        elif activelist_name:
            output_message = f"Successfully added entries to the active list '{activelist_name}' in ArcSight."

        arcsight_manager.logout()

    except Exception as e:
        output_message = f"Error executing action {ADD_ENTRIES_TO_ACTIVE_LIST_SCRIPT_NAME}. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False
        status = EXECUTION_STATE_FAILED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
