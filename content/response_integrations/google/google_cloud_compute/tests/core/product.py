"""Google Cloud Compute fake product – returns canned data to the session router.

Each public method corresponds to one API endpoint used by GoogleCloudComputeManager.
Tests configure responses via setters; a context-manager ``fail_requests`` triggers
simulated 500 errors for negative-path tests.
"""
from __future__ import annotations
import abc

import contextlib
from typing import Any

from TIPCommon.types import SingleJson


class GoogleCloudCompute(abc.ABC):
    """In-memory fake of the Google Cloud Compute / OS Config APIs."""

    def __init__(self) -> None:
        self._fail_requests_active: bool = False
        self._fail_status_code: int = 500

        # Per-endpoint canned response stores
        self._zones_response: SingleJson = {"items": [{"name": "us-central1-a"}]}
        self._instances_aggregated: SingleJson = {
            "items": {
                "zones/us-central1-a": {
                    "instances": []
                }
            }
        }
        self._instances: SingleJson = {"items": []}
        self._instance: SingleJson = {}
        self._instance_iam_policy: SingleJson = {}
        self._set_iam_policy_response: SingleJson = {}
        self._operation: SingleJson = {}
        self._firewall_rule: SingleJson = {}
        self._patch_job: SingleJson = {}

    # ------------------------------------------------------------------ #
    # Context manager – force every endpoint to raise an HTTP 500         #
    # ------------------------------------------------------------------ #

    @contextlib.contextmanager
    def fail_requests(self, status_code: int = 500) -> Any:
        """Temporarily make all endpoints return an HTTP error."""
        self._fail_requests_active = True
        self._fail_status_code = status_code
        try:
            yield
        finally:
            self._fail_requests_active = False

    def _maybe_fail(self) -> None:
        """Raise RuntimeError when fail mode is active (caught by MockSession)."""
        if self._fail_requests_active:
            raise RuntimeError(f"Simulated HTTP {self._fail_status_code} error")

    # ------------------------------------------------------------------ #
    # Setters – used by tests to prime canned data                        #
    # ------------------------------------------------------------------ #

    def set_zones_response(self, response: SingleJson) -> None:
        self._zones_response = response

    def set_instances_aggregated(self, response: SingleJson) -> None:
        self._instances_aggregated = response

    def set_instances(self, response: SingleJson) -> None:
        self._instances = response

    def set_instance(self, response: SingleJson) -> None:
        self._instance = response

    def set_instance_iam_policy(self, response: SingleJson) -> None:
        self._instance_iam_policy = response

    def set_set_iam_policy_response(self, response: SingleJson) -> None:
        self._set_iam_policy_response = response

    def set_operation(self, response: SingleJson) -> None:
        self._operation = response

    def set_firewall_rule(self, response: SingleJson) -> None:
        self._firewall_rule = response

    def set_patch_job(self, response: SingleJson) -> None:
        self._patch_job = response

    # ------------------------------------------------------------------ #
    # API endpoint simulators                                              #
    # ------------------------------------------------------------------ #

    def get_zones(self) -> SingleJson:
        self._maybe_fail()
        return self._zones_response

    def get_instances_aggregated(self) -> SingleJson:
        self._maybe_fail()
        return self._instances_aggregated

    def get_instances(self) -> SingleJson:
        self._maybe_fail()
        return self._instances

    def get_instance(self) -> SingleJson:
        self._maybe_fail()
        return self._instance

    def get_instance_iam_policy(self) -> SingleJson:
        self._maybe_fail()
        return self._instance_iam_policy

    def set_instance_iam_policy_api(self) -> SingleJson:
        self._maybe_fail()
        return self._set_iam_policy_response

    def post_operation(self) -> SingleJson:
        self._maybe_fail()
        return self._operation

    def get_operation(self) -> SingleJson:
        self._maybe_fail()
        return self._operation

    def patch_operation(self) -> SingleJson:
        self._maybe_fail()
        return self._operation

    def delete_operation(self) -> SingleJson:
        self._maybe_fail()
        return self._operation

    def get_firewall_rule(self) -> SingleJson:
        self._maybe_fail()
        return self._firewall_rule

    def patch_firewall_rule(self) -> SingleJson:
        self._maybe_fail()
        return self._operation

    def execute_patch_job(self) -> SingleJson:
        self._maybe_fail()
        return self._patch_job

    def get_patch_job(self) -> SingleJson:
        self._maybe_fail()
        return self._patch_job
