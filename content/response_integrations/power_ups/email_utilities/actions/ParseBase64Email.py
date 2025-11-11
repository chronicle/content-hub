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

import base64
import collections
import datetime
import hashlib
import ipaddress
import json
import os.path
import re
import typing
from collections import Counter

import extract_msg
import olefile
from msg_parser import MsOxMessage
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from tld import get_fld
from urlextract import URLExtract

from ..core import EmailParser, EmailParserRegex, EmailParserRouting


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime.datetime):
        serial = obj.isoformat()
        return serial
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode()
    raise TypeError("Type not serializable")


def parse_headers(msg, denylist=[], is_allowlist=False, stop_transport=""):
    transport = []
    transport_stopped = False
    headers = {}
    for r in msg.header._headers[::-1]:
        if stop_transport and r[0].lower() == stop_transport.lower():
            transport_stopped = True
        if r[0].lower() == "received" and not transport_stopped:
            trans = {"Name": r[0].lower(), "Header": r[1]}
            trans.update(parse_transport(r[0], r[1]))
            transport.append(trans)
        if is_allowlist:
            if r[0].lower() in denylist:
                # h = {"Name": r[0].lower(), "Header": r[1]}
                # h.update(parse_transport(r[0], r[1]))
                # header.append(h)
                if r[0].lower() not in headers:
                    headers[r[0].lower()] = []
                headers[r[0].lower()].append(r[1])
        elif r[0].lower() not in denylist:
            # h = {"Name": r[0].lower(), "Header": r[1]}
            # h.update(parse_transport(r[0], r[1]))
            # header.append(h)
            if r[0].lower() not in headers:
                headers[r[0].lower()] = []
            headers[r[0].lower()].append(r[1])

    return headers, transport


def string_sliding_window_loop(
    body: str,
    slice_step: int = 50000,
) -> typing.Iterator[str]:
    """Yield a more or less constant slice of a large string.
    If we start directly a *re* findall on 500K+ body we got time and memory issues.
    If more than the configured slice step, lets cheat, we will cut around the thing we search "://, @, ."
    in order to reduce regex complexity.

    Args:
        body: Body to slice into smaller pieces.
        slice_step: Slice this number or characters.

    Returns:
        typing.Iterator[str]: Sliced body string.

    """
    body_length = len(body)
    if body_length <= slice_step:
        yield body

    else:
        ptr_start = 0
        for ptr_end in range(slice_step, body_length, slice_step):
            if " " in body[ptr_end - 1 : ptr_end]:
                while not (
                        EmailParserRegex.window_slice_regex.match(
                        body[ptr_end - 1 : ptr_end],
                    )
                        or ptr_end > body_length
                ):
                    if ptr_end > body_length:
                        ptr_end = body_length
                        break

                    ptr_end += 1

            yield body[ptr_start:ptr_end]

            ptr_start = ptr_end


def get_uri_ondata(body: str) -> list[str]:
    """Function for extracting URLs from the input string.

    Args:
        body (str): Text input which should be searched for URLs.

    Returns:
        list: Returns a list of URLs found in the input string.

    """
    list_observed_urls: typing.Counter[str] = Counter()

    extractor = URLExtract()

    for found_url in extractor.find_urls(body, check_dns=True):
        if "." not in found_url:
            # if we found a URL like e.g. http://afafasasfasfas; that makes no
            # sense, thus skip it
            continue
        list_observed_urls[found_url] = 1
        # found_url = urllib.parse.urlparse(found_url).geturl()
        # let's try to be smart by stripping of noisy bogus parts
        # found_url = re.split(r'''[', ")}\\]''', found_url, 1)[0]
        # list_observed_urls[found_url] = 1
    return list(list_observed_urls)


def parse_body(body):
    #    ep = eml_parser.EmlParser()
    parsed = {}
    list_observed_urls: list[str] = []
    list_observed_email: typing.Counter[str] = Counter()
    list_observed_dom: typing.Counter[str] = Counter()
    list_observed_ip: typing.Counter[str] = Counter()
    # print('parsing body')

    for body_slice in string_sliding_window_loop(body):
        list_observed_urls = get_uri_ondata(body_slice)
        extractor = URLExtract(extract_email=True)

        for match in extractor.find_urls(body_slice):
            # for match in EmailParserRegex.email_regex.findall(body_slice):
            c = URLExtract()
            removedurl = c.find_urls(match, check_dns=True)
            if not removedurl:
                match = match.replace("mailto:", "")
                list_observed_email[match.lower()] = 1
        for match in list_observed_urls:
            try:
                dom = get_fld(match.lower(), fix_protocol=True)
                list_observed_dom[dom] = 1
            except Exception:
                pass
                # list_observed_dom[match.lower()] = 1
        for match in EmailParserRegex.ipv4_regex.findall(body_slice):
            try:
                ipaddress_match = ipaddress.ip_address(match)
            except ValueError:
                continue
            else:
                if not (ipaddress_match.is_private):
                    list_observed_ip[match] = 1
        for match in EmailParserRegex.ipv6_regex.findall(body_slice):
            try:
                ipaddress_match = ipaddress.ip_address(match)
            except ValueError:
                continue
            else:
                if not (ipaddress_match.is_private):
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
        (
            collections.Counter()
        )  # Array for storing potential duplicate "HOP"
        if header:
            line = str(header).lower()
            received_line_flat = re.sub(r"(\r|\n|\s|\t)+", " ", line, flags=re.UNICODE)
            parsed_routing = ""
            if "received" in name.lower():
                parsed_routing = EmailParserRouting.parserouting(received_line_flat)
                headers_struc["received"].append(parsed_routing)
            ips_in_received_line_v4 = EmailParserRegex.ipv4_regex.findall(
                received_line_flat,
            )
            ips_in_received_line_v6 = EmailParserRegex.ipv6_regex.findall(
                received_line_flat,
            )

            for ip in ips_in_received_line_v4:
                try:
                    ip_obj = ipaddress.ip_address(ip)
                except ValueError:
                    print(f'Invalid IP in received line - "{ip}"')
                else:
                    if not (ip_obj.is_private):
                        headers_struc["ipv4"].append(str(ip_obj))

            for ip in ips_in_received_line_v6:
                try:
                    ip_obj = ipaddress.ip_address(ip)
                except ValueError:
                    print(f'Invalid IP in received line - "{ip}"')
                else:
                    if not (ip_obj.is_private):
                        headers_struc["ipv6"].append(str(ip_obj))

                # search for domain
            for m in EmailParserRegex.recv_dom_regex.findall(received_line_flat):
                try:
                    ip_obj = ipaddress.ip_address(m)
                except ValueError:
                    # we find IPs using the previous IP crawler, hence we ignore them
                    # here.
                    # iff the regex fails, we add the entry
                    headers_struc["domain"].append(m)

                # search for e-mail addresses
            for mail_candidate in EmailParserRegex.email_regex.findall(
                received_line_flat,
            ):
                # print(mail_candidate)
                if parsed_routing and mail_candidate not in parsed_routing.get(
                    "for",
                    [],
                ):
                    headers_struc["email"] += [mail_candidate]
            # print(headers_struc['email'])

    except TypeError:  # Ready to parse email without received headers.
        raise Exception("Exception occurred while parsing received lines.")

    headers_struc["email"] = list(set(headers_struc["email"]))
    headers_struc["domain"] = list(set(headers_struc["domain"]))
    headers_struc["ip"] = list(set(headers_struc["ipv4"])) + list(
        set(headers_struc["ipv6"]),
    )

    return headers_struc


def attachment(filename, content):
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


def body(msg, content_type):
    body_json = {
        "content_type": content_type,
        "content": msg if msg is not None else "",
        "hash": hashlib.sha256(str(msg).encode("utf-8")).hexdigest(),
    }
    body_json.update(parse_body(msg))
    return body_json


def header(x_msg, o_msg, denylist, is_allowlist, stop_transport):
    to_smtp = "null"
    from_smtp = "null"
    if "ReceivedByAddressType" in o_msg:
        if o_msg["ReceivedByAddressType"] == "EX":
            to_smtp = "ReceivedBySmtpAddress"
        else:
            to_smtp = "ReceivedByEmailAddress"

        if o_msg["SenderAddressType"] == "EX":
            from_smtp = "SenderSmtpAddress"
        else:
            from_smtp = "SenderEmailAddress"
    if to_smtp in o_msg:
        to = o_msg.get(to_smtp)
    else:
        to = x_msg.to

    if from_smtp in o_msg:
        from_header = o_msg.get(from_smtp)
    else:
        from_header = x_msg.sender

    headers, transport = parse_headers(x_msg, denylist, is_allowlist, stop_transport)

    header_json = {
        "to": [to],
        "from": from_header,
        "subject": o_msg["Subject"] if "Subject" in o_msg else x_msg.subject,
        "cc": x_msg.cc,
        "date": x_msg.date,
        "header": headers,
        "transport": transport,
    }

    return header_json


def fill_json(x_msg, o_msg, denylist, is_allowlist, stop_transport):
    _current_json = {
        "header": header(x_msg, o_msg, denylist, is_allowlist, stop_transport),
        "body": [body(x_msg.body, "text/plain")],
    }
    if x_msg.htmlBody:
        _current_json["body"].append(body(x_msg.htmlBody, "text/html"))
    return _current_json


def parse_msg(msg, denylist, is_allowlist, stop_transport):
    x_msg = extract_msg.Message(msg)
    msg_obj = MsOxMessage(msg)
    msox_msg = msg_obj._message.as_dict()

    _cur_json = fill_json(x_msg, msox_msg, denylist, is_allowlist, stop_transport)
    _cur_json["attached_emails"] = {}
    _cur_json["attachment"] = []

    # add the attachments to current json
    _att_counter = 0
    for _attachment in x_msg.attachments:
        # _attachment.save()
        msox_obj = None
        for msox_attachments in msox_msg["attachments"]:
            if (
                msox_msg["attachments"][msox_attachments]["AttachFilename"]
                == _attachment.shortFilename
            ):
                msox_obj = msox_msg["attachments"][msox_attachments]

        if _attachment.type in "msg":
            _attached_json = fill_json(
                _attachment.data,
                msox_obj["EmbeddedMessage"]["properties"],
                denylist,
                is_allowlist,
                stop_transport,
            )  # , attached_obj.as_dict())
            try:
                _attached_json["body"].append(
                    body(
                        base64.b64encode(_attachment.data.compressedRtf).decode(),
                        "text/base64",
                    ),
                )
                _attached_json["body"].append(body(attachment.data.rtfBody, "text/rtf"))
            except:
                pass
            for _attach_attached in _attachment.data.attachments:
                _attached_json["attachment"].append(
                    attachment(
                        filename=_attach_attached.shortFilename,
                        content=_attach_attached.data,
                    ),
                )
            _cur_json["attached_emails"][_attachment.shortFilename] = _attached_json
        elif _attachment.type in "data":
            # if attachment in parent msg has binary content
            _att_counter += 1
            _cur_json["attachment"].append(
                attachment(
                    filename=msox_obj["AttachLongFilename"],
                    content=_attachment.data,
                ),
            )
            # _cur_json['attachment'].append(attachment(filename = msox_obj['AttachLongFilename'], content = msox_obj['AttachDataObject']))
    #        _cur_json['attached_files'].append({"filename": _attachment.shortFilename, "base64_data":  base64.b64encode
    #                                (_attachment.data).decode()})
    return _cur_json


def process_attachment(attachment, denylist, is_allowlist, stop_transport):
    attached_msg = base64.b64decode(attachment["raw"])

    try:
        attached_parsed = EmailParser.decode_email_b(
            attached_msg,
            include_raw_body=True,
            include_attachment_data=True,
            email_force_tld=True,
        )
        if len(attached_parsed["header"]["to"]) == 0:
            attached_parsed = parse_msg(
                attached_msg,
                denylist,
                is_allowlist,
                stop_transport,
            )
    except:
        attached_parsed = parse_msg(
            attached_msg,
            denylist,
            is_allowlist,
            stop_transport,
        )
    return attached_parsed


def main():
    siemplify = SiemplifyAction()
    status = EXECUTION_STATE_COMPLETED  # used to flag back to siemplify system, the action final status
    output_message = (
        "output message :"  # human readable message, showed in UI as the action result
    )
    result_value = (
        None  # Set a simple result value, used for playbook if\else and placeholders.
    )

    siemplify.script_name = "Parse Email"
    base64_blob = siemplify.parameters["EML/MSG Base64 String"]
    denylist = list(
        set(
            [
                x.strip().lower()
                for x in (siemplify.parameters.get("Blacklisted Headers") or "").split(
                    ",",
                )
            ],
        ),
    )
    is_allowlist = siemplify.parameters["Use Blacklist As Whitelist"].lower() == "true"
    stop_transport = (
        siemplify.parameters.get("Stop Transport At Header", "") or ""
    ).strip() or ""
    content = base64.b64decode(base64_blob)

    try:
        if olefile.isOleFile(content):
            m = parse_msg(content, denylist, is_allowlist, stop_transport)

        else:
            m = EmailParser.decode_email_b(
                content,
                include_raw_body=True,
                include_attachment_data=True,
                email_force_tld=True,
            )

    except Exception:
        m = EmailParser.decode_email_b(
            content,
            include_raw_body=True,
            include_attachment_data=True,
            email_force_tld=True,
        )

    m["attached_emails"] = []
    m["attachments"] = []
    attachments = []
    nested_emails = {}
    eml_headers = m.get("header")

    m["urls"] = []
    m["domains"] = []
    m["emails"] = []

    m["observed"] = {}
    received = {}
    received["ips"] = []
    received["emails"] = []
    received["domains"] = []
    received["domains_internal"] = []
    received["foremail"] = []
    sending = {}
    sending["hosts"] = []
    sending["emails"] = []
    sending["domains"] = []

    m["received"] = received

    if "received_ip" in eml_headers:
        m["received"]["ips"].extend(eml_headers.get("received_ip"))

    if "received_email" in eml_headers:
        m["received"]["emails"].extend(eml_headers.get("received_email"))

    if "received_domain" in eml_headers:
        m["received"]["domains"].extend(eml_headers.get("received_domain"))

    if "received_domains_internal" in eml_headers:
        m["received"]["domains_internal"].extend(
            eml_headers.get("received_domains_internal"),
        )

    if "received_foremail" in eml_headers:
        m["received"]["foremail"].extend(eml_headers.get("received_foremail"))

    observed = {}
    observed["urls"] = []
    observed["domains"] = []
    observed["emails"] = []
    observed["ips"] = []
    m["observed"] = {}
    m["observed"] = observed

    try:
        for attachment in m["attachment"]:
            attachment["subject"] = m["header"]["subject"]
            attachments.append(attachment)
            try:
                nested_email = process_attachment(
                    attachment,
                    denylist,
                    is_allowlist,
                    stop_transport,
                )
                n_att = []
                if "attachment" in nested_email:
                    for nested_a in nested_email["attachment"]:
                        a = nested_a
                        del a["raw"]
                        a["subject"] = nested_email["header"]["subject"]
                        n_att.append(a)
                    nested_email["attachments"] = n_att

                    for nested_attachment in nested_email["attachment"]:
                        # attachments.append(nested_attachment)
                        try:
                            nested_nested_email = process_attachment(
                                nested_attachment,
                                denylist,
                                is_allowlist,
                                stop_transport,
                            )
                            nested_attachments_holder = []
                            for nested_nested_attachment in nested_nested_email[
                                "attachment"
                            ]:
                                # attachments.append(nested_nested_attachment)
                                del nested_nested_attachment["raw"]
                                nested_attachments_holder.append(
                                    nested_nested_attachment,
                                )
                            nested_nested_email["attachments"] = (
                                nested_attachments_holder
                            )
                            del nested_nested_email["attachment"]
                            nested_nested_email["filename"] = nested_attachment[
                                "filename"
                            ]
                            nested_emails[nested_attachment["hash"]["md5"]] = {
                                "filename": nested_attachment["filename"],
                                "email": nested_nested_email,
                            }
                        except Exception:
                            pass

                    del nested_email["attachment"]

                nested_email["filename"] = attachment["filename"]
                nested_emails[attachment["hash"]["md5"]] = {
                    "filename": attachment["filename"],
                    "email": nested_email,
                }
            except Exception as b:
                print("failed in attachment parsing")
                print(b)
        m["attachments"] = list({v["hash"]["sha256"]: v for v in attachments}.values())
        m["attached_emails"] = list(nested_emails.values())

        del m["attachment"]
        for b in m["body"]:
            m["observed"]["domains"].extend(b.get("domain", []))
            m["observed"]["urls"].extend(b.get("uri", []))
            m["observed"]["emails"].extend(b.get("email", []))

        for attached_email in m["attached_emails"]:
            for email_body in attached_email["email"]["body"]:
                m["observed"]["domains"].extend(email_body.get("domain", []))
                m["observed"]["urls"].extend(email_body.get("uri", []))
                m["observed"]["ips"].extend(email_body.get("ip", []))
                m["observed"]["emails"].extend(email_body.get("email", []))

            eml_headers = attached_email.get("email").get("header")

            if "received_ip" in eml_headers:
                m["received"]["ips"].extend(eml_headers.get("received_ip"))

            if "received_email" in eml_headers:
                m["received"]["emails"].extend(eml_headers.get("received_email"))

            if "received_domain" in eml_headers:
                m["received"]["domains"].extend(eml_headers.get("received_domain"))

            if "received_foremail" in eml_headers:
                m["received"]["foremail"].extend(eml_headers.get("received_foremail"))

            if "received_domains_internal" in eml_headers:
                m["received"]["domains_internal"].extend(
                    eml_headers.get("received_domains_internal"),
                )

        siemplify.LOGGER.info("header")
        siemplify.LOGGER.info(m["header"])
        siemplify.LOGGER.info("header")
        m["observed"]["domains"] = list(set(m["observed"]["domains"]))
        m["observed"]["urls"] = list(set(m["observed"]["urls"]))
        m["observed"]["emails"] = list(set(m["observed"]["emails"]))
        m["observed"]["ips"] = list(set(m["observed"]["ips"]))

        m["received"]["ips"] = list(set(m["received"]["ips"]))
        m["received"]["emails"] = list(set(m["received"]["emails"]))
        m["received"]["domains"] = list(set(m["received"]["domains"]))
        m["received"]["foremail"] = list(set(m["received"]["foremail"]))
        m["received"]["domains_internal"] = list(set(m["received"]["domains_internal"]))

        m["domains"] = m["observed"]["domains"].copy()
        m["domains"].extend(m["received"]["domains"])
        m["domains"].extend(m["received"]["domains_internal"])
        m["domains"] = list(set(m["domains"]))

        m["ips"] = m["observed"]["ips"].copy()
        m["ips"].extend(m["received"]["ips"])
        m["ips"] = list(set(m["ips"]))

        m["emails"] = m["observed"]["emails"].copy()
        m["emails"].extend(m["received"]["emails"])
        m["emails"].extend(m["received"]["foremail"])
        m["emails"] = list(set(m["emails"]))

        m["urls"] = m["observed"]["urls"]

    except Exception as e:
        siemplify.LOGGER.error(e)

    siemplify.result.add_result_json(json.dumps(m, sort_keys=True, default=str))
    siemplify.result.add_json("Parsed Mail", m)

    output_message = "Parsed message file."
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: {output_message}",
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
