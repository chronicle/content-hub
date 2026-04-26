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

import binascii
import datetime
import ipaddress
import json
import re
import socket

import checkdmarc
import dns.resolver
import pydnsbl
import tldextract
from dateutil.parser import parse
from ipwhois import IPWhois
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core import EmailParserRouting, EmailUtilitiesManager
from ..core.IpLocation import DbIpCity


def ip_in_subnetwork(ip_address, subnetwork):
    """Returns True if the given IP address belongs to the
    subnetwork expressed in CIDR notation, otherwise False.
    Both parameters are strings.

    Both IPv4 addresses/subnetworks (e.g. "1.1.1.1"
    and "1.1.1.1/24") and IPv6 addresses/subnetworks (e.g.
    "2a02:a448:ddb0::" and "2a02:a448:ddb0::/44") are accepted.
    """
    (ip_integer, version1) = ip_to_integer(ip_address)
    (ip_lower, ip_upper, version2) = subnetwork_to_ip_range(subnetwork)

    if version1 != version2:
        raise ValueError("incompatible IP versions")

    return ip_lower <= ip_integer <= ip_upper


def ip_to_integer(ip_address):
    """Converts an IP address expressed as a string to its
    representation as an integer value and returns a tuple
    (ip_integer, version), with version being the IP version
    (either 4 or 6).

    Both IPv4 addresses (e.g. "1.1.1.1") and IPv6 addresses
    (e.g. "2a02:a448:ddb0::") are accepted.
    """
    # try parsing the IP address first as IPv4, then as IPv6
    for version in (socket.AF_INET, socket.AF_INET6):
        try:
            ip_hex = socket.inet_pton(version, ip_address)
            ip_integer = int(binascii.hexlify(ip_hex), 16)

            return (ip_integer, 4 if version == socket.AF_INET else 6)
        except:
            pass

    raise ValueError("invalid IP address")


def subnetwork_to_ip_range(subnetwork):
    """Returns a tuple (ip_lower, ip_upper, version) containing the
    integer values of the lower and upper IP addresses respectively
    in a subnetwork expressed in CIDR notation (as a string), with
    version being the subnetwork IP version (either 4 or 6).

    Both IPv4 subnetworks (e.g. "1.1.1.1/24") and IPv6
    subnetworks (e.g. "2a02:a448:ddb0::/44") are accepted.
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
            except:
                pass
    except:
        pass

    raise ValueError("invalid subnetwork")


def dateParser(line):
    """DateParser will read in a line and parse a date.
    :param line:
    :return: {str} string
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


def getHeaderVal(h, data, rex="\\s*(.*?)\n\\S+:\\s"):
    """GetHeaderVal will get the value from one of the email headers.
    :param h:
    :param data:
    :param rex:
    :return:
    """
    r = re.findall(f"{h}:{rex}", data, re.VERBOSE | re.DOTALL | re.IGNORECASE)
    if r:
        return r[0].strip()
    return None


def getAuthVal(a, data, rex=r"(\w+)\b"):
    """GetAuthVal parses the authentication-results header for values.
    Not really used any more.
    :param a:
    :param data:
    :param rex:
    :return:
    """
    r = re.findall(rf"{a}={rex}", data, re.VERBOSE | re.DOTALL | re.IGNORECASE)
    if r:
        return r[0].strip()
    return None


def return_domain(email):
    f_domain = re.search("<(.*?)>", email)

    if f_domain:
        domain = re.search("@(.*)", f_domain.group(1))
    else:
        domain = re.search("@(.*)", email)

    if domain == None:
        return None
    return domain.group(1)


def ip_check(ip, domain):
    spf_record = EmailUtilitiesManager.SpfRecord.from_domain(domain).record.split(" ")

    includes = [x.split(":")[1] for x in spf_record if x.startswith("include")]
    ips = [x.split(":")[1] for x in spf_record if x.startswith("ip")]
    for include_domain in includes:
        include_spf = EmailUtilitiesManager.SpfRecord.from_domain(
            include_domain,
        ).record.split(" ")
        includes.extend(
            [x.split(":")[1] for x in include_spf if x.startswith("include")],
        )
        ips.extend([x.split(":")[1] for x in include_spf if x.startswith("ip")])
    for cidr in ips:
        if ip_in_subnetwork(ip, cidr):
            return True
    return False


def parseHops(received):
    previous_hop = {}
    hops = []
    ip_checker = pydnsbl.DNSBLIpChecker()
    domain_checker = pydnsbl.DNSBLDomainChecker()
    for hop in reversed(received):
        hop_info = {}
        hop_info["blacklist_info"] = []
        hop_info["from_ip_whois"] = {}
        hop_info["by_ip_whois"] = {}

        try:
            parsed_route = EmailParserRouting.parserouting(hop)
        except Exception:
            raise
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
                    test_ip = ipaddress.ip_address(f)
                    ip_check = ip_checker.check(f)
                    # hop_info['from'] = f
                    try:
                        obj = IPWhois(f)
                        hop_info["from_ip_whois"] = obj.lookup_rdap(depth=1)
                        response = DbIpCity.get(f, api_key="free")
                        hop_info["from_geo"] = json.loads(response.to_json())
                    except Exception as expe:
                        template = (
                            "An exception of type {0} occurred. Arguments:\n{1!r}"
                        )
                        message = template.format(type(expe).__name__, expe.args)

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
                        except Exception as exp:
                            template = (
                                "An exception of type {0} occurred. Arguments:\n{1!r}"
                            )
                            message = template.format(type(exp).__name__, exp.args)

                        denylist["blacklisted"] = domain_check.blacklisted
                        denylist["detected_by"] = domain_check.detected_by.copy()
                        denylist["categories"] = domain_check.categories.copy()
                        hop_info["blacklist_info"].append(denylist)
                    except Exception as e:
                        template = (
                            "An exception of type {0} occurred. Arguments:\n{1!r}"
                        )
                        message = template.format(type(e).__name__, e.args)
                        logger(message)
                except Exception as ex:
                    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                    message = template.format(type(ex).__name__, ex.args)
                    logger(message)

                if "blacklisted" in denylist:
                    if denylist["blacklisted"] == True:
                        hop_info["blacklisted"] = True
        else:
            hop_info["from"] = ""
        if "by" in parsed_route:
            hop_info["by"] = parsed_route["by"][0]
            try:
                test_ip = ipaddress.ip_address(hop_info["by"])

                obj = IPWhois(hop_info["by"])

                response = DbIpCity.get(hop_info["by"], api_key="free")
                hop_info["by_geo"] = json.loads(response.to_json())
                hop_info["by_ip_whois"] = obj.lookup_rdap(depth=1)

            except Exception:
                try:
                    resolved_ip_answer = dns.resolver.resolve(hop_info["by"])
                    resolved_ip = resolved_ip_answer[0]
                    try:
                        obj = IPWhois(resolved_ip)
                        hop_info["by_ip_whois"] = obj.lookup_rdap(depth=1)
                        response = DbIpCity.get(resolved_ip, api_key="free")
                        hop_info["by_geo"] = json.loads(response.to_json())
                    except Exception as expl:
                        template = (
                            "An exception of type {0} occurred. Arguments:\n{1!r}"
                        )
                        message = template.format(type(expl).__name__, expl.args)
                except Exception as exp:
                    template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                    message = template.format(type(exp).__name__, exp.args)

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


def coalesce(input_dict, *arg):
    for el in arg:
        if el in input_dict:
            if isinstance(input_dict[el], list):
                return input_dict[el][0]
            return input_dict[el]
    return None


def buildResult(header, siemplify):
    """Creates the result object after parsing the email.
    :param header:
    :param mail_data:
    :return:
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
    except:
        pass

    try:
        received_spf = header.get("received-spf")[0]
        res = re.search(r"domain of (?:.*?@)?(.*?)\s", received_spf)
        if res:
            result["SPFDomain"] = res.group(1)
    except:
        pass
    domain_check = checkdmarc.check_domains(
        [result["FromDomain"]],
        include_tag_descriptions=True,
    )
    result["SPF"] = domain_check.get("spf")
    result["DMARC"] = domain_check.get("dmarc")
    result["MX"] = domain_check.get("mx")
    result["DNSSec"] = domain_check.get("dnssec")

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
    except:
        result["ARCVerify"] = {}
        result["ARCVerify"]["result"] = "error"
    result["RelayInfo"] = []
    result["SourceServer"] = ""

    try:
        result["RelayInfo"] = parseHops(header["received"])
        for fromserver_str in reversed(header["received"]):
            if "by" in fromserver_str:
                fromserver = EmailParserRouting.parserouting(fromserver_str)
                try:
                    if "by" in fromserver:
                        test_ip = ipaddress.ip_address(fromserver["by"][0])
                        result["SourceServerIP"] = fromserver["by"][0]
                        result["SourceServer"] = fromserver["by"][0]
                except Exception:
                    if "by" in fromserver:
                        result["SourceServer"] = fromserver["by"][0]
                        try:
                            result["SourceServerIP"] = (
                                EmailUtilitiesManager.Resolver().query(
                                    result["SourceServer"],
                                )[0][2]
                            )
                        except:
                            pass
                continue
    except Exception:
        pass

    try:
        result["SPF"]["Auth"] = ip_check(result["SourceServerIP"], result["FromDomain"])
    except Exception:
        result["SPF"]["Auth"] = False
    try:
        result["StrongSPF"] = EmailUtilitiesManager.SpfRecord.from_domain(
            result["FromDomain"],
        ).is_record_strong()
    except:
        result["StrongSPF"] = False

    return result


@output_handler
def main(siemplify):
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

    headers_res = buildResult(h, siemplify)
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
    logger = siemplify.LOGGER.info
    main(siemplify)
