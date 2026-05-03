from __future__ import annotations
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.CyberarkVaultManager import CyberarkManager
from ..core.CyberarkVaultManager import PasswordVaultManager


@output_handler
def main():
    siemplify = SiemplifyAction()
    conf = siemplify.get_configuration("CyberArkVault")
    username = conf["Username"]
    password = conf["Password"]
    use_ssl = conf.get("Use SSL", "False").lower() == "true"
    api_root = conf["Api Root"]
    api_root_password = conf["Password Vault Api Root"]
    app_id = conf["Application ID"]

    cyberark_manager = CyberarkManager(username, password, api_root, use_ssl)
    is_connect = cyberark_manager.test_connectivity()

    # Test Password Component
    password_manager = PasswordVaultManager(api_root_password, app_id, use_ssl)
    password_manager.test_connectivity("Mock Safe", "Mock Folder")

    # If no exception occur - then connection is successful
    output_message = "Connected successfully."

    siemplify.end(output_message, "true")


if __name__ == "__main__":
    main()
