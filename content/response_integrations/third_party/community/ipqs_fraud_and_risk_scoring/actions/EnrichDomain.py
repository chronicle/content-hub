from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler

from ..core.IPQSManager import PROVIDER, IPQSManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    data_json = {}
    api_key = siemplify.extract_configuration_param(PROVIDER, "API Key")
    strictness = int(
        siemplify.extract_action_param(param_name="Strictness", print_value=True),
    )
    fast = siemplify.extract_action_param(param_name="Fast", print_value=True)
    data_json["strictness"] = strictness
    if fast:
        data_json["fast"] = "true"
    ipqs_manager = IPQSManager(siemplify, api_key, data_json)
    ipqs_manager.enrich([EntityTypes.HOSTNAME])


if __name__ == "__main__":
    main()
