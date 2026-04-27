from __future__ import annotations
class IronportRequestData:
    @staticmethod
    def get_token_request_data(username, password):
        payload = {"data": {"userName": username, "passphrase": password}}

        params = {}
        return payload, params

    @staticmethod
    def get_messages_request_data(start_date, end_date, offset=0, limit=None):
        payload = {}

        params = {
            "searchOption": "messages",
            "startDate": start_date,
            "endDate": end_date,
            "offset": offset,
        }

        if limit:
            params["limit"] = limit

        return payload, params

    @staticmethod
    def get_reports_request_data(start_date, end_date, device_type, query_type):
        payload = {}

        params = {
            "startDate": start_date,
            "endDate": end_date,
            "device_type": device_type,
            "query_type": query_type,
        }

        return payload, params
