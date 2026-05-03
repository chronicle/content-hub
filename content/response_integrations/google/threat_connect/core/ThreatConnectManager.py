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
from urllib.parse import quote_plus
from urllib.request import getproxies

import requests

from threatconnect.RequestObject import RequestObject
from threatconnect import ThreatConnect

from .constants import (
    FAILURE_STATUS,
    FIELDS_LIST,
    GROUPS,
    GROUP_REQUEST_URI,
    GROUPS_TYPES_MAP,
    INDICATOR_OWNERS_REQUEST_URI,
    INDICATOR_REQUEST_URI,
    URL,
)
from .exceptions import ThreatConnectException

# =====================================
#              CLASSES                #
# =====================================


def select_proxy(url, proxies):
    """Select a proxy for the url, if applicable.

    :param url: The url being for the request
    :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs
    """
    proxies = proxies or {}
    urlparts = requests.utils.urlparse(url)
    if urlparts.hostname is None:
        return proxies.get(urlparts.scheme, proxies.get("all"))

    proxy = None
    if requests.utils.should_bypass_proxies(url, proxies.get("no_proxy")):
        return proxy

    proxy_keys = [
        urlparts.scheme + "://" + urlparts.hostname,
        urlparts.scheme,
        "all://" + urlparts.hostname,
        "all",
    ]

    for proxy_key in proxy_keys:
        if proxy_key in proxies:
            proxy = proxies[proxy_key]
            break

    return proxy


class NoProxyAdapter(requests.adapters.HTTPAdapter):
    def get_connection(self, url, proxies=None):
        """Returns a urllib3 connection for the given URL. This should not be
        called from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param url: The URL to connect to.
        :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        :rtype: urllib3.ConnectionPool
        """
        proxy = select_proxy(url, proxies)

        if proxy and proxy not in proxies.get("no_proxy", []):
            proxy = requests.adapters.prepend_scheme_if_needed(proxy, "http")
            proxy_manager = self.proxy_manager_for(proxy)
            conn = proxy_manager.connection_from_url(url)
        else:
            # Only scheme should be lower case
            parsed = requests.adapters.urlparse(url)
            url = parsed.geturl()
            conn = self.poolmanager.connection_from_url(url)

        return conn


class ThreatconnectAPI:
    def __init__(self, api_access_id, api_secret_key, api_default_org, api_base_url):
        self.tc_api = ThreatConnect(
            api_access_id, api_secret_key, api_default_org, api_base_url
        )

        # ThreatConnect overrides the passed proxy settings (sets them to None).
        # ThreatConnect also uses requests'session.send() method, which doesn't
        # fetch the environment proxy settings and ignores them. The only way
        # to pass proxy settings to send() is by explicitly specifying the
        # proxy param in the send(proxy={...}). Unfortunately, the creators of
        # requests didn't add proxy bypass to explicitly given proxy param
        # (both session.get, post... and session.send()). While in session.get()
        # you can bypass proxy using env variables, with send() you can't.
        # So in order to overcome this, _proxies should be set to getproxies()
        # (collect the env proxy settings) and a custom adapter must be used.
        # The custom adapter will check the passed proxy settings when send()
        # is called, and will check if should bypass or not.
        # The custom adapter WILL NOT fetch the environment proxy settings by
        # itself so tc_api._proxies must be overriden.
        self.tc_api._proxies = getproxies()
        self.tc_api._session.mount("https://", NoProxyAdapter())

    def get_data(self, query, method="GET", params=None):
        """
        :param query: {string} query format
        :param method:
        :return: {json} a single Indicator information
        """
        ro = RequestObject()
        ro.set_http_method(method)
        # set the URI (uniform resource identifier) for the request
        ro.set_request_uri(query)
        # Set params for request
        if params:
            for key, val in params.items():
                ro.add_payload(key, val)
        response = self.tc_api.api_request(ro)

        if response.status_code == 404:
            raise ThreatConnectException(f"Resource not found: {query}")

        response.raise_for_status()

        if str(response.json().get("status")).lower() == FAILURE_STATUS:
            raise ThreatConnectException(
                f"An error occurred: {response.json().get('message', 'no message')}"
            )

        return response.json().get("data")

    def fix_attributes_for_presentation(self, attributes_json):
        """
        :param attributes_json: {list} attributes full details
        :return: {dict} attributes details
        """
        if not attributes_json["resultCount"]:
            return None
        types = {}
        for attribute in attributes_json["attribute"]:
            if attribute["type"] not in types:
                types[attribute["type"]] = []
            types[attribute["type"]].append(attribute["value"])
        return types

    def fix_tags_for_presentation(self, tags):
        """
        :param tags: {list} tags full details
        :return: {list} tags names list
        """
        if not tags["resultCount"]:
            return None
        tags_names = [tag["name"] for tag in tags["tag"]]
        return tags_names

    def fix_associated_groups_for_presentation(self, associated_groups):
        """
        :param associated_groups: {list} groups full details
        :return: {dict} groups fixed details
        """
        new_groups_dict = {}
        if not associated_groups["resultCount"]:
            return None
        for group in associated_groups["group"]:
            group_type = group["type"]
            if group_type in GROUPS_TYPES_MAP:
                group_type = GROUPS_TYPES_MAP[group_type]
            if group_type not in new_groups_dict:
                # Create new key for the specific group type
                new_groups_dict[group_type] = []
            group.update(self.get_group_info(group))

            # Put all the data in new_groups_dict
            new_groups_dict[group_type].append(group)

        return new_groups_dict

    def test_connectivity(self):
        """
        Test connectivity to threatconnect api via request to list all visible groups
        :return: {boolean} True if connection succeed, else false
        """
        result = self.get_data(GROUPS)
        if result:
            return True
        return False

    def get_group_info(self, grp):
        """
        :param grp: {dict} associated group information
        :return: {dict} associated group richer information
        """
        group = grp["id"]
        group_type = grp["type"]
        if group_type in GROUPS_TYPES_MAP:
            group_type = GROUPS_TYPES_MAP[group_type]
        base_query = GROUP_REQUEST_URI.format(groupType=group_type, groupId=str(group))
        result = self.get_data(base_query)
        result["securityLabels"] = self.get_data(f"{base_query}/securityLabels")
        result["tags"] = self.get_data(f"{base_query}/tags")
        result["attributes"] = self.fix_attributes_for_presentation(
            self.get_data(f"{base_query}/attributes")
        )

        return result

    def get_indicator_data(self, indicator_type, indicator_value, owner_name):
        """
        Retrieve a single Indicator information
        :param indicator_type: {string} url/hash/host/ip
        :param indicator_value: {string}
        :param owner_name: {string} Owner name to fetch the data from
        :return: {dict} indicator information
        """
        # When retrieving information about a specific URL, you will need to URL encode the Indicator.
        if indicator_type == URL:
            indicator_value = quote_plus(indicator_value)

        base_query = INDICATOR_REQUEST_URI.format(
            indicatorType=indicator_type, indicator=str(indicator_value)
        )
        result = {}

        result["general"] = self.get_data(base_query, params={"owner": owner_name})
        # Check whether there are general results, if empty there is no reason to continue sending requests
        if not result["general"]:
            return None

        for field in FIELDS_LIST:
            result[field] = self.get_data(
                f"{base_query}/{field}", params={"owner": owner_name}
            )
            if field == "attributes":
                result[field] = self.fix_attributes_for_presentation(result[field])
            if field == "groups":
                result[field] = self.fix_associated_groups_for_presentation(
                    result[field]
                )
            if field == "tags":
                result[field] = self.fix_tags_for_presentation(result[field])

        return result

    def get_indicator_info(self, indicator_type, indicator_value, owner_name=None):
        """
        Retrieve a single Indicator information if no owner is specify result will include all exists owners data
        :param indicator_type: {string} url/hash/host/ip
        :param indicator_value: {string}
        :param owner_name: {string} Owner name to fetch the data from
        :return: {dict} indicator information (optional)
        """
        results = {}
        # In case Owners is explicit
        if owner_name:
            results = self.get_indicator_data(
                indicator_type, indicator_value, owner_name
            )
            return results

        # Fetch data for all existing owners, first owner will be used as the primary data,
        # the rest will be in results dict under the owner name (results['owner_name'])
        all_owners_names = self.get_indicator_owners_names(
            indicator_type, indicator_value
        )
        if all_owners_names:
            results = self.get_indicator_data(
                indicator_type, indicator_value, all_owners_names[0]
            )
            # Appending all the rest owners data to the result dict
            for owner in all_owners_names[1:]:
                results[owner] = self.get_indicator_data(
                    indicator_type, indicator_value, owner
                )

        return results

    def get_indicator_owners_names(self, indicator_type, indicator_value):
        """
        Retrieve all owners names exists for a specific indicator
        :param indicator_type: {string}
        :param indicator_value: {string}
        :return: {list} Owners names
        """
        if indicator_type == URL:
            indicator_value = quote_plus(indicator_value)

        base_query = INDICATOR_OWNERS_REQUEST_URI.format(
            indicatorType=indicator_type, indicator=str(indicator_value)
        )
        owners_data = self.get_data(base_query)

        return [owner["name"] for owner in owners_data["owner"]]
