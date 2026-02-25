from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction

from ..core.constants import INTEGRATION_NAME, LIST_DOMAIN_INFRATAGS_SCRIPT_NAME
from ..core.silent_push_manager import SilentPushManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = LIST_DOMAIN_INFRATAGS_SCRIPT_NAME

    # Extract Integration config
    server_url = siemplify.extract_configuration_param(
        INTEGRATION_NAME, "Silent Push Server"
    )
    api_key = siemplify.extract_configuration_param(INTEGRATION_NAME, "API Key")

    domain = siemplify.extract_action_param("Domain", print_value=True)
    cluster = siemplify.extract_action_param("Cluster", print_value=True)
    mode = siemplify.extract_action_param("Mode", print_value=True)
    arg_match = siemplify.extract_action_param("Match", print_value=True)
    as_of = siemplify.extract_action_param("As Of", print_value=True)
    origin_uid = siemplify.extract_action_param("Origin UID", print_value=True)
    use_get = siemplify.extract_action_param("Use Get", print_value=True)
    cluster = cluster.lower() == "true"

    domains: list = domain.split(",")
    if not domains and not use_get:
        raise ValueError('"domains" argument is required when using POST.')

    try:
        sp_manager = SilentPushManager(server_url, api_key, logger=siemplify.LOGGER)
        raw_response = sp_manager.list_domain_infratags(
            domains,
            cluster,
            mode=mode,
            arg_match=arg_match,
            as_of=as_of,
            origin_uid=origin_uid,
        )

        response_mode = raw_response.get("response", {}).get("mode", "").lower()
        if response_mode and response_mode != mode:
            raise ValueError(f"Expected mode '{mode}' but got '{response_mode}'")

        infratags = raw_response.get("response", {}).get("infratags", [])
        tag_clusters = raw_response.get("response", {}).get("tag_clusters", [])

        if not infratags:
            error_message = f"No data found for domain: {domain}"
            siemplify.LOGGER.error(error_message)
            status = EXECUTION_STATE_FAILED
            siemplify.end(error_message, "false", status)

        if cluster:
            tag_clusters_res = format_tag_clusters(tag_clusters)
            output_message = (
                f"infratags: {infratags}, Domain Tag Clusters: {tag_clusters_res}"
            )
            siemplify.result.add_result_json(
                {
                    "infratags": infratags,
                    "Domain Tag Clusters": tag_clusters_res,
                }
            )
        else:
            output_message = f"infratags: {infratags}"
            siemplify.result.add_result_json({"infratags": infratags})
        status = EXECUTION_STATE_COMPLETED
        result_value = True

    except Exception as error:
        result_value = False
        status = EXECUTION_STATE_FAILED
        output_message = (
            f"Failed to retrieve data of domain :{domain} "
            f"for {INTEGRATION_NAME} server! Error: {error}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(error)

    for entity in siemplify.target_entities:
        print(entity.identifier)

    siemplify.LOGGER.info(
        "\n  status: {}\n  result_value: {}\n  output_message: {}".format(
            status, result_value, output_message
        )
    )
    siemplify.end(output_message, result_value, status)


def format_tag_clusters(tag_clusters: list):
    """
    Helper function to format the tag clusters output.

    Args:
        tag_clusters (list): List of domain tag clusters.

    Returns:
        str: Formatted table output for tag clusters.
    """
    if not tag_clusters:
        return "\n\n**No tag cluster data returned by the API.**"

    cluster_details = [
        {"Cluster Level": key, "Details": value}
        for cluster in tag_clusters
        for key, value in cluster.items()
    ]
    return cluster_details


if __name__ == "__main__":
    main()
