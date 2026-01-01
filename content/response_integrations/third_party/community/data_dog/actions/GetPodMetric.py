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
    pod_metric = {}
    api_key = siemplify.extract_configuration_param(IDENTIFIER, "API Key")
    app_key = siemplify.extract_configuration_param(IDENTIFIER, "APP Key")

    pod_namespaces_list = siemplify.extract_action_param("Pod Name")
    start_time = siemplify.extract_action_param("Start Time")
    end_time = siemplify.extract_action_param("End Time")

    datadog_manager = DataDogManager(api_key, app_key)

    # Converting the pod_namespace into a list
    if pod_namespaces_list is not None:
        pod_namespaces_list = pod_namespaces_list.split(",")

    for pod in pod_namespaces_list:
        pod = pod.strip()
        pod_cpu = datadog_manager.get_timeseries_point_metrics_cpu_pod(
            pod,
            start_time,
            end_time,
        )
        if pod_cpu.get("status") == "ok" and len(pod_cpu.get("series")) > 0:
            siemplify.LOGGER.info(
                f"The CPU of the Pod '{pod}'  was fetched successfully.",
            )
            pod_metric["pod_CPU"] = pod_cpu
            result_value = True
            output_message.append(
                f"The CPU of the Pod '{pod}' was fetched successfully.",
            )
        else:
            siemplify.LOGGER.info(f"The CPU of the Pod '{pod}' wasn't found.")
            output_message.append(f"The CPU of the Pod '{pod}' wasn't found.")

        pod_memory = datadog_manager.get_timeseries_point_metrics_memory_pod(
            pod,
            start_time,
            end_time,
        )
        if pod_memory.get("status") == "ok" and len(pod_memory.get("series")) > 0:
            siemplify.LOGGER.info(
                f"The memory of the Pod '{pod}' was fetched successfully.",
            )
            pod_metric["pod_memory"] = pod_memory
            result_value = True
            output_message.append(
                f"The memory of the Pod:'{pod}' was fetched successfully.",
            )

        else:
            siemplify.LOGGER.info(f"The memory of the Pod '{pod}' wasn't fetched.")
            output_message.append(f"The memory of the Pod '{pod}' wasn't fetched.")

        pod_processes = datadog_manager.get_processes_by_tags(f"pod_name:{pod}")
        pod_metric["pod_processes"] = pod_processes
        if bool(pod_processes):
            siemplify.LOGGER.info(
                f"The processes of the pod '{pod}' were retrieved successfully",
            )
            output_message.append(
                f"The processes of the pod '{pod}' were retrieved successfully",
            )

        else:
            siemplify.LOGGER.info(f"The processes of the Pod '{pod}' wasn't fetched.")
            output_message.append(f"The processes of the Pod '{pod}' wasn't fetched.")

        json_result[f"pod_name_{pod}"] = pod_metric
    siemplify.result.add_result_json(json_result)

    siemplify.end("\n".join(output_message), result_value)


if __name__ == "__main__":
    main()
