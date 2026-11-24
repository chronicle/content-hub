from __future__ import annotations

import unittest

from zscaler.core.auth import AuthenticatedSession, SessionAuthenticationParameters


class TestApiRootNormalization(unittest.TestCase):
    """
    Tests URL normalization logic in AuthenticatedSession for both
    Legacy API Key and OAuth 2.0 authentication modes.
    """

    def setUp(self) -> None:
        self.session = AuthenticatedSession()

    def test_legacy_auth_zsapi_domain(self) -> None:
        """
        Verifies that for legacy auth, a zsapi domain is normalized to /api/v1(no /zia).
        """
        params = SessionAuthenticationParameters(
            api_root="https://zsapi.zscloud.net",
            login_id="user@test.com",
            api_key="key",
            password="pass",
        )
        # pylint: disable=protected-access
        self.session._reset_auth_state()
        self.session._check_auth_type(params)
        normalized = self.session._normalize_api_root(params.api_root)
        self.assertEqual(normalized, "https://zsapi.zscloud.net/api/v1")

    def test_legacy_auth_admin_domain(self) -> None:
        """
        Verifies that for legacy auth, an admin domain is normalized to /api/v1.
        """
        params = SessionAuthenticationParameters(
            api_root="https://admin.zscloud.net",
            login_id="user@test.com",
            api_key="key",
            password="pass",
        )
        # pylint: disable=protected-access
        self.session._reset_auth_state()
        self.session._check_auth_type(params)
        normalized = self.session._normalize_api_root(params.api_root)
        self.assertEqual(normalized, "https://admin.zscloud.net/api/v1")

    def test_legacy_auth_with_zia_in_path(self) -> None:
        """
        Verifies that for legacy auth, if /zia/api/v1 is in the path, it is corrected to
        /api/v1.
        """
        params = SessionAuthenticationParameters(
            api_root="https://zsapi.zscloud.net/zia/api/v1",
            login_id="user@test.com",
            api_key="key",
            password="pass",
        )
        # pylint: disable=protected-access
        self.session._reset_auth_state()
        self.session._check_auth_type(params)
        normalized = self.session._normalize_api_root(params.api_root)
        self.assertEqual(normalized, "https://zsapi.zscloud.net/api/v1")

    def test_oauth_auth_zsapi_domain(self) -> None:
        """
        Verifies that for OAuth auth, a zsapi domain is normalized to /zia/api/v1.
        """
        params = SessionAuthenticationParameters(
            api_root="https://zsapi.zscloud.net",
            client_id="cid",
            client_secret="csec",
            login_api_root="https://login.zsapi.net",
        )
        # pylint: disable=protected-access
        self.session._reset_auth_state()
        self.session._check_auth_type(params)
        normalized = self.session._normalize_api_root(params.api_root)
        self.assertEqual(normalized, "https://zsapi.zscloud.net/zia/api/v1")

    def test_oauth_auth_full_zia_path(self) -> None:
        """
        Verifies that for OAuth auth, a full /zia/api/v1 path is preserved.
        """
        params = SessionAuthenticationParameters(
            api_root="https://zsapi.zscloud.net/zia/api/v1",
            client_id="cid",
            client_secret="csec",
            login_api_root="https://login.zsapi.net",
        )
        # pylint: disable=protected-access
        self.session._reset_auth_state()
        self.session._check_auth_type(params)
        normalized = self.session._normalize_api_root(params.api_root)
        self.assertEqual(normalized, "https://zsapi.zscloud.net/zia/api/v1")

    def test_oauth_auth_admin_domain_with_zia(self) -> None:
        """
        Verifies that for OAuth auth, an admin domain with /zia path is normalized to /zia/api/v1.
        """
        params = SessionAuthenticationParameters(
            api_root="https://admin.zscalerone.net/zia",
            client_id="cid",
            client_secret="csec",
            login_api_root="https://login.zsapi.net",
        )
        # pylint: disable=protected-access
        self.session._reset_auth_state()
        self.session._check_auth_type(params)
        normalized = self.session._normalize_api_root(params.api_root)
        self.assertEqual(normalized, "https://admin.zscalerone.net/zia/api/v1")

    def test_legacy_auth_admin_domain_with_zia(self) -> None:
        """
        Verifies that for legacy auth, an admin domain with /zia path strips /zia and normalizes to /api/v1.
        """
        params = SessionAuthenticationParameters(
            api_root="https://admin.zscalerone.net/zia",
            login_id="user@test.com",
            api_key="key",
            password="pass",
        )
        # pylint: disable=protected-access
        self.session._reset_auth_state()
        self.session._check_auth_type(params)
        normalized = self.session._normalize_api_root(params.api_root)
        self.assertEqual(normalized, "https://admin.zscalerone.net/api/v1")


if __name__ == "__main__":
    unittest.main()
