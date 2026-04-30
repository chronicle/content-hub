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
import json
import re
import time
import typing

import dateutil
import six
from json2html import *
from json2table import convert


class DotAccessibleDict:
    reserved = ["self"]

    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            if key in self.reserved:
                # in our case, we have a key in dict which is "self", and it would cause problems while parsing
                key = f"_{key}"
            if type(val) == dict:
                setattr(self, key, DotAccessibleDict(**val))
            elif type(val) == list:
                setattr(
                    self,
                    key,
                    [DotAccessibleDict(**el) if isinstance(el, dict) else el for el in val],
                )
            else:
                setattr(self, key, val)

    def get(self, index):
        target = self
        parts = index.split(".")
        for i in parts:
            if isinstance(target, list):
                target = target[0]
            target = getattr(target, i)
        return target

    def set(self, index, value):
        if index:
            parts = index.split(".")
            tmp_obj = getattr(self, parts[0]) if hasattr(self, parts[0]) else DotAccessibleDict()
            if len(parts) > 1:
                tmp_obj.set(".".join(parts[1:]), value)
            else:
                tmp_obj = value
            setattr(self, parts[0], tmp_obj)
        return self

    def filter(self, fields):
        new_dict = DotAccessibleDict()
        for field in fields:
            new_dict.set(field, self.get(field))
        return new_dict

    def to_dict(self):
        obj = {}
        for i in self.__dict__:
            val = getattr(self, i)
            if isinstance(val, DotAccessibleDict):
                obj[i] = val.to_dict()
            elif isinstance(val, list):
                obj[i] = [el.to_dict() if isinstance(el, DotAccessibleDict) else el for el in val]
            else:
                obj[i] = val
        return obj


def json2tbl(json_object, build_direction="LEFT_TO_RIGHT", table_attributes=None):
    """JSON 2 Table
    Converts a JSON object into an HTML table.  Chain the results of this filter to |safe to remove HTML encoding.
    :param json_object: {dict or list} JSON object to convert into HTML.
    :param build_direction: {unicode} String denoting the build direction of the table. Only supports dict input json_objects.
                            If "TOP_TO_BOTTOM" child objects will be appended below parents, i.e. in the subsequent row.
                            If "LEFT_TO_RIGHT" child objects will be appended to the right of parents, i.e. in the subsequent column.
                            Default is "LEFT_TO_RIGHT". {"TOP_TO_BOTTOM", "LEFT_TO_RIGHT"}
    :param table_attributes: {dict} Dictionary of (key, value) pairs describing attributes to add to the table. Each
                            attribute is added according to the template key="value". For example, the table { "border" : 1 }
                            modifies the generated table tags to include border="1" as an attribute.
                            The generated opening tag would look like <table border="1">.
                            Only supports "class" attribute for input json_object of list type.
                            Default is None.
    :return: {str} String of converted HTML.
    """
    if isinstance(json_object, dict):
        return convert(
            json_object,
            build_direction=build_direction,
            table_attributes=table_attributes,
        )
    if isinstance(json_object, list):
        if table_attributes and "class" in table_attributes:
            return json2html.convert(
                json=json_object,
                table_attributes=f'class="{table_attributes["class"]}"',
            )
        return json2html.convert(json=json_object)
    return None


def to_json(a, *args: typing.Any, **kw):
    """Convert the value to JSON"""
    return json.dumps(a, *args, **kw)


def to_nice_json(a, indent=4, sort_keys=True, *args: typing.Any, **kw):
    """Make verbose, human readable JSON"""
    return to_json(
        a,
        indent=indent,
        sort_keys=sort_keys,
        separators=(",", ": "),
        *args,
        **kw,
    )


def is_in_list(val, in_list):
    return val in in_list


def _get_regex_flags(ignorecase=False):
    return re.IGNORECASE if ignorecase else 0


def regex_match(value, pattern, ignorecase=False):
    if not isinstance(value, six.string_types):
        value = str(value)
    flags = _get_regex_flags(ignorecase)
    return bool(re.match(pattern, value, flags))


def regex_replace(value, pattern, replacement, ignorecase=False):
    if not isinstance(value, six.string_types):
        value = str(value)
    flags = _get_regex_flags(ignorecase)
    regex = re.compile(pattern, flags)
    return regex.sub(replacement, value)


def regex_search(value, pattern, ignorecase=False):
    if not isinstance(value, six.string_types):
        value = str(value)
    flags = _get_regex_flags(ignorecase)
    return bool(re.search(pattern, value, flags))


def regex_substring(value, pattern, result_index=0, ignorecase=False):
    if not isinstance(value, six.string_types):
        value = str(value)
    flags = _get_regex_flags(ignorecase)
    return re.findall(pattern, value, flags)[result_index]


def filter_datetime(date, fmt="%Y/%m/%d %H:%M:%S"):
    try:
        if len(str(int(date))) == 13:
            ts = int(date) / 1000
            date = datetime.datetime.fromtimestamp(ts)
        elif len(str(int(date))) == 9 or len(str(int(date))) == 10:
            date = datetime.datetime.fromtimestamp(int(date))
        else:
            date = dateutil.parser.parse(date)
    except:
        date = dateutil.parser.parse(date)

    return date.strftime(fmt)


def map_priority(p):
    priority = {
        "-1": "info",
        "40": "low",
        "60": "medium",
        "80": "high",
        "100": "critical",
    }
    return priority.get(p)


def timectime(s):
    a_str = str(s)
    if len(a_str) == 13:
        s /= 1000
    # return datetime.datetime.fromtimestamp(int(s))
    return time.ctime(int(s))  # datetime.datetime.fromtimestamp(s)


def dedup_list_of_dicts(list_of_dicts):
    """Dedup a list of dictionaries. It checks to see if the key/values are the same."""
    seen = set()
    new_l = []
    for d in list_of_dicts:
        t = tuple(d.items())
        if t not in seen:
            seen.add(t)
            new_l.append(d)
    return new_l


def ternary(value, true_val, false_val, none_val=None):
    """Value ? true_val : false_val"""
    if value is None and none_val is not None:
        return none_val
    if bool(value):
        return true_val
    return false_val


def comment(text, style="plain", **kw):
    # Predefined comment types
    comment_styles = {
        "plain": {"decoration": "# "},
        "erlang": {"decoration": "% "},
        "c": {"decoration": "// "},
        "cblock": {"beginning": "/*", "decoration": " * ", "end": " */"},
        "xml": {"beginning": "<!--", "decoration": " - ", "end": "-->"},
    }

    # Pointer to the right comment type
    style_params = comment_styles[style]

    prepostfix = kw["decoration"] if "decoration" in kw else style_params["decoration"]

    # Default params
    p = {
        "newline": "\n",
        "beginning": "",
        "prefix": (prepostfix).rstrip(),
        "prefix_count": 1,
        "decoration": "",
        "postfix": (prepostfix).rstrip(),
        "postfix_count": 1,
        "end": "",
    }

    # Update default params
    p.update(style_params)
    p.update(kw)

    # Compose substrings for the final string
    str_beginning = ""
    if p["beginning"]:
        str_beginning = f"{p['beginning']}{p['newline']}"
    str_prefix = ""
    if p["prefix"]:
        if p["prefix"] != p["newline"]:
            str_prefix = str("{}{}".format(p["prefix"], p["newline"])) * int(
                p["prefix_count"],
            )
        else:
            str_prefix = str("{}".format(p["newline"])) * int(p["prefix_count"])
    str_text = (
        "{}{}".format(
            p["decoration"],
            # Prepend each line of the text with the decorator
            text.replace(p["newline"], "{}{}".format(p["newline"], p["decoration"])),
        )
    ).replace(
        # Remove trailing spaces when only decorator is on the line
        f"{p['decoration']}{p['newline']}",
        f"{p['decoration'].rstrip()}{p['newline']}",
    )
    str_postfix = p["newline"].join(
        [""] + [p["postfix"] for x in range(p["postfix_count"])],
    )
    str_end = ""
    if p["end"]:
        str_end = f"{p['newline']}{p['end']}"

    # Return the final string
    return f"{str_beginning}{str_prefix}{str_text}{str_postfix}{str_end}"


def filter_json(json_object, include_keys):
    # include_keys is a comma separated list of key paths in a json object.
    # using . as the separator between nested keys.
    dynamic_object = DotAccessibleDict(**json_object)
    filter_keys = include_keys.split(",")
    filtered = dynamic_object.filter(filter_keys)
    return filtered.to_dict()


def epochTimeToHuman(epoch_time):
    epoch_time = int(epoch_time) / 1000
    human_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(epoch_time))
    return str(human_time)


def startswith(json_object, stringToFind):
    matches = []
    for k, v in json_object.items():
        if k.startswith(stringToFind):
            matches.append(v)
    return matches


def endswith(json_object, stringToFind):
    matches = []
    for k, v in json_object.items():
        if k.endswith(stringToFind):
            matches.append(v)
    return matches
