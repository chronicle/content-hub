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
import hashlib
import ipaddress
import operator
import os
import re
from collections import Counter
from typing import Iterator, List

import chardet

from urllib.parse import urlparse

import base64

from .constants import MAGIC
from dateutil import parser

email_regex = re.compile(
    r"""([a-zA-Z0-9.!#$%&'*+-/=?\^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*)""",
    re.MULTILINE,
)
#                 /^[a-zA-Z0-9.!#$%&'*+-/=?\^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/

recv_dom_regex = re.compile(
    r"""(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]"""
)
recv_dom_regex_ignorecase = re.compile(
    r"""(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]""",
    re.IGNORECASE,
)

dom_regex = re.compile(
    r"""(?:\s|[\(\/<>|@'=])([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]{2,})+)(?:$|\?|\s|#|&|[\/<>'\)])""",
    re.MULTILINE,
)
ipv4_regex = re.compile(
    r"""((?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))""",
    re.MULTILINE,
)

# From https://gist.github.com/mnordhoff/2213179 : IPv6 with zone ID (RFC 6874)
ipv6_regex = re.compile(
    "((?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|::(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,2}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,3}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}:(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,4}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,5}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){,6}[0-9A-Fa-f]{1,4})?::)"
)

# simple version for searching for URLs
# character set based on http://tools.ietf.org/html/rfc3986
# url_regex_simple = re.compile(r'''(?i)\b((?:(hxxps?|https?|ftps?)://)[^ ]+)''', re.VERBOSE | re.MULTILINE)
url_regex_simple = re.compile(
    r"""(([a-z]{3,}s?:\/\/)[a-z0-9\-_:]+(\.[a-z0-9\-_]+)*"""
    + r"""(\/[a-z0-9_\-\.~!*'();:@&=+$,\/  ?%#\[\]]*)?)""",
    re.VERBOSE | re.MULTILINE | re.I,
)

priv_ip_regex = re.compile(
    r"^(((10(\.\d{1,3}){3})|(192\.168(\.\d{1,3}){2})|(172\.(([1][6-9])|([2]\d)|([3][0-1]))(\.\d{1,3}){2}))|(127(\.\d{1,3}){3})|(::1))"
)

reg_date = re.compile(r";[ \w\s:,+\-\(\)]+$")
no_par = re.compile(r"\([^()]*\)")

parentheses_regex = r"\([^)]*\)"

window_slice_regex = re.compile(r"""\s""")


def is_ole_file(file_content: str) -> bool:
    """
    Test if a file is an OLE container (according to the magic bytes in its header).
    This function only checks the first 8 bytes of the file, not the rest of the OLE structure.
    Args:
        file_content: Content of the OLE file
    Returns:
        True if OLE, False otherwise.
    """
    # filename is a bytes string containing the OLE file to be parsed:
    file_header = file_content[: len(MAGIC)] if isinstance(file_content, bytes) else ""
    return file_header == MAGIC


def prepare_json(
    extracted_msg, msox_msg: dict, blacklist: list, is_whitelist: bool
) -> dict:
    """
    Prepare json from extracted msg
    Args:
        extracted_msg: The Message object
        msox_msg: The extracted msg as dict
        blacklist: The list of headers to exclude.
        is_whitelist: Specify whether use blacklist as whitelist or no
    Returns:
        The prepared json
    """
    current_json = {
        "header": prepare_header_json(extracted_msg, msox_msg, blacklist, is_whitelist),
        "body": [prepare_body_json(extracted_msg.body, "text/plain")],
    }

    if extracted_msg.htmlBody:
        current_json["body"].append(
            prepare_body_json(extracted_msg.htmlBody, "text/html")
        )

    return current_json


def prepare_header_json(
    extracted_msg, msox_msg: dict, blacklist: list, is_whitelist: bool
) -> dict:
    """
    Prepare json from header data
    Args:
        extracted_msg: The Message object
        msox_msg: The extracted msg as dict
        blacklist: The list of headers to exclude.
        is_whitelist: Specify whether use blacklist as whitelist or no
    Returns:
        The prepared json
    """
    to_smtp = ""
    from_smtp = ""

    if "ReceivedByAddressType" in msox_msg:
        to_smtp = (
            "ReceivedBySmtpAddress"
            if msox_msg["ReceivedByAddressType"] == "EX"
            else "ReceivedByEmailAddress"
        )
        from_smtp = (
            "SenderSmtpAddress"
            if msox_msg["SenderAddressType"] == "EX"
            else "SenderEmailAddress"
        )

    to = msox_msg.get(to_smtp) if to_smtp in msox_msg else extracted_msg.to
    from_header = (
        msox_msg.get(from_smtp) if from_smtp in msox_msg else extracted_msg.sender
    )

    headers = parse_headers(extracted_msg, blacklist, is_whitelist)

    header_json = {
        "to": [to],
        "from": from_header,
        "subject": (
            msox_msg["Subject"] if "Subject" in msox_msg else extracted_msg.subject
        ),
        "cc": extracted_msg.cc,
        "date": extracted_msg.date,
        "header": headers,
    }

    return header_json


def parse_headers(msg, blacklist=[], is_whitelist=False):
    headers = []

    for header in msg.header._headers[::-1]:
        if is_whitelist:
            if header[0].lower() in blacklist:
                header_item = {"Name": header[0].lower(), "Header": header[1]}
                header_item.update(parse_transport(header[0], header[1]))
                headers.append(header_item)
        else:
            if header[0].lower() not in blacklist:
                header_item = {"Name": header[0].lower(), "Header": header[1]}
                header_item.update(parse_transport(header[0], header[1]))
                headers.append(header_item)

    return headers


def parse_transport(name, header):
    headers_struc = {}

    if "received" in name.lower():
        headers_struc["received"] = []

    headers_struc["email"] = []
    headers_struc["domain"] = []
    headers_struc["ip"] = []
    headers_struc["ipv4"] = []
    headers_struc["ipv6"] = []

    try:
        if header:
            line = str(header).lower()
            received_line_flat = re.sub(r"(\r|\n|\s|\t)+", " ", line, flags=re.UNICODE)
            parsed_routing = ""

            if "received" in name.lower():
                parsed_routing = parse_received_header(received_line_flat)
                headers_struc["received"].append(parsed_routing)

            ips_in_received_line_v4 = ipv4_regex.findall(received_line_flat)
            ips_in_received_line_v6 = ipv6_regex.findall(received_line_flat)

            for ip in ips_in_received_line_v4:
                try:
                    ip_obj = ipaddress.ip_address(
                        ip
                    )  # type of findall is list[str], so this is correct
                except ValueError:
                    print(f'Invalid IP in received line - "{ip}"')
                else:
                    if not ip_obj.is_private:
                        headers_struc["ipv4"].append(str(ip_obj))

            for ip in ips_in_received_line_v6:
                try:
                    ip_obj = ipaddress.ip_address(
                        ip
                    )  # type of findall is list[str], so this is correct
                except ValueError:
                    print(f'Invalid IP in received line - "{ip}"')
                else:
                    if not ip_obj.is_private:
                        headers_struc["ipv6"].append(str(ip_obj))

            # search for domain
            for domain in recv_dom_regex.findall(received_line_flat):
                try:
                    ip_obj = ipaddress.ip_address(
                        domain
                    )  # type of findall is list[str], so this is correct
                except ValueError:
                    # we find IPs using the previous IP crawler, hence we ignore them
                    # here.
                    # if the regex fails, we add the entry
                    headers_struc["domain"].append(domain)

            # search for e-mail addresses
            for mail_candidate in email_regex.findall(received_line_flat):
                if parsed_routing and mail_candidate not in parsed_routing.get(
                    "for", []
                ):
                    headers_struc["email"] += [mail_candidate]

    except TypeError:  # Ready to parse email without received headers.
        raise Exception("Exception occurred while parsing received lines.")

    # Concatenate for emails into one array | uniq
    # for rapid "find"

    # Uniq data found
    headers_struc["email"] = list(set(headers_struc["email"]))
    headers_struc["domain"] = list(set(headers_struc["domain"]))
    headers_struc["ip"] = list(set(headers_struc["ipv4"])) + list(
        set(headers_struc["ipv6"])
    )

    # Clean up if empty
    if not headers_struc["email"]:
        del headers_struc["email"]

    if not headers_struc["domain"]:
        del headers_struc["domain"]

    if not headers_struc["ip"]:
        del headers_struc["ip"]

    return headers_struc


def prepare_body_json(msg, content_type):
    body_json = {
        "content_type": content_type,
        "content": msg if msg is not None else "",
        "hash": hashlib.sha256(get_encoded_string(msg)).hexdigest(),
    }

    body_json.update(parse_body(msg))
    return body_json


def parse_body(body):
    parsed = {}
    list_observed_urls = []
    list_observed_email = Counter()
    list_observed_dom = Counter()
    list_observed_ip = Counter()

    for body_slice in string_sliding_window_loop(body):
        list_observed_urls = get_uri_ondata(body_slice)

        for match in email_regex.findall(body_slice):
            list_observed_email[match.lower()] = 1

        for match in dom_regex.findall(body_slice):
            list_observed_dom[match.lower()] = 1

        for match in ipv4_regex.findall(body_slice):
            try:
                ipaddress_match = ipaddress.ip_address(match)
            except ValueError:
                continue
            else:
                if not ipaddress_match.is_private:
                    list_observed_ip[match] = 1

        for match in ipv6_regex.findall(body_slice):
            try:
                ipaddress_match = ipaddress.ip_address(match)
            except ValueError:
                continue
            else:
                if not ipaddress_match.is_private:
                    list_observed_ip[match] = 1

    if list_observed_urls:
        parsed["uri"] = list(list_observed_urls)
    if list_observed_email:
        parsed["email"] = list(list_observed_email)
    if list_observed_dom:
        parsed["domain"] = list(list_observed_dom)
    if list_observed_ip:
        parsed["ip"] = list(list_observed_ip)

    return parsed


def string_sliding_window_loop(body: str, slice_step: int = 500) -> Iterator[str]:
    """
    Yield a more or less constant slice of a large string.
    If we start directly a *re* findall on 500K+ body we got time and memory issues.
    If more than the configured slice step, lets cheat, we will cut around the thing we search "://, @, ."
    in order to reduce regex complexity.
    Args:
        body: Body to slice into smaller pieces
        slice_step: Slice this number or characters.
    Returns:
        Sliced body string.
    """
    body_length = len(body)

    if body_length <= slice_step:
        yield body

    else:
        ptr_start = 0
        for ptr_end in range(slice_step, body_length, slice_step):
            if " " in body[ptr_end - 1 : ptr_end]:
                while not (
                    window_slice_regex.match(body[ptr_end - 1 : ptr_end])
                    or ptr_end > body_length
                ):
                    if ptr_end > body_length:
                        ptr_end = body_length
                        break

                    ptr_end += 1

            yield body[ptr_start:ptr_end]

            ptr_start = ptr_end


def get_uri_ondata(body: str) -> List[str]:
    """
    Function for extracting URLs from the input string.
    Args:
        body: Text input which should be searched for URLs.
    Returns:
        Returns a list of URLs found in the input string.
    """
    list_observed_urls = Counter()
    found = url_regex_simple.findall(body)

    for url in found:
        for found_url in url:
            if "." not in found_url:
                # if we found a URL like e.g. http://afafasasfasfas; that makes no sense, thus skip it
                continue

            found_url = urlparse(found_url).geturl()
            # let's try to be smart by stripping of noisy bogus parts
            found_url = re.split(r"""[', ")}\\]""", found_url, 1)[0]
            list_observed_urls[found_url] = 1

    return list(list_observed_urls)


def prepare_attachment_json(filename, content):
    attachment_json = {
        "filename": filename,
        "size": len(content),
        "extension": os.path.splitext(filename)[1][1:],
        "hash": {
            "md5": hashlib.md5(content).hexdigest(),
            "sha1": hashlib.sha1(content).hexdigest(),
            "sha256": hashlib.sha256(content).hexdigest(),
            "sha512": hashlib.sha512(content).hexdigest(),
        },
        "raw": base64.b64encode(content).decode(),
    }

    return attachment_json


def get_encoded_string(msg_str: str) -> str:
    """
    Get the encoded message
    Args:
        msg_str: Message unicode string
    Returns:
        The encoded message
    """
    try:
        msg_str = msg_str.encode("utf-8")
    except Exception:
        try:
            encoding = chardet.detect(msg_str).get("encoding", "utf-8")
            msg_str = msg_str.encode(encoding)
        except Exception:
            msg_str = "Unable to encode value (unknown encoding)"

    return msg_str


def filter_eml_headers(
    header: dict, blacklist: list, is_whitelist: bool = False
) -> None:
    """
    Filter parsed eml headers
    Args:
        header: The parsed eml header
        blacklist: The list of headers to exclude
        is_whitelist: Specify whether use blacklist as whitelist or no
    """
    headers = header.get("header", {})
    filtered_headers = {}

    for key, value in headers.items():
        if is_whitelist:
            if key in blacklist:
                filtered_headers[key] = value
        else:
            if key not in blacklist:
                filtered_headers[key] = value

    header["header"] = filtered_headers


def parse_received_header(received_header_str: str) -> dict:
    """
    Parsing received header of .msg mail files
    Args:
        received_header_str: Received header string
    Returns:
        Parsed received header
    """
    received_header_words = ["from ", "by ", "with ", "for "]
    received_header_str = received_header_str.replace("\n", "")
    received_header_str = received_header_str.replace("\r", "").lower()

    word_indexes = {
        word: received_header_str.find(word)
        for word in received_header_words
        if received_header_str.find(word) > -1
    }
    word_indexes = dict(sorted(word_indexes.items(), key=lambda item: item[1]))
    word_indexes_sorted_tup = sorted(word_indexes.items(), key=operator.itemgetter(1))
    indexes_list = [idx for key, idx in word_indexes_sorted_tup]
    word_index_in_list = 0
    received_header = {}

    for word, index in word_indexes_sorted_tup:
        if word_index_in_list < len(word_indexes) - 1:
            received_header[word.strip()] = received_header_str[
                index + len(word) : indexes_list[word_index_in_list + 1]
            ]
        else:
            received_header[word.strip()] = received_header_str[
                index + len(word) : received_header_str.find(";")
            ]
        word_index_in_list += 1

    if not received_header:
        received_header["warning"] = ["Nothing Parsable"]

    for word in ["from", "by", "for"]:
        if received_header.get(word):
            word_splitted = received_header[word].replace("(", "")
            word_splitted = word_splitted.replace(")", "")
            word_splitted = word_splitted.replace("]", "")
            word_splitted = word_splitted.replace("[", "")
            word_splitted = word_splitted.split(" ")
            received_header[word] = list(
                {_word.strip() for _word in word_splitted if _word}
            )

    if received_header.get("for"):
        mails_list = []
        for _mail in received_header.get("for"):
            extracted_mail = email_regex.findall(_mail)
            if extracted_mail:
                mails_list.append(extracted_mail[0])
        received_header["for"] = mails_list

    splitted_header = received_header_str

    try:
        _date = re.sub(r"\([^)]*\)", "", splitted_header)
        _date = re.findall(reg_date, _date)
        _date = _date[0].strip() if _date else ""
        _date = _date.replace(";", "").strip()

        _date = parser.parse(_date)
        received_header["date"] = _date.strftime("%Y-%m-%d %H:%M:%S %z")
    except Exception as error:
        received_header["date"] = splitted_header[1]

    received_header["src"] = received_header_str
    return received_header
