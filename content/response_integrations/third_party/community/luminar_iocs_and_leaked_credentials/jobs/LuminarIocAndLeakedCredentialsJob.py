from __future__ import annotations

from datetime import datetime

import requests
from soar_sdk.SiemplifyJob import SiemplifyJob

SCRIPT_NAME = "CloseCasesBasedOnSearch"
SEARCH_URL = "external/v1/search/CaseSearchEverything"
BULK_ASSIGN_URL = "external/v1/cases/ExecuteBulkAssign"
BULK_CLOSE_URL = "external/v1/cases/ExecuteBulkCloseCase"
CASE_MIN_URL = "{}/external/v1/cases/GetCaseFullDetails/{}"
TIMEOUT = 60.0


def get_bearer_token(siemplify, username, password):
    address = f"{siemplify.API_ROOT}/{'external/v1/accounts/Login?format=camel'}"
    response = siemplify.session.post(
        address,
        json={"Username": username, "Password": password},
    )
    response.raise_for_status()
    return response.json()["token"]


def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME  # In order to use the SiemplifyLogger, you must assign a name to the script.
    username = siemplify.parameters["Siemplify Username"]
    password = siemplify.parameters["Siemplify Password"]
    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    try:
        bearer_token = get_bearer_token(siemplify, username, password)
        session = requests.Session()
        session.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {bearer_token}",
        }
        payload = {"isCaseClosed": False, "title": "Luminar IOCs"}

        res_search = session.post(
            f"{siemplify.API_ROOT}/{SEARCH_URL}",
            json=payload,
            timeout=TIMEOUT,
        )

        res_search.raise_for_status()
        results = res_search.json().get("results") or res_search.json().get("Results")
        case_ids = (
            [item.get("id") or item.get("Id") for item in results] if results else []
        )
        for case_id in case_ids:
            try:
                cases = []
                case_data = siemplify.session.get(
                    CASE_MIN_URL.format(siemplify.API_ROOT, case_id),
                    timeout=TIMEOUT,
                )
                expiration_date = case_data.json()["alerts"][0]["securityEventCards"][
                    0
                ]["fields"][1]["items"][0]["value"]

                if expiration_date and (
                    datetime.strptime(expiration_date[:19], "%Y-%m-%dT%H:%M:%S")
                    < datetime.today()
                ):
                    cases.append(case_id)
                    res_assign = session.post(
                        f"{siemplify.API_ROOT}/{BULK_ASSIGN_URL}",
                        json={"casesIds": cases, "userName": username},
                        timeout=TIMEOUT,
                    )
                    res_assign.raise_for_status()
                    close_payload = {
                        "closeComment": "Expired IOCs",
                        "closeReason": "Maintenance",
                        "rootCause": "Other",
                        "casesIds": cases,
                    }
                    res_close = session.post(
                        f"{siemplify.API_ROOT}/{BULK_CLOSE_URL}",
                        json=close_payload,
                        timeout=TIMEOUT,
                    )
                    res_close.raise_for_status()
                    siemplify.LOGGER.info(res_close.content)
            except Exception as err:
                siemplify.LOGGER.info(err)
                continue
    except Exception as err:
        siemplify.LOGGER.error(f"General error performing Job {SCRIPT_NAME}")
        siemplify.LOGGER.exception(err)
        raise

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end_script()


if __name__ == "__main__":
    main()
