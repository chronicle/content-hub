from __future__ import annotations

import subprocess as sproc


class DataFilter:
    def truncateSensitiveData(inp_string):
        # truncate data like mac address, ip address etc.
        if "ip_address" in inp_string:
            return "ip_address : xxx.xxx.xxx.xxx"
        if "mac_address" in inp_string:
            return "mac_address : XX:XX:XX:XX:XX"
        return inp_string


class ChronicleSOARCommons:
    def extract_action_param(
        siemplify,
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

        input_dictionary = siemplify.parameters

        if not param_name:
            raise Exception("Parameter 'param_name' cannot be None")

        if default_value and not (type(default_value) == input_type):
            raise Exception(
                f"Given default_value of '{default_value}' doesn't match expected type {input_type.__name__}",
            )

        #  =========== start validation logic =====================
        value = input_dictionary.get(param_name)

        if not value:
            if is_mandatory:
                raise Exception(f"Missing mandatory parameter {param_name}")
            value = default_value
            siemplify.LOGGER.info(
                f"Parameter {param_name} was not found or was empty, used default_value"
                f" {default_value} instead",
            )
            return value

        if print_value:
            siemplify.LOGGER.info(f"{param_name}: {value}")

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
                raise Exception(
                    f"Paramater named {param_name}, with value {value} isn't a valid BOOL",
                )
            result = lowered == str(True).lower()
        elif input_type == int:
            result = int(value)
        elif input_type == float:
            result = float(value)
        elif input_type == str:
            result = str(value)
        else:
            raise Exception(
                f"input_type {input_type.__name__} isn't not supported for conversion",
            )

        if remove_whitespaces:
            return result.strip()

        return result


class CommonUtils:
    def collect_command_output(command):
        output = CommonUtils.decode_utf8(sproc.check_output(command))
        return output

    def decode_utf8(encoded_input):
        if encoded_input != None and len(encoded_input) > 0:
            return encoded_input.decode("utf-8")

        return ""
