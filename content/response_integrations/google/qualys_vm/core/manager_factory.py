from __future__ import annotations

from typing import TYPE_CHECKING

from TIPCommon import extract_configuration_param

from .constants import INTEGRATION_NAME
from .QualysVMManager import QualysVMManager

if TYPE_CHECKING:
    from soar_sdk.SiemplifyAction import SiemplifyAction


def create_qualys_manager_from_action(siemplify: SiemplifyAction) -> QualysVMManager:
    """
    Creates QualysVMManager object from SiemplifyAction config params
    """
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
        is_mandatory=True,
        print_value=True,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        print_value=True,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        is_mandatory=True,
        input_type=bool,
        print_value=True,
    )
    x_request_with_header = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="X-Requested-With Header",
        is_mandatory=True,
        print_value=True,
    )
    return QualysVMManager(
        api_root,
        username,
        password,
        verify_ssl,
        siemplify_logger=siemplify.LOGGER,
        x_request_with_header=x_request_with_header,
    )
