from __future__ import annotations

import dataclasses
from typing import Optional

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class RansomwareResilience:
    """Virtual RRS API server state.

    Each field holds a mock response that can be overridden per test.
    If a field is None, the corresponding getter returns a safe default.

    Error simulation:
        Set ``<endpoint>_status_code`` to a non-2xx value to make the mock
        endpoint return that HTTP status.  The corresponding
        ``<endpoint>_response`` will be used as the error body.
    """

    token_response: Optional[SingleJson] = None
    enrich_ip_response: Optional[SingleJson] = None
    enrich_storage_response: Optional[SingleJson] = None
    check_job_status_response: Optional[SingleJson] = None
    take_snapshot_response: Optional[SingleJson] = None
    volume_offline_response: Optional[SingleJson] = None

    # Error simulation — set to a non-2xx code to trigger error responses
    token_status_code: Optional[int] = None
    enrich_ip_status_code: Optional[int] = None
    enrich_storage_status_code: Optional[int] = None
    check_job_status_status_code: Optional[int] = None
    take_snapshot_status_code: Optional[int] = None
    volume_offline_status_code: Optional[int] = None

    def get_token(self) -> SingleJson:
        """Return mock OAuth token response."""
        if self.token_response:
            return self.token_response
        return {
            "access_token": "mock_access_token_12345",
            "expires_in": 1800,
        }

    def get_enrich_ip(self) -> SingleJson:
        """Return mock enrich IP response."""
        if self.enrich_ip_response:
            return self.enrich_ip_response
        return {
            "job_id": "mock-job-id::job-1",
            "status": "queued",
            "source": "rps-agent",
            "agent_id": "mock-agent-id",
            "records": [],
        }

    def get_enrich_storage(self) -> SingleJson:
        """Return mock enrich storage response."""
        if self.enrich_storage_response:
            return self.enrich_storage_response
        return []

    def get_check_job_status(self) -> SingleJson:
        """Return mock job status response."""
        if self.check_job_status_response:
            return self.check_job_status_response
        return {
            "job_id": "mock-job-id::job-1",
            "source": "rps-agent",
            "status": "SUCCESS",
            "records": [],
        }

    def get_take_snapshot(self) -> SingleJson:
        """Return mock take snapshot response."""
        if self.take_snapshot_response:
            return self.take_snapshot_response
        return {
            "job_id": "mock-job-id",
            "status": "queued",
            "source": "ontap",
            "agent_id": "mock-agent-id",
        }

    def get_volume_offline(self) -> SingleJson:
        """Return mock volume offline response."""
        if self.volume_offline_response:
            return self.volume_offline_response
        return {
            "job_id": "mock-job-id",
            "status": "queued",
            "source": "ontap",
            "agent_id": "mock-agent-id",
        }
