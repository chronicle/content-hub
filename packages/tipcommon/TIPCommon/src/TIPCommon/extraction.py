# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import SiemplifyVaultUtils

from .data_models import ConnectorParameter, ConnectorParamTypes
from .utils import clean_result
from .validation import ParameterValidator


def extract_script_param(
    siemplify,
    input_dictionary,
    param_name,
    default_value=None,
    input_type=str,
    is_mandatory=False,
    print_value=False,
    remove_whitespaces=True,
):
    """Extracts a script parameter from an input dictionary.

    Args:
        siemplify: The Siemplify object.
        input_dictionary (dict): The input dictionary.
        param_name (str): The parameter name.
        default_value (Any): The default value.
        input_type (type): The input type.
        is_mandatory (bool): Whether the parameter is mandatory.
        print_value (bool): Whether to print the value.
        remove_whitespaces (bool): Whether to remove whitespaces from the value.

    Returns:
        The extracted value.

    """
    # internal param validation:
    if not siemplify:
        raise Exception("Parameter 'siemplify' cannot be None")

    if not param_name:
        raise Exception("Parameter 'param_name' cannot be None")

    if default_value and not (type(default_value) == input_type):
        raise Exception(
            f"Given default_value of '{default_value}' doesn't match expected type {input_type.__name__}"
        )

    #  =========== start validation logic =====================

    context = getattr(siemplify, "context", None)
    vault_settings = getattr(context, "vault_settings", None) if context else None
    vault_settings = vault_settings or getattr(siemplify, "vault_settings", None)

    if vault_settings is None:
        value = input_dictionary.get(param_name)
    else:
        value = SiemplifyVaultUtils.extract_vault_param(
            input_dictionary.get(param_name),
            vault_settings
        )

    if not value:
        if is_mandatory:
            raise Exception(f"Missing mandatory parameter {param_name}")
        value = default_value
        siemplify.LOGGER.info(
            f"Parameter {param_name} was not found or was empty, used default_value {default_value} instead"
        )
        return value

    if print_value:
        siemplify.LOGGER.info("{}: {}".format(param_name, value))

    # None values should not be converted.
    if value is None:
        return None

    if input_type == bool:
        lowered = str(value).lower()
        valid_lowered_bool_values = [
            str(True).lower(),
            str(False).lower(),
            str(bool(None)).lower(),
        ]  # In Python - None and bool False are the same logicly

        if lowered not in valid_lowered_bool_values:
            raise Exception(f"Paramater named {param_name}, with value {value} isn't a valid BOOL")
        result = lowered == str(True).lower()
    elif input_type == int:
        validator = ParameterValidator(siemplify)
        result = validator.validate_integer(
            param_name=param_name, value=value, print_value=print_value
        )
    elif input_type == float:
        result = float(value)
    elif input_type == str:
        result = str(value)
    elif input_type == unicode:
        result = value
    else:
        raise Exception(f"input_type {input_type.__name__} isn't not supported for conversion")

    if remove_whitespaces:
        return clean_result(result)

    return result


def extract_configuration_param(
    siemplify,
    provider_name,
    param_name,
    default_value=None,
    input_type=str,
    is_mandatory=False,
    print_value=False,
    remove_whitespaces=True,
):
    """Extracts a configuration parameter value from the Integrations's configuration.

    Args:
        siemplify: The Siemplify object.
        provider_name: The Integration Identifier.
        param_name: The parameter name.
        default_value: The default value yo set in case there's no value in the configuration.
        input_type: The input type.
        is_mandatory: Whether the parameter is mandatory.
        print_value: Whether to print the value.
        remove_whitespaces: Whether to remove whitespaces from the value.

    Returns:
        The extracted value.

    """
    if not provider_name:
        raise Exception("provider_name cannot be None/empty")

    configuration = siemplify.get_configuration(provider_name)
    return extract_script_param(
        siemplify=siemplify,
        input_dictionary=configuration,
        param_name=param_name,
        default_value=default_value,
        input_type=input_type,
        is_mandatory=is_mandatory,
        print_value=print_value,
        remove_whitespaces=remove_whitespaces,
    )


def extract_action_param(
    siemplify,
    param_name,
    default_value=None,
    input_type=str,
    is_mandatory=False,
    print_value=False,
    remove_whitespaces=True,
):
    """Extracts an action parameter from the Siemplify object.

    Args:
        siemplify (SiemplifyAction.SiemplifyAction): The Siemplify object.
        param_name (str): The name of the parameter to extract.
        default_value (Any):
            The default value to return if the parameter is not found.
        input_type (type): The type of the parameter.
        is_mandatory (bool): Whether the parameter is mandatory.
        print_value (bool): Whether to print the value of the parameter.
        remove_whitespaces (bool):
            Whether to remove whitespaces from the value of the parameter.

    Returns:
        Any: The value of the parameter.

    """
    return extract_script_param(
        siemplify=siemplify,
        input_dictionary=siemplify.parameters,
        param_name=param_name,
        default_value=default_value,
        input_type=input_type,
        is_mandatory=is_mandatory,
        print_value=print_value,
        remove_whitespaces=remove_whitespaces,
    )


def extract_connector_param(
    siemplify,
    param_name,
    default_value=None,
    input_type=str,
    is_mandatory=False,
    print_value=False,
    remove_whitespaces=True,
):
    """Extracts a connector parameter from the Siemplify object.

    Args:
        siemplify (SiemplifyConnectors.SiemplifyConnectorExecution):
            The Siemplify object.
        param_name (str): The name of the parameter to extract.
        default_value (Any, optional): The default value to return if the parameter is not found.
        input_type (type, optional): The type of the parameter.
        is_mandatory (bool, optional): Whether the parameter is mandatory.
        print_value (bool, optional): Whether to print the value of the parameter.
        remove_whitespaces (bool, optional): Whether to remove whitespaces from the value of the parameter.

    Returns:
        Any: The value of the parameter.

    """
    return extract_script_param(
        siemplify=siemplify,
        input_dictionary=siemplify.parameters,
        param_name=param_name,
        default_value=default_value,
        input_type=input_type,
        is_mandatory=is_mandatory,
        print_value=print_value,
        remove_whitespaces=remove_whitespaces,
    )


def extract_job_param(
    siemplify,
    param_name,
    default_value=None,
    input_type=str,
    is_mandatory=False,
    print_value=False,
    remove_whitespaces=True,
):
    """Extracts a connector parameter from the Siemplify object.

    Args:
        siemplify (SiemplifyJob.SiemplifyJob): The SiemplifyJob object.
        param_name (str): The name of the parameter to extract.
        default_value (Any, optional):
            The default value to return if the parameter is not found.
        input_type (type, optional): The type of the parameter.
        is_mandatory (bool, optional): Whether the parameter is mandatory.
        print_value (bool, optional): Whether to print the value of the parameter.
        remove_whitespaces (bool, optional):
            Whether to remove whitespaces from the value of the parameter.

    Returns:
        Any: The value of the parameter.

    """
    return extract_script_param(
        siemplify=siemplify,
        input_dictionary=siemplify.parameters,
        param_name=param_name,
        default_value=default_value,
        input_type=input_type,
        is_mandatory=is_mandatory,
        print_value=print_value,
        remove_whitespaces=remove_whitespaces,
    )


def get_connector_detailed_params(siemplify):
    """Gets the detailed parameters for a connector.

    Args:
        siemplify (SiemplifyConnectors.SiemplifyConnectorExecution):
            The Siemplify object.

    Returns:
        list: A list of ConnectorParameter objects.

    """
    if not siemplify:
        raise Exception("Parameter 'siemplify' cannot be None")
    try:
        context = siemplify.context
        connector_info = context.connector_info
        params = connector_info.params
        detailed_params = [ConnectorParameter(p) for p in params]

        # TODO: (b/288932557)
        # This is workaround for SDK legacy code and should be removed when fixed
        detailed_params = [p for p in detailed_params if p.type != ConnectorParamTypes.SCRIPT]

        return detailed_params

    except AttributeError as e:
        siemplify.LOGGER.error("could not fetch connector detailed parameters: {}".format(e))
        raise
