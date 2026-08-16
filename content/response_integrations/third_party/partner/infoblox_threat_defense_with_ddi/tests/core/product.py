"""Fake Infoblox Threat Defense with DDI backend for tests — holds state and serves canned responses."""

from __future__ import annotations

import contextlib
import dataclasses

from TIPCommon.types import SingleJson

DEFAULT_ACCOUNT_RESPONSE: SingleJson = {"results": {"customer_id": "test-customer-id"}}


class SimulatedAPIFailure(Exception):
    """Raised by a fake product method while ``Infoblox.fail_requests`` is active.

    Carries the HTTP status code and JSON body the mock session should answer
    with, so tests can exercise the integration's error-handling branches
    (``HandleExceptions``) for a specific status code (400/404/409/429/5xx).
    """

    def __init__(self, status_code: int = 500, body: SingleJson | None = None):
        self.status_code = status_code
        self.body = body if body is not None else {"error": [{"message": "Simulated API failure"}]}
        super().__init__(str(self.body))


@dataclasses.dataclass(slots=True)
class Infoblox:
    """In-memory fake of the Infoblox backend used by InfobloxSession."""

    _account_response: SingleJson = dataclasses.field(default_factory=lambda: dict(DEFAULT_ACCOUNT_RESPONSE))
    _ping_response: SingleJson | None = None
    _dns_record_response: SingleJson | None = None
    _ip_lookup_response: SingleJson | None = None
    _host_lookup_response: SingleJson | None = None
    _dhcp_lease_response: SingleJson | None = None

    _custom_list_response: SingleJson | None = None
    _custom_list_by_id_response: SingleJson | None = None
    _create_custom_list_response: SingleJson | None = None
    _update_custom_list_items_response: SingleJson | None = None

    _network_list_response: SingleJson | None = None
    _network_list_by_id_response: SingleJson | None = None
    _create_network_list_response: SingleJson | None = None
    _update_network_list_response: SingleJson | None = None

    _security_policies_response: SingleJson | None = None
    _create_security_policy_response: SingleJson | None = None
    _update_security_policy_response: SingleJson | None = None

    _tide_response: SingleJson | None = None
    _dossier_initiate_response: SingleJson | None = None
    _dossier_result_response: SingleJson | None = None

    _insights_indicators_response: SingleJson | None = None
    _insights_events_response: SingleJson | None = None
    _insights_assets_response: SingleJson | None = None
    _insight_details_response: SingleJson | None = None
    _insight_status_response: SingleJson | None = None
    _insights_list_response: SingleJson | None = None
    _recommendation_action_response: SingleJson | None = None
    _undo_recommendation_response: SingleJson | None = None

    _dns_events_page_response: SingleJson | None = None

    _fail_requests_active: bool = False
    _fail_status_code: int = 500
    _fail_body: SingleJson | None = None

    @contextlib.contextmanager
    def fail_requests(self, status_code: int = 500, body: SingleJson | None = None):
        """Force every routed call inside the context to raise ``SimulatedAPIFailure``."""
        self._fail_requests_active = True
        self._fail_status_code = status_code
        self._fail_body = body
        try:
            yield
        finally:
            self._fail_requests_active = False
            self._fail_status_code = 500
            self._fail_body = None

    def _check_fail(self) -> None:
        if self._fail_requests_active:
            raise SimulatedAPIFailure(self._fail_status_code, self._fail_body)

    # --- Setters -------------------------------------------------------------

    def set_account_response(self, response: SingleJson) -> None:
        self._account_response = response

    def set_ping_response(self, response: SingleJson) -> None:
        self._ping_response = response

    def set_dns_record_response(self, response: SingleJson) -> None:
        self._dns_record_response = response

    def set_ip_lookup_response(self, response: SingleJson) -> None:
        self._ip_lookup_response = response

    def set_host_lookup_response(self, response: SingleJson) -> None:
        self._host_lookup_response = response

    def set_dhcp_lease_response(self, response: SingleJson) -> None:
        self._dhcp_lease_response = response

    def set_custom_list_response(self, response: SingleJson) -> None:
        self._custom_list_response = response

    def set_custom_list_by_id_response(self, response: SingleJson) -> None:
        self._custom_list_by_id_response = response

    def set_create_custom_list_response(self, response: SingleJson) -> None:
        self._create_custom_list_response = response

    def set_update_custom_list_items_response(self, response: SingleJson) -> None:
        self._update_custom_list_items_response = response

    def set_network_list_response(self, response: SingleJson) -> None:
        self._network_list_response = response

    def set_network_list_by_id_response(self, response: SingleJson) -> None:
        self._network_list_by_id_response = response

    def set_create_network_list_response(self, response: SingleJson) -> None:
        self._create_network_list_response = response

    def set_update_network_list_response(self, response: SingleJson) -> None:
        self._update_network_list_response = response

    def set_security_policies_response(self, response: SingleJson) -> None:
        self._security_policies_response = response

    def set_create_security_policy_response(self, response: SingleJson) -> None:
        self._create_security_policy_response = response

    def set_update_security_policy_response(self, response: SingleJson) -> None:
        self._update_security_policy_response = response

    def set_tide_response(self, response: SingleJson) -> None:
        self._tide_response = response

    def set_dossier_initiate_response(self, response: SingleJson) -> None:
        self._dossier_initiate_response = response

    def set_dossier_result_response(self, response: SingleJson) -> None:
        self._dossier_result_response = response

    def set_insights_indicators_response(self, response: SingleJson) -> None:
        self._insights_indicators_response = response

    def set_insights_events_response(self, response: SingleJson) -> None:
        self._insights_events_response = response

    def set_insights_assets_response(self, response: SingleJson) -> None:
        self._insights_assets_response = response

    def set_insight_details_response(self, response: SingleJson) -> None:
        self._insight_details_response = response

    def set_insight_status_response(self, response: SingleJson) -> None:
        self._insight_status_response = response

    def set_insights_list_response(self, response: SingleJson) -> None:
        self._insights_list_response = response

    def set_recommendation_action_response(self, response: SingleJson) -> None:
        self._recommendation_action_response = response

    def set_undo_recommendation_response(self, response: SingleJson) -> None:
        self._undo_recommendation_response = response

    def set_dns_events_page_response(self, response: SingleJson) -> None:
        """Response served only for the first (offset=0) page; later pages are empty."""
        self._dns_events_page_response = response

    # --- Getters (used by the routed session functions) -----------------------

    def get_account(self) -> SingleJson:
        self._check_fail()
        return self._account_response

    def ping(self) -> SingleJson:
        self._check_fail()
        return self._ping_response or {}

    def dns_record_lookup(self) -> SingleJson:
        self._check_fail()
        return self._dns_record_response or {"results": []}

    def ip_lookup(self) -> SingleJson:
        self._check_fail()
        return self._ip_lookup_response or {"results": []}

    def host_lookup(self) -> SingleJson:
        self._check_fail()
        return self._host_lookup_response or {"results": []}

    def dhcp_lease_lookup(self) -> SingleJson:
        self._check_fail()
        return self._dhcp_lease_response or {"results": []}

    def get_custom_list(self) -> SingleJson:
        self._check_fail()
        return self._custom_list_response or {"results": []}

    def get_custom_list_by_id(self) -> SingleJson:
        self._check_fail()
        return self._custom_list_by_id_response or {"results": {}}

    def create_custom_list(self) -> SingleJson:
        self._check_fail()
        return self._create_custom_list_response or {"results": {}}

    def update_custom_list(self) -> SingleJson:
        self._check_fail()
        return self._custom_list_by_id_response or {"results": {}}

    def update_custom_list_items(self) -> SingleJson:
        self._check_fail()
        return self._update_custom_list_items_response or {}

    def remove_custom_list(self) -> SingleJson:
        self._check_fail()
        return {}

    def get_network_list(self) -> SingleJson:
        self._check_fail()
        return self._network_list_response or {"results": []}

    def get_network_list_by_id(self) -> SingleJson:
        self._check_fail()
        return self._network_list_by_id_response or {"results": {}}

    def create_network_list(self) -> SingleJson:
        self._check_fail()
        return self._create_network_list_response or {"results": {}}

    def update_network_list(self) -> SingleJson:
        self._check_fail()
        return self._update_network_list_response or {"results": {}}

    def remove_network_list(self) -> SingleJson:
        self._check_fail()
        return {}

    def get_security_policies(self) -> SingleJson:
        self._check_fail()
        return self._security_policies_response or {"results": []}

    def create_security_policy(self) -> SingleJson:
        self._check_fail()
        return self._create_security_policy_response or {"results": {}}

    def update_security_policy(self) -> SingleJson:
        self._check_fail()
        return self._update_security_policy_response or {"results": {}}

    def remove_security_policy(self) -> SingleJson:
        self._check_fail()
        return {}

    def indicator_threat_lookup_with_tide(self) -> SingleJson:
        self._check_fail()
        return self._tide_response or {"threat": []}

    def initiate_indicator_intel_lookup_with_dossier(self) -> SingleJson:
        self._check_fail()
        return self._dossier_initiate_response or {"job_id": "job-1", "status": "PENDING"}

    def get_indicator_intel_lookup_result(self) -> SingleJson:
        self._check_fail()
        return self._dossier_result_response or {"results": []}

    def get_infoblox_iq_for_threat_defense_indicators(self) -> SingleJson:
        self._check_fail()
        return self._insights_indicators_response or {"indicators": []}

    def get_infoblox_iq_for_threat_defense_events(self) -> SingleJson:
        self._check_fail()
        return self._insights_events_response or {"events": []}

    def get_infoblox_iq_for_threat_defense_assets(self) -> SingleJson:
        self._check_fail()
        return self._insights_assets_response or {"assets": []}

    def get_infoblox_iq_for_threat_defense_details(self) -> SingleJson:
        self._check_fail()
        return self._insight_details_response or {}

    def update_infoblox_iq_for_threat_defense_status(self) -> SingleJson:
        self._check_fail()
        return self._insight_status_response or {}

    def get_infoblox_iq_for_threat_defense_list(self) -> SingleJson:
        self._check_fail()
        return self._insights_list_response or {"insight_list": []}

    def execute_recommendation_actions(self) -> SingleJson:
        self._check_fail()
        return self._recommendation_action_response or {"results": []}

    def undo_recommendation_action(self) -> SingleJson:
        self._check_fail()
        return self._undo_recommendation_response or {"result": {}}

    def get_dns_security_events_page(self, offset: str | int | None) -> SingleJson:
        self._check_fail()
        is_first_page = offset in (None, "0", 0) or str(offset) == "0"
        if not is_first_page or self._dns_events_page_response is None:
            return {"result": []}
        return self._dns_events_page_response
