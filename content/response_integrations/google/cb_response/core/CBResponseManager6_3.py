from __future__ import annotations
from .CBResponseManager import CBResponseManager

API_ENDPOINTS = {
    "create_alert_for_watchlist": "{}/api/v1/watchlist/{}/action_type/alert"
}


class CBResponseManager6_3(CBResponseManager):
    def __init__(self, *args, **kwargs):
        super(CBResponseManager6_3, self).__init__(*args, **kwargs)

    def create_alert_action_for_watchlist(self, watchlist_id):
        """
        Create an alert action for watchlist
        :param watchlist_id: {int} watchlist ID
        :return:
        """
        url = API_ENDPOINTS["create_alert_for_watchlist"].format(
            self.api_root, watchlist_id
        )
        body = {"enabled": True}
        response = self.session.put(url, json=body)
        return self.validate_response(response)
