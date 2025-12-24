import time

import requests

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning,
)

API_ROOT = "https://app.houdin.io/api/v1/{0}"
AVAILABLE_SCANNERS = [
    "vt",
    "urlscan",
    "mesmer",
    "servicenow",
    "abuseipdb",
    "alienvault",
    "elasticsearch",
    "triage",
]


class HoudinManager:
    def __init__(self, api_key, verify_ssl=True):
        self.api_key = api_key

    def test_connectivity(self):
        """Ping to server to be sure that connected
        :return: None
        :raises Exception: If connection failed
        """
        retry = 0
        while retry < 2:
            try:
                headers = {"Accept": "application/json", "X-API-Key": self.api_key}
                response = requests.request(
                    method="POST", url=API_ROOT.format("ping"), headers=headers
                )
                result = response.json()
                if response.status_code == 500:
                    retry += 1
                    continue
                if response.status_code != 200:
                    result = result.get(
                        "error", "An issue occurred during verification. Please retry."
                    )
                    raise Exception(f"Error while verifying connection: {result}")
                break
            except Exception as e:
                raise Exception(f"Error while verifying connection: {e}")

    def cleanScanOn(self, input_list):
        """Clean the scanOn input list
        :param input_list: List of scan targets
        :return: Cleaned list or None if empty
        """
        cleaned = []
        for item in input_list:
            if not isinstance(item, str):
                continue
            stripped = item.strip()
            if stripped in AVAILABLE_SCANNERS or stripped.startswith("custom_"):
                cleaned.append(stripped)
        return cleaned if cleaned else None

    def launch_scan(self, artifact, scanOn=None):
        """Launch a scan on the provided artifact
        :param artifact: The artifact to scan
        :param scanOn: Optional list of scan targets
        :return: Scan ID and status
        """
        headers = {"Content-Type": "application/json", "X-API-Key": self.api_key}
        retry = 0
        scan_id = None
        while retry < 2:
            try:
                post_url = API_ROOT.format("scan/launch")
                post_data = {"artifact": artifact}
                if scanOn and scanOn != [""] and self.cleanScanOn(scanOn):
                    post_data["scanOn"] = self.cleanScanOn(scanOn)
                post_response = requests.post(post_url, json=post_data, headers=headers)
                if post_response.status_code == 500:
                    retry += 1
                    continue
                post_response.raise_for_status()
                post_result = post_response.json()
                scan_id = post_result.get("scanID")
                status = post_result.get("status")
                break
            except Exception as e:
                raise Exception(f"{e}")
        if not scan_id:
            raise Exception("No scanID received in response.")
        return scan_id, status

    def poll_scan_result(self, scan_id, max_retries=10, retry_interval=3):
        """Poll for the scan result
        :param scan_id: The ID of the scan to poll
        :return: The scan result
        """
        headers = {"Accept": "application/json", "X-API-Key": self.api_key}
        poll_url = API_ROOT.format(f"scan/result?scanID={scan_id}")
        retry = 0
        while retry < max_retries:
            try:
                response = requests.get(poll_url, headers=headers)
                if response.status_code == 202:
                    time.sleep(retry_interval)
                    retry += 1
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise Exception(f"{e}")
        raise Exception("Polling for scan result failed after maximum retries.")
