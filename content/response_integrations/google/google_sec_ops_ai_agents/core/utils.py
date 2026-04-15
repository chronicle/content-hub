from __future__ import annotations

import os
from typing import TYPE_CHECKING
from . import consts
from ..core.data_models import IntegrationParameters
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.utils import BASE_1P_SDK_CONTROLLER_VERSION

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR


def get_google_secops_api_uri(soar_sdk_object: ChronicleSOAR) -> str:
    """Get Google SecOps URI.

    Args:
        soar_sdk_object: The SOAR SDK object.

    Returns:
        str: Google SecOps URI.
    """
    sdk_config = soar_sdk_object.sdk_config
    domain = sdk_config.domain
    project = os.getenv("ONE_PLATFORM_URL_PROJECT")
    location = os.getenv("ONE_PLATFORM_URL_LOCATION")
    instance = os.getenv("ONE_PLATFORM_URL_INSTANCE")

    return (
        f"https://{domain}/{BASE_1P_SDK_CONTROLLER_VERSION}/"
        f"projects/{project}/locations/{location}/instances/{instance}"
    )


def build_integration_params(
    soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """Build integration parameters from the SOAR SDK object.

      Args:
          soar_sdk_object: The SOAR SDK object.

      Returns:
          The integration parameters.
      """

    # TODO: use get_sdk_api_uri when featSdkDataplane is 100% true
    api_root = get_google_secops_api_uri(soar_sdk_object)
    verify_ssl: bool = extract_configuration_param(
        soar_sdk_object,
        provider_name=consts.INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        print_value=True,
    )
    return IntegrationParameters(
        api_root=api_root,
        verify_ssl=verify_ssl,
    )
