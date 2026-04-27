from __future__ import annotations
from urllib.parse import urljoin
import requests
from .HarmonyMobileParser import HarmonyMobileParser
from .constants import ENDPOINTS, DEFAULT_LIMIT, RISK_MAP
from .UtilsManager import validate_response, filter_old_alerts


class HarmonyMobileManager:
    def __init__(
        self, api_root, client_id, client_secret, verify_ssl, siemplify_logger=None
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Harmony Mobile API root
        :param client_id: {str} Harmony Mobile client id
        :param client_secret: {str} Harmony Mobile client secret
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.parser = HarmonyMobileParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self._set_auth_token()

    def _set_auth_token(self):
        """
        Set Authorization header to request session.
        """
        self.session.headers.update(
            {"Authorization": f"Bearer {self._generate_token()}"}
        )

    def _generate_token(self):
        """
        Generate auth token
        :return: {str} The auth token
        """
        url = self._get_full_url("auth")
        payload = {"clientId": self.client_id, "accessKey": self.client_secret}

        response = self.session.post(url, data=payload)
        validate_response(response)
        return self.parser.get_token(response.json())

    def _get_full_url(self, url_id, **kwargs):
        """
        Get full url from url identifier.
        :param url_id: {str} The id of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_id].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity
        """
        url = self._get_full_url("ping")
        response = self.session.get(url)
        validate_response(response)

    def get_alerts(self, existing_ids, limit, start_timestamp, risk):
        """
        Get alerts
        :param existing_ids: {list} The list of existing ids
        :param limit: {int} The limit for results
        :param start_timestamp: {int} The timestamp for oldest alert to fetch
        :param risk: {str} The lowest risk for alert to fetch
        :return: {list} The list of filtered Alert objects
        """
        if existing_ids:
            params = {"id__gt": existing_ids[-1]}

            alerts = self.get_sorted_alerts(limit, params)
        else:
            alerts = self.get_sorted_alerts(limit)

            if alerts:
                while alerts[0].timestamp >= start_timestamp:
                    params = {"id__lt": alerts[0].id}

                    older_alerts = self.get_sorted_alerts(limit, params)

                    if not older_alerts:
                        break

                    alerts = sorted(alerts + older_alerts, key=lambda x: x.id)

        filtered_alerts = self.get_filtered_alerts(alerts, start_timestamp, risk)
        return filter_old_alerts(
            self.siemplify_logger, filtered_alerts, existing_ids, "id"
        )

    def get_sorted_alerts(self, limit, params=None):
        """
        Get sorted alerts
        :param limit: {int} The limit for results
        :param params: {dict} The params of the request
        """
        return sorted(
            self._paginate_results(
                method="GET",
                url=self._get_full_url("alerts"),
                parser_method="build_alert_object",
                limit=max(limit, DEFAULT_LIMIT),
                params=params,
            ),
            key=lambda x: x.id,
        )

    @staticmethod
    def get_filtered_alerts(alerts, timestamp, risk):
        """
        Filter alerts by timestamp and risk
        :param alerts: {list} The list of Alert objects to filter
        :param timestamp: {int} Timestamp to filter alerts
        :param risk: {str} The lowest risk to filter alerts
        :return: {list} The list of filtered Alert objects
        """
        values = list(RISK_MAP.values())

        return [
            alert
            for alert in alerts
            if alert.timestamp >= timestamp
            and (
                not risk
                or values.index(RISK_MAP.get(alert.risk_level)) >= values.index(risk)
            )
        ]

    def _paginate_results(
        self,
        method,
        url,
        parser_method,
        params=None,
        body=None,
        limit=None,
        err_msg="Unable to get results",
        page_size=100,
    ):
        """
        Paginate the results
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param parser_method: {str} The name of parser method to build the result
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param err_msg: {str} The message to display on error
        :param page_size: {int} Items per page
        :return: {list} List of results
        """
        params = params or {}
        page_number = 0
        params["limit"] = page_size
        params.update({"offset": page_number * page_size})

        response = None
        results = []

        while True:
            if response:
                if limit and len(results) >= limit:
                    break

                page_number += 1
                params.update({"offset": page_number * page_size})

            response = self.session.request(method, url, params=params, json=body)

            validate_response(response, err_msg)
            current_items = [
                getattr(self.parser, parser_method)(item_json)
                for item_json in response.json().get("objects", [])
            ]
            results.extend(current_items)
            if len(current_items) < page_size:
                break

        return results[:limit] if limit else results

    def get_devices(self):
        """
        Get devices
        :return: {list} List of Device objects
        """
        return self._paginate_results(
            method="GET",
            url=self._get_full_url("devices"),
            parser_method="build_device_object",
        )
