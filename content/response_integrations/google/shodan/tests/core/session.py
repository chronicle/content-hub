from __future__ import annotations

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction

from .product import Shodan


class ShodanSession(
    MockSession[MockRequest, MockResponse, Shodan]
):
    def get_routed_functions(self) -> list[RouteFunction]:
        return []

    @router.get(r".*\S+/\S+/\S+")
    def get_ip_info(self, request: MockRequest) -> MockResponse:
        try:
            response_data = self._product.get_ip_info()
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    @router.get(r".*\S+/\S+")
    def search(self, request: MockRequest) -> MockResponse:
        try:
            response_data = self._product.search()
            return MockResponse(content=response_data)
        except Exception as e:
            return MockResponse(content=str(e), status_code=500)

    _DEFAULT_DICT_RESPONSE = {"ok": True, "result": "success", "data": {"id": "mock_id", "name": "mock"}, "results": [{"id": "mock_id"}], "token": "mock_token_value", "access_token": "mock_token_value", "accessToken": "mock_token_value", "refreshToken": "mock_refresh_token", "session": "mock_session", "sid": "mock_session_id", "userId": "mock_user", "selectedAccountSettingsId": "mock_account", "expires_in": 3600, "token_type": "Bearer", "offering": "community", "success": True, "IsSuccessful": True, "message": "OK", "response_code": "1", "version": "1.0", "status": "ok", "rawOutput": ["mock_key: mock_value"], "output": {}}

    def send(self, request, **kwargs):
        """Handle session.send(PreparedRequest) used by some SDKs (e.g. sixgill)."""
        method = getattr(request, "method", None) or "GET"
        url = getattr(request, "url", None) or ""
        return self.request(method, url, **kwargs)

    def _do_request(self, method, request):
        """Override to return a default response for unmatched routes.

        Returns a default response for any HTTP call not matched by a
        specific @router route. The response shape (dict vs list) is
        determined at generation time based on how the integration's
        test_connectivity method consumes the response.
        """
        if self._product._fail_requests_active:
            return MockResponse(
                content={"error": "Simulated API failure"},
                status_code=500,
                headers={"Content-Type": "application/json"},
            )
        from integration_testing.custom_types import NO_RESPONSE
        import re as _re
        response = NO_RESPONSE
        path = request.url.path
        for path_pattern, fn in self.routes[method].items():
            if _re.fullmatch(path_pattern, path) is not None:
                response = fn(request)
                break
        if response is NO_RESPONSE:
            resp = MockResponse(
                content=self._DEFAULT_DICT_RESPONSE,
                headers={"Content-Type": "application/json",
                         "X-FeApi-Token": "mock_token_value",
                         "X-auth-access-token": "mock_token_value",
                         "X-auth-refresh-token": "mock_token_value",
                         "DOMAIN_UUID": "mock_uuid",
                         "Xsrf-Token": "mock_xsrf_token",
                         "Set-Cookie": "JSESSIONID=mock_session; APPSESSIONID=mock_session"},
            )
            resp.cookies.set('JSESSIONID', 'mock_session')
            resp.cookies.set('APPSESSIONID', 'mock_session')
            return resp
        return response
