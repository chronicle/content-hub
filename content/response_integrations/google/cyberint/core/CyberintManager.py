from __future__ import annotations
import requests
from urllib.parse import urljoin
from .constants import ENDPOINTS, DEFAULT_LIMIT, API_TIME_FORMAT
from .CyberintParser import CyberintParser
from .UtilsManager import validate_response, filter_old_alerts
import math
import datetime


class CyberintManager:
    def __init__(self, api_root, api_key, verify_ssl, siemplify_logger=None):
        """
        The method is used to init an object of Manager class
        :param api_root: {str} Cyberint API root
        :param api_key: {str} Cyberint password
        :param verify_ssl: {bool} Specifies if certificate that is configured on the api root should be validated
        :param siemplify_logger: Siemplify logger
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.siemplify_logger = siemplify_logger
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers.update({"Cookie": f"access_token={self.api_key}"})
        self.parser = CyberintParser()

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
        request_url = self._get_full_url("ping")
        payload = {"page": 1, "size": 10}
        response = self.session.post(request_url, json=payload)
        validate_response(response)

    def update_alert(self, alert_id, status, closure_reason):
        """
        Update alert status
        :param alert_id: {str} Alert id
        :param status: {str} Status to update
        :param closure_reason: {str} Closure reason, if status is "closed"
        """
        request_url = self._get_full_url("update_alert")
        payload = {"alert_ref_ids": [alert_id], "data": {"status": status}}

        if closure_reason:
            payload["data"]["closure_reason"] = closure_reason

        response = self.session.put(request_url, json=payload)
        validate_response(response)

    def get_alerts(
        self, existing_ids, limit, start_timestamp, type_filter, severity_filter
    ):
        """
        Get alerts
        :param existing_ids: {list} The list of existing ids
        :param limit: {int} The limit for results
        :param start_timestamp: {datetime} The timestamp for oldest alert to fetch
        :param type_filter: {list} Type filter to apply
        :param severity_filter: {list} Severity filter to apply
        :return: {list} The list of filtered Finding objects
        """
        request_url = self._get_full_url("get_alerts")
        payload = {
            "page": 1,
            "size": DEFAULT_LIMIT,
            "filters": {
                "created_date": {
                    "from": start_timestamp.strftime(API_TIME_FORMAT),
                    "to": datetime.datetime.now().strftime(API_TIME_FORMAT),
                },
                "severity": severity_filter,
                "status": ["open", "acknowledged"],
            },
        }
        if type_filter:
            payload["filters"]["type"] = type_filter

        response = self.session.post(request_url, json=payload)
        validate_response(response)
        json_result = response.json()
        total = json_result.get("total", 0)
        pages = math.ceil(total / DEFAULT_LIMIT)

        alerts = self.parser.build_alerts_list(json_result)

        for page in range(pages):
            if page > 0:
                payload["page"] = page + 1
                response = self.session.post(request_url, json=payload)
                validate_response(response)
                alerts.extend(self.parser.build_alerts_list(response.json()))

        filtered_alerts = filter_old_alerts(
            logger=self.siemplify_logger, alerts=alerts, existing_ids=existing_ids
        )
        return sorted(filtered_alerts, key=lambda alert: alert.created_date)[:limit]
