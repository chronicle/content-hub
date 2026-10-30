# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import os
import shutil
import sys

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_connector_param
from TIPCommon.transformation import dict_to_flat

from csv_integration.core.constants import CSV_CONNECTOR_SCRIPT_NAME, DEFAULT_PRODUCT, DEFAULT_VENDOR
from csv_integration.core.CSVManager import CSVManager, FILE_ENCODINGS_DEFAULT
from csv_integration.core.exceptions import CSVConnectorException, CSVEncodingException
from csv_integration.core.utils import (
    CUSTOM_CONFIGURATION_FILE_NAME,
    calculate_row_time,
    get_encodings_or_raise,
    get_environment_common,
    is_overflowed,
    load_custom_severity_configuration,
    map_severity_value,
    string_to_multi_value,
)


# ============================== CONSTS ===================================== #
CSV_LIMIT = 10
DEFAULT_RULE_GENERATOR = "CSV"
DEFAULT_NAME = "Perform CSV <{}>"
DONE_FOLDER_NAME = "Done"
ERROR_FOLDER_NAME = "Error"
DEFAULT_TIMEZONE = "UTC"


@output_handler
def main(is_test_run=False):
    processed_alerts = []
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CSV_CONNECTOR_SCRIPT_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button"\\"Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("------------------- Main - Param Init -------------------")

    csv_folder_path = extract_connector_param(
        siemplify=siemplify,
        param_name="Csv Folder Path",
        is_mandatory=True,
        print_value=True,
    )
    files_limit = extract_connector_param(
        siemplify=siemplify,
        param_name="CSV Limit",
        print_value=True,
        input_type=int,
        default_value=CSV_LIMIT,
    )
    device_product_field_name = extract_connector_param(
        siemplify=siemplify,
        param_name="DeviceProductField",
        is_mandatory=True,
        print_value=True,
    )
    time_field_name = extract_connector_param(
        siemplify=siemplify, param_name="Time Field Name", print_value=True
    )
    time_field_timezone = extract_connector_param(
        siemplify=siemplify,
        param_name="Time Field Timezone",
        print_value=True,
        default_value=DEFAULT_TIMEZONE,
    )
    environment_field_name = extract_connector_param(
        siemplify,
        param_name="Environment Field Name",
        default_value="",
        print_value=True,
    )
    environment_regex_pattern = extract_connector_param(
        siemplify,
        param_name="Environment Regex Pattern",
        default_value=".*",
        print_value=True,
    )
    rule_generator_field_name = extract_connector_param(
        siemplify=siemplify, param_name="Rule Generator Field Name", print_value=True
    )
    file_has_header = extract_connector_param(
        siemplify=siemplify,
        param_name="CSV Has Header",
        print_value=True,
        input_type=bool,
        default_value=False,
    )
    file_encodings = string_to_multi_value(
        extract_connector_param(
            siemplify=siemplify,
            param_name="File Encoding Types",
            print_value=True,
            default_value=",".join(FILE_ENCODINGS_DEFAULT),
        )
    )
    alert_name_field = extract_connector_param(
        siemplify=siemplify, param_name="Alert Field Name", print_value=True
    )
    severity_field_name = extract_connector_param(
        siemplify=siemplify, param_name="Severity Field Name", print_value=True
    )

    try:
        load_custom_severity_configuration(
            severity_field_name,
            os.path.join(siemplify.run_folder, CUSTOM_CONFIGURATION_FILE_NAME),
        )

        create_folders_if_not_exist(siemplify, csv_folder_path)

        csv_manager = CSVManager(siemplify)
        file_encodings = get_encodings_or_raise(siemplify, file_encodings)

        all_csv_paths = csv_manager.get_relevant_csv_files(
            csv_folder_or_file_path=csv_folder_path, csv_count_limit=files_limit
        )
        siemplify.LOGGER.info(f"Found {len(all_csv_paths)} CSV files")

        for csv_path in all_csv_paths:
            siemplify.LOGGER.info(
                f"\nStarted processing file: {os.path.basename(csv_path)}"
            )
            try:
                csv_rows = csv_manager.read_csv(
                    csv_path, file_encodings, file_has_header=file_has_header
                )
                row_processed_successfully = True
                for index, row in csv_rows.iterrows():
                    # The indicator that a row was processed correctly is by default set to True
                    try:
                        siemplify.LOGGER.info(
                            f"---------- Converting CSV Record {csv_path}-{index} to Siemplify Alert ----------"
                        )
                        alert_info = create_alert_info(
                            siemplify=siemplify,
                            row=row,
                            row_index=index,
                            csv_path=csv_path,
                            time_field_name=time_field_name,
                            alert_name_field=alert_name_field,
                            time_field_timezone=time_field_timezone,
                            severity_field_name=severity_field_name,
                            device_product_name=device_product_field_name,
                            rule_generator_field_name=rule_generator_field_name,
                            environment_common=get_environment_common(
                                siemplify,
                                environment_field_name,
                                environment_regex_pattern,
                            ),
                        )
                        if is_overflowed(siemplify, alert_info, is_test_run):
                            siemplify.LOGGER.info(
                                f"{alert_info.rule_generator}-{alert_info.ticket_id}-"
                                f"{alert_info.environment}-{alert_info.device_product} "
                                "found as overflow alert. Skipping."
                            )
                            # If is overflowed we should skip
                            continue

                        processed_alerts.append(alert_info)

                        siemplify.LOGGER.info(
                            f"Successfully converted convert CSV Record {csv_path}-{index} to Siemplify alert"
                        )
                        if is_test_run:
                            siemplify.LOGGER.info(
                                "This is a TEST run. Only 1 alert will be processed."
                            )
                            break

                    except Exception as e:
                        row_processed_successfully = False
                        # Set the indicator to False, so the processed file will be moved to Error folder
                        siemplify.LOGGER.error(
                            f"Failed to convert CSV Record {csv_path}-{index} to Siemplify alert"
                        )
                        siemplify.LOGGER.exception(e)
                        if is_test_run:
                            raise

                if not is_test_run:
                    # In case of running connector as test - do not move the csv to any folder
                    if row_processed_successfully:
                        try:
                            processed_file_handling(
                                siemplify, csv_path, csv_folder_path, DONE_FOLDER_NAME
                            )
                        except Exception as e:
                            siemplify.LOGGER.exception(e)
                            processed_file_handling(
                                siemplify, csv_path, csv_folder_path, ERROR_FOLDER_NAME
                            )
                            siemplify.LOGGER.error(
                                f"Unable to move {csv_path} to Done folder"
                                f" {os.path.join(csv_folder_path, DONE_FOLDER_NAME)}"
                            )
                            siemplify.LOGGER.info(
                                f"Move {csv_path} to Error folder "
                                f"{os.path.join(csv_folder_path, ERROR_FOLDER_NAME)}"
                            )
                    else:
                        # If at least one row wasn't processed correctly, move the whole file to Error folder
                        processed_file_handling(
                            siemplify, csv_path, csv_folder_path, ERROR_FOLDER_NAME
                        )
                        siemplify.LOGGER.error(
                            f"An error occurred while processing the file {csv_path}"
                        )
                        siemplify.LOGGER.info(
                            f"File {csv_path} moved to Error folder "
                            f"{os.path.join(csv_folder_path, ERROR_FOLDER_NAME)}"
                        )
            except CSVEncodingException as e:
                siemplify.LOGGER.exception(e)
                siemplify.LOGGER.error(
                    "Please provide right encoding's for reading csv file's"
                )
                raise

            except Exception as e:
                # Execution failed - move to error folder
                siemplify.LOGGER.exception(e)
                if not is_test_run:
                    try:
                        processed_file_handling(
                            siemplify, csv_path, csv_folder_path, ERROR_FOLDER_NAME
                        )
                    except Exception as e:
                        siemplify.LOGGER.error(
                            f"Unable to move {csv_path} to Error folder "
                            f"{os.path.join(csv_folder_path, ERROR_FOLDER_NAME)}"
                        )
                        siemplify.LOGGER.exception(e)

        siemplify.LOGGER.info(f"Created {len(processed_alerts)} cases.")
        siemplify.LOGGER.info(
            "-------------------- Main - CSV Connector Finish --------------------"
        )
        siemplify.return_package(processed_alerts)

    except Exception as e:
        siemplify.LOGGER.error(e)
        siemplify.LOGGER.exception(e)


def create_folders_if_not_exist(siemplify, csv_folder_path):
    """
    Check if supportive folders: Done and Error exist, if not create them
    :param siemplify: {Siemplify}
    :param csv_folder_path: {str} Folder containing all CSV files
    """
    for folder_to_create in [
        os.path.join(csv_folder_path, DONE_FOLDER_NAME),
        os.path.join(csv_folder_path, ERROR_FOLDER_NAME),
    ]:
        try:
            # Make Done folder if doesn't exist
            if not os.path.exists(folder_to_create):
                os.makedirs(folder_to_create)
                siemplify.LOGGER.info(f"New folder created: {folder_to_create}")
        except Exception as e:
            siemplify.LOGGER.error(f"Unable to create folder: {e}")
            raise CSVConnectorException(e)


def get_alert_name(siemplify, event_json, alert_name_field, csv_path):
    """
    Get alert name
    :return: {str} alert name
    """
    if alert_name_field not in event_json:
        siemplify.LOGGER.info(
            f"Provided 'Alert Field Name' does not exist in {csv_path}"
        )
    return event_json.get(alert_name_field) or DEFAULT_NAME.format(csv_path)


def create_alert_info(
    siemplify,
    *,
    environment_common,
    csv_path,
    row_index,
    row,
    time_field_name,
    severity_field_name,
    rule_generator_field_name,
    device_product_name,
    time_field_timezone,
    alert_name_field,
):
    """
    Builds alert
    :return: {CaseInfo} The newly created case
    """
    event_json = dict_to_flat(row.to_dict())
    alert_info = CaseInfo()
    alert_id = f"{csv_path}-{row_index}"
    alert_info.name = get_alert_name(siemplify, event_json, alert_name_field, csv_path)
    alert_info.ticket_id = alert_info.display_id = alert_info.identifier = alert_id
    alert_info.priority = map_severity_value(severity_field_name, alert_data=event_json)
    alert_info.device_vendor = DEFAULT_VENDOR
    alert_info.rule_generator = (
        row.get(rule_generator_field_name) or DEFAULT_RULE_GENERATOR
    )
    alert_info.device_product = row.get(device_product_name) or DEFAULT_PRODUCT

    # Get file time
    alert_info.end_time = alert_info.start_time = calculate_row_time(
        siemplify,
        row=row,
        csv_path=csv_path,
        time_field_name=time_field_name,
        time_field_timezone=time_field_timezone,
    )
    alert_info.end_time = alert_info.start_time
    alert_info.events = [event_json]
    alert_info.environment = environment_common.get_environment(event_json)

    return alert_info


def processed_file_handling(siemplify, csv_path, csv_folder_path, folder_tag):
    """
    Move csv to a folder based on the execution status (can not create cases from csv rows)
    :param siemplify: {Siemplify}
    :param csv_path {str} Full path to csv file
    :param csv_folder_path {str} Folder containing all csv files
    :param folder_tag {str} A tag that specifies to which folder is the csv file moved
    """
    csv_file_name = os.path.basename(csv_path)
    final_csv_folder_path = os.path.join(csv_folder_path, folder_tag)

    if folder_tag == DONE_FOLDER_NAME:
        shutil.move(csv_path, os.path.join(final_csv_folder_path, csv_file_name))
        siemplify.LOGGER.info(
            f"Execution succeed - {csv_file_name} is moved to DONE folder {final_csv_folder_path}"
        )
    elif folder_tag == ERROR_FOLDER_NAME:
        shutil.move(csv_path, os.path.join(final_csv_folder_path, csv_file_name))
        siemplify.LOGGER.info(
            f"Execution failed - {csv_file_name} is moved to ERROR folder {final_csv_folder_path}"
        )


if __name__ == "__main__":
    # Connectors are run in iterations. The interval is configurable from the ConnectorsScreen UI.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
