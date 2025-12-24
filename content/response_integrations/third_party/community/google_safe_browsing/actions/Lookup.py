from __future__ import annotations

from pysafebrowsing import SafeBrowsing
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

IDENTIFIER = "Google Safe Browsing"


@output_handler
def main():
    siemplify = SiemplifyAction()

    api_key = siemplify.extract_configuration_param(IDENTIFIER, "Api Key")
    url = siemplify.extract_action_param(param_name="Url", is_mandatory=True)

    safe_browsing_manager = SafeBrowsing(api_key)
    res = safe_browsing_manager = safe_browsing_manager.lookup_urls([url])
    is_malicious_str = res[url]["malicious"]
    siemplify.result.add_result_json(res)

    is_malicious_bool = bool(is_malicious_str)

    if is_malicious_bool:
        siemplify.end("The URL was found malicious", is_malicious_bool)
    else:
        siemplify.end("The URL was not found malicious", is_malicious_bool)


if __name__ == "__main__":
    main()
