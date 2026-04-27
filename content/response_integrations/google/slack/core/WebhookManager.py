from __future__ import annotations
import requests


class WebhookManager:

    def __init__(self, base_url, token_id="", verify_ssl=True):
        self.base_url = base_url
        self.token_id = token_id
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self.session.headers.update({"Content-Type": "application/json"})

    def get_request(self, sorting="newest"):
        url = f"{self.base_url}/token/{self.token_id}/requests?sorting={sorting}"
        response = self.session.get(url)
        return response

    def get_data(self, *args, **kwargs):
        response = self.get_request(*args, **kwargs)
        res = self._get_validated_response(response)
        data = res.get("data")
        return data

    def _get_validated_response(self, response):
        try:
            res_json = response.json()
        except Exception as _:
            raise Exception(response.content)
        try:
            response.raise_for_status()
        except Exception as _:
            raise Exception(res_json)
        return res_json
