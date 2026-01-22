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

import math
import os
import re

from SiemplifyUtils import unix_now

from .consts import (
    ONE_DAY_IN_MILLISECONDS,
    SLO_APPROACHING_COMMENT,
    SLO_APPROACHING_REGEXP,
    SLO_BREACHED_COMMENT,
)
from .data_models import UserProfileCard
from .rest.soar_api import get_user_profile_cards
from .transformation import removeprefix
from .types import ChronicleSOAR
from .utils import is_python_37, none_to_default_value


def get_user_by_id(chronicle_soar, user_id):
    # type: (ChronicleSOAR, str) -> UserProfileCard | None
    """Get a UserProfileCard object from user_id

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        user_id (str): The user ID, e.g. f6dc053c-58bb-4da5-95bb-739be7d297a2

    Returns:
        UserProfileCard | None: The user object if it was found, else None

    """
    users = get_users_profile_cards_with_pagination(chronicle_soar)
    for user in users:
        if user.user_name == user_id:
            return user


def get_users_profile_cards_with_pagination(
    chronicle_soar,
    search_term="",
    page_size=20,
    filter_by_role=False,
    filter_disabled_users=False,
    filter_support_users=False,
    fetch_only_support_users=False,
    filter_permission_types=None,
):
    # type: (ChronicleSOAR, str, int, bool, bool, bool, bool, list[int] | None) -> list[UserProfileCard]
    """Get all users profiles cards using pagination

    The page size is used as the limit of number of users each iteration.

    Args:
        chronicle_soar (ChronicleSOAR): A chronicle soar SDK object
        search_term (str): Search terms
        page_size (int): Number of users to return
        filter_by_role (bool): Whether to filter out by role
        filter_disabled_users (bool): Whether to filter out disabled users
        filter_support_users (bool): Whether to filter out support users
        fetch_only_support_users (bool): Whether to return support users only.
        filter_permission_types (list[int] | None):
            List of filter permission types (e.g. 0)

    Returns:
        list[UserProfileCard]: List of all users

    """
    filter_permission_types = none_to_default_value(filter_permission_types, [])

    users = []
    last_fetch_number = page_size
    while last_fetch_number == page_size:
        requested_page = len(users)
        response_json = get_user_profile_cards(
            chronicle_soar=chronicle_soar,
            search_term=search_term,
            requested_page=requested_page,
            page_size=page_size,
            filter_by_role=filter_by_role,
            filter_support_users=filter_support_users,
            filter_disabled_users=filter_disabled_users,
            fetch_only_support_users=fetch_only_support_users,
            filter_permission_types=filter_permission_types,
        )
        results = response_json.get("objectsList", response_json.get("items"))
        for user in results:
            users.append(UserProfileCard.from_json(user))

        last_fetch_number = len(results)

    return users


def get_soar_case_comments(chronicle_soar, case_id):
    # type: (SiemplifyAction | SiemplifyJob, str | int) -> list[CaseComment]
    """Get a list of comment objects from a case by its ID

    Args:
        chronicle_soar (SiemplifyAction | SiemplifyJob):
            The SDK object
        case_id (str | int):
            The ID of the case which comments needs to be fetched

    Returns:
        list[base.action.CaseComment]: List of comment objects

    """
    comments = chronicle_soar.get_case_comments(case_id)
    if is_python_37:
        from .base.action import parse_case_comment

        return [parse_case_comment(comment) for comment in comments]

    return [comment for comment in comments]


def get_clean_comment_body(comment, prefix):
    # type: (str | CaseComment, str) -> str
    """Remove a prefix from comment string or comment object

    Args:
        comment (str | CaseComment):
            The comment string or comment object to remove the prefix from
        prefix (str): The prefix to remove

    Raises:
        TypeError: If the type of comment is not str or CaseComment

    Returns:
        str: The comment without the prefix

    """
    if is_python_37:
        from .base.action import CaseComment

        if isinstance(comment, CaseComment):
            return removeprefix(comment.comment, prefix)

    if isinstance(comment, str):
        return removeprefix(comment, prefix)

    raise TypeError(
        f"The provided comment was of type {type(comment)}, which is not str "
        "or TIPCommon.base.action.CaseComment"
    )


def remove_prefix_from_comments(comments, prefix):
    # type: (list[str], str) -> list[str]
    """Remove a prefix (if exists) from a list of comments

    Args:
        comments (list[str]): The comments to remove prefix from
        prefix (str): The prefix to remove

    Returns:
        list[str]: List of all comments after the prefix was removed from them

    """
    return [get_clean_comment_body(comment, prefix) for comment in comments]


def is_slo_comment(comment):
    # type: (str) -> bool
    """Check if a comment is an SLO warning comment

    SLO comment is either an SLO warning or SLO breached message:
    'SLO will be breached in {int} days.' or 'SLO was breached.'

    Args:
        comment (str): The comment to check

    Returns:
        bool: True if it's an SLO comment, else False

    """
    return (
        comment == SLO_BREACHED_COMMENT or re.fullmatch(SLO_APPROACHING_REGEXP, comment) is not None
    )


def create_slo_message(slo, interval_days, existing_comments):
    # type: (int, Iterable[int], Iterable[str]) -> str | None
    """Get SLO warnings message based on time intervals, and existing comments

    For interval_days=[0, 1, 7, 14] it will send a message warning that the
    SLO would be breached once between 7-14 days of the expiration time,
    once between 1-7 days of the expiration time, and once when the SLO was
    breached.
    If a comment was already sent in the current breached interval, no new
    comment will be returned, but None.

    Args:
        slo (int):
            The SLO breach date in unix microseconds (e.g. 1_673_774_674_567)
        interval_days (Iterable[int]):
            An iterable containing the number of days from time breach warnings
            should be sent (e.g. [0, 1, 3, 7, 14])
        existing_comments (Iterable[int]):
            The existing comments to check if a comment was already sent

    Raises:
        ValueError: If one of the time intervals happens to be negative

    Returns:
        The comment if a comment should be sent, else None

    """
    for interval in interval_days:
        if interval < 0:
            raise ValueError("Dy intervals must be positive!")

    unique_comments = set(existing_comments)
    if SLO_BREACHED_COMMENT in unique_comments:
        return None

    # Mapping which comments have been set already
    comment_regex = re.compile(SLO_APPROACHING_REGEXP)
    sorted_days = sorted(interval_days)

    if sorted_days[0] != 0:
        sorted_days.insert(0, 0)

    reversed_sorted_days = list(reversed(sorted_days))
    checked_slo_times = dict.fromkeys(sorted_days, False)
    for comment in unique_comments:
        match = comment_regex.fullmatch(comment)
        if match is None:
            continue

        days = int(match.group(1))

        # This could have been sent by this code
        if days > reversed_sorted_days[0]:
            continue

        # Mark an interval as True to indicate a comment from this interval was
        # already sent
        for i, num_days in enumerate(reversed_sorted_days):
            if days > num_days:
                next_interval = reversed_sorted_days[i - 1]
                checked_slo_times[next_interval] = True
                break

    now = unix_now()
    for i, days in enumerate(sorted_days):
        future_time = now + (days * ONE_DAY_IN_MILLISECONDS)

        if future_time < slo or checked_slo_times[days]:
            continue

        days_left = math.ceil((slo - now) / ONE_DAY_IN_MILLISECONDS)

        # Making sure the number of days after ceil is still withing the
        # interval's range except for 0 where the number could also be negative
        if i > 0 and not (sorted_days[i - 1] < days_left <= days):
            continue

        comment = (
            SLO_BREACHED_COMMENT if days_left <= 0 else SLO_APPROACHING_COMMENT.format(days_left)
        )
        return comment


def save_file(chronicle_soar: ChronicleSOAR, path: str, name: str, content: bytes) -> bytes | None:
    """Save file to GCP bucket or local path.

    Args:
        chronicle_soar (ChronicleSOAR): SiemplifyAction objects
        path (str): Path of the folder, where files should be saved.
        name (str): File name to be saved.
        content (bytes): File content in bytes format.

    Returns:
        str | None: Path to the downloaded files

    """
    if not hasattr(chronicle_soar, "set_bytes_blob"):
        return None

    identifier = os.path.join(path, name)
    chronicle_soar.set_bytes_blob(identifier, content)

    return identifier


def get_file(chronicle_soar: ChronicleSOAR, identifier: str) -> bytes | None:
    """Get file content in bytes.

    Args:
        chronicle_soar (ChronicleSOAR): SiemplifyAction object.
        identifier (str): File name identifier along with full path.

    Returns:
        bytes | None: bytes data of the provided identifier.

    """
    if not hasattr(chronicle_soar, "get_bytes_blob"):
        return None

    return chronicle_soar.get_bytes_blob(identifier)


def get_secops_mode() -> str | None:
    """Returns the SECOPS_MODE environment variable."""
    return os.environ.get("SECOPS_MODE") or os.environ.get("SEC_OPS_MODE")
