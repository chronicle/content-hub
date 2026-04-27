from __future__ import annotations
from soar_sdk.SiemplifyAction import SiemplifyAction
from TIPCommon import extract_script_param
from .NetskopeManager import NetskopeManager
from .NetskopeManagerV2 import NetskopeManagerV2


class NetskopeManagerFactory:
    @staticmethod
    def get_manager(
        siemplify: SiemplifyAction, api_version: str
    ) -> NetskopeManager | NetskopeManagerV2:
        """Get Netskope manager instance based on API version.

        Args:
            siemplify (SiemplifyAction): The Siemplify action instance.
            api_version (str): The API version (v1 or v2).

        Returns:
            NetskopeManager | NetskopeManagerV2: The manager instance.
        """
        config = siemplify.get_configuration("Netskope")

        server_address: str = extract_script_param(
            siemplify,
            input_dictionary=config,
            param_name="Api Root",
            is_mandatory=True,
            print_value=True,
        )
        verify_ssl: bool = extract_script_param(
            siemplify,
            input_dictionary=config,
            param_name="Verify SSL",
            is_mandatory=True,
            default_value=True,
            input_type=bool,
            print_value=True,
        )

        if api_version.lower() == "v1":
            api_key: str = extract_script_param(
                siemplify,
                input_dictionary=config,
                param_name="V1 Api Key",
                is_mandatory=True,
            )
            return NetskopeManager(server_address, api_key, verify_ssl=verify_ssl)
        if api_version.lower() == "v2":
            v2_api_token: str | None = extract_script_param(
                siemplify,
                input_dictionary=config,
                param_name="V2 Api Key",
                is_mandatory=False,
            )
            client_id: str | None = extract_script_param(
                siemplify,
                input_dictionary=config,
                param_name="Client ID",
                is_mandatory=False,
            )
            client_secret: str | None = extract_script_param(
                siemplify,
                input_dictionary=config,
                param_name="Client Secret",
                is_mandatory=False,
            )

            if not v2_api_token and not (client_id and client_secret):
                raise ValueError(
                    "Either V2 Api Key or Client ID/Client Secret must be provided"
                )

            return NetskopeManagerV2(
                api_root=server_address,
                v2_api_token=v2_api_token,
                client_id=client_id,
                client_secret=client_secret,
                verify_ssl=verify_ssl,
            )
        raise ValueError(f"Unsupported API version: {api_version}")
