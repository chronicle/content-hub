# =====================================
#              IMPORTS                #
# =====================================
from __future__ import annotations
import requests
import urllib.parse
import copy
import arrow

# =====================================
#             CONSTANTS               #
# =====================================
HEADERS = {"X-Elastica-Dbname-Resolved": "True"}

GET_INCIDENT_LOGS_URL = "api/admin/v1/logs/get/?app=Investigate&subtype=all&user={user_name}&created_timestamp={time_stamp}"
PING_URL = "audit/v2/datasources/"

TIME_FORMMAT = "%Y-%m-%dT%H:%M:%S"


# =====================================
#              CLASSES                #
# =====================================
class ElasticaCloudSOCManagerError(Exception):
    pass


class ElasticaCloudSOCManager:
    def __init__(self, api_root, key_id, key_secret, verify_ssl=False):
        """
        :param api_root: api root url {string}
        :param key_id: api key id {string}
        :param key_secret: api key secret {string}
        :param verify_ssl: verify sll at the http requests or not {bool}
        """
        self.api_root = self.validate_api_root(
            api_root
        )  # https://xxx.elastica.net/tenant/
        self.session = requests.session()
        self.session.auth = (key_id, key_secret)
        self.session.headers = copy.deepcopy(HEADERS)
        self.session.verify = verify_ssl

    @staticmethod
    def validate_api_root(api_root):
        """
        Validate API root string contains '/' at the end because 'urlparse' lib is used.
        :param api_root: api root url {string}
        :return: valid api root {string}
        """
        if api_root[-1] == "/":
            return api_root
        return api_root + "/"

    @staticmethod
    def validate_response(http_response):
        """
        Validated an HTTP response.
        :param http_response: HTTP response object.
        :return: {void}
        """
        try:
            http_response.raise_for_status()

        except requests.HTTPError as err:
            raise ElasticaCloudSOCManagerError(
                f"Status Code: {http_response.status_code}, Content: {http_response.content}, Error: {err}"
            )

    def ping(self):
        """
        Test integration connectivity.
        :return: is succeed {bool}
        """
        request_url = urllib.parse.urljoin(self.api_root, PING_URL)

        response = self.session.get(request_url)

        self.validate_response(response)

        return True

    def get_user_investigation_logs_since_time(
        self, user_name, creation_arrow_timestamp=arrow.now()
    ):
        """
        Fetch user investigation logs since timestamp.
        :param user_name: user name {string}
        :param creation_arrow_timestamp: fetch logs since time {arrow}
        :return: list of dicts {list}
        """
        time_stamp_str = creation_arrow_timestamp.strftime(TIME_FORMMAT)
        request_url = urllib.parse.urljoin(
            self.api_root,
            GET_INCIDENT_LOGS_URL.format(
                user_name=user_name, time_stamp=time_stamp_str
            ),
        )

        response = self.session.get(request_url)
        self.validate_response(response)

        return response.json().get("logs")


# if __name__ == '__main__':
#     esm = ElasticaCloudSOCManager('https://api-vip.elastica.net/siemplifyco/', '41eee3d26fce11e89fdb06f77665d172',
#                                   'aaRlwxE1Kd4culWG0gG8dTXaE7GSNbzUxxRDBfkWpG0')
#
#     import datetime
#     time = arrow.Arrow.now() + datetime.timedelta(days=-30)
#     logs = esm.get_user_investigation_logs_since_time('MENY@SIEMPLIFY.CO', time)
#     res = esm.ping()
#     pass
