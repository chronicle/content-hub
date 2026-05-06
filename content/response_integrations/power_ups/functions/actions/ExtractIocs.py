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

import ipaddress
import re
import urllib.parse
from html import unescape

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from tld import get_fld
from urlextract import URLExtract

IPV4_REGEX: re.Pattern[str] = re.compile(r"""(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})""")
IPV6_REGEX: re.Pattern[str] = re.compile(
    r"""((?:[0-9A-Fa-f]{1,4}:){6}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|::(?:[0-9A-Fa-f]{1,4}:){5}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){4}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){3}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,2}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:){2}(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,3}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}:(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,4}[0-9A-Fa-f]{1,4})?::(?:[0-9A-Fa-f]{1,4}:[0-9A-Fa-f]{1,4}|(?:(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}(?:[0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]))|(?:(?:[0-9A-Fa-f]{1,4}:){,5}[0-9A-Fa-f]{1,4})?::[0-9A-Fa-f]{1,4}|(?:(?:[0-9A-Fa-f]{1,4}:){,6}[0-9A-Fa-f]{1,4})?::)""",
)
EMAIL_REGEXP: re.Pattern[str] = re.compile(
    r"(?i)"  # Case-insensitive matching
    r"(?:[A-Z0-9!#$%&'*+/=?^_`{|}~-]+"  # Unquoted local part
    r"(?:\.[A-Z0-9!#$%&'*+/=?^_`{|}~-]+)*"  # Dot-separated atoms in local part
    r"|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]"  # Quoted strings
    r"|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")"  # Escaped characters in local part
    r"@"  # Separator
    r"[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?"  # Domain name
    r"\.(?:[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?)+",  # Top-level domain and subdomains
)


@output_handler
def main() -> None:
    try:
        siemplify: SiemplifyAction = SiemplifyAction()
        input_string: str = siemplify.extract_action_param(
            "Input String",
            print_value=True,
        )
        status: int = EXECUTION_STATE_COMPLETED
        urls_found: list[str] = get_urls(input_string)
        domains_found: list[str] = extract_domains_from_urls(urls_found)
        ips_found = extract_ips(input_string)
        emails_found: list[str] = extract_emails(input_string)
        json_result: dict[str, list[str]] = {
            "domains": domains_found,
            "ips": ips_found,
            "urls": urls_found,
            "emails": emails_found,
        }
        siemplify.result.add_result_json(json_result)
        siemplify.result.add_json("Json", json_result)
        components: list[str] = []
        if urls_found:
            components.append(f"URLs: {','.join(urls_found)}")
        if domains_found:
            components.append(f"Domains: {','.join(domains_found)}")
        if ips_found:
            components.append(f"IPs: {','.join(ips_found)}")
        if emails_found:
            components.append(f"Emails: {','.join(emails_found)}")

        if components:
            output_message = "Extracted the following:\n" + "\n".join(components)
        else:
            output_message = "No IOCs extracted from the string."

        siemplify.LOGGER.info(f"status: {status}\noutput_message: {output_message}")
        siemplify.end(output_message, output_message, status)

    except Exception as e:
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.exception(f"Error occurred: {e!s}")
        siemplify.end(f"Failed due to error: {e!s}", "", status)


def get_urls(body: str) -> list[str]:
    """Function for extracting URLs from the input string.

    Args:
        body (str): Text input which should be searched for URLs.

    Returns:
        list: Returns a list of URLs found in the input string.

    """
    list_observed_urls: dict[str, None] = {}
    extractor: URLExtract = URLExtract(cache_dns=False)
    for found_url in extractor.find_urls(body, check_dns=True):
        if "." not in found_url:
            # If we found a URL like http://afafasasfasfas that makes no
            # sense, thus skip it
            continue

        try:
            _ = ipaddress.ip_address(found_url)
            # We want to skip any IP addresses we find in the body.
            # These will be added when via the extract_ips method.
            continue

        except ValueError:
            pass

        clean_uri: str | None = clean_found_url(found_url)
        if clean_uri is not None:
            list_observed_urls[clean_uri] = None

    return list(list_observed_urls)


def clean_found_url(url: str) -> str | None:
    """Cleans up the found URL, removing unnecessary characters and validating it.

    Args:
        url (str): The URL to be cleaned up.

    Returns:
        str: A cleaned URL or None if it's invalid.

    """
    if "." not in url and "[" not in url:
        # If we found a URL like http://afafasasfasfas; that makes no
        # sense, thus skip it. Include http://[2001:db8::1]
        return None

    try:
        url = url.lstrip("\"'\t \r\n").replace("\r", "").replace("\n", "").rstrip("/")
        url = urllib.parse.urlparse(url).geturl()

        scheme_url = re.sub(r":/{1,3}", "://", url, count=1) if ":/" in url[:10] else f"noscheme://{url}"

        tld = urllib.parse.urlparse(scheme_url).hostname.rstrip(".").rsplit(".", 1)[-1].lower()
        if tld in {
            "aspx",
            "css",
            "gif",
            "htm",
            "html",
            "js",
            "jpg",
            "jpeg",
            "php",
            "png",
        }:
            return None

    except ValueError:
        return None

    # let's try to be smart by stripping of noisy bogus parts
    url = re.split(r"""[', ")}\\]""", url, 1)[0]

    # filter bogus URLs
    if url.endswith("://"):
        return None

    if "&" in url:
        url = unescape(url)

    return url


def extract_domains_from_urls(urls: list[str]) -> list[str]:
    """Extracts domains from a list of URLs.

    Args:
        urls (list): List of URLs from which to extract domains.

    Returns:
        list: List of domains extracted from URLs.

    """
    # Extract domains
    domains: dict[str, None] = {}
    for url in urls:
        try:
            dom: str = get_fld(url.lower(), fix_protocol=True)
            domains[dom] = None

        except Exception:
            pass

    return list(domains)


def extract_ips(body: str, include_internal: bool = True) -> list[str]:
    """Extracts IP addresses from a given string.

    Args:
        body (str): The string from which IPs are to be extracted
        include_internal (bool): Whether to include internal IPs in the result
    Returns:
        list: List of IPs extracted from the string.

    """
    ips: dict[str, None] = {}
    for ip_type in (IPV4_REGEX, IPV6_REGEX):
        for match in ip_type.findall(body):
            try:
                ipaddress_match: ipaddress.IPv4Address | ipaddress.IPv6Address = ipaddress.ip_address(match)

            except ValueError:
                continue

            else:
                if not ipaddress_match.is_private or (include_internal and match != "::"):
                    ips[match] = None

    return list(ips)


def extract_emails(body: str) -> list[str]:
    """Extracts emails from a given string.

    Args:
        body (str): The string from which emails are to be extracted.

    Returns:
        list: List of emails extracted from the string.

    """
    return list({e.lower(): None for e in EMAIL_REGEXP.findall(body)})


if __name__ == "__main__":
    main()
