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

"""Analyze the headers of an email and report routing, authentication, and
reputation findings.

Accepts a JSON object of email headers and produces SPF/DKIM/DMARC/ARC
authentication results (from the message's Authentication-Results headers),
DKIM/ARC signature verification, per-hop relay enrichment (WHOIS, geo-location,
denylist checks), and source-server details.
"""

from __future__ import annotations

import binascii
import datetime
import ipaddress
import json
import re
import socket
from typing import Any

import dns.resolver
import pydnsbl
import tldextract
from dateutil.parser import parse
from ipwhois import IPWhois
from mailsuite.utils import parse_authentication_results
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core import AuthenticationResults, EmailParserRouting, EmailUtilitiesManager
from ..core.IpLocation import DbIpCity


def ip_in_subnetwork(ip_address: str, subnetwork: str) -> bool:
    """Returns True if the given IP address belongs to the
    subnetwork expressed in CIDR notation, otherwise False.
    Both parameters are strings.

    Both IPv4 addresses/subnetworks (e.g. "1.1.1.1"
    and "1.1.1.1/24") and IPv6 addresses/subnetworks (e.g.
    "2a02:a448:ddb0::" and "2a02:a448:ddb0::/44") are accepted.

    Raises:
        ValueError: If the address and subnetwork are different IP versions.
    """
    (ip_integer, version1) = ip_to_integer(ip_address)
    (ip_lower, ip_upper, version2) = subnetwork_to_ip_range(subnetwork)

    if version1 != version2:
        raise ValueError("incompatible IP versions")

    return ip_lower <= ip_integer <= ip_upper


def ip_to_integer(ip_address: str) -> tuple[int, int]:
    """Converts an IP address expressed as a string to its
    representation as an integer value and returns a tuple
    (ip_integer, version), with version being the IP version
    (either 4 or 6).

    Both IPv4 addresses (e.g. "1.1.1.1") and IPv6 addresses
    (e.g. "2a02:a448:ddb0::") are accepted.

    Raises:
        ValueError: If the string is not a valid IPv4 or IPv6 address.
    """
    # try parsing the IP address first as IPv4, then as IPv6
    for version in (socket.AF_INET, socket.AF_INET6):
        try:
            ip_hex = socket.inet_pton(version, ip_address)
            ip_integer = int(binascii.hexlify(ip_hex), 16)

            return (ip_integer, 4 if version == socket.AF_INET else 6)
        except OSError:
            # not a valid address for this family; try the next one
            pass

    raise ValueError("invalid IP address")


def subnetwork_to_ip_range(subnetwork: str) -> tuple[int, int, int]:
    """Returns a tuple (ip_lower, ip_upper, version) containing the
    integer values of the lower and upper IP addresses respectively
    in a subnetwork expressed in CIDR notation (as a string), with
    version being the subnetwork IP version (either 4 or 6).

    Both IPv4 subnetworks (e.g. "1.1.1.1/24") and IPv6
    subnetworks (e.g. "2a02:a448:ddb0::/44") are accepted.

    Raises:
        ValueError: If the string is not a valid CIDR subnetwork.
    """
    try:
        fragments = subnetwork.split("/")
        network_prefix = fragments[0]
        netmask_len = int(fragments[1])

        # try parsing the subnetwork first as IPv4, then as IPv6
        for version in (socket.AF_INET, socket.AF_INET6):
            ip_len = 32 if version == socket.AF_INET else 128

            try:
                suffix_mask = (1 << (ip_len - netmask_len)) - 1
                netmask = ((1 << ip_len) - 1) - suffix_mask
                ip_hex = socket.inet_pton(version, network_prefix)
                ip_lower = int(binascii.hexlify(ip_hex), 16) & netmask
                ip_upper = ip_lower + suffix_mask

                return (ip_lower, ip_upper, 4 if version == socket.AF_INET else 6)
            except (OSError, ValueError):
                # not a valid network for this family; try the next one
                pass
    except (ValueError, IndexError):
        pass

    raise ValueError("invalid subnetwork")


def date_parser(line: str) -> datetime.datetime:
    """Parse a date out of a header line, tolerating fuzzy formats.

    Args:
        line: The header line to extract a date from.

    Returns:
        The parsed datetime.
    """
    try:
        r = parse(line, fuzzy=True)
    # if the fuzzy parser failed to parse the line due to
    # incorrect timezone information issue #5 GitHub
    except ValueError:
        r = re.findall(r"^(.*?)\s*(?:\(|utc)", line, re.IGNORECASE)
        if r:
            r = parse(r[0])
    return r


def get_header_val(h: str, data: str, rex: str = "\\s*(.*?)\n\\S+:\\s") -> str | None:
    """Extract the value of a single header from raw header text.

    Args:
        h: The header name to search for.
        data: The raw header text to search within.
        rex: The regex fragment matching the header's value.

    Returns:
        The matched header value, or None if not found.
    """
    r = re.findall(f"{h}:{rex}", data, re.VERBOSE | re.DOTALL | re.IGNORECASE)
    if r:
        return r[0].strip()
    return None


def get_auth_val(a: str, data: str, rex: str = r"(\w+)\b") -> str | None:
    """Parse a value out of the Authentication-Results header (legacy helper).

    Args:
        a: The authentication mechanism name to search for.
        data: The header text to search within.
        rex: The regex fragment matching the value.

    Returns:
        The matched value, or None if not found.
    """
    r = re.findall(rf"{a}={rex}", data, re.VERBOSE | re.DOTALL | re.IGNORECASE)
    if r:
        return r[0].strip()
    return None


def return_domain(email: str) -> str | None:
    """Return the domain portion of an email address.

    Args:
        email: An address, optionally in ``Display Name <local@domain>`` form.

    Returns:
        The domain after the ``@``, or None if no domain is present.
    """
    f_domain = re.search("<(.*?)>", email)

    if f_domain:
        domain = re.search("@(.*)", f_domain.group(1))
    else:
        domain = re.search("@(.*)", email)

    if domain is None:
        return None
    return domain.group(1)


def parse_hops(received: list[str], siemplify: SiemplifyAction) -> list[dict]:
    """Build per-hop relay details from a message's Received headers.

    Walks the Received headers oldest-first and, for each hop, records timing,
    the from/by hosts, and best-effort WHOIS, geo-location, and denylist (RBL)
    enrichment. Enrichment failures are logged and skipped rather than raised.

    Args:
        received: The message's Received header values.
        siemplify: The action object, used for logging.

    Returns:
        One dict of relay details per hop.
    """
    previous_hop = {}
    hops = []
    ip_checker = pydnsbl.DNSBLIpChecker()
    domain_checker = pydnsbl.DNSBLDomainChecker()
    for hop in reversed(received):
        hop_info = {}
        hop_info["blacklist_info"] = []
        hop_info["from_ip_whois"] = {}
        hop_info["by_ip_whois"] = {}

        parsed_route = EmailParserRouting.parserouting(hop)
        if "date" not in parsed_route:
            continue
        hop_info["time"] = (
            parsed_route["date"].astimezone(datetime.UTC).replace(tzinfo=None)
        )
        hop_info["blacklisted"] = False
        if "from" in parsed_route:
            for f in parsed_route["from"]:
                denylist = {}
                hop_info["from"] = f
                try:
                    ipaddress.ip_address(f)
                    ip_check = ip_checker.check(f)
                    # hop_info['from'] = f
                    try:
                        obj = IPWhois(f)
                        hop_info["from_ip_whois"] = obj.lookup_rdap(depth=1)
                        response = DbIpCity.get(f, api_key="free")
                        hop_info["from_geo"] = json.loads(response.to_json())
                    except Exception as e:
                        siemplify.LOGGER.debug(
                            f"WHOIS/geo enrichment failed for a from-hop IP: {e}",
                        )

                    denylist["blacklisted"] = ip_check.blacklisted
                    denylist["detected_by"] = ip_check.detected_by.copy()
                    denylist["categories"] = ip_check.categories.copy()
                    hop_info["blacklist_info"].append(denylist)
                except ValueError:
                    try:
                        domain_check = domain_checker.check(f)
                        resolved_ip_answer = dns.resolver.resolve(f)
                        # for r in resolved_ip_answer:
                        #    resolved_ip = r
                        try:
                            obj = IPWhois(resolved_ip_answer[0])
                            ip_whois = obj.lookup_rdap(depth=1)
                            response = DbIpCity.get(
                                resolved_ip_answer[0],
                                api_key="free",
                            )
                            hop_info["from_geo"] = json.loads(response.to_json())
                            hop_info["from_ip_whois"] = ip_whois
                        except Exception as e:
                            siemplify.LOGGER.debug(
                                "WHOIS/geo enrichment failed for a resolved "
                                f"from-hop host: {e}",
                            )

                        denylist["blacklisted"] = domain_check.blacklisted
                        denylist["detected_by"] = domain_check.detected_by.copy()
                        denylist["categories"] = domain_check.categories.copy()
                        hop_info["blacklist_info"].append(denylist)
                    except Exception as e:
                        siemplify.LOGGER.debug(
                            f"Denylist/DNS lookup failed for a from-hop host: {e}",
                        )
                except Exception as e:
                    siemplify.LOGGER.warn(f"Failed to analyze a from-hop: {e}")

                if "blacklisted" in denylist:
                    if denylist["blacklisted"]:
                        hop_info["blacklisted"] = True
        else:
            hop_info["from"] = ""
        if "by" in parsed_route:
            hop_info["by"] = parsed_route["by"][0]
            try:
                ipaddress.ip_address(hop_info["by"])

                obj = IPWhois(hop_info["by"])

                response = DbIpCity.get(hop_info["by"], api_key="free")
                hop_info["by_geo"] = json.loads(response.to_json())
                hop_info["by_ip_whois"] = obj.lookup_rdap(depth=1)

            except Exception as e:
                siemplify.LOGGER.debug(
                    f"by-hop is not a direct IP or enrichment failed, trying DNS: {e}",
                )
                try:
                    resolved_ip_answer = dns.resolver.resolve(hop_info["by"])
                    resolved_ip = resolved_ip_answer[0]
                    try:
                        obj = IPWhois(resolved_ip)
                        hop_info["by_ip_whois"] = obj.lookup_rdap(depth=1)
                        response = DbIpCity.get(resolved_ip, api_key="free")
                        hop_info["by_geo"] = json.loads(response.to_json())
                    except Exception as e:
                        siemplify.LOGGER.debug(
                            "WHOIS/geo enrichment failed for a resolved "
                            f"by-hop host: {e}",
                        )
                except Exception as e:
                    siemplify.LOGGER.debug(
                        f"Could not resolve/enrich a by-hop host: {e}",
                    )

        if "with" in parsed_route:
            hop_info["with"] = parsed_route["with"].split(" ")[0]
        else:
            hop_info["with"] = ""
        if previous_hop:
            hop_info["delay"] = (
                parsed_route["date"] - previous_hop["date"]
            ).total_seconds()
        else:
            hop_info["delay"] = "*"
        previous_hop = hop_info
        previous_hop["date"] = parsed_route["date"]
        hops.append(hop_info)
    return hops


def coalesce(input_dict: dict, *arg: str) -> Any:
    """Return the first present key's value from a dict.

    Args:
        input_dict: The dict to look in.
        *arg: Candidate keys, tried in order.

    Returns:
        The first matching value (its first element if that value is a list),
        or None if no candidate key is present.
    """
    for el in arg:
        if el in input_dict:
            if isinstance(input_dict[el], list):
                return input_dict[el][0]
            return input_dict[el]
    return None


def build_result(header: dict, siemplify: SiemplifyAction) -> dict:
    """Assemble the full analysis result for a set of email headers.

    Args:
        header: The email headers as a mapping of name to value(s).
        siemplify: The action object, used for logging.

    Returns:
        The analysis result: sender metadata, authentication results and
        summaries, DKIM/ARC verification, relay info, and source server.
    """
    result = {
        "From": coalesce(header, "from"),
        "To": coalesce(header, "to", "delivered-to"),
        "Subject": coalesce(header, "subject"),
        "MessageID": coalesce(header, "message-id"),
        "Date": coalesce(header, "date"),
    }
    result["FromDomain"] = return_domain(result["From"])

    ext = tldextract.extract(result["FromDomain"])

    result["FromParentDomain"] = f"{ext.domain}.{ext.suffix}"
    result["MFromDomain"] = return_domain(coalesce(header, "return-path", "from"))
    try:
        dmarc_sig = coalesce(header, "authentication-results")
        res = re.search(r"header.i=@(.*?)\s", dmarc_sig)
        if res:
            result["DmarcDomain"] = res.group(1)
    except Exception as e:
        siemplify.LOGGER.debug(f"Could not derive DmarcDomain from headers: {e}")

    try:
        received_spf = header.get("received-spf")[0]
        res = re.search(r"domain of (?:.*?@)?(.*?)\s", received_spf)
        if res:
            result["SPFDomain"] = res.group(1)
    except Exception as e:
        siemplify.LOGGER.debug(f"Could not derive SPFDomain from headers: {e}")
    # The receiving MTA records the actual SPF/DKIM/DMARC verdict for *this*
    # message in the Authentication-Results header(s). Parse those to report
    # whether the email passed authentication, rather than looking up the From
    # domain's published policy (which only describes what the domain enforces,
    # not whether this particular message passed it).
    # Repeated headers may arrive either as a list under the
    # "authentication-results" key (eml_parser shape) or as separate "_N"-suffixed
    # keys (message_from_string shape); collect and flatten both into one list.
    auth_results = []
    for key, value in header.items():
        if re.sub(r"_\d+$", "", key).lower() == "authentication-results":
            if isinstance(value, list):
                auth_results.extend(value)
            else:
                auth_results.append(value)
    if auth_results:
        try:
            result["AuthenticationResults"] = parse_authentication_results(
                auth_results,
                from_domain=result["FromDomain"],
            )
        except ValueError as e:
            result["AuthenticationResults"] = [{"error": str(e)}]
    else:
        result["AuthenticationResults"] = []

    # A receiver may emit one combined Authentication-Results header or split the
    # checks across several (e.g. Postfix with separate milters). Collapse them
    # into a provider-independent summary, and also keep them grouped by
    # authserv-id so a consumer can weigh which server's verdict to trust.
    result["AuthenticationSummary"] = (
        AuthenticationResults.summarize_authentication_results(
            result["AuthenticationResults"],
        )
    )
    result["AuthenticationByServer"] = (
        AuthenticationResults.group_authentication_results_by_server(
            result["AuthenticationResults"],
        )
    )

    dkim = EmailUtilitiesManager.DKIM(logger=siemplify.LOGGER, headers=header)
    arc = EmailUtilitiesManager.ARC(logger=siemplify.LOGGER, headers=header)

    try:
        result["DKIMVerify"] = dkim.verify()
    except Exception as e:
        result["DKIMVerify"] = "error"
        result["DKIMVerificationError"] = str(e)

    arc_res = {}
    try:
        arc_res["result"], arc_res["details"], arc_res["reason"] = arc.verify()
        arc_res["result"] = arc_res["result"].decode()
        result["ARCVerify"] = arc_res
    except Exception as e:
        result["ARCVerify"] = {"result": "error"}
        siemplify.LOGGER.debug(f"ARC verification failed: {e}")
    result["RelayInfo"] = []
    result["SourceServer"] = ""

    try:
        result["RelayInfo"] = parse_hops(header["received"], siemplify)
        for fromserver_str in reversed(header["received"]):
            if "by" in fromserver_str:
                fromserver = EmailParserRouting.parserouting(fromserver_str)
                try:
                    if "by" in fromserver:
                        ipaddress.ip_address(fromserver["by"][0])
                        result["SourceServerIP"] = fromserver["by"][0]
                        result["SourceServer"] = fromserver["by"][0]
                except Exception as e:
                    siemplify.LOGGER.debug(
                        f"Source server is not a direct IP, resolving by name: {e}",
                    )
                    if "by" in fromserver:
                        result["SourceServer"] = fromserver["by"][0]
                        try:
                            result["SourceServerIP"] = (
                                EmailUtilitiesManager.Resolver().query(
                                    result["SourceServer"],
                                )[0][2]
                            )
                        except Exception as e:
                            siemplify.LOGGER.debug(
                                f"Could not resolve source server IP: {e}",
                            )
                continue
    except Exception as e:
        siemplify.LOGGER.warn(f"Failed to build relay/source-server info: {e}")

    try:
        result["StrongSPF"] = EmailUtilitiesManager.SpfRecord.from_domain(
            result["FromDomain"],
        ).is_record_strong()
    except Exception as e:
        result["StrongSPF"] = False
        siemplify.LOGGER.debug(f"Could not evaluate StrongSPF: {e}")

    return result


@output_handler
def main(siemplify: SiemplifyAction) -> None:
    """Parse the "Headers JSON" action parameter and emit the analysis result."""
    headers_json = siemplify.extract_action_param(
        "Headers JSON",
        default_value="{}",
        print_value=False,
    )

    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = (
        "output message :"  # human readable message, showed in UI as the action result
    )
    result_value = (
        None  # Set a simple result value, used for playbook if\else and placeholders.
    )
    h = json.loads(headers_json)

    headers_res = build_result(h, siemplify)
    # print(json.dumps(headers_res, indent=4, sort_keys=True, default=str))
    siemplify.result.add_result_json(headers_res)
    siemplify.result.add_json("Headers", headers_res)
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    siemplify = SiemplifyAction()
    siemplify.script_name = "Analyze Headers"
    main(siemplify)
