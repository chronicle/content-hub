"""MockSession routing fake HTTP requests to the Infoblox product fixture."""

from __future__ import annotations

from typing import Iterable

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from .product import Infoblox, SimulatedAPIFailure


def _respond(callable_):
    """Call a product method, turning a ``SimulatedAPIFailure`` into an error MockResponse."""
    try:
        return MockResponse(content=callable_())
    except SimulatedAPIFailure as e:
        return MockResponse(content=e.body, status_code=e.status_code)
    except Exception as e:  # pragma: no cover - defensive fallback
        return MockResponse(content=str(e), status_code=500)


class InfobloxSession(MockSession[MockRequest, MockResponse, Infoblox]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.ping,
            self.get_account,
            self.dns_record_lookup,
            self.ip_lookup,
            self.host_lookup,
            self.dhcp_lease_lookup,
            self.create_custom_list,
            self.get_custom_list,
            self.get_custom_list_by_id,
            self.update_custom_list,
            self.remove_custom_list,
            self.update_custom_list_items,
            self.create_network_list,
            self.get_network_list,
            self.get_network_list_by_id,
            self.update_network_list,
            self.remove_network_list,
            self.create_security_policy,
            self.get_security_policies,
            self.update_security_policy,
            self.remove_security_policy,
            self.indicator_threat_lookup_with_tide,
            self.initiate_indicator_intel_lookup_with_dossier,
            self.get_indicator_intel_lookup_result,
            self.get_infoblox_iq_for_threat_defense_indicators,
            self.get_infoblox_iq_for_threat_defense_events,
            self.get_infoblox_iq_for_threat_defense_assets,
            self.update_status_of_insight,
            self.get_infoblox_iq_for_threat_defense_details,
            self.execute_recommendation_actions,
            self.undo_recommendation_action,
            self.get_infoblox_iq_for_threat_defense_list,
            self.get_dns_security_events,
        ]

    # --- Connectivity / account -------------------------------------------------

    @router.get(r"^/api/authn/v1/account/?$")
    def ping(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.ping)

    @router.get(r"^/api/atcfw/v1/account/?$")
    def get_account(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_account)

    # --- DDI lookups -------------------------------------------------------------

    @router.get(r"^/api/ddi/v1/dns/record/?$")
    def dns_record_lookup(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.dns_record_lookup)

    @router.get(r"^/api/ddi/v1/ipam/address/?$")
    def ip_lookup(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.ip_lookup)

    @router.get(r"^/api/ddi/v1/ipam/host/?$")
    def host_lookup(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.host_lookup)

    @router.get(r"^/api/ddi/v1/dhcp/lease/?$")
    def dhcp_lease_lookup(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.dhcp_lease_lookup)

    # --- Custom (named) lists ------------------------------------------------

    @router.post(r"^/api/atcfw/v1/named_lists/?$")
    def create_custom_list(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.create_custom_list)

    @router.get(r"^/api/atcfw/v1/named_lists/?$")
    def get_custom_list(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_custom_list)

    @router.get(r"^/api/atcfw/v1/named_lists/[^/]+/?$")
    def get_custom_list_by_id(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_custom_list_by_id)

    @router.put(r"^/api/atcfw/v1/named_lists/[^/]+/?$")
    def update_custom_list(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.update_custom_list)

    @router.delete(r"^/api/atcfw/v1/named_lists/[^/]+/?$")
    def remove_custom_list(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.remove_custom_list)

    @router.patch(r"^/api/atcfw/v1/named_lists/[^/]+/items/?$")
    def update_custom_list_items(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.update_custom_list_items)

    # --- Network lists ---------------------------------------------------------

    @router.post(r"^/api/atcfw/v1/network_lists/?$")
    def create_network_list(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.create_network_list)

    @router.get(r"^/api/atcfw/v1/network_lists/?$")
    def get_network_list(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_network_list)

    @router.get(r"^/api/atcfw/v1/network_lists/[^/]+/?$")
    def get_network_list_by_id(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_network_list_by_id)

    @router.put(r"^/api/atcfw/v1/network_lists/[^/]+/?$")
    def update_network_list(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.update_network_list)

    @router.delete(r"^/api/atcfw/v1/network_lists/[^/]+/?$")
    def remove_network_list(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.remove_network_list)

    # --- Security policies -------------------------------------------------------

    @router.post(r"^/api/atcfw/v1/security_policies/?$")
    def create_security_policy(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.create_security_policy)

    @router.get(r"^/api/atcfw/v1/security_policies/?$")
    def get_security_policies(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_security_policies)

    @router.put(r"^/api/atcfw/v1/security_policies/[^/]+/?$")
    def update_security_policy(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.update_security_policy)

    @router.delete(r"^/api/atcfw/v1/security_policies/[^/]+/?$")
    def remove_security_policy(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.remove_security_policy)

    # --- TIDE / Dossier -----------------------------------------------------------

    @router.get(r"^/tide/api/data/threats/?$")
    def indicator_threat_lookup_with_tide(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.indicator_threat_lookup_with_tide)

    @router.get(r"^/tide/api/services/intel/lookup/indicator/[^/]+/?$")
    def initiate_indicator_intel_lookup_with_dossier(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.initiate_indicator_intel_lookup_with_dossier)

    @router.get(r"^/tide/api/services/intel/lookup/jobs/[^/]+/results/?$")
    def get_indicator_intel_lookup_result(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_indicator_intel_lookup_result)

    # --- Infoblox IQ for Threat Defense (SOC insights) --------------------------

    @router.get(r"^/api/v2/insights/[^/]+/indicators/?$")
    def get_infoblox_iq_for_threat_defense_indicators(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_infoblox_iq_for_threat_defense_indicators)

    @router.get(r"^/api/v2/insights/[^/]+/events/?$")
    def get_infoblox_iq_for_threat_defense_events(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_infoblox_iq_for_threat_defense_events)

    @router.get(r"^/api/v2/insights/[^/]+/assets/?$")
    def get_infoblox_iq_for_threat_defense_assets(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_infoblox_iq_for_threat_defense_assets)

    @router.put(r"^/api/v2/insights/status/?$")
    def update_status_of_insight(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.update_infoblox_iq_for_threat_defense_status)

    @router.get(r"^/api/v2/insights/[^/]+/?$")
    def get_infoblox_iq_for_threat_defense_details(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_infoblox_iq_for_threat_defense_details)

    @router.post(r"^/api/v2/insights/[^/]+/actions/?$")
    def execute_recommendation_actions(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.execute_recommendation_actions)

    @router.post(r"^/api/v2/insights/global-activity/[^/]+/undo/?$")
    def undo_recommendation_action(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.undo_recommendation_action)

    @router.get(r"^/api/v2/insights/?$")
    def get_infoblox_iq_for_threat_defense_list(self, request: MockRequest) -> MockResponse:
        return _respond(self._product.get_infoblox_iq_for_threat_defense_list)

    # --- DNS security events (paginated, used by the DNS connector) ------------

    @router.get(r"^/api/dnsdata/v2/dns_event/?$")
    def get_dns_security_events(self, request: MockRequest) -> MockResponse:
        params = get_request_payload(request)
        offset = params.get("_offset") if params else None
        try:
            return MockResponse(content=self._product.get_dns_security_events_page(offset))
        except SimulatedAPIFailure as e:
            return MockResponse(content=e.body, status_code=e.status_code)
