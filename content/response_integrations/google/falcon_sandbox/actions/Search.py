from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import dict_to_flat
from ..core.FalconSandboxManager import FalconSandboxManager
import json

SCRIPT_NAME = "Falcon Sandbox - Search"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    configurations = siemplify.get_configuration("FalconSandbox")
    server_address = configurations["Api Root"]
    key = configurations["Api Key"]

    file_name = siemplify.parameters.get("File Name")
    file_type = siemplify.parameters.get("File Type")
    file_type_desc = siemplify.parameters.get("File Type Description")
    verdict = siemplify.parameters.get("Verdict")
    av_detect = siemplify.parameters.get("AV Multiscan Range")
    vx_family = siemplify.parameters.get("AV Family Substring")
    tag = siemplify.parameters.get("Hashtag")
    port = siemplify.parameters.get("Port")
    host = siemplify.parameters.get("Host")
    domain = siemplify.parameters.get("Domain")
    url = siemplify.parameters.get("HTTP Request Substring")
    similat_to = siemplify.parameters.get("Similar Samples")
    context = siemplify.parameters.get("Sample Context")

    falcon_manager = FalconSandboxManager(server_address, key)
    siemplify.LOGGER.info("Connected to Hybrid Analysis")

    results = falcon_manager.search(
        file_name,
        file_type,
        file_type_desc,
        verdict,
        av_detect,
        vx_family,
        tag,
        port,
        host,
        domain,
        url,
        similat_to,
        context,
    )

    if results:
        flat_results = []

        # Flatten results
        for result in results:
            flat_results.append(dict_to_flat(result))

        csv_output = falcon_manager.construct_csv(flat_results)

        siemplify.result.add_data_table("Falcon Search Results", csv_output)

        output_message = f"Found {len(results)} results"

    else:
        output_message = "No results found"

    siemplify.result.add_result_json(json.dumps(results))
    siemplify.end(output_message, json.dumps(results))


if __name__ == "__main__":
    main()
