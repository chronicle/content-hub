from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.DataDogManager import DataDogManager

IDENTIFIER = "DataDog"


@output_handler
def main():
    siemplify = SiemplifyAction()
    result_value = False
    output_message = ""
    found_db_identifier = {}
    not_found_db_identifier = []

    rds_metric = {}
    json_result = {}
    api_key = siemplify.extract_configuration_param(IDENTIFIER, "API Key")
    app_key = siemplify.extract_configuration_param(IDENTIFIER, "APP Key")

    db_instance_identifier_list = siemplify.extract_action_param(
        "Database Instance Identifier",
    )
    start_time = siemplify.extract_action_param("Start Time")
    end_time = siemplify.extract_action_param("End Time")

    datadog_manager = DataDogManager(api_key, app_key)

    # Converting the DataBase instance identifier into a list
    if db_instance_identifier_list is not None:
        db_instance_identifier_list = db_instance_identifier_list.split(",")

    for db_identifier in db_instance_identifier_list:
        db_identifier = db_identifier.strip()

        aws_rds_cpu = datadog_manager.get_aws_rds_metrics_cpu(
            db_identifier,
            start_time,
            end_time,
        )
        if aws_rds_cpu.get("status") == "ok" and len(aws_rds_cpu.get("series")) > 0:
            siemplify.LOGGER.info(
                f"The CPU of {db_identifier}  was fetched successfully.",
            )
            rds_metric["db_CPU"] = aws_rds_cpu
            result_value = True
        else:
            siemplify.LOGGER.info(f"The CPU of {db_identifier} wasn't fetched.")

        aws_rds_memory = datadog_manager.get_aws_rds_metrics_memory(
            db_identifier,
            start_time,
            end_time,
        )
        if (
            aws_rds_memory.get("status") == "ok"
            and len(aws_rds_memory.get("series")) > 0
        ):
            siemplify.LOGGER.info(
                f"The memory usage of {db_identifier} was fetched successfully",
            )
            rds_metric["db_memory"] = aws_rds_memory
            result_value = True

        else:
            siemplify.LOGGER.info(f"The memory of {db_identifier} wasn't fetched")

        aws_rds_storage = datadog_manager.get_aws_rds_metrics_storage(
            db_identifier,
            start_time,
            end_time,
        )
        if (
            aws_rds_storage.get("status") == "ok"
            and len(aws_rds_storage.get("series")) > 0
        ):
            siemplify.LOGGER.info(
                f"The free storage of {db_identifier} was fetched successfully",
            )
            rds_metric["db_free_storage"] = aws_rds_storage
            result_value = True

        else:
            siemplify.LOGGER.info(f"The free storage of {db_identifier} wasn't fetched")

        if bool(rds_metric) == True:
            found_db_identifier[f"db_instance_identifier: {db_identifier}"] = rds_metric
            output_message = (
                f"The metric of {db_instance_identifier_list} was found successfully"
            )
            result_value = True
        else:
            not_found_db_identifier.append(db_identifier)
            output_message = f"The metric of {db_identifier} wasn't found"

    json_result["founded_db_instance_identifier"] = found_db_identifier
    json_result["not_found_db_instance_identifier"] = not_found_db_identifier
    siemplify.result.add_result_json(json_result)

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
