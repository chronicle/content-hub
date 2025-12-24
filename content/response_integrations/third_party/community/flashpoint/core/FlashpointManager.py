from __future__ import annotations

import copy
import json
from datetime import datetime
from urllib.parse import urlparse

import requests

DEFAULT_TIME = datetime.now()
API_ROOT = "https://fp.tools/api/v4"
HEADERS = {"Authorization": "", "Content-Type": "application/json"}
ENRICHMENT_FIELDS = {
    "card_numbers": "enrichments.card-numbers.card-numbers.bin",
    "cves": "enrichments.cves",
    "ip_addresses": "enrichments.ip-addresses.ip-addresses",
    "email_addresses": "enrichments.email-addresses.email-addresses",
    "languages": "enrichments.language",
    "domains": "enrichments.domains",
    "links": "enrichments.links",
}
# The sorting can be 'desc' for descending and 'asc' ascending
SORT_RESULTS_TIMESTAMP = "desc"


class FlashpointManager:
    def __init__(
        self,
        api_key,
        proxy_server_address=None,
        proxy_username=None,
        proxy_password=None,
    ):
        # def __init__(self, api_key):
        """:param api_root: API root URL.
        :param token: Flashpoint API Key
        """
        self.session = requests.session()
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.headers["Authorization"] = f"Bearer {api_key}"

        if proxy_server_address:
            self.set_proxy(proxy_server_address, proxy_username, proxy_password)

    def set_proxy(self, proxy_server_address, proxy_username=None, proxy_password=None):
        """Configure proxy
        :param proxy_server_address: {str} The proxy server address
        :param proxy_username: {str} Proxy username
        :param proxy_password: {str} Proxy password
        """
        server_url = urlparse(proxy_server_address)
        scheme = server_url.scheme
        hostname = server_url.hostname
        port = server_url.port
        credentials = ""
        if proxy_username and proxy_password:
            credentials = f"{proxy_username}:{proxy_password}@"
        proxy_str = f"{scheme}://{credentials}{hostname}"
        if port:
            proxy_str += f":{port!s}"

        self.session.proxies = {"http": proxy_str, "https": proxy_str}

    def test_connectivity(self):
        params = {"query": "+basetypes:(forum) +Carding +Exploit", "limit": 1}
        response = self.session.get(f"{API_ROOT}/all/search", params=params)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        if response.json():
            return True
        raise Exception("Something went wrong, please try again")

    def indicators_custom_query(
        self,
        results_limit,
        start_date,
        end_date,
        search_tags,
        query,
        sort_timestamp,
        attributes_types,
        basetypes_path=None,
    ):
        if sort_timestamp.lower() == "descending":
            sort_timestamp = "desc"
        elif sort_timestamp.lower() == "ascending":
            sort_timestamp = "asc"
        params = {
            "limit": int(results_limit),
            "start_date": start_date,
            "end_date": end_date,
            "search_tags": search_tags,
            "query": query,
            "sort_timestamp": sort_timestamp,
            "types": attributes_types,
        }
        url = f"{API_ROOT}/indicators/{basetypes_path}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def custom_query(self, query_content, new_query_url):
        url = f"{API_ROOT}" + f"{new_query_url}"
        params = json.loads(query_content)
        response = self.session.post(url, json=params)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def IOC_Enrichment(self, query, results_limit, SORT_RESULTS_TIMESTAMP):
        data = {
            "query": query,
            "limit": results_limit,
            "sort_timestamp": SORT_RESULTS_TIMESTAMP,
        }
        response = self.session.get(f"{API_ROOT}/indicators/attribute", params=data)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()

    def search_CCM(self, last_timestamp, time_now, limit=100):
        params = {
            "q": f"basetypes:(credential-sighting) +created_at.timestamp:[{last_timestamp} TO {time_now}]",
            "limit": limit,
        }
        response = self.session.get(f"{API_ROOT}/all/search", params=params)
        response.raise_for_status()
        try:
            response.json()
        except:
            raise Exception(response.content)
        return response.json()


def get_unicode(test):
    return str(test)


def dict_to_flat(target_dict):
    """Receives nested dictionary and returns it as a flat dictionary.
    :param target_dict: {dict}
    :return: Flat dict : {dict}
    """
    target_dict = copy.deepcopy(target_dict)

    def expand(raw_key, raw_value):
        key = raw_key
        value = raw_value
        """
        :param key: {string}
        :param value: {string}
        :return: Recursive function.
        """
        if value is None:
            return [(get_unicode(key), "")]
        if isinstance(value, dict):
            # Handle dict type value
            return [
                (
                    f"{get_unicode(key)}_{get_unicode(sub_key)}",
                    get_unicode(sub_value),
                )
                for sub_key, sub_value in dict_to_flat(value).items()
            ]
        if isinstance(value, list):
            # Handle list type value
            count = 1
            l = []
            items_to_remove = []
            for value_item in value:
                if isinstance(value_item, dict):
                    # Handle nested dict in list
                    l.extend(
                        [
                            (
                                f"{get_unicode(key)}_{get_unicode(count)}_{get_unicode(sub_key)}",
                                sub_value,
                            )
                            for sub_key, sub_value in dict_to_flat(value_item).items()
                        ],
                    )
                    items_to_remove.append(value_item)
                    count += 1
                elif isinstance(value_item, list):
                    l.extend(
                        expand(get_unicode(key) + "_" + get_unicode(count), value_item),
                    )
                    count += 1
                    items_to_remove.append(value_item)
            for value_item in items_to_remove:
                value.remove(value_item)
            for value_item in value:
                l.extend([(get_unicode(key) + "_" + get_unicode(count), value_item)])
                count += 1
            return l
        return [(get_unicode(key), get_unicode(value))]

    items = [
        item
        for sub_key, sub_value in target_dict.items()
        for item in expand(sub_key, sub_value)
    ]
    return dict(items)
