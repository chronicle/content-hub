from __future__ import annotations

import requests
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler


class FullContactManager:
    def __init__(self, api_key, verify_ssl=True):
        # self.api_key = api_key
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self.verify_ssl = verify_ssl

    def enrich_person(self, email):
        url = "https://api.fullcontact.com/v3/person.enrich"
        data = {"email": email}
        res = requests.post(
            url,
            headers=self._headers,
            json=data,
            verify=self.verify_ssl,
        )
        return res

    def enrich_domain(self, domain):
        url = "https://api.fullcontact.com/v3/company.enrich"
        data = {"domain": domain}
        res = requests.post(
            url,
            headers=self._headers,
            json=data,
            verify=self.verify_ssl,
        )
        return res


@output_handler
def main():
    siemplify = SiemplifyAction()

    domain = "google.com"
    api_key = siemplify.get_configuration("Full Contact")["API Key"]

    if domain:
        fcm = FullContactManager(api_key)
        res2 = fcm.enrich_domain(domain).json()
        if "status" in res2 and res2["status"] == 401:
            raise Exception(res2)

    output_message = "Success"
    result_value = True

    siemplify.end(output_message, result_value)


if __name__ == "__main__":
    main()
