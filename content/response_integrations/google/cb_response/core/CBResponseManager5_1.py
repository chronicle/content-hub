from __future__ import annotations
from .CBResponseManager import CBResponseManager

API_ENDPOINTS = {"get_alerts": "{}/api/v1/alert"}


class CBResponseManager5_1(CBResponseManager):
    def __init__(self, *args, **kwargs):
        super(CBResponseManager5_1, self).__init__(*args, **kwargs)

    def get_alerts(self, query):
        """
        Get all alerts from CB Response
        :param query: {str} The query to filter te alerts by
        :return: {list} List of the alerts info (Alert)
        """
        url = API_ENDPOINTS["get_alerts"].format(self.api_root)
        params = {"q": query}
        alerts = self._paginate_results("GET", url, params=params)
        return [
            self.parser.build_siemplify_alert_obj(alert_json) for alert_json in alerts
        ]
