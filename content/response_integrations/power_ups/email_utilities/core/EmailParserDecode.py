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

from __future__ import annotations

import datetime
import email
import email.errors
import email.header
import email.policy
import email.utils
import json
import logging
import typing

import dateutil.parser

from . import EmailParserRegex

try:
    try:
        import cchardet as chardet
    except ImportError:
        import chardet
except ImportError:
    chardet = None

logger = logging.getLogger(__name__)


def decode_field(field: str) -> str:
    """Try to get the specified field using the Header module.

    If there is also an associated encoding, try to decode the
    field and return it, else return a specified default value.

    Args:
        field (str): String to decode

    Returns:
        str: Clean encoded strings

    """
    try:
        decoded = email.header.decode_header(field)
    except email.errors.HeaderParseError:
        return field

    string = ""

    for text, charset in decoded:
        if charset:
            string += decode_string(text, charset)
        # @TODO might be an idea to check with chardet here
        elif isinstance(text, bytes):
            string += text.decode("utf-8", "ignore")
        else:
            string += text

    return string


def decode_string(string: bytes, encoding: str | None) -> str:
    """Try anything possible to parse an encoded bytes string and return the result.

    We do this using the encoding hint, if this fails, we try to detect the correct
    encoding using the chardet module, if that failed we try latin-1, utf-8 and
    as a last resort ascii.
    In any case we always return something.

    Args:
        string (bytes): The bytes string to be decoded.
        encoding (str, optional): An optional encoding hint.

    Returns:
        str: A decoded form of the string.

    """
    if string == b"":
        return ""

    if encoding is not None:
        try:
            return string.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            pass

    if chardet:
        enc = chardet.detect(string)
        if not (enc["confidence"] is None or enc["encoding"] is None) and not (
            enc["confidence"] == 1 and enc["encoding"] == "ascii"
        ):
            value = string.decode(enc["encoding"], "replace")
        else:
            value = string.decode("ascii", "replace")
    else:
        text = ""

        for e in ("latin1", "utf-8"):
            try:
                text = string.decode(e)
            except UnicodeDecodeError:
                pass
            else:
                break

        value = string.decode("ascii", "ignore") if text == "" else text

    return value


def workaround_bug_27257(msg: email.message.Message, header: str) -> list[str]:
    """Function to work around bug 27257 and just tries its best using \
    the compat32 policy to extract any meaningful information, i.e. \
    e-mail addresses.

    Args:
        msg (email.message.Message): An e-mail message object.
        header (str): The header field to decode.

    Returns:
        list: Returns a list of strings which represent e-mail addresses.

    """
    return_value: list[str] = []

    for value in workaround_field_value_parsing_errors(msg, header):
        if value != "":
            m = EmailParserRegex.regex.email_regex.findall(value)
            if m:
                return_value += list(set(m))

    return return_value


def workaround_field_value_parsing_errors(
    msg: email.message.Message,
    header: str,
) -> list[str]:
    """Function to work around field value parsing errors by trying a best effor parsing using \
    the compat32 policy to extract any meaningful information.

    Args:
        msg (email.message.Message): An e-mail message object.
        header (str): The header field to decode.

    Returns:
        list: Return an extracted list of strings.

    """
    new_policy = None if msg.policy == email.policy.compat32 else msg.policy  # type: ignore[attr-defined]

    msg.policy = email.policy.compat32  # type: ignore[attr-defined]

    return_value = [value for value in msg.get_all(header, []) if value != ""]

    if new_policy is not None:
        msg.policy = new_policy  # type: ignore[attr-defined]

    return return_value


def robust_string2date(line: str) -> datetime.datetime:
    """Parses a date string to a datetime.datetime object using different methods.

    It is guaranteed to always return a valid datetime.datetime object.
    If first tries the built-in email module method for parsing the date according
    to related RFC's.
    If this fails it returns, dateutil is tried. If that fails as well, a datetime.datetime
    object representing "1970-01-01 00:00:00 +0000" is returned.
    In case there is no timezone information in the parsed date, we set it to UTC.

    Args:
        line (str): A string which should be parsed.

    Returns:
        datetime.datetime: Returns a datetime.datetime object.

    """
    # "." -> ":" replacement is for fixing bad clients (e.g. outlook express)
    default_date = "1970-01-01T00:00:00+0000"

    # if the input is empty, we return a default date
    if line == "":
        return dateutil.parser.parse(default_date)

    try:
        date_ = email.utils.parsedate_to_datetime(line)
    except (TypeError, ValueError, LookupError):
        logger.debug('Exception parsing date "%s"', line, exc_info=True)

        try:
            date_ = dateutil.parser.parse(line)
        except (AttributeError, ValueError, OverflowError):
            # Now we are facing an invalid date.
            return dateutil.parser.parse(default_date)

    if date_.tzname() is None:
        return date_.replace(tzinfo=datetime.UTC)

    return date_


def json_serial(obj: typing.Any) -> str | None:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime.datetime):
        return obj.astimezone(datetime.UTC).isoformat() if obj.tzinfo is not None else obj.isoformat()

    msg = f"Type not serializable - {type(obj)!s}"
    raise TypeError(msg)


def export_to_json(parsed_msg: dict, sort_keys: bool = False) -> str:
    """Function to convert a parsed e-mail dict to a JSON string.

    Args:
        parsed_msg (dict): The parsed e-mail dict which is the result of
                           one of the decode_email functions.
        sort_keys (bool, optional): If True, sorts the keys in the JSON output.
                                    Default: False.

    Returns:
        str: Returns the JSON string.

    """
    return json.dumps(parsed_msg, default=json_serial, sort_keys=sort_keys, indent=2)
