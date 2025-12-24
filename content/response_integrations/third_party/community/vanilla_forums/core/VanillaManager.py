from __future__ import annotations

import json
import random
import string

import requests

headers = {"Authorization": "Bearer api_token", "Content-Type": "application/json"}


class VanillaManager:
    """Vanilla Manager"""

    def __init__(self, api_token, base_url):
        """Initiates instance of Manager.
        :param api_token: api token
        :param base_url: base url for all requests
        """
        self.api_token = api_token
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.session.headers["Authorization"] = f"Bearer {api_token}"

    def test_connectivity(self):
        """Tests connectivity to the product
        :return: True if connection is successful. Otherwise, False.
        """
        url = f"{self.base_url}/v2/categories"
        params = {"maxDepth": "1", "limit": "1"}
        response = self.session.get(url, params=params)
        try:
            res_json = response.json()
        except:
            raise Exception(response.content)
        try:
            response.raise_for_status()
        except:
            raise Exception(res_json)

        return True

    def genereate_pass(self, string_length):
        """Generates a series of 2 random Upper%Lower letters digits by given length.
        :param string_length: wanted length of series
        :return: series of stringLength random characters as described
        """
        pas = "".join(random.choice(string.ascii_uppercase) for i in range(1))
        pas += "".join(random.choice(string.ascii_lowercase) for i in range(1))
        pas += "".join(random.choice(string.digits) for i in range(string_length - 2))
        return pas

    def add_new_user(
        self,
        new_email,
        new_f_name,
        new_l_name,
        new_password,
        new_role_id,
        need_char,
        special_char,
        photo,
        emailConfirmed,
        bypassSpam=True,
    ):
        """Adds a user to vanilla forums.
        :param new_email: email address of the new user
        :param new_f_name: first name of new user
        :param new_l_name: last name of new user
        :param new_password: password for new user
        :param new_role_id: id of the role to give the new user
        :param need_char: True if the special character is needed
        :param special_char: character to add to new username if name already exists
        :param photo: photo url for new user's profile
        :emailConfirmed: is user email confirmed
        :bypassSpam: should bypass spam
        :return: json with the details of the new user.
        """
        special_char = special_char if need_char else " "
        new_username = new_f_name + special_char + new_l_name

        endpoint_url = f"{self.base_url}/v2/users"

        # The details to be assigned to user in Vanilla:
        payload = {
            "bypassSpam": bypassSpam,
            "email": new_email,
            "emailConfirmed": emailConfirmed,
            "name": new_username,
            "password": new_password,
            "photo": photo,
            "roleID": [new_role_id],
        }

        # Add user to Vanilla users:
        response = self.session.post(endpoint_url, data=json.dumps(payload))

        try:
            res_json = response.json()

        except:
            raise Exception(response.content)
        try:
            response.raise_for_status()
        except:
            raise Exception(res_json)

        res_json["password"] = new_password
        return res_json

    def search_user_by_email(self, user_email):
        """Searches user in Vanilla by and email.
        :param user_email: email address of the user you want to search
        :return: json with the user's details.
        """
        endpoint_url = f"{self.base_url}/v2/users"
        res_json = {}
        current_page = 0
        while True:
            # Split search to page ranges:
            current_page += 1
            params = {"page": f"{current_page}", "limit": "100"}
            response = self.session.get(endpoint_url, params=params)
            response.raise_for_status()
            users = response.json()
            if not users:
                # no more users
                break
            for user in users:
                if user.get("email").lower() == user_email:
                    res_json = user
                    # User found by email!
                    break

        return res_json

    def search_user_by_name(self, user_name):
        """Searches user in Vanilla by and email.
        :param user_name: username of the user you want to search
        :return: json with the user's details.
        """
        endpoint_url = f"{self.base_url}/v2/users/by-names"
        params = {"name": user_name, "order": "name", "page": "1", "limit": "1"}
        response = self.session.get(endpoint_url, params=params)
        try:
            res_json = response.json()
        except:
            raise Exception(response.content)
        try:
            response.raise_for_status()
        except:
            raise Exception(res_json)

        return res_json

    def get_user_details(self, user_id):
        """Fetches user details by ID.
        :param user_id: ID of the user you want to fetch
        :return: json with the user's details.
        """
        endpoint_url = f"{self.base_url}/v2/users/{user_id}"
        response = self.session.get(endpoint_url)
        response.raise_for_status()

        try:
            res_json = response.json()
        except:
            raise Exception(response.content)
        try:
            response.raise_for_status()
        except:
            raise Exception(res_json)
        return res_json

    def give_user_badge(self, badge_id, user_id):
        """Gives user a new badge.
        :param badge_id: ID of the badge to give the user
        :param user_id: ID of user to be given the badge
        :return: json with the badge and user details.
        """
        url = f"{self.base_url}/v2/badges/{badge_id}/users"
        params = {"userID": user_id}
        response = self.session.post(url, json=params)
        try:
            res_json = response.json()
        except:
            raise Exception(response.content)
        try:
            response.raise_for_status()
        except:
            raise Exception(res_json)

        return res_json

    def change_user_rank(self, rank_id, user_id):
        """Changes the rank of a user.
        :param rank_id: ID of the rank to give the user
        :param user_id: ID of the user to be assigned the rank
        :return: json with the rank ID.
        """
        endpoint_url = f"{self.base_url}/v2/users/{user_id}/rank"
        payload = {"rankID": rank_id}

        # Update the user's rank in Vanilla:
        response = self.session.put(endpoint_url, json=payload)
        try:
            res_json = response.json()
        except:
            raise Exception(response.content)
        try:
            response.raise_for_status()

        except:
            raise Exception(res_json)

        return res_json

    def give_user_role(self, role_id, user_id):
        """Assigns user with a role.
        :param role_id: ID of the role to be assigned to the user
        :param user_id: ID of the user to be given the role
        :return: json with the user's details containing the new role's details.
        """
        endpoint_url = f"{self.base_url}/v2/users/{user_id}"
        payload = json.dumps({"roleID": [role_id]})
        response = self.session.patch(endpoint_url, data=payload)
        try:
            res_json = response.json()
            if "message" in res_json:
                raise Exception(res_json.get("message"))
            if "roles" not in res_json or len(res_json.get("roles")) == 0:
                raise Exception(f"{role_id} is not a valid role ID.")
        except Exception as e:
            raise Exception(e)
        try:
            response.raise_for_status()
        except:
            raise Exception(res_json)

        return res_json

    def get_leaderboard_analytics(self, board, limit, start, end):
        """Fetches analytics of a given leaderboard in a given period of time, to a limited amount of positions.
        :param board: name of the wanted board
        :param limit: limitation of positions to show in analytics
        :param start: start of time range
        :param end: end of time range
        :return: json with leaderboard analytics, by position.
        """
        endpoint_url = f"{self.base_url}/v2/analytics/leaderboard"
        params = {"board": board, "limit": limit, "start": start, "end": end}
        response = self.session.get(endpoint_url, params=params)

        try:
            res_json = response.json()
        except:
            raise Exception(response.content)
        try:
            response.raise_for_status()
        except:
            raise Exception(res_json)
        return res_json
