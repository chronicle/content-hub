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
import base64
import email
import os

from urllib.parse import urlparse

import magic

import copy
import datetime
import hashlib
import json
import re
import uuid

import mailparser
from .constants import LOCALHOST
from mailparser import utils as mailparser_utils
from mailparser.const import EPILOGUE_DEFECTS
from soar_sdk.SiemplifyUtils import convert_string_to_datetime
from .UtilsManager import (
    dom_regex,
    email_regex,
    ipv4_regex,
    ipv6_regex,
    priv_ip_regex,
    recv_dom_regex_ignorecase,
    url_regex_simple,
)


class EmailParser:
    def __init__(self, siemplify, raw_string_mail):
        self.raw_string_mail = raw_string_mail
        self.mailparser_lib_mail = mailparser.parse_from_string(self.raw_string_mail)
        self.email_lib_mail = email.message_from_string(self.raw_string_mail)
        self.siemplify = siemplify

    def extract_content_transfer_encoding(self, raw_data_body):
        mail_part_list = raw_data_body.split("\r\n")
        content_transfer_encoding = ""
        for element in mail_part_list:
            if "Content-Transfer-Encoding" in element:
                content_transfer_encoding = element
                break
        return content_transfer_encoding.split(":")[1].strip()

    def parse_header_to(self, raw_data_mail):
        to_mails = [item for sublist in raw_data_mail.get("to", []) for item in sublist]
        return set([x for x in to_mails if re.match(email_regex, x)])

    def parse_to(self, raw_data_mail):
        to_mails = [item for sublist in raw_data_mail.get("to", []) for item in sublist]
        return [x for x in to_mails if re.match(email_regex, x)]

    def parse_body_base(self):
        body_parts = []
        txt_plain_parts = self.mailparser_lib_mail.text_plain
        txt_html_parts = self.mailparser_lib_mail.text_html

        txt_plain_parts_idx = 0
        txt_html_parts_idx = 0

        for part in self.email_lib_mail.walk():
            part_headers = {}
            for key, value in part.items():
                if key.lower() in part_headers:
                    part_headers[key.lower()].append(value)
                else:
                    part_headers[key.lower()] = [value]

            if part.get_content_type() not in [
                "text/html",
                "text/plain",
            ]:  # Validate regarding other unknown types
                continue
            if "attachment" in part_headers.get("content-disposition", ""):
                continue
            if part.get_content_type() == "text/html":
                content = txt_html_parts[txt_html_parts_idx]
                txt_html_parts_idx += 1
            else:
                content = txt_plain_parts[txt_plain_parts_idx]
                txt_plain_parts_idx += 1

            uris = self.parse_urls(content)

            charset = part.get_content_charset()
            if not charset:
                body = part.get_payload(decode=True)
            else:
                try:
                    body = part.get_payload(decode=True).decode(charset, "ignore")
                except Exception:
                    body = part.get_payload(decode=True).decode("ascii", "ignore")
            try:
                _hash = hashlib.sha256(body).hexdigest()
            except Exception:
                _hash = hashlib.sha256(body.encode("UTF-8")).hexdigest()

            content_header = part_headers
            content_header.update(
                {
                    "content-type": [part.get_content_type()],
                    "mime-version": part_headers.get("mime-version"),
                }
            )
            payload = {
                "content": content,
                "content_header": content_header,
                "content_type": part.get_content_type(),
                "domain": self.parse_domains(content),
                "hash": _hash,
                "uri": uris,
                "email": self.parse_body_emails(content),
            }
            content_transfer_encoding = part.get(
                "content-transfer-encoding", ""
            ).lower()
            if content_transfer_encoding:
                payload["content_header"]["content-transfer-encoding"] = [
                    content_transfer_encoding
                ]
            body_parts.append(payload)
        return body_parts

    def parse_body_emails(self, body_part):
        emails = set()
        re_emails = re.findall(email_regex, body_part)
        for email in re_emails:
            emails.add(email)

        return list(emails)

    def parse_emails(self, raw_data_mail):
        emails = set()
        for section in raw_data_mail.get("received", []):
            s = section.get("for", "")
            if s is not None:
                re_emails = re.findall(email_regex, s)
                for email in re_emails:
                    emails.add(email)

        for section in raw_data_mail.get("delivered-to", []):
            all_delivered = "".join(section)
            re_emails = re.findall(email_regex, all_delivered)
            for email in re_emails:
                emails.add(email)

        for section in raw_data_mail.get("to", []):
            all_delivered = "".join(section)
            re_emails = re.findall(email_regex, all_delivered)
            for email in re_emails:
                emails.add(email)

        for section in raw_data_mail.get("from", []):
            all_delivered = "".join(section)
            re_emails = re.findall(email_regex, all_delivered)
            for email in re_emails:
                emails.add(email)
        return list(emails)

    def parse_ips(self, raw_data_mail):
        ips = set()
        for section in raw_data_mail.get("received", []):
            s = section.get("from", "")
            if s is not None:
                from_ips = re.findall(ipv4_regex, s) + re.findall(ipv6_regex, s)
                for ip in from_ips:
                    ips.add(ip)
        return {"ips": ips}

    def parse_urls(self, body):
        list_observed_urls = []
        for match in url_regex_simple.findall(body):
            found_url = match[0].replace("hxxp", "http")
            found_url = urlparse(found_url).geturl()
            found_url = re.split(r"""[\', ", \,, \), \}, \\]""", found_url)[0]
            list_observed_urls.append(found_url)
        return list_observed_urls

    def parse_received_domain(self, raw_data_mail):
        received_domains = []
        new_received_domains = raw_data_mail.get("received", [])
        for receive in new_received_domains:
            doms = recv_dom_regex_ignorecase.findall(receive.get("by", ""))
            doms.extend(recv_dom_regex_ignorecase.findall(receive.get("from", "")))
            for dom in doms:
                if "." in dom:
                    try:
                        if ipv4_regex.match(dom) or dom == LOCALHOST:
                            continue
                    except ValueError:
                        pass
                received_domains.append(dom)
        return list(set(received_domains))

    def parse_received_foremail(self, raw_data_mail):
        received_foremail = self.parse_to(raw_data_mail)
        return list(set(received_foremail))

    def received_ip(self, raw_data_mail):
        ips = set()
        for section in raw_data_mail.get("received", []):
            data = [section.get("from", ""), section.get("by", "")]
            for s in data:
                from_ips = re.findall(ipv4_regex, s) + re.findall(ipv6_regex, s)
                for ip in from_ips:
                    if not priv_ip_regex.match(ip):
                        ips.add(ip)
        return list(ips)

    def get_attachments_md5(self, decoded_data):
        return hashlib.md5(decoded_data).hexdigest()

    def get_attachments_sha1(self, decoded_data):
        return hashlib.sha1(decoded_data).hexdigest()

    def get_attachments_sha256(self, decoded_data):
        return hashlib.sha256(decoded_data).hexdigest()

    def get_attachments_sha512(self, decoded_data):
        return hashlib.sha512(decoded_data).hexdigest()

    def get_mime_type(self, data):
        if magic:
            try:
                ms = magic.open(magic.NONE)
                ms.load()
                return ms.buffer(data).decode("utf-8")
            except Exception:
                pass
        return ""

    def get_mime_type_short(self, data):
        if magic:
            try:
                ms = magic.open(magic.MAGIC_MIME_TYPE)
                ms.load()
                return ms.buffer(data).decode("utf-8")
            except Exception:
                pass
        return ""

    @staticmethod
    def _is_attachment(mime_part: email.message.Message) -> bool:
        """
        Determine if a MIME part is a valid attachment or not.
        Based on :
        https://www.ietf.org/rfc/rfc2183.txt
        More about the content-disposition allowed fields and values:
        https://www.iana.org/assignments/cont-disp/cont-disp.xhtml#cont-disp-1
        Args:
            mime_part: The MIME part
        Returns:
            True if MIME part is an attachment, False otherwise
        """
        # Each attachment should have the Content-Disposition header
        content_disposition = mime_part.get("Content-Disposition", "")

        # "Real" attachments differs from inline attachments (like images in signature)
        # by having Content-Disposition headers, that starts with 'attachment'.
        # Inline attachments have the word 'inline' at the beginning of the header.
        # Inline attachments are being displayed as part of the email, and not as a separate
        # file. In most cases, the term attachment is related to the MIME parts that start with
        # 'attachment'.
        # The values are not case sensitive
        if content_disposition.lower().startswith("attachment"):
            return True
        if content_disposition.lower().startswith("inline"):
            return True
        if mime_part.get_content_maintype() == "image" and mime_part.get("Content-ID"):
            return True
        return False

    def get_msg_parts(self, msg):  # Taken from parse method in mailparser library
        parts = []  # Normal parts plus defects

        # walk all mail parts to search defects
        for p in msg.walk():
            part_content_type = p.get_content_type()
            self.mailparser_lib_mail._append_defects(p, part_content_type)
            parts.append(p)

        # If defects are in epilogue defects get epilogue
        if self.mailparser_lib_mail.defects_categories & EPILOGUE_DEFECTS:
            epilogue = mailparser_utils.find_between(
                self.mailparser_lib_mail.epilogue,
                f"{'--' + self.mailparser_lib_mail.get_boundary()}",
                f"{'--' + self.mailparser_lib_mail.get_boundary() + '--'}",
            )

            try:
                p = email.message_from_string(epilogue)
                parts.append(p)
            except TypeError:
                pass
            except Exception:
                pass
        return parts

    def _iterate_multipart_recursively(self, msg, counter=0):
        attachments = {}
        if msg.is_multipart():
            for part in msg.get_payload():
                attachments.update(self._iterate_multipart_recursively(part, counter))
        else:
            if not self._is_attachment(msg):
                return attachments

            # Attachment extraction is taken from parse() method in mailparser library
            parts = self.get_msg_parts(msg)
            for i, p in enumerate(parts):
                content_id = mailparser_utils.ported_string(p.get("content-id"))
                filename = mailparser_utils.decode_header_part(p.get_filename())
                if not filename:
                    filename = f"part-{counter:03d}"

                mail_content_type = mailparser_utils.ported_string(p.get_content_type())
                transfer_encoding = mailparser_utils.ported_string(
                    p.get("content-transfer-encoding", "")
                ).lower()
                content_disposition = mailparser_utils.ported_string(
                    p.get("content-disposition")
                )
                data = msg.get_payload(decode=True)
                attachments[str(uuid.uuid1())] = {
                    "content_header": {
                        "content-description": [filename or ""],
                        "content-disposition": [content_disposition or ""],
                        "content-id": [content_id or ""],
                        "content_transfer_encoding": [transfer_encoding or ""],
                        "content-type": [mail_content_type + f'; name="{filename}"'],
                    },
                    "hash": {
                        "md5": self.get_attachments_md5(data),
                        "sha1": self.get_attachments_sha1(data),
                        "sha256": self.get_attachments_sha256(data),
                        "sha512": self.get_attachments_sha512(data),
                    },
                    "filename": filename or "",
                    "extension": os.path.splitext(filename or "")[1][1:],
                    "mime_type_short": self.get_mime_type_short(data),
                    "mime_type": self.get_mime_type(data),
                    "raw": base64.b64encode(data),
                    "size": len(data),
                }

                counter += 1
        return attachments

    def parse_attachments(self):
        attachments = self._iterate_multipart_recursively(self.email_lib_mail, 0)
        if not attachments:
            return []
        else:
            all_attachments = []
            for _attachment_key, attachment in attachments.items():
                all_attachments.append(attachment)
        return all_attachments

    def parse_header_received(self, raw_data_mail):
        raw_received = raw_data_mail.get("received", [])
        srcs = []
        for k, v in self.mailparser_lib_mail.message.items():
            if k.lower() == "received":
                srcs.append(v)

        for i, item in enumerate(raw_received):
            if item.get("for"):
                emails = []
                for received_email in re.findall(email_regex, item.get("for", "")):
                    emails.append(received_email)
                if emails:
                    item.pop("for", None)
                    item.update({"for": list(set(emails))})
            if item.get("from"):
                froms = []
                for _from in re.findall(ipv4_regex, item.get("from", "")):
                    froms.append(_from)
                for _from in re.findall(ipv6_regex, item.get("from", "")):
                    froms.append(_from)
                for _from in re.findall(dom_regex, " " + item.get("from", "")):
                    froms.append(_from)
                if froms:
                    item.pop("from", None)
                    item.update({"from": list(set(froms))})
            if item.get("date"):
                try:
                    formatted_date = convert_string_to_datetime(
                        item.get("date_utc"), "UTC"
                    ).strftime("%Y-%m-%d %H:%M:%S%z")
                    timezone = formatted_date.split("+")[1]
                    timezone = timezone[:2] + ":" + timezone[2:]
                    item.pop("date", None)
                    item.update({"date": formatted_date.split("+")[0] + "+" + timezone})
                except Exception:
                    pass
            for src in srcs:
                if item.get("id", "") in src:
                    item["src"] = src
                    break

            if item.get("by"):
                by = recv_dom_regex_ignorecase.findall(item.get("by", ""))
                by.extend(ipv6_regex.findall(item.get("by", "")))
                by.extend(ipv4_regex.findall(item.get("by", "")))
                item.pop("by", None)
                item["by"] = by
        return raw_received

    def get_emails_from_header(self, header):
        # parse and decode to
        field = email.utils.getaddresses(self.email_lib_mail.get_all(header, []))
        return_field = []
        for m in field:
            if not m[1] == "":
                return_field.append(m[1].lower())
        return return_field

    def parse_headers(self, raw_data_mail):
        headers = {}
        for k, v in self.mailparser_lib_mail.message.items():
            if k.lower() in headers:
                headers[k.lower()].append(v)
            else:
                headers[k.lower()] = [v]
        return headers

    def parse_domains(self, payload):
        list_observed_dom = set()
        for match in dom_regex.findall(payload):
            list_observed_dom.add(match.lower())
        return list(list_observed_dom)

    def call_method(self, raw_data_mail, parse_methods_names):
        json_result = {}
        for _method in parse_methods_names:
            json_result.update(_method(raw_data_mail))
        return json_result

    def build_header_json(self, raw_data_mail):
        _from = re.findall(email_regex, self.mailparser_lib_mail.headers.get("From"))
        formatted_date = None
        try:
            formatted_date = convert_string_to_datetime(
                raw_data_mail.get("date"), "UTC"
            ).strftime("%Y-%m-%d %H:%M:%S%z")
        except Exception:
            pass
        headers = {
            "date": formatted_date or raw_data_mail.get("date"),
            "parse_date": datetime.datetime.utcnow(),
            "delivered_to": [self.mailparser_lib_mail.headers.get("Delivered-To")],
            "from": _from[0] if _from else "",
            "header": self.parse_headers(raw_data_mail),
            "received": self.parse_header_received(copy.deepcopy(raw_data_mail)),
            "received_domain": self.parse_received_domain(raw_data_mail),
            "received_foremail": self.parse_received_foremail(raw_data_mail),
            "received_ip": self.received_ip(raw_data_mail),
            "subject": self.mailparser_lib_mail.headers.get("Subject"),
            "to": self.parse_header_to(raw_data_mail),
        }
        cc = self.get_emails_from_header("cc")
        if cc:
            headers["cc"] = cc
        return headers

    def return_parsed_json_email(self):
        raw_data_mail = json.loads(self.mailparser_lib_mail.mail_json)
        parsed_urls = self.parse_urls(self.mailparser_lib_mail.body)
        return {
            "attached_emails": [],
            "attachment": self.parse_attachments(),
            "body": self.parse_body_base(),
            "domains": self.parse_domains(self.mailparser_lib_mail.body),
            "emails": self.parse_emails(raw_data_mail),
            "header": self.build_header_json(raw_data_mail),
            "ips": list(self.parse_ips(raw_data_mail).get("ips")),
            "urls": parsed_urls,
        }
