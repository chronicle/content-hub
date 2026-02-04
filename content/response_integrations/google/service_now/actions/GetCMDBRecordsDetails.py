from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import construct_csv

from ..core.constants import (
    CSV_FILE_NAME,
    DEFAULT_MAX_RECORDS_TO_RETURN,
    GET_CMDB_RECORDS_SCRIPT_NAME,
    INTEGRATION_NAME,
)
from ..core.exceptions import ServiceNowNotFoundException, ServiceNowRecordNotFoundException
from ..core.ServiceNowManager import DEFAULT_TABLE, ServiceNowManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_CMDB_RECORDS_SCRIPT_NAME

    siemplify.LOGGER.info("=" * 10 + " Main - Param Init " + "=" * 10)
    # Configuration params
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        print_value=False,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        print_value=False,
    )
    default_incident_table = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Incident Table",
        print_value=True,
        default_value=DEFAULT_TABLE,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
    )
    client_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client ID",
        print_value=False,
    )
    client_secret = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Client Secret",
        print_value=False,
    )
    refresh_token = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Refresh Token",
        print_value=False,
    )
    use_oauth = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Use Oauth Authentication",
        default_value=False,
        input_type=bool,
    )
    # Parameters
    class_name = extract_action_param(
        siemplify, param_name="Class Name", is_mandatory=True, print_value=True
    )
    sys_ids_str = extract_action_param(
        siemplify, param_name="Sys ID", is_mandatory=True, print_value=True
    )
    max_records = extract_action_param(
        siemplify,
        param_name="Max Records To Return",
        is_mandatory=False,
        print_value=True,
        input_type=int,
        default_value=DEFAULT_MAX_RECORDS_TO_RETURN,
    )
    sys_ids = [sys_id.strip() for sys_id in sys_ids_str.split(",") if sys_id]

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    successful_sys_ids, failed_sys_ids, results = [], [], []

    if max_records <= 0:
        max_records = DEFAULT_MAX_RECORDS_TO_RETURN
        siemplify.LOGGER.error(
            f"Parameter: Max Records To Return can't be negative. Using default value of {DEFAULT_MAX_RECORDS_TO_RETURN}."
        )

    try:
        service_now_manager = ServiceNowManager(
            api_root=api_root,
            username=username,
            password=password,
            default_incident_table=default_incident_table,
            verify_ssl=verify_ssl,
            siemplify_logger=siemplify.LOGGER,
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            use_oauth=use_oauth,
        )

        for sys_id in sys_ids:
            try:
                sys_id_data = service_now_manager.list_cmdb_records_details(
                    class_name=class_name,
                    sys_id=sys_id,
                    max_records_to_return=max_records,
                )
                results.append(sys_id_data)
                successful_sys_ids.append(sys_id)
            except ServiceNowRecordNotFoundException:
                output_message = (
                    f'Record with Sys ID "{sys_id}" was not found in table "{class_name}"'
                )
                raise ServiceNowRecordNotFoundException(output_message)
            except ServiceNowNotFoundException:
                output_message = (
                    "Action wasn’t able to return details for CMDB records in the Class ‘{}’ "
                    "in Service Now. Reason: Class ‘{}’ was not found.".format(
                        class_name, class_name
                    )
                )
                raise ServiceNowNotFoundException(output_message)
            except Exception as err:
                failed_sys_ids.append(sys_id)
                siemplify.LOGGER.error(
                    f"Action wasn’t able to return details for CMDB records: Reason: {err}"
                )
                siemplify.LOGGER.exception(err)

        if results:
            # Collect relations and insert data into Results.csv file
            relations = []
            for result in results:
                for relation in result.inbound_relations + result.outbound_relations:
                    relations.append(relation.to_table())

            siemplify.result.add_data_table(
                title=CSV_FILE_NAME, data_table=construct_csv(relations)
            )
            # Add data into JSON result
            siemplify.result.add_result_json([result.to_json() for result in results])

        if successful_sys_ids:
            output_message += (
                "Successfully returned details for CMDB records in the Class ‘{}’ from Service Now "
                "for the following Sys IDs: \n{}\n".format(
                    class_name, "\n".join(successful_sys_ids)
                )
            )

        if failed_sys_ids:
            output_message += (
                "\nAction wasn’t able to return details for CMDB records in the Class ‘{}’ from "
                "Service Now for the following Sys IDs: \n{}\n".format(
                    class_name, "\n".join(failed_sys_ids)
                )
            )

        if not successful_sys_ids:
            output_message = "Information about the provided Sys ids was not found."
            result_value = False

    except ServiceNowNotFoundException as e:
        output_message = str(e)
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
    except Exception as e:
        output_message = f'General error performing action "Get CMDB Records Details". Reason: {e}'
        status = EXECUTION_STATE_FAILED
        result_value = False
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
