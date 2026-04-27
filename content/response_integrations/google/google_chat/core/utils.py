from __future__ import annotations
import json


def parse_string_to_dict(string, err_msg="Invalid JSON type"):
    """
    Parse json string to dict
    :param string: string to parse
    :param err_msg: err message
    :return: {dict} parsed dict
    """
    try:
        return json.loads(string)
    except Exception:
        raise Exception(err_msg)


def validate_positive_integer(number, err_msg="Limit parameter should be positive"):
    if number <= 0:
        raise Exception(err_msg)
