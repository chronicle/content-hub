from __future__ import annotations

from pysafebrowsing import SafeBrowsing
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

IDENTIFIER = "Google Safe Browsing"


@output_handler
def main():
    siemplify = SiemplifyAction()

    api_key = siemplify.extract_configuration_param(IDENTIFIER, "Api Key")

    safe_browsing_manager = SafeBrowsing(api_key)
    safe_browsing_manager = safe_browsing_manager.lookup_urls(
        ["http://malware.testing.google.test/testing/malware/"],
    )

    siemplify.end("Connected successfully", True)


if __name__ == "__main__":
    main()
