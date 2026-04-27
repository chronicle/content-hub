from __future__ import annotations
def encode_sensitive_data(message, sensitive_data_arr):
    """
    Encode sensitive data
    :param message: {str} The error message which may contain sensitive data
    :param sensitive_data_arr: {list} The list of sensitive data
    :return: {str} The error message with encoded sensitive data
    """
    for sensitive_data in sensitive_data_arr:
        message = message.replace(sensitive_data, encode_data(sensitive_data))

    return message


def encode_data(sensitive_data):
    """
    Encode string
    :param sensitive_data: {str} String to be encoded
    :return: {str} Encoded string
    """
    if len(sensitive_data) > 1:
        return f"{sensitive_data[0]}...{sensitive_data[-1]}"
    return sensitive_data
