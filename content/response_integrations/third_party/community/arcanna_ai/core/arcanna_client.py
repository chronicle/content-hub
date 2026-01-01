from __future__ import annotations

import time

import requests
from requests import HTTPError


class ArcannaClient:
    """Implements Arcanna API"""

    def __init__(self, api_key, base_url, verify=True):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = verify
        self.session.headers.update(
            {"accept": "application/json", "x-arcanna-api-key": self.api_key},
        )

    def test_arcanna(self):
        url_suffix = "/api/v1/health"
        return self._get_request(url_suffix)

    def retry_mechanism(self, retry_count, seconds_per_retry):
        if retry_count == 0:
            return False
        retry_count -= 1
        time.sleep(seconds_per_retry)
        return True

    def list_jobs(self):
        url_suffix = "/api/v1/jobs"
        return self._get_request(url_suffix)

    def get_job_by_id(self, job_id):
        url_suffix = "/api/v1/jobs/" + job_id
        return self._get_request(url_suffix)

    def get_job_decision_set(self, job_id):
        url_suffix = f"/api/v1/jobs/{job_id}/labels"
        return self._get_request(url_suffix)

    def get_job_decision_set_by_name(self, job_name):
        url_suffix = "/api/v1/jobs/get_by_name/labels"
        body = {"job_name": job_name}
        return self._post_request(url_suffix, body)

    def get_job_by_name(self, job_name):
        url_suffix = "/api/v1/jobs/get_by_name"
        body = {"job_name": job_name}
        return self._post_request(url_suffix, body)

    def send_raw_event(self, job_id, raw_body, event_id=None):
        url_suffix = "/api/v1/events/"

        if event_id is not None:
            url_suffix = url_suffix + str(event_id)
        body = {"job_id": job_id, "raw_body": raw_body}
        return self._post_request(url_suffix, body)

    def get_event_status(self, job_id, event_id):
        url_suffix = f"/api/v1/events/{job_id}/{event_id}"
        return self._get_request(url_suffix)

    def send_feedback(self, job_id, event_id, username, arcanna_label):
        url_suffix = f"/api/v1/events/{job_id}/{event_id}/feedback"
        body = {"cortex_user": username, "feedback": arcanna_label}
        return self._put_request(url_suffix, body)

    def train_model(self, job_id, username):
        url_suffix = f"/api/v1/jobs/{job_id}/train?username={username}"
        body = {"username": username}
        return self._post_request(url_suffix, body)

    def export_event(self, job_id, event_id):
        url_suffix = f"/api/v1/events/{job_id}/{event_id}/export"
        return self._get_request(url_suffix)

    def _get_request(self, url_suffix):
        raw_response = self.session.get(url=self.base_url + url_suffix, timeout=30)
        if raw_response.status_code != 200:
            raise HTTPError(
                f"Error in API call [{raw_response.status_code}]. Reason: {raw_response.text}",
            )
        return raw_response.json()

    def _post_request(self, url_suffix, body):
        raw_response = self.session.post(
            url=self.base_url + url_suffix,
            json=body,
            timeout=30,
        )
        if raw_response.status_code not in [200, 201]:
            raise HTTPError(
                f"Arcanna error HttpCode={raw_response.status_code} body={raw_response.text}",
            )
        return raw_response.json()

    def _put_request(self, url_suffix, body):
        raw_response = self.session.put(
            url=self.base_url + url_suffix,
            json=body,
            timeout=30,
        )
        if raw_response.status_code != 200:
            raise HTTPError(
                f"Arcanna Error HttpCode={raw_response.status_code} body={raw_response.text}",
            )
        return raw_response.json()
