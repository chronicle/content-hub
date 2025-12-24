from __future__ import annotations

import json

import requests

# Consts:
headers = {"Content-Type": "application/json"}


class PhilipsManager:
    def __init__(self, bridge_ip, user_name):
        """Initialization for Manager instance.
        :param bridge_ip: the IP address of the Philips HUE bridge
        :param user_name: the username to authorize access to the product's attributes
        """
        infix = "/api/"
        prefix = "https://"

        # adv_url is advanced URL with embedded advanced authorization endpoints:
        self.base_url = prefix + bridge_ip + infix + user_name
        self.session = requests.Session()
        self.session.headers.update(headers)

    def test_connectivity(self):
        """Tests the connectivity to the site.
        :return: True if connection is successful, otherwise false.
        """
        response = self.session.get(self.base_url, timeout=5.0)
        response.raise_for_status()

        return True

    def search_light_id(self, light_id):
        """Checks if the bridge has a light with this light_id.
        :return: True the light_id exists under the bridge.
        """
        endpoint_url = self.base_url + "/lights/"
        response = self.session.get(endpoint_url, timeout=5.0)
        res_json = response.json()
        str_light_id = f"{light_id}"
        if str_light_id not in res_json.keys():
            return False

        return True

    def reachability(self, light_id):
        """Checks if the light with this light_id is reachable (and not too far) from the bridge.
        :return: True the light with light_id is reachable.
        """
        endpoint_url = self.base_url + "/lights/" + light_id
        response = self.session.get(endpoint_url, timeout=5.0)

        response.raise_for_status()
        res_json = response.json()
        if "error" in res_json:
            raise Exception(res_json.get("error"))
        is_reachable = res_json.get("state").get("reachable")

        return is_reachable

    def adjust_light(
        self,
        light_id,
        on_state,
        hue=10000,
        alert_effect="none",
        saturation=254,
        brightness=254,
    ):
        """Adjusts the lighting by the next parameters:
        :param light_id: id of the light you want to adjust
        :param on_state: true for truning on, false for turning of
        :param saturation: sets light saturation, range: 0-254
        :param birghtness: sets light birghtness, range: 0-254
        :param hue: sets the color of the light, range: 0-65535
        :return: json with the details of the light bulb state.
        """
        res_json = {}
        res_json["light reachability"] = self.reachability(light_id)

        if res_json.get("light reachability"):
            payload = json.dumps(
                {
                    "on": on_state,
                    "alert": alert_effect,
                    "hue": hue,
                    "sat": saturation,
                    "bri": brightness,
                },
            )

            endpoint_url = self.base_url + "/lights/" + light_id + "/state"

            response = self.session.put(endpoint_url, data=payload, timeout=5.0)

            try:
                res_json["results"] = response.json()
            except:
                raise Exception(response.content)
            try:
                response.raise_for_status()
            except:
                raise Exception(res_json)
            if "error" in res_json["results"][0]:
                raise Exception(res_json["results"][0].get("error"))

        return res_json
