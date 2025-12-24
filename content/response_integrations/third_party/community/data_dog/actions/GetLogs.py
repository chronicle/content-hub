from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.DataDogManager import DataDogManager

IDENTIFIER = "DataDog"


@output_handler
def main():
    siemplify = SiemplifyAction()
    result_value = False
    output_message = [""]
    json_result = {}
    namespace_logs = {}

    api_key = siemplify.extract_configuration_param(IDENTIFIER, "API Key")
    app_key = siemplify.extract_configuration_param(IDENTIFIER, "APP Key")

    namespace_list = siemplify.extract_action_param("Namespace")
    start_time = siemplify.extract_action_param("Start Time")
    end_time = siemplify.extract_action_param("End Time")

    datadog_manager = DataDogManager(api_key, app_key)

    # Converting the namespace_list into a list
    if namespace_list is not None:
        namespace_list = namespace_list.split(",")

    for namespace in namespace_list:
        namespace = namespace.strip()
        logs = datadog_manager.get_logs(namespace, start_time, end_time)

        if len(logs.get("logs")) > 0:
            siemplify.LOGGER.info(
                f"The Logs for the namespace: {namespace} were fetched successfully.",
            )
            output_message.append(
                f"The Logs for the namespace: {namespace} were fetched successfully.",
            )
            result_value = True
            json_result[f"NameSpace: {namespace}"] = logs

        else:
            siemplify.LOGGER.error(f"The Logs for {namespace} were not found")
            output_message.append(f"The Logs for {namespace} were not found")

    siemplify.result.add_result_json(json_result)

    siemplify.end("\n".join(output_message), result_value)


if __name__ == "__main__":
    main()
