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

import datetime
import ipaddress
import json
import re
from typing import Any

import dns.resolver
import pydnsbl
import tldextract
from ipwhois import IPWhois
from mailsuite.utils import parse_authentication_results
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core import AuthenticationResults, EmailParserRouting, EmailUtilitiesManager
from ..core.IpLocation import DbIpCity


def return_domain(email: str | None) -> str | None:
    """Return the domain portion of an email address.

    Args:
        email: An address, optionally in ``Display Name <local@domain>`` form.
            Some parsers hand repeated headers over as a list; the first entry
            is used in that case.

    Returns:
        The domain after the ``@``, or None if no domain is present or the
        input is not a string (e.g. the header is missing).
    """
    if isinstance(email, list):
        email = email[0] if email else None
    if not isinstance(email, str):
        return None
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
                    # Private/reserved relay addresses can't appear on public
                    # denylists, and querying RBL, WHOIS, and geo-IP services
                    # about them would leak internal topology to third parties.
                    if not ipaddress.ip_address(f).is_global:
                        siemplify.LOGGER.debug(
                            "Skipping RBL/WHOIS/geo enrichment for a "
                            "non-global from-hop IP",
                        )
                    else:
                        ip_check = ip_checker.check(f)
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
                        resolved_ip = str(dns.resolver.resolve(f)[0])
                        if ipaddress.ip_address(resolved_ip).is_global:
                            try:
                                obj = IPWhois(resolved_ip)
                                ip_whois = obj.lookup_rdap(depth=1)
                                response = DbIpCity.get(resolved_ip, api_key="free")
                                hop_info["from_geo"] = json.loads(response.to_json())
                                hop_info["from_ip_whois"] = ip_whois
                            except Exception as e:
                                siemplify.LOGGER.debug(
                                    "WHOIS/geo enrichment failed for a resolved "
                                    f"from-hop host: {e}",
                                )
                        else:
                            siemplify.LOGGER.debug(
                                "Skipping WHOIS/geo enrichment for a from-hop "
                                "host that resolves to a non-global IP",
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
                by_ip = ipaddress.ip_address(hop_info["by"])
            except ValueError:
                by_ip = None
            if by_ip is not None:
                if by_ip.is_global:
                    try:
                        obj = IPWhois(hop_info["by"])
                        response = DbIpCity.get(hop_info["by"], api_key="free")
                        hop_info["by_geo"] = json.loads(response.to_json())
                        hop_info["by_ip_whois"] = obj.lookup_rdap(depth=1)
                    except Exception as e:
                        siemplify.LOGGER.debug(
                            f"WHOIS/geo enrichment failed for a by-hop IP: {e}",
                        )
                else:
                    siemplify.LOGGER.debug(
                        "Skipping WHOIS/geo enrichment for a non-global by-hop IP",
                    )
            else:
                try:
                    resolved_ip = str(dns.resolver.resolve(hop_info["by"])[0])
                    if ipaddress.ip_address(resolved_ip).is_global:
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
                    else:
                        siemplify.LOGGER.debug(
                            "Skipping WHOIS/geo enrichment for a by-hop host "
                            "that resolves to a non-global IP",
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


def build_result(
    header: dict,
    siemplify: SiemplifyAction,
    use_authentication_results_original: bool = False,
    allow_multiple_authentication_results: bool = False,
) -> dict:
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

    if result["FromDomain"]:
        ext = tldextract.extract(result["FromDomain"])
        result["FromParentDomain"] = f"{ext.domain}.{ext.suffix}"
    else:
        result["FromParentDomain"] = None
    # MFromDomain is the RFC 5321 MAIL FROM (envelope) domain, taken from the
    # Return-Path header the final receiver writes from the envelope; when that
    # header is absent it falls back to the RFC 5322 From domain.
    result["MFromDomain"] = return_domain(coalesce(header, "return-path", "from"))

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
    # A Secure Email Gateway may preserve the internet-boundary results in an
    # Authentication-Results-Original header before stamping its own; prefer it
    # when the user opted in, falling back to Authentication-Results when the
    # message doesn't carry one.
    auth_results = []
    if use_authentication_results_original:
        auth_results = AuthenticationResults.collect_authentication_results(
            header,
            header_name="authentication-results-original",
        )
    if not auth_results:
        auth_results = AuthenticationResults.collect_authentication_results(header)
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
            allow_multiple=allow_multiple_authentication_results,
        )
    )
    result["AuthenticationByServer"] = (
        AuthenticationResults.group_authentication_results_by_server(
            result["AuthenticationResults"],
        )
    )

    # DMARC evaluates the RFC 5322 From domain, which the receiver records as
    # the dmarc method's header.from property (RFC 8601). The dkim method's
    # header.i property is a different identity (the AUID) and only matches the
    # DMARC domain when DKIM happens to be aligned, so it must not be used here.
    dmarc_domain = AuthenticationResults.get_dmarc_from_domain(
        result["AuthenticationResults"],
    )
    if dmarc_domain is None:
        try:
            res = re.search(
                r"header\.from=([^\s;]+)",
                " ".join(str(value) for value in auth_results),
            )
            if res:
                dmarc_domain = res.group(1)
        except Exception as e:
            siemplify.LOGGER.debug(f"Could not derive DmarcDomain from headers: {e}")
    if dmarc_domain:
        result["DmarcDomain"] = dmarc_domain

    # The spf method's smtp.mailfrom property is authoritative for the domain
    # SPF evaluated; the Received-SPF comment scraped above is free-form,
    # provider-specific text kept only as a fallback.
    spf_domain = AuthenticationResults.get_spf_mail_from_domain(
        result["AuthenticationResults"],
    )
    if spf_domain:
        result["SPFDomain"] = spf_domain

    dkim = EmailUtilitiesManager.DKIM(logger=siemplify.LOGGER, headers=header)
    arc = EmailUtilitiesManager.ARC(logger=siemplify.LOGGER, headers=header)

    # A message may carry several DKIM signatures (an ESP's and the brand's,
    # for example), so every signature is tried: DKIMVerify is True when any
    # of them verifies, and "error" only when every attempt raised.
    dkim_signatures = AuthenticationResults.collect_authentication_results(
        header,
        header_name="dkim-signature",
    )
    dkim_results = []
    dkim_errors = []
    for idx in range(max(1, len(dkim_signatures))):
        try:
            dkim_results.append(dkim.verify(idx=idx))
        except Exception as e:
            dkim_errors.append(str(e))
    if dkim_results:
        result["DKIMVerify"] = any(dkim_results)
    else:
        result["DKIMVerify"] = "error"
        result["DKIMVerificationError"] = "; ".join(dkim_errors)

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
        # Received headers are prepended by each hop, so walking the reversed
        # list visits the path oldest-first; the first hop with a "by" host is
        # the origin-side server that first received the message, which is what
        # SourceServer reports.
        for fromserver_str in reversed(header["received"]):
            if "by" not in fromserver_str:
                continue
            fromserver = EmailParserRouting.parserouting(fromserver_str)
            if "by" not in fromserver:
                continue
            by_host = fromserver["by"][0]
            result["SourceServer"] = by_host
            try:
                ipaddress.ip_address(by_host)
                result["SourceServerIP"] = by_host
            except ValueError:
                try:
                    result["SourceServerIP"] = EmailUtilitiesManager.Resolver().query(
                        by_host,
                        query_type="A",
                    )[0][2]
                except Exception as e:
                    siemplify.LOGGER.debug(
                        f"Could not resolve source server IP: {e}",
                    )
            break
    except Exception as e:
        siemplify.LOGGER.warn(f"Failed to build relay/source-server info: {e}")

    return result


@output_handler
def main(siemplify: SiemplifyAction) -> None:
    """Parse the "Headers JSON" action parameter and emit the analysis result."""
    headers_json = siemplify.extract_action_param(
        "Headers JSON",
        default_value="{}",
        print_value=False,
    )
    use_authentication_results_original = siemplify.extract_action_param(
        "Use Authentication-Results-Original Header",
        input_type=bool,
        default_value=False,
    )
    allow_multiple_authentication_results = siemplify.extract_action_param(
        "Allow Multiple Authentication-Results Headers",
        input_type=bool,
        default_value=False,
    )

    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = (
        "output message :"  # human readable message, showed in UI as the action result
    )
    result_value = (
        None  # Set a simple result value, used for playbook if\else and placeholders.
    )
    h = json.loads(headers_json)

    headers_res = build_result(
        h,
        siemplify,
        use_authentication_results_original=use_authentication_results_original,
        allow_multiple_authentication_results=allow_multiple_authentication_results,
    )
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
