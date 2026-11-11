from __future__ import annotations

from typing import TYPE_CHECKING
from open_search.core import constants
from open_search.core.data_models import IntegrationParameters
from open_search.core.exceptions import OpenSearchManagerError
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob
from TIPCommon.extraction import extract_script_param

if TYPE_CHECKING:
    from TIPCommon.types import ChronicleSOAR


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    """
    Extract auth params for the manager.
    Args:
         soar_sdk_object: ChronicleSOAR SDK object.
    Returns:
        IntegrationParameters: IntegrationParameters object containing
         connection details.
    """
    sdk_class_name = type(soar_sdk_object).__name__

    if sdk_class_name == SiemplifyAction.__name__:
        input_dictionary = soar_sdk_object.get_configuration(constants.INTEGRATION_NAME)
    elif sdk_class_name in (
        SiemplifyConnectorExecution.__name__,
        SiemplifyJob.__name__,
    ):
        input_dictionary = soar_sdk_object.parameters
    else:
        raise OpenSearchManagerError(
            "Provided SOAR instance is not supported for parameter extraction! "
            f"Provided type: {sdk_class_name}."
        )

    return IntegrationParameters(
        server=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Server Address",
            is_mandatory=True,
            print_value=True,
        ),
        username=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Username",
        ),
        password=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Password",
        ),
        jwt_token=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="JWT Token",
        ),
        authenticate=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Authenticate",
            input_type=bool,
            default_value=False,
        ),
        verify_ssl=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="Verify SSL",
            input_type=bool,
            default_value=False,
        ),
        ca_certificate_file=extract_script_param(
            soar_sdk_object,
            input_dictionary=input_dictionary,
            param_name="CA Certificate File",
        ),
    )
