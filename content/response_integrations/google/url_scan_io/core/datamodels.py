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
from TIPCommon.transformation import add_prefix_to_dict, dict_to_flat
from ..core.constants import INTEGRATION_NAME, SEVERITIES_COLORS, URL_INSIGHT_HTML_TEMPLATE
from ..core.UtilsManager import timestamp_to_iso


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def is_empty(self):
        return not bool(self.raw_data)


class ScanDetails(BaseModel):
    def __init__(self, raw_data, *, uuid=None, report_url=None, dom_url=None, screenshot_url=None):
        super(ScanDetails, self).__init__(raw_data)
        self.uuid = uuid
        self.dom_url = dom_url
        self.report_url = report_url
        self.screenshot_url = screenshot_url


class URL(BaseModel):
    def __init__(
        self,
        raw_data,
        verdicts,
        lists,
        uuid,
        score,
        screenshot_url,
        result_link,
        url,
        ips,
        countries,
        domains,
        transactions,
        ip_address,
        city,
        country,
        asnname,
        domain,
        certificates,
    ):
        super(URL, self).__init__(raw_data)
        self.verdicts = verdicts
        self.lists = lists
        self.uuid = uuid
        self.score = score
        self.screenshot_url = screenshot_url
        self.result_link = result_link

        # fields for insight
        self.url = url if url is not None and url != "" else "N/A"
        self.ips = ips
        self.countries = countries
        self.domains = domains
        self.transactions = transactions
        self.ip_address = ip_address if ip_address is not None and ip_address != "" else "N/A"
        self.city = city if city is not None and city != "" else "N/A"
        self.country = country if country is not None and country != "" else "N/A"
        self.asnname = asnname if asnname is not None and asnname != "" else "N/A"
        self.domain = domain if domain is not None and domain != "" else "N/A"
        self.certificates = certificates

    def to_shorten_json(self):
        """
        Build customize json (all of the dicts flat values + lists section)
        :return: {dict} scan report after construction
        """
        json_results = {}

        for key, value in self.raw_data.items():
            if isinstance(value, list):
                value = {"values": value}

            if key not in ["lists", "verdicts", "metatags", "usertags"]:
                key_dict = {}
                for sub_key, sub_value in value.items():
                    # check if the sub value is flat (not dict/list)
                    if not isinstance(sub_value, dict) and not isinstance(sub_value, list):
                        key_dict.update({sub_key: sub_value})
                if key_dict:
                    json_results.update({key: key_dict})
            else:
                json_results.update({key: value})

        return json_results

    def to_shorten_json_for_enrichment(self):
        """
        Build customize json (all of the dicts flat values + lists section)
        :return: {dict} scan report after construction
        """
        json_results = {}

        for key, value in self.raw_data.items():
            if isinstance(value, list):
                value = {"values": value}

            if key not in ["lists", "verdicts", "metatags", "usertags"]:
                key_dict = {}
                for sub_key, sub_value in value.items():
                    # check if the sub value is flat (not dict/list)
                    if not isinstance(sub_value, dict) and not isinstance(sub_value, list):
                        key_dict.update({sub_key: sub_value})
                if key_dict:
                    json_results.update({key: key_dict})

            elif key == "verdicts":
                key_name = "categories"
                list_key_values = value.get("overall").get("categories")
                json_results.update({key_name: list_key_values})
                key_name = "overall_score"
                score = value.get("overall").get("score")
                json_results.update({key_name: score})

            else:
                for list_key, list_value in value.items():
                    if list_value:
                        if isinstance(list_value[0], str) and list_key != "hashes":
                            key_name = f"{key}_{list_key}"
                            list_value = [i for i in list_value if i is not None]
                            list_key_values = ",".join(list_value)
                            json_results.update({key_name: list_key_values})

        return json_results

    def to_enrichment(self):
        return add_prefix_to_dict(
            dict_to_flat(self.to_shorten_json_for_enrichment()), INTEGRATION_NAME
        )

    def as_url_insight(self, screenshot_to_add):

        severity_color = SEVERITIES_COLORS.get("low")
        if int(self.score) > 0:
            severity_color = SEVERITIES_COLORS.get("high")

        screenshot = "<p>Not Available</p>"

        if screenshot_to_add is not None:
            screenshot = (
                f'<img src="data:image/jpeg;base64,"{screenshot_to_add.decode("utf-8")}><br></br>'
            )

        certificate_issuer = "N/A"
        certificate_valid_from = "N/A"
        certificate_valid_to = "N/A"

        if self.certificates:
            for certificate in self.certificates:
                if self.domain == certificate.get("subjectName"):
                    certificate_issuer = certificate.get("issuer")
                    certificate_valid_from = timestamp_to_iso(certificate.get("validFrom"))
                    certificate_valid_to = timestamp_to_iso(certificate.get("validTo"))

        return URL_INSIGHT_HTML_TEMPLATE.format(
            severity_color=severity_color,
            score=self.score,
            url=self.url,
            number_of_ips=len(self.ips),
            number_of_countries=len(self.countries),
            number_of_domains=len(self.domains),
            number_od_transactions=len(self.transactions),
            ip_address=self.ip_address,
            city=self.city,
            country=self.country,
            asnname=self.asnname,
            domain=self.domain,
            certificate_issuer=certificate_issuer,
            certificate_valid_from=certificate_valid_from,
            certificate_valid_to=certificate_valid_to,
            screenshot=screenshot,
        )


class SearchObject(BaseModel):
    def __init__(self, raw_data, item_id, task, stats, page, screenshot, report_link):
        super(SearchObject, self).__init__(raw_data)
        self.item_id = item_id
        self.task = task
        self.stats = stats
        self.page = page
        self.screenshot = screenshot
        self.report_link = report_link

    def to_table(self):
        return {
            "Scan ID": self.item_id,
            "URL": self.task.task_url,
            "Scan Date": self.task.time,
            "Size": self.stats.data_length,
            "IPs": self.stats.unique_ips,
            "Unique Countries": self.stats.unique_countries,
            "Country": self.page.country,
            "Scan Type": self.task.visibility,
        }


class SearchTask(BaseModel):
    def __init__(self, raw_data, task_url, time, visibility):
        super(SearchTask, self).__init__(raw_data)
        self.task_url = task_url
        self.time = time
        self.visibility = visibility


class SearchStats(BaseModel):
    def __init__(self, raw_data, data_length, unique_ips, unique_countries):
        super(SearchStats, self).__init__(raw_data)
        self.data_length = data_length
        self.unique_ips = unique_ips
        self.unique_countries = unique_countries


class SearchPage(BaseModel):
    def __init__(self, raw_data, country):
        super(SearchPage, self).__init__(raw_data)
        self.country = country
