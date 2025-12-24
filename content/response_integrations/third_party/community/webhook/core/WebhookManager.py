from __future__ import annotations

import requests

headers = {"Content-Type": "application/json"}


class WebhookManager:
    def __init__(self, base_url):
        """Initialization for Manager instance.
        :param base_url: the base URL for any use of requests
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(headers)

    def test_connectivity(self):
        """Tests the connectivity to the site.
        :return: True if connection is successful, otherwise false.
        """
        response = self.session.get(self.base_url)
        response.raise_for_status()

        return True

    def create_token(self, def_content, def_content_type, timeout):
        """Creates a webhook (generates token) with the given attributes.
        :param def_content: content of the page <base_url>/<the_new_token>
        :param def_content_type: type of that content
        :param timeout: seconds to wait before returning response
        :return:
        """
        endpoint_url = f"{self.base_url}/token"
        payload = {
            "default_status": 200,
            "default_content": def_content,
            "default_content_type": def_content_type,
            "timeout": timeout,
            "cors": False,
            "expiry": True,
            "alias": "my-webhook",
            "actions": True,
        }

        response = self.session.post(endpoint_url, json=payload)

        try:
            res_json = response.json()
        except:
            raise Exception(response.content)
        try:
            response.raise_for_status()
        except:
            raise Exception(res_json)

        return res_json

    def get_requests(self, token_id, res_choice):
        """Get either all requests of the token_id, or only the latest one.
        :param token_id: ID of the token to inspect
        :param res_choice: represents choice of WHICH requests to get (All, Latest)
        :return: Json holding all the data regarding each request to the URL.
        """
        # Distinguish between ALL REQUESTS and LATEST REQUEST ONLY:
        latest = res_choice == "latest"
        endpoint_url = f"{self.base_url}/token/{token_id}/requests"
        # Get requests:
        response = self.session.get(endpoint_url)

        try:
            res_json = response.json()
        except:
            raise Exception(response.content)
        try:
            response.raise_for_status()
        except:
            raise Exception(res_json)

        # FILTERING -OUT- THE SLACKBOT AUTO-GENERATED REQUEST:
        output_dict = [x for x in res_json["data"] if "Slack" not in x["user_agent"]]
        res_json["data"] = output_dict

        # LEAVING ONLY LATEST REQUEST if latest:
        if latest:
            if len(res_json.get("data")) > 0:
                filter_scondaries_dict = [
                    res_json["data"][len(res_json.get("data")) - 1],
                ]
                res_json["data"] = filter_scondaries_dict
                res_json["requests_type"] = "latest"

        res_json["requests_type"] = "latest" if latest else "all"

        return res_json

    def delete_token(self, token_id):
        """Deletes the token <token_id> therefore making the URL <base_url>/<token_id> inaccessible.
        :param token_id: ID of the token to be deleted
        :return: Status of the action.
        """
        endpoint_url = f"{self.base_url}/token/{token_id}"
        response = self.session.delete(endpoint_url)

        try:
            response.raise_for_status()
        except:
            raise Exception(response.json())

        return response.status_code
