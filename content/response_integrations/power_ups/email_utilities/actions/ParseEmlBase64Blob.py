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
import re
from email import message_from_string

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

# CONSTS:
EMAIL_PATTERN = "(?<=<)(.*?)(?=>)"


def _extract_subject(msg):
    # type: (email.message.Message) -> unicode
    """Extract message subject from email message.
    :param msg: {email.message.Message} Message object.
    :return: {string} Subject text.
    """
    raw_subject = msg.get("subject")
    if not raw_subject:
        return ""
    try:
        parsed_value, encoding = decode_header(raw_subject)[0]
        if encoding is None:
            return parsed_value
        return parsed_value.decode(encoding)
    except UnicodeDecodeError:
        msg = "Unable to decode email subject"
        return msg


def _is_attachment(mime_part, include_inline=False):
    # type: (email.message.Message, bool) -> bool
    """Determine if a MIME part is a valid attachment or not.
    Based on :
    https://www.ietf.org/rfc/rfc2183.txt
    More about the content-disposition allowed fields and values:
    https://www.iana.org/assignments/cont-disp/cont-disp.xhtml#cont-disp-1
    :param mime_part: {email.message.Message} The MIME part
    :param include_inline: {bool} Whether to consider inline attachments as well or not
    :return: {bool} True if MIME part is an attachment, False otherwise
    """
    # Each attachment should have the Content-Disposition header
    content_disposition = mime_part.get("Content-Disposition")

    if not content_disposition or not isinstance(content_disposition, str):
        return False

    # "Real" attachments differs from inline attachments (like images in signature)
    # by having Content-Disposition headers, that starts with 'attachment'.
    # Inline attachments have the word 'inline' at the beginning of the header.
    # Inline attachments are being displayed as part of the email, and not as a separate
    # file. In most cases, the term attachment is related to the MIME parts that start with
    # 'attachment'.
    # The values are not case sensitive
    if content_disposition.lower().startswith("attachment"):
        return True

    if include_inline and content_disposition.lower().startswith("inline"):
        return True

    return False


def extract_content(msg):
    """Extracts content from an e-mail message.
    :param msg: {email.message.Message} An eml object
    :return: {tuple} Text body, Html body, files dict (file_name: file_hash),
    count of parts of the emails
    """
    html_body = ""
    text_body = ""
    count = 0

    if not msg.is_multipart():
        # Not an attachment!
        # See where this belong - text_body or html_body
        content_type = msg.get_content_type()
        if content_type == "text/plain":
            text_body += msg.get_payload(decode=True).decode("utf-8")
        elif content_type == "text/html":
            html_body += msg.get_payload(decode=True).decode("utf-8")

        return text_body, html_body, 1

    # This IS a multipart message.
    # So, we iterate over it and call extract_content() recursively for
    # each part.
    for part_msg in msg.get_payload():
        # part is a new Message object which goes back to extract_content
        part_text_body, part_html_body, part_count = extract_content(part_msg)
        text_body += part_text_body
        html_body += part_html_body
        count += part_count

    return text_body, html_body, count


def extract_field(field):
    temp = re.findall(EMAIL_PATTERN, field)
    if temp:
        return temp
    return field


def extract_metadata(msg):
    """Extract metadata (sender, recipient, date and subject) from EML
    :param msg: {email.message.Message} An eml object
    :return: (tuple) sender, recipient, date and subject
    """
    return (
        extract_field(msg.get("from", "").strip()),
        extract_field(msg.get("to", "").strip()),
        extract_field(msg.get("cc", "").strip()),
        extract_field(msg.get("bcc", "").strip()),
        msg.get("subject", "").strip(),
        msg.get("date", "").strip(),
    )


@output_handler
def main():
    siemplify = SiemplifyAction()
    output_message = "No EML found"
    result_value = False

    base64_blob = siemplify.parameters.get("Base64 EML Blob")
    eml_content = base64.b64decode(base64_blob).decode("utf-8")

    json_result = []

    email = message_from_string(eml_content)
    sender, to, cc, bcc, subject, date = extract_metadata(email)
    text_body, html_body, count = extract_content(email)
    curr_json_result = {
        "base64_blob": base64_blob,
        "headers": email._headers,
        "sender": sender,
        "to": to,
        "cc": cc,
        "bcc": bcc,
        "subject": subject,
        "date": date,
        "text_body": text_body,
        "html_body": html_body,
        "count": count,
    }
    json_result.append({"Entity": subject, "EntityResult": curr_json_result})
    for i, item in enumerate(email.get_payload()):
        if item.is_multipart():
            # print("Item {} is multipart".format(i))
            for part in item.get_payload():
                if _is_attachment(part):
                    # print ("DEBUG if: part is attachment".format())
                    pass
                elif part.is_multipart():  # part.get_content_maintype() == "multipart":
                    # print ("DEBUG elif: part is multipart".format())

                    # Here we assume it was an EML attachment and want to return it

                    curr_b64_blob = base64.b64encode(
                        part.as_string().encode("utf-8"),
                    ).decode("utf-8")
                    file_name = "UNKOWN"
                    for header in part.items():
                        if header[0].lower() == "subject":
                            file_name = header[1]

                    sender, to, cc, bcc, subject, date = extract_metadata(part)
                    text_body, html_body, count = extract_content(part)
                    curr_json_result = {
                        "base64_blob": curr_b64_blob,
                        "headers": part._headers,
                        "sender": sender,
                        "to": to,
                        "cc": cc,
                        "bcc": bcc,
                        "subject": subject,
                        "date": date,
                        "text_body": text_body,
                        "html_body": html_body,
                        "count": count,
                    }
                    json_result.append(
                        {"Entity": file_name, "EntityResult": curr_json_result},
                    )
                    for part2 in part.get_payload():
                        #  print ("DEBUG PART2: part2 is {}".format(part2.get_content_maintype()))
                        pass
                else:
                    pass
                    # print ("DEBUG else: part is {}".format(part.get_content_maintype()))
        else:
            print(f"Item {i} is NOT multipart")
    siemplify.result.add_result_json(json_result)
    if json_result:
        output_message = "EML found and returned in json result"
        result_value = True

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
