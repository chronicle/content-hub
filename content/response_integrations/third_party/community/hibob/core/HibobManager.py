from __future__ import annotations

import copy

import requests

# The api_root is a default value in the integration params
# api_root = 'https://api.hibob.com'

headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "Authorization": "api_token",
}


def get_unicode(yair):
    return str(yair)


def dict_to_flat(target_dict):
    """Receives nested dictionary and returns it as a flat dictionary.
    :param target_dict: {dict}
    :return: Flat dict : {dict}
    """
    target_dict = copy.deepcopy(target_dict)

    def expand(raw_key, raw_value):
        key = raw_key
        value = raw_value
        """
        :param key: {string}
        :param value: {string}
        :return: Recursive function.
        """
        if value is None:
            return [(get_unicode(key), "")]
        if isinstance(value, dict):
            # Handle dict type value
            return [
                (
                    f"{get_unicode(key)}_{get_unicode(sub_key)}",
                    get_unicode(sub_value),
                )
                for sub_key, sub_value in dict_to_flat(value).items()
            ]
        if isinstance(value, list):
            # Handle list type value
            count = 1
            l = []
            items_to_remove = []
            for value_item in value:
                if isinstance(value_item, dict):
                    # Handle nested dict in list
                    l.extend(
                        [
                            (
                                f"{get_unicode(key)}_{get_unicode(count)}_{get_unicode(sub_key)}",
                                sub_value,
                            )
                            for sub_key, sub_value in dict_to_flat(value_item).items()
                        ],
                    )
                    items_to_remove.append(value_item)
                    count += 1
                elif isinstance(value_item, list):
                    l.extend(
                        expand(get_unicode(key) + "_" + get_unicode(count), value_item),
                    )
                    count += 1
                    items_to_remove.append(value_item)

            for value_item in items_to_remove:
                value.remove(value_item)

            for value_item in value:
                l.extend([(get_unicode(key) + "_" + get_unicode(count), value_item)])
                count += 1

            return l
        return [(get_unicode(key), get_unicode(value))]

    items = [
        item
        for sub_key, sub_value in target_dict.items()
        for item in expand(sub_key, sub_value)
    ]
    return dict(items)


class HibobManager:
    """Hibob Manager"""

    def __init__(self, api_root, api_token):
        self.api_root = api_root
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update(headers)
        self.session.headers["Authorization"] = api_token

    def test_connectivity(self):
        """Test connectivity to Hibob
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.api_root}/api/user"
        response = self.session.get(url)

        if response.status_code == 401:
            raise Exception("Unauthorized for url, Bad credentials")

        if response.status_code == 404:
            raise Exception("The url doesnt exists, Please enter a valid url")

        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        if response.json():
            return True
        raise Exception("Something went wrong, please try again")

    def get_all_users_details(self):
        """Read all company people and showing inactive users"""
        all_user_detail_url = f"{self.api_root}/v1/people"
        response = self.session.get(all_user_detail_url)

        if response.status_code == 404:
            return None

        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def get_user_details(self, employee_identifier):
        """Read company people by id or email
        Gets specific user details by giving email or id
        """
        employee_detail_url = f"{self.api_root}/v1/people/{employee_identifier}"
        response = self.session.get(employee_detail_url)

        if response.status_code == 404:
            return None

        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()

    def invite_employee_to_hibob(self, employee_identifier, welcome_wizard_id):
        invitation_url = (
            f"{self.api_root}/v1/employees/{employee_identifier}/invitations"
        )
        body_params = {"welcomeWizardId": welcome_wizard_id}

        response = self.session.post(invitation_url, json=body_params)

        if response.status_code == 404:
            return None
        # if response.status_code == 400:
        #     return ('Bad request,please valid the employees id and the welcome wizard id')
        response.raise_for_status()
        return response.content

    def revoke_access_to_hibob(self, employee_identifier):
        revoke_access_url = (
            f"{self.api_root}/v1/employees/{employee_identifier}/uninvite"
        )
        response = self.session.post(revoke_access_url)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.content

    def get_user_image(self, employee_identifier):
        user_image_url = f"{self.api_root}/v1/avatars/{employee_identifier}"

        # Getting the full url of the image
        response = self.session.get(user_image_url)

        if response.status_code == 404:
            return None
        response.raise_for_status()

        return response.content

    def upload_user_image(self, employee_identifier, image_url):
        upload_image_url = f"{self.api_root}/v1/avatars/{employee_identifier}"
        body_params = {"url": image_url}

        response = self.session.put(upload_image_url, json=body_params)

        response.raise_for_status()
        return response.content

    def get_summery_about_all_wizards(self):
        welcome_wizard_url = f"{self.api_root}/v1/onboarding/wizards"

        response = self.session.get(welcome_wizard_url)
        response.raise_for_status()

        try:
            response.json()
        except:
            raise Exception(response.content)

        return response.json()
