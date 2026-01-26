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

"""validation
==========

This module contains the ``Validator`` class for validating various types of parameters.
Each method takes a parameter name, a value, and optional keyword arguments.
The functions raise a ParameterValidationError if the parameter value is invalid.

The validation functions return the provided value in its validated type.

Usage Example::
    validator  = ParameterValidator(siemplify)   # siemplify SDK object
    validated_value = validator.validate_float(param_name='something', value='3.7')
    print(validated_value)  # 3.7 as float

    validated_value = validator.validate_int(param_name='something', validated_value)
    print(validated_value)  # 3 as integer
"""

from __future__ import annotations

import json

from .exceptions import ParameterValidationError
from .transformation import (
    convert_comma_separated_to_list,
    convert_list_to_comma_string,
)
from .types import ChronicleSOAR
from .utils import is_valid_email

empty = object()


class ParameterValidator:
    """Class that contains parameters validation functions"""

    _WARN_MSG_WITH_VALUE = (
        "Invalid parameter: {param_name}, "
        "value provided: {value}, "
        "Issue: {msg}, "
        "Default value {default_value} will be used instead."
    )
    _WARN_MSG_WITHOUT_VALUE = (
        "Invalid parameter: {param_name}, "
        "Issue: {msg}, "
        "Default value {default_value} will be used instead."
    )

    def __init__(self, siemplify: ChronicleSOAR) -> None:
        self.logger = siemplify.LOGGER

    @classmethod
    def _get_warning(cls, param_name: str, value, error_msg, default_value, print_value=True):
        """Gets a formatted warning message for failed validation check

        Args:
            param_name: The name of the parameter
            value: The value of the parameter
            error_msg: The error message
            default_value: The default value to use instead of the original value
            print_value: Flag to set if parameter value to be shown on UI and log or not.

        Returns:
            formatted warning string

        """
        if print_value:
            return cls._WARN_MSG_WITH_VALUE.format(
                param_name=param_name, value=value, msg=error_msg, default_value=default_value
            )
        return cls._WARN_MSG_WITHOUT_VALUE.format(
            param_name=param_name, msg=error_msg, default_value=default_value
        )

    def _log_warning(self, param_name, value, error_msg, default_value, print_value=True):
        """Logs a formatted warning message for failed validation check

        Args:
            param_name: The name of the parameter
            value: The value of the parameter
            error_msg: The error message
            default_value: The default value to use instead of the original value

        """
        self.logger.warning(
            self._get_warning(
                param_name=param_name,
                value=value,
                error_msg=error_msg,
                default_value=default_value,
                print_value=print_value,
            )
        )

    def validate_json(
        self,
        param_name,
        json_string,
        default_value=empty,
        print_value=True,
        print_error=False,
        **kwargs,
    ):
        """Validate a JSON string.

        Args:
            param_name (str): The name of the parameter.
            json_string (str): The JSON string to validate.
            default_value (any): The default value to return in case of validation error
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message
            **kwrags (dict): Keyword arguments for the `json.loads()` function.

        Returns:
            The parsed JSON object.

        Raises:
            ParameterValidationError: If the JSON string is invalid.

        """
        try:
            res = json.loads(json_string, **kwargs)
            return res
        except Exception as err:
            err_msg = "The JSON structure is invalid"
            if default_value is not empty:
                self._log_warning(
                    param_name=param_name,
                    value=json_string,
                    error_msg=err_msg,
                    default_value=default_value,
                    print_value=print_value,
                )
                return default_value
            raise ParameterValidationError(
                param_name,
                json_string,
                err_msg,
                err,
                print_value=print_value,
                print_error=print_error,
            ) from err

    def validate_ddl(
        self,
        param_name,
        value,
        ddl_values,
        case_sensitive=False,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validate a DDL string.

        Args:
            param_name (str): The name of the parameter.
            value (str): The DDL string to validate.
            ddl_values (list): A list of valid DDL values.
            case_sensitive (bool): Whether to perform case-sensitive validation.
            default_value (any): The default value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message


        Returns:
            The validated DDL string.

        Raises:
            ParameterValidationError: If the DDL string is invalid.

        """
        _value = value
        if not case_sensitive:
            _value = value.lower()
            ddl_values = [val.lower() for val in ddl_values]
        if _value not in ddl_values:
            err_msg = (
                f"The provided value must be one of the following: "
                f"{convert_list_to_comma_string(ddl_values)}"
            )
            if default_value is not empty:
                self._log_warning(
                    param_name=param_name,
                    value=value,
                    error_msg=err_msg,
                    default_value=default_value,
                    print_value=print_value,
                )
                return default_value
            raise ParameterValidationError(
                param_name,
                value,
                err_msg,
                print_value=print_value,
                print_error=print_error,
            )
        return value

    def validate_csv(
        self,
        param_name,
        csv_string,
        delimiter=",",
        possible_values=None,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates a comma-separated value (CSV) string.

        Args:
            param_name (str): The name of the parameter.
            csv_string (str): The comma-separated value (CSV) string to validate.
            delimiter (str): The character that separates the values in the CSV string.
            possible_values (list): A list of possible values.
            default_value (any): The default value to return in case of validation error
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the CSV string is not valid.

        Returns:
            list: The list of values in the CSV string.

        """
        try:
            res = convert_comma_separated_to_list(csv_string, delimiter=delimiter)
            if possible_values is not None:
                assert all(val in possible_values for val in res)
            return res
        except AssertionError as err:
            raise ParameterValidationError(
                param_name,
                csv_string,
                f"Possible values: {convert_list_to_comma_string(possible_values)}",
                err,
                print_value=print_value,
                print_error=print_error,
            ) from err
        except Exception as err:
            if default_value is not empty:
                self._log_warning(
                    param_name=param_name,
                    value=csv_string,
                    error_msg=str(err),
                    default_value=default_value,
                    print_value=print_value,
                )
                return default_value
            raise ParameterValidationError(
                param_name,
                csv_string,
                "Invalid CSV payload",
                err,
                print_value=print_value,
                print_error=print_error,
            ) from err

    def validate_float(
        self,
        param_name,
        value,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates a float string.

        Args:
            param_name (str): The name of the parameter.
            value (str | float): The value to validate.
            default_value (any): The default value to return in case of validation error
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the value is not a float.

        Returns:
            float: The validated value.

        """
        try:
            _value = float(value)
            return _value
        except Exception as err:
            err_msg = "The value must be a number"
            if default_value is not empty:
                self._log_warning(
                    param_name=param_name,
                    value=value,
                    error_msg=str(err),
                    default_value=default_value,
                    print_value=print_value,
                )
                return default_value
            raise ParameterValidationError(
                param_name,
                value,
                err_msg,
                err,
                print_value=print_value,
                print_error=print_error,
            ) from err

    def validate_integer(
        self,
        param_name,
        value,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates an integer string.

        Args:
            param_name (str): The name of the parameter.
            value (str | int): The value to validate.
            default_value (any): The default value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the value is not an integer.

        Returns:
            int: The validated value.

        """
        try:
            _value = int(value)
            return _value
        except Exception as err:
            err_msg = "The value must be an integer"
            if default_value is not empty:
                self._log_warning(
                    param_name=param_name,
                    value=value,
                    error_msg=err_msg,
                    default_value=default_value,
                    print_value=print_value,
                )
                return default_value
            raise ParameterValidationError(
                param_name,
                value,
                err_msg,
                err,
                print_value=print_value,
                print_error=print_error,
            ) from err

    def validate_upper_limit(
        self,
        param_name,
        value,
        limit,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates an upper limit string.

        Args:
            param_name (str): The name of the parameter.
            value (str | int): The value to validate.
            limit (int): The upper limit.
            default_value (any): The default value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the value is greater than the limit.

        Returns:
            int: The validated value.

        """
        _value = self.validate_integer(param_name, value, default_value)
        if _value > limit:
            err_msg = f"The value can't be greater then {limit}"
            if default_value is not empty:
                self._log_warning(
                    param_name=param_name,
                    value=value,
                    error_msg=err_msg,
                    default_value=default_value,
                    print_value=print_value,
                )
                return default_value
            raise ParameterValidationError(
                param_name,
                value,
                err_msg,
                print_value=print_value,
                print_error=print_error,
            )
        return _value

    def validate_lower_limit(
        self,
        param_name,
        value,
        limit,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates a lower limit string.

        Args:
            param_name (str): The name of the parameter.
            value (str | int): The value to validate.
            limit (int): The lower limit.
            default_value (any): The default value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the value is less than the limit.

        Returns:
            int: The validated value.

        """
        _value = self.validate_integer(param_name, value, default_value)
        if _value < limit:
            err_msg = f"The value can't be lower then {limit}"
            if default_value is not empty:
                self._log_warning(
                    param_name=param_name,
                    value=value,
                    error_msg=err_msg,
                    default_value=default_value,
                    print_value=print_value,
                )
                return default_value
            raise ParameterValidationError(
                param_name,
                value,
                err_msg,
                print_value=print_value,
                print_error=print_error,
            )
        return _value

    def validate_positive(
        self,
        param_name,
        value,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates a positive integer string.

        Args:
            param_name (str): The name of the parameter.
            value (str | int): The value to validate.
            default_value (any): The default value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the value is not positive.

        Returns:
            int: The validated value.

        """
        return self.validate_lower_limit(
            param_name,
            value,
            limit=1,
            default_value=default_value,
            print_value=print_value,
            print_error=print_error,
        )

    def validate_non_negative(
        self,
        param_name,
        value,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates a non-negative integer string.

        Args:
            param_name (str): The name of the parameter.
            value (str | int): The value to validate.
            default_value (any): The default value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the value is negative.

        Returns:
            int: The validated value.

        """
        return self.validate_lower_limit(
            param_name,
            value,
            limit=0,
            default_value=default_value,
            print_value=print_value,
            print_error=print_error,
        )

    def validate_non_zero(
        self,
        param_name,
        value,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates a non-zero integer string.

        Args:
            param_name (str): The name of the parameter.
            value (str | int): The value to validate.
            default_value (any): The default value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the value is zero.

        Returns:
            int: The validated value.

        """
        _value = self.validate_integer(param_name, value, default_value)
        if _value == 0:
            err_msg = "The value can't be 0"
            if default_value is not empty:
                self._log_warning(
                    param_name=param_name,
                    value=value,
                    error_msg=err_msg,
                    default_value=default_value,
                    print_value=print_value,
                )
                return default_value
            raise ParameterValidationError(
                param_name,
                value,
                err_msg,
                print_value=print_value,
                print_error=print_error,
            )
        return _value

    def validate_percentage(
        self,
        param_name,
        value,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates a percentage string.

        Args:
            param_name (str): The name of the parameter.
            value (str | int): The value to validate.
            default_value (any): The default value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the value is not a percentage.

        Returns:
            int: The validated value.

        """
        return self.validate_range(
            param_name,
            value,
            min_limit=0,
            max_limit=100,
            default_value=default_value,
            print_value=print_value,
            print_error=print_error,
        )

    def validate_range(
        self,
        param_name,
        value,
        min_limit,
        max_limit,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates a range string.

        Args:
            param_name (str): The name of the parameter.
            value (str): The value to validate.
            min_limit (int): The lower limit.
            max_limit (int): The upper limit.
            default_value (any): The defaul value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the value is not within the range.

        Returns:
            int: The validated value.

        """
        try:
            self.validate_lower_limit(param_name, value, min_limit, default_value)
            return self.validate_upper_limit(param_name, value, max_limit, default_value)
        except ParameterValidationError as err:
            err_msg = f"The value must be between {min_limit} and {max_limit}"
            if default_value is not empty:
                self._log_warning(
                    param_name=param_name,
                    value=value,
                    error_msg=err_msg,
                    default_value=default_value,
                    print_value=print_value,
                )
                return default_value
            raise ParameterValidationError(
                param_name,
                value,
                err_msg,
                print_value=print_value,
                print_error=print_error,
            ) from err

    def validate_severity(
        self,
        param_name,
        severity,
        min_limit=None,
        max_limit=None,
        possible_values=None,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates a severity string.

        Args:
            param_name (str): The name of the parameter.
            severity (str): The value to validate.
            min_limit (int): The lower limit.
            max_limit (int): The upper limit.
            possible_values (list): A list of possible values.
            default_value (any): The defaul value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the value is not valid.

        Returns:
            int: The validated value.

        """
        try:
            _severity = int(severity)
            if max_limit and min_limit:
                _severity = self.validate_range(
                    param_name,
                    severity,
                    min_limit,
                    max_limit,
                    default_value,
                    print_value=print_value,
                    print_error=print_error,
                )
            elif max_limit:
                _severity = self.validate_upper_limit(
                    param_name,
                    severity,
                    max_limit,
                    default_value,
                    print_value=print_value,
                    print_error=print_error,
                )
            elif min_limit:
                _severity = self.validate_lower_limit(
                    param_name,
                    severity,
                    min_limit,
                    default_value,
                    print_value=print_value,
                    print_error=print_error,
                )
        except ValueError:
            _severity = self.validate_ddl(
                param_name,
                severity,
                ddl_values=possible_values,
                default_value=default_value,
                print_value=print_value,
                print_error=print_error,
            )
        return _severity

    def validate_email(
        self,
        param_name,
        email,
        default_value=empty,
        print_value=True,
        print_error=False,
    ):
        """Validates an email string.

        Args:
            param_name (str): The name of the parameter.
            email (str): The email address string to validate.
            default_value (any): The defaul value to return in case of validation error.
            print_value (bool): Print the param's value as part of the message
            print_error (bool): Print the exception error as part of the message

        Raises:
            ParameterValidationError: If the email address string is not valid.

        Returns:
            str: The email address string.

        """
        _email = email.lower()
        if not is_valid_email(_email):
            err_msg = "Invalid email address"
            if default_value is not empty:
                self._log_warning(
                    param_name=param_name,
                    value=email,
                    error_msg=err_msg,
                    default_value=default_value,
                    print_value=print_value,
                )
                return default_value
            raise ParameterValidationError(
                param_name,
                email,
                err_msg,
                print_value=print_value,
                print_error=print_error,
            )
        return email
