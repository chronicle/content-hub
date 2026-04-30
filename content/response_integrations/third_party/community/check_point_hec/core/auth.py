from TIPCommon.extraction import extract_script_param
from TIPCommon.types import ChronicleSOAR
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyJob import SiemplifyJob

from .constants import INTEGRATION_IDENTIFIER
from .data_models import IntegrationParameters
from .exceptions import CheckPointHECIntegrationError


def build_auth_params(soar_sdk_object: ChronicleSOAR) -> IntegrationParameters:
    sdk_class = type(soar_sdk_object).__name__
    if sdk_class == SiemplifyAction.__name__:
        input_dictionary = soar_sdk_object.get_configuration(INTEGRATION_IDENTIFIER)
    elif sdk_class in (
            SiemplifyConnectorExecution.__name__,
            SiemplifyJob.__name__,
    ):
        input_dictionary = soar_sdk_object.parameters
    else:
        raise CheckPointHECIntegrationError(
            f"Provided SOAR instance is not supported! type: {sdk_class}.",
        )

    host = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Host",
    )
    client_id = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Client ID",
    )
    client_secret = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Client Secret",
    )
    verify_ssl = extract_script_param(
        soar_sdk_object,
        input_dictionary=input_dictionary,
        param_name="Verify SSL",
        default_value=True,
        input_type=bool,
        is_mandatory=True,
        print_value=True,
    )

    return IntegrationParameters(
        host=host,
        client_id=client_id,
        client_secret=client_secret,
        verify_ssl=verify_ssl,
        is_infinity='cloudinfra' in host
    )
