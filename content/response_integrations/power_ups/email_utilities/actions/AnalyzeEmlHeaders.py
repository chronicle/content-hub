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

# TODO: Implement the following features:
# 1) Add DMARC, SPF, DKIM and ARC verification flags. If exists and if pass or not (pass/fail)

from __future__ import annotations

import base64
import json
import re
from email import message_from_string

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

INTEGRATION_NAME = "EmailUtilties"
SCRIPT_NAME = "Analyze EML Headers"
EXCLUDED_DOMAINS_ADDRESSES = ["127.0.0.1", "localhost"]

EMAIL_ADDRESS_REGEX = r"""(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])"""

RED_COLOR = "FF0000"
GREEN_COLOR = "00FF00"
DOT_HTML_SNNIPET = """<div style="text-align:center"><span style="height: 5px;  width: 5px;  background-color: #{};  border-radius: 50%;  display: inline-block;"></span></div>"""
# DOT_HTML_SNNIPET = """<style>.dot_insight {{{{  height: 5px;  width: 5px;  background-color: #{};  border-radius: 50%;  display: inline-block;}}}}</style><div style="text-align:center">  <span class="dot_insight"></span>{{}}</div>"""
RED_DOT_HTML_SNNIPET = DOT_HTML_SNNIPET.format(RED_COLOR)
GREEN_DOT_HTML_SNNIPET = DOT_HTML_SNNIPET.format(GREEN_COLOR)


def get_html_headers_table(headers):
    html_table = "<table><tbody>{}</tbody></table>"
    rows = []
    for k, v in headers.items():
        row = f"<tr><td>{k}</td><td>{v}</td></tr>"
        rows.append(row)
    return html_table.format("".join(rows))


def get_domains_and_addresses(headers):
    list_of_tuples = []
    for k, v in headers.items():
        if k.startswith("Received"):
            tuple_result = process_header_to_extract_domain_address(v)
            if tuple_result:
                list_of_tuples.append(tuple_result)

    return list_of_tuples


def process_header_to_extract_domain_address(header):
    extracted_domains = re.findall(r"\s\((.*?)\.{0,1}\s\[", header)
    extracted_addresses = re.findall(r"\s\[(.*?)\]\)", header)

    if extracted_domains and extracted_addresses:
        if extracted_domains[0] in EXCLUDED_DOMAINS_ADDRESSES or extracted_addresses[0] in EXCLUDED_DOMAINS_ADDRESSES:
            return None
        return extracted_domains[0], extracted_addresses[0]
    return None


def get_generic_siemplify_recommendations(headers):
    return_list = []
    lower_case_headers = {k.lower(): v for k, v in headers.items()}

    if "Return-Path".lower() in lower_case_headers:
        flag = False
        if "From".lower() in lower_case_headers:
            if re.findall(
                EMAIL_ADDRESS_REGEX,
                lower_case_headers["Return-Path".lower()],
            ) != re.findall(EMAIL_ADDRESS_REGEX, lower_case_headers["From".lower()]):
                return_list.append(
                    {
                        "message": '"Return-Path" header does not match "From" header',
                        "score": 6,
                        "status": RED_DOT_HTML_SNNIPET,
                    },
                )

        if "X-Original-Sender".lower() in lower_case_headers:
            if (
                re.findall(
                    EMAIL_ADDRESS_REGEX,
                    lower_case_headers["Return-Path".lower()],
                )
                != lower_case_headers["X-Original-Sender".lower()]
            ):
                return_list.append(
                    {
                        "message": '"Return-Path" header does not match "X-Original-Sender" header',
                        "score": 5,
                        "status": RED_DOT_HTML_SNNIPET,
                    },
                )

        if flag:
            return_list.append(
                {
                    "message": '"Return-Path" header checked',
                    "score": 0,
                    "status": GREEN_DOT_HTML_SNNIPET,
                },
            )
    else:  # Return path does not exist
        return_list.append(
            {
                "message": '"Return-Path" header does not exist',
                "score": 5,
                "status": RED_DOT_HTML_SNNIPET,
            },
        )

    if "Reply-To".lower() in lower_case_headers:
        flag = False
        if "From".lower() in lower_case_headers:
            if re.findall(
                EMAIL_ADDRESS_REGEX,
                lower_case_headers["Reply-To".lower()],
            ) != re.findall(EMAIL_ADDRESS_REGEX, lower_case_headers["From".lower()]):
                return_list.append(
                    {
                        "message": '"Reply-To" header does not match "From" header',
                        "score": 4,
                        "status": RED_DOT_HTML_SNNIPET,
                    },
                )
        if flag:
            return_list.append(
                {
                    "message": '"Reply-To" header checked',
                    "score": 0,
                    "status": GREEN_DOT_HTML_SNNIPET,
                },
            )
    else:  # "Reply-To" does bit exist
        # return_list.append({"message": "\"Reply-To\" header does not exist", "score": 4, "status": RED_DOT_HTML_SNNIPET})
        pass

    if "X-Distribution".lower() in lower_case_headers:
        return_list.append(
            {
                "message": '"X-Distribution" header present and with value: {}'.format(
                    lower_case_headers["X-Distribution".lower()],
                ),
                "score": 1,
                "status": RED_DOT_HTML_SNNIPET,
            },
        )
    else:
        return_list.append(
            {
                "message": '"X-Distribution" header checked (does not exist)',
                "score": 0,
                "status": GREEN_DOT_HTML_SNNIPET,
            },
        )

    # if "X-Mailer".lower() in lower_case_headers:
    #     return_list.append({"message": "\"X-Mailer\" header exists and with value: {}".format(lower_case_headers['X-Mailer'.lower()]), "score": 1, "status": RED_DOT_HTML_SNNIPET})
    # else:
    #     return_list.append({"message": "\"X-Mailer\" header checked (does not exist)", "score": 0, "status": GREEN_DOT_HTML_SNNIPET})

    if "Bcc".lower() in lower_case_headers:
        return_list.append(
            {
                "message": '"Bcc" heaedr exists',
                "score": 1,
                "status": RED_DOT_HTML_SNNIPET,
            },
        )
    else:
        return_list.append(
            {
                "message": '"Bcc" header checked (does not exist)',
                "score": 0,
                "status": GREEN_DOT_HTML_SNNIPET,
            },
        )

    if "X-UIDL".lower() in lower_case_headers:
        return_list.append(
            {
                "message": '"X-UIDL" header exists',
                "score": 1,
                "status": RED_DOT_HTML_SNNIPET,
            },
        )
    else:
        return_list.append(
            {
                "message": '"X-UIDL" header checked (does not exist)',
                "score": 0,
                "status": GREEN_DOT_HTML_SNNIPET,
            },
        )

    if "Message-Id".lower() not in lower_case_headers or "SMTPIN_ADDED_MISSING" in lower_case_headers.get(
        "Message-ID".lower(), ""
    ):  # Message-ID   SMTPIN_ADDED_MISSING
        return_list.append(
            {
                "message": '"Message-ID" header missing from original EML',
                "score": 5,
                "status": RED_DOT_HTML_SNNIPET,
            },
        )
    else:
        return_list.append(
            {
                "message": '"Message-ID" header checked - Nothing abnormal',
                "score": 0,
                "status": GREEN_DOT_HTML_SNNIPET,
            },
        )

    return return_list


def process_user_authenticated_header(headers):
    return_dict = {}
    return_dict["siemplify_recommendations"] = []
    if "X-Authenticated-User" in headers:
        raw = hedaers["X-Authenticated-User"]
        domain = raw[raw.index("@") + 1 :] if "@" in raw else None
        return_dict["domain"] = domain

        if "From" in headers:
            if raw != headers["From"]:
                return_dict["siemplify_recommendations"].append(
                    {
                        "message": '"X-Authenticated-User" header does not match "From" header',
                        "score": 10,
                    },
                )

    return return_dict


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("================= Main - Param Init =================")

    result_json = {}
    output_message = ""
    result_value = "true"
    status = EXECUTION_STATE_COMPLETED

    try:
        if siemplify.parameters.get("Base64 EML"):
            eml_content = base64.b64decode(siemplify.parameters.get("Base64 EML"))
            if not eml_content:
                msg = (
                    "Missing eml example for {}".format(
                        siemplify.parameters.get("EML Example"),
                    )
                )
                raise Exception(
                    msg,
                )

            extracted_email = message_from_string(eml_content)

            header_list = extracted_email._headers
        elif siemplify.parameters.get("Header List"):
            real_headers = {}
            header_list = json.loads(siemplify.parameters.get("Header List"))
        else:
            msg = "Bad input. You must have at least one."
            raise Exception(msg)

        headers_dict = {}
        duplicate_key_dict = {}
        for item in header_list:
            try:
                key = f"{item[0]}"
                val = item[1]
            except:
                raise Exception(item)
            if key not in duplicate_key_dict:
                duplicate_key_dict[key] = 1
                headers_dict[key] = val
            else:
                duplicate_key_dict[key] += 1
                headers_dict[f"{key}_{duplicate_key_dict[key]}"] = val

        real_headers = headers_dict
        # raise Exception(real_headers)
        result_json["extracted_headers"] = real_headers

        html_table_all_headers = get_html_headers_table(real_headers)
        result_json["html_table_all_headers"] = html_table_all_headers

        list_of_domain_address_tuples = get_domains_and_addresses(real_headers)
        list_of_domain_address = [{"domain": t[0], "address": t[1]} for t in list_of_domain_address_tuples]
        result_json["list_of_domain_address"] = list_of_domain_address

        user_authenticated_header = process_user_authenticated_header(real_headers)
        if "domain" in user_authenticated_header:
            result_json["user_authenticated_header_domain"] = user_authenticated_header["domain"]

        siemplify_recommendations = get_generic_siemplify_recommendations(real_headers)

        siemplify_recommendations.extend(
            user_authenticated_header["siemplify_recommendations"],
        )
        result_json["header_analysis_result"] = siemplify_recommendations
        total_rules_matched = 0
        for item in siemplify_recommendations:
            if item["score"] > 0:
                total_rules_matched += 1
        result_json["total_rules_matched"] = total_rules_matched
        result_json["total_rules_checked"] = len(siemplify_recommendations)

        if not siemplify_recommendations:
            siemplify_recommendations = "Siemlify did not find anything suspicious in the headers"
        else:
            siemplify_recommendations = "<table>{}</table>".format(
                "".join(
                    [
                        '<tr><td style="padding-right:12px">{}</td><td>{}</td></tr>'.format(
                            x["status"],
                            x["message"],
                        )
                        for x in siemplify_recommendations
                    ],
                ),
            )

        result_json["header_analysis_result_html"] = siemplify_recommendations

        if result_json:
            siemplify.result.add_result_json(result_json)

    except Exception as e:
        siemplify.LOGGER.exception("General error performing action %s", SCRIPT_NAME)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "Failed"
        output_message += "\n unknown failure"
        raise

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
