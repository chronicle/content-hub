"""
Action script for Domain Tools - Ping.

Test Connectivity
"""

from __future__ import annotations

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import *  # noqa: F403
from soar_sdk.SiemplifyUtils import output_handler

from ..core.DomainToolsManager import DomainToolsManager

URL = EntityTypes.URL
HOST = EntityTypes.HOSTNAME


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("DomainTools")
    username = conf["Username"]
    key = conf["ApiToken"]
    verify_ssl = conf["Verify SSL"]
    dt_manager = DomainToolsManager(username, key, verify_ssl=verify_ssl)

    output_message = "Connection Established" if dt_manager else "Connection Failed"
    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
