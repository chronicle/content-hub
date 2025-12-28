from __future__ import annotations

import requests
from soar_sdk.SiemplifyAction import SiemplifyAction

INTEGRATION_NAME = "PhishTank"

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "phishtank/Siemplify",
}


def main():
    siemplify = SiemplifyAction()

    service_url = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME,
        param_name="Service Url",
    )
    payload = {"url": "google.com", "format": "json"}
    res = requests.post(service_url, headers=HEADERS, params=payload)
    res.raise_for_status()

    siemplify.end("PhishTank is connected", True)


if __name__ == "__main__":
    main()
