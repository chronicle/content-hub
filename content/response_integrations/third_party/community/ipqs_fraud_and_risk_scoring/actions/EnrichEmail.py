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
    abuse_strictness = int(
        siemplify.extract_action_param(param_name="Abuse Strictness", print_value=True),
    )
    fast = siemplify.extract_action_param(param_name="Fast", print_value=True)
    timeout = siemplify.extract_action_param(
        param_name="Timeout in seconds",
        print_value=True,
    )
    suggest_domain = siemplify.extract_action_param(
        param_name="Suggest Domain",
        print_value=True,
    )
    data_json["abuse_strictness"] = abuse_strictness
    if fast:
        data_json["fast"] = "true"
    if timeout and timeout != "7":
        data_json["timeout"] = int(timeout)
    if suggest_domain:
        data_json["suggest_domain"] = "true"

    ipqs_manager = IPQSManager(siemplify, api_key, data_json)
    ipqs_manager.enrich([EntityTypes.USER])


if __name__ == "__main__":
    main()
