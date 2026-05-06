# Copyright 2026 Google LLC
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

import re
from datetime import datetime, timedelta

from .consts import MD5_LENGTH, SHA1_LENGTH
from .exceptions import LastlineInvalidParamException


def remove_empty_kwargs(**kwargs) -> dict:
    """Remove keys from dictionary that has the value None
    :param kwargs: key value arguments
    :return: {dict} dictionary without keys that have the value None
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def get_max_hours_backwards_as_date(hours_backwards: int) -> str:
    """Get Max Hours Backwards as string date
    :param hours_backwards: {int} Hours to calculate backwards
    :return: {str}
    """
    hours_backwards_time = datetime.now() - timedelta(hours=hours_backwards)
    return hours_backwards_time.strftime("%Y-%m-%d %H:%M:%S")


def is_valid_sh1(file_hash: str) -> bool:
    """Check if the given string is valid SH1 file hash
    :param file_hash: {str} String to check
    :return: True if it is a valid SH1 file hash, else False
    """
    return (
        bool(file_hash and len(file_hash) == SHA1_LENGTH and re.findall(r"([0-9a-fA-F\d]{40})", file_hash))
    )


def is_valid_md5(file_hash: str) -> bool:
    """Check if the given string is valid MD5 file hash
    :param file_hash: {str} String to check
    :return: True if it is a valid MD5 file hash, else False
    """
    return (
        bool(file_hash and len(file_hash) == MD5_LENGTH and re.findall(r"([0-9a-fA-F\d]{32})", file_hash))
    )


def get_file_hash(file_hash: str) -> tuple:
    """Return tuple with the right file hash format and None for the second
    :param file_hash: {str} String to check
    :return: {Tuple} (SH1 or None, MD5 or None)
    raise LastlineInvalidParamException if it is not MD5 or SHA1 file hash formats
    """
    sha1 = file_hash if is_valid_sh1(file_hash) else None
    md5 = file_hash if is_valid_md5(file_hash) else None

    if sha1 or md5:
        return sha1, md5
    msg = "Invalid 'submission name' parameter was provided!"
    raise LastlineInvalidParamException(
        msg
    )
