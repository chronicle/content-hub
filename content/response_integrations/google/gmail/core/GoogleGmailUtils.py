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

import asyncio
import base64
from email import encoders
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import gzip
import itertools
import json
import os
import re
import urllib.parse

import aiohttp
from bs4 import BeautifulSoup
from google.auth import iam
from google.auth.transport._aiohttp_requests import Request
from google.oauth2 import _service_account_async

import html2text

from TIPCommon.base.utils import NewLineLogger
from TIPCommon.rest.auth import get_adc
from TIPCommon.rest.auth import get_auth_request
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_empty_string_or_none

from ..core.GoogleGmailExceptions import GoogleCloudAuthenticationError
from ..core.GoogleGmailExceptions import InvalidJSONFormatException

DEFAULT_DIVIDER = ";"
URL_ENCLOSING_PREFIX = "["
URL_ENCLOSING_SUFFIX = "]"
PLACEHOLDER_START = "["
PLACEHOLDER_END = "]"
URLS_REGEX_COMPLEX = (
    r"(?i)\[?(?:(?:(?:http|https)"
    r"(?:://))|www\.(?!://))(?:[a-zA-Z0-9\-\._~:;/\?#\[\]@!\$&'\(\)\*\+,=%<>])+"
)

HTML_IMAGE_TAG = "cstimage"
HTML_IMAGE_TAG_NAME_ATTR = "cid"
HTML_IMAGE_TAG_BASE64_ATTR = "base64image"


def parse_string_to_dict(string: str) -> SingleJson:
    """Parse json string to dict.

    Args:
        string: string to parse

    Returns:
        parsed dict
    """
    try:
        return json.loads(string)
    except json.JSONDecodeError as err:
        raise InvalidJSONFormatException(
            f"Unable to parse provided json. Error is: {err}"
        ) from err


async def extract_body(response: aiohttp.ClientResponse) -> str:
    """Extract and decompress body from AuthorizedSession response."""
    content_ = await response.read()

    try:
        content_ = gzip.decompress(content_)
    except gzip.BadGzipFile:
        pass

    return (
        content_.decode("utf-8")
        if hasattr(content_, "decode")
        else content_
    )


# TODO move to TIPCommon
def extract_regex_from_content(
        regex_map: dict[str, str],
        email_subject: str,
        email_bodies: list[str]
) -> dict[str, str]:
    """Get urls, subject, from and to addresses from email body.

    Args:
        regex_map: Regex mapping
        email_subject: {str} email subject
        email_bodies: {str} email body

    Returns:
        fields after parse.
    """
    result_dictionary = {}
    for key, regex_value in regex_map.items():
        if regex_value:
            regex_object = re.compile(regex_value)
            all_results = set(
                itertools.chain(*(
                    re.findall(regex_value, body, flags=re.MULTILINE)
                    for body in email_bodies
                ))
            )
            all_results.update(regex_object.findall(email_subject))

            for index, result in enumerate(all_results, 1):
                # Divide keys
                key_name = f"{key}_{index}"
                result_dictionary[key_name] = result

    return result_dictionary


# TODO move to TIPCommon
def build_regex_map(logger: NewLineLogger, regex_list: list[str]) -> dict[str, str]:
    """Build regex map from a regex list, with key: value pairs."""
    regex_map = {}
    for regex_item in regex_list:
        try:
            if ": " in regex_item:
                # Split only once by ":"
                user_regex = regex_item.split(": ", 1)
                # check if user regex include key (regex name)
                # and value (the regex itself)
                if len(user_regex) >= 2:
                    regex_map.update({user_regex[0]: user_regex[1]})
        except IndexError as e:
            logger.error(
                f"Unable to get parse whitelist item {regex_item}. "
                f"Ignoring item and continuing."
            )
            logger.exception(e)
    return regex_map


# TODO move to TIPCommon
def get_html_urls_from_html_2_text_obj(html_content: str) -> tuple[str, str]:
    """Create a HTML2Text object and get html urls.

    Args:
        html_content: {str} The html content

    Returns:
        The list of visible urls, the list of not visible urls from original src
        attribute
    """
    html_renderer = html2text.HTML2Text()
    html_renderer.ignore_tables = True
    html_renderer.protect_links = True
    html_renderer.ignore_images = False
    html_renderer.ignore_links = False
    html_renderer.handle(html_content)
    return html_renderer.html_links, html_renderer.html_links_original_src


# TODO move to TIPCommon
def check_url_enclosing(url: str) -> str:
    """Check if url enclosed and remove enclosing characters.

    Args:
        url: {str} url to check

    Returns:
        {str} transformed url
    """
    if url.startswith(URL_ENCLOSING_PREFIX) and url.endswith(URL_ENCLOSING_SUFFIX):
        return url[1:-1]

    return url


# TODO move to TIPCommon
def get_html_urls(html_contents: list[str]) -> tuple[str, str]:
    """Get urls from html content.

    Args:
        html_contents: {str} The html contents list

    Returns:
        Comma-separated list of visible urls,
        Comma-separated list of not visible urls from original src attribute
    """
    regex_object = re.compile(URLS_REGEX_COMPLEX)
    urls = set()
    original_src_urls = set()

    for html_content in html_contents:
        _urls_list, _original_src_urls_list = (
            get_html_urls_from_html_2_text_obj(html_content)
        )

        for url in _urls_list:
            url_ = regex_object.search(url)
            if url_ is None:
                continue

            urls.add(
                check_url_enclosing(
                    urllib.parse.unquote_plus(url_.group(0))
                )
            )

        for url in _original_src_urls_list:
            url_ = regex_object.search(url)
            if url_ is None:
                continue

            original_src_urls.add(
                check_url_enclosing(
                    urllib.parse.unquote_plus(url_.group(0))
                )
            )

    return DEFAULT_DIVIDER.join(urls), DEFAULT_DIVIDER.join(original_src_urls)


# TODO move to TIPCommon
def transform_template_string(template: str, event: SingleJson) -> str:
    """Transform string containing template using event data.

    Args:
        template: {str} String containing template
        event: {dict} Case event

    Returns:
        {str} Transformed string
    """
    index = 0

    while (
        PLACEHOLDER_START in template[index:]
        and PLACEHOLDER_END in template[index:]
    ):
        partial_template = template[index:]
        start, end = (
            partial_template.find(PLACEHOLDER_START) + len(PLACEHOLDER_START),
            partial_template.find(PLACEHOLDER_END)
        )
        substring = partial_template[start:end]
        value = event.get(substring) if event.get(substring) else ""
        template = template.replace(
            f"{PLACEHOLDER_START}{substring}{PLACEHOLDER_END}",
            value,
            1,
        )
        index = index + start + len(value)

    return template


# TODO move to TIPCommon
def transform_dict_keys(
        original_dict: SingleJson,
        prefix: str,
        suffix: str | None = None,
        keys_to_except=tuple()
) -> SingleJson:
    """Transform dict keys by adding prefix and suffix.

    Args:
        original_dict: Dict to transform keys
        prefix: Prefix for the keys
        suffix: Suffix for the keys
        keys_to_except: The list of keys which shouldn't be transformed

    Returns:
        The transformed dict
    """
    if prefix and suffix:
        return {
            f"{prefix}_{key}_{suffix}" if key not in keys_to_except else key
            : value for key, value in original_dict.items()
        }

    if prefix:
        return {
            f"{prefix}_{key}" if key not in keys_to_except else key
            : value for key, value in original_dict.items()
        }

    return original_dict


# TODO Move to TIPCommon
def get_auth_request_async(verify_ssl: bool = True) -> Request:
    """
    Creates an Authorized HTTP request to a GCP resource API.

    Args:
        verify_ssl (bool, optional): Verify SSL certificate. Defaults to True.

    Returns:
        google.auth.transport.requests.Request: An authorized request object
    """
    auth_request_session = aiohttp.ClientSession(
        # Auto decompress is not supported for current implementation
        auto_decompress=False,
        connector=aiohttp.TCPConnector(
            ssl=(None if verify_ssl is True else False),
        ),
        # Allow to fetch proxy set from the env.
        trust_env=True
    )
    return Request(session=auth_request_session)


def build_workspace_credentials(
        workload_identity_email: str | None,
        service_account_json: SingleJson | None,
        scopes: list[str],
        delegated_email: str,
        verify_ssl: bool,
) -> _service_account_async.Credentials:
    """Build async credentials for Google Workspace.

    Args:
        workload_identity_email: Workload identity Email
        service_account_json: Service Account JSON key
        scopes: List of OAuth2 scopes to be used
        delegated_email: Delegated email to impersonate in Google Workspace
        verify_ssl: Verify SSL

    Returns:
        _service_account_async.Credentials: Credentials object with delegated_email
            as subject
    """
    if service_account_json:
        return (
            _service_account_async.Credentials
            .from_service_account_info(service_account_json, scopes=scopes)
            .with_subject(delegated_email)
        )

    if not is_empty_string_or_none(workload_identity_email):
        # Create an IAM signer using the SA credentials.
        adc_creds = get_adc()[0]
        signer = iam.Signer(
            get_auth_request(verify_ssl),
            adc_creds,
            workload_identity_email
        )

        # Create OAuth 2.0 Service Account credentials using the IAM-based
        # signer and the bootstrap_credential's service account email.
        # Impersonate the given subject.
        creds = _service_account_async.Credentials(
            signer,
            workload_identity_email,
            "https://accounts.google.com/o/oauth2/token",
            scopes=scopes,
            subject=delegated_email,
        )
        return creds

    raise GoogleCloudAuthenticationError(
        "No service account or workload identity email were provided."
    )


def extract_email(identity_str: str) -> str:
    """Extract email address from identity string if it is valid.

    Examples:
        Gmail Team <mail-noreply@google.com> -> mail-noreply@google.com
        mail-doreply@google.com -> mail-doreply@google.com
    """
    return (
        re.search(r"<(.+)>", identity_str).groups()[0]
        if re.search(r"<(.+)>", identity_str) is not None
        else identity_str
    )


# TODO move to TIPCommon
class TaskTimeoutGuard:
    def __init__(
            self,
            scheduled_tasks: list[asyncio.Task],
            logger: NewLineLogger,
    ):
        self.scheduled_tasks = scheduled_tasks
        self.logger = logger

    async def __aenter__(self) -> None:
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None | bool:
        if exc_val is None or not issubclass(exc_type, asyncio.TimeoutError):
            return

        self.logger.info(
            "Task encountered a timeout while processing scheduled tasks"
        )
        task_exceptions = []
        for task in self.scheduled_tasks:
            try:
                if not task.done():
                    task.cancel()
                    await task
                    continue

                task_exception = task.exception()
                if task_exception is not None:
                    task_exceptions.append(task_exception)

            except asyncio.CancelledError:
                pass

        if task_exceptions:
            raise ExceptionGroup(
                "Tasks have encountered some exceptions",
                *task_exceptions
            )

        return True


def get_payload_decoded(mime: Message) -> str:
    """Extract payload from a mime message."""
    payload_ = mime.get_payload()
    if isinstance(payload_, list):
        html_body = None
        text_body = None
        embedded_bodies = []

        for mime_ in payload_:
            if mime_.get_content_type() == "text/html":
                html_body = mime_.get_payload()
                continue

            if mime_.get_content_type() == "text/plain":
                text_body = mime_.get_payload()
                continue

            if mime_.is_multipart():
                body = get_payload_decoded(mime_)
                if body is not None:
                    embedded_bodies.append(body)

        if html_body is not None:
            embedded_bodies.append(html_body)
        elif text_body is not None:
            embedded_bodies.append(text_body)

        return "<br>".join(embedded_bodies[::-1])

    return payload_


def set_attachments(
        message: MIMEMultipart,
        attachments_paths: list[str] | None = None,
) -> None:
    """Set attachments to MIMEMultipart."""
    if attachments_paths is None:
        return

    for attachments_path in attachments_paths or []:
        with open(attachments_path, "rb") as fp:
            attachment_data = fp.read()
            file_name = os.path.basename(attachments_path)
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment_data)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename=\"{file_name}\""
            )
            message.attach(part)


def set_body(
        message: MIMEMultipart,
        body: str,
) -> None:
    """Prepare payload before sending an email."""
    # Passing default parser to avoid getting a warning from BeautifulSoup
    soup = BeautifulSoup(body, features="html.parser")
    message.attach(MIMEText(body, "html", "utf-8"))

    # Extract cstimage tags images from html template
    for cst_tag in soup.findAll(HTML_IMAGE_TAG):
        image_name = cst_tag[HTML_IMAGE_TAG_NAME_ATTR]
        image_content = base64.b64decode(cst_tag[HTML_IMAGE_TAG_BASE64_ATTR])
        img = MIMEImage(image_content, image_name)
        img.add_header("Content-ID", f"<{image_name}>")
        img.add_header("Content-Disposition", "inline", filename=image_name)
        message.attach(img)
