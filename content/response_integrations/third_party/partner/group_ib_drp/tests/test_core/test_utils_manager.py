"""Unit tests for ``core.UtilsManager`` (``extract_host``, ``EntityValidator``, ``GIBConnector``).

These functions are pure helpers that the actions and connectors lean on,
so they get full direct coverage here. ``GIBConnector.init_action_poller``
is exercised both with explicit ``creds`` (the path the connectors use)
and via integration-config lookup (the path the actions use).
"""

from __future__ import annotations

import pathlib
import sys
import sysconfig

_SITE_PACKAGES = pathlib.Path(sysconfig.get_paths()["purelib"])
_SOAR_SDK_DIR = _SITE_PACKAGES / "soar_sdk"
if _SOAR_SDK_DIR.is_dir() and str(_SOAR_SDK_DIR) not in sys.path:
    sys.path.insert(0, str(_SOAR_SDK_DIR))

from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402

from group_ib_drp.core.UtilsManager import (  # noqa: E402
    CaseProcessor,
    EntityValidator,
    GIBConnector,
    extract_host,
)


class TestExtractHost:
    """``extract_host`` is the primary input to alert names/case titles, so we
    cover URL shapes that real DRP feeds throw at the connectors."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("https://www.example.com/path?x=1", "example.com"),
            ("http://EXAMPLE.com:8080/foo", "example.com"),
            ("https://user:pass@example.com/path", "example.com"),
            ("example.com/path?q=1", "example.com"),
            ("www.example.com", "example.com"),
            ("https://sub.domain.example.co.uk/", "sub.domain.example.co.uk"),
            ("ftp://files.example.com/abc", "files.example.com"),
        ],
    )
    def test_returns_lowercase_host_from_various_url_shapes(self, value, expected):
        assert extract_host(value) == expected

    def test_returns_fallback_for_blank_input(self):
        assert extract_host("", fallback="missing") == "missing"
        assert extract_host(None, fallback="missing") == "missing"

    def test_returns_empty_string_when_blank_input_and_no_fallback(self):
        assert extract_host("") == ""
        assert extract_host(None) == ""

    def test_strips_whitespace_before_parsing(self):
        assert extract_host("   https://example.com/  ") == "example.com"

    def test_falls_back_when_parse_explodes(self, monkeypatch):
        """If ``urlsplit`` raises, ``extract_host`` falls back to the supplied
        default. This is what keeps the connectors from crashing when an
        upstream feed sends a malformed URL."""

        def boom(_):
            raise ValueError("kaboom")

        monkeypatch.setattr("group_ib_drp.core.UtilsManager.urllib.parse.urlsplit", boom)
        assert extract_host("anything", fallback="fallback-uid") == "fallback-uid"

    def test_falls_back_to_truncated_raw_when_parse_explodes_and_no_fallback(self, monkeypatch):
        """The 60-char safety cap on ``raw[:60]`` only fires when parsing
        raised and no fallback was supplied. Without it, the function would
        leak unbounded user input into alert names."""

        def boom(_):
            raise ValueError("kaboom")

        monkeypatch.setattr("group_ib_drp.core.UtilsManager.urllib.parse.urlsplit", boom)
        long_input = "x" * 200
        assert extract_host(long_input) == "x" * 60


class TestEntityValidator:
    """Sanity-check the entity classifier the older actions rely on.

    The validator is only used by legacy code paths in the integration but
    keeping it tested protects against accidental breakage when validators
    versions are bumped.
    """

    @pytest.fixture
    def validator(self) -> EntityValidator:
        return EntityValidator()

    def test_classifies_domain(self, validator):
        ident, kind = validator.get_entity_type("Example.COM")
        assert kind == "domain"
        assert ident == "example.com"

    def test_classifies_ipv4(self, validator):
        ident, kind = validator.get_entity_type("8.8.8.8")
        assert kind == "ip"
        assert ident == "8.8.8.8"

    def test_classifies_sha256_hash(self, validator):
        sha = "a" * 64
        _, kind = validator.get_entity_type(sha)
        assert kind == "hash"

    def test_classifies_email(self, validator):
        ident, kind = validator.get_entity_type("foo@example.com")
        assert kind == "email"
        assert ident == "foo@example.com"

    def test_classifies_url_with_domain_netloc(self, validator):
        ident, kind = validator.get_entity_type("https://example.com/path")
        assert kind == "domain"
        assert ident == "example.com"

    def test_returns_none_for_unrecognised_input(self, validator):
        assert validator.get_entity_type("not a real entity") == (None, None)


class TestGIBConnector:
    """``GIBConnector.init_action_poller`` glues SOAR config to ciaops's poller.

    We mock ``create_drp_poller`` so no real DRPPoller is built, then assert
    the credentials and Verify-SSL flag are forwarded as expected and that
    a missing trailing slash on the API URL is normalised.
    """

    def _make_siemplify_with_config(self, config: dict) -> MagicMock:
        siemplify = MagicMock(name="SiemplifyAction")
        siemplify.LOGGER = MagicMock()
        siemplify.get_configuration.return_value = dict(config)
        return siemplify

    def test_init_action_poller_with_explicit_creds_tuple(self):
        siemplify = self._make_siemplify_with_config({})
        with patch("group_ib_drp.core.UtilsManager.create_drp_poller") as create_drp_poller_mock:
            create_drp_poller_mock.return_value = MagicMock(name="DRPPoller")
            poller = GIBConnector(siemplify).init_action_poller(
                creds=("user", "key", "https://drp.example.com/client_api/", True)
            )
        create_drp_poller_mock.assert_called_once_with(
            username="user",
            api_key="key",
            api_url="https://drp.example.com/client_api/",
            verify_ssl=True,
        )
        assert poller is create_drp_poller_mock.return_value

    def test_init_action_poller_appends_trailing_slash(self):
        siemplify = self._make_siemplify_with_config({})
        with patch("group_ib_drp.core.UtilsManager.create_drp_poller") as create_drp_poller_mock:
            GIBConnector(siemplify).init_action_poller(
                creds=("user", "key", "https://drp.example.com/client_api", False)
            )
        kwargs = create_drp_poller_mock.call_args.kwargs
        assert kwargs["api_url"] == "https://drp.example.com/client_api/"
        assert kwargs["verify_ssl"] is False

    def test_init_action_poller_with_3_value_creds_defaults_verify_ssl_true(self):
        """Backwards-compat: older connectors passed only 3 values."""
        siemplify = self._make_siemplify_with_config({})
        with patch("group_ib_drp.core.UtilsManager.create_drp_poller") as create_drp_poller_mock:
            GIBConnector(siemplify).init_action_poller(creds=("user", "key", "https://drp.example.com/api/"))
        kwargs = create_drp_poller_mock.call_args.kwargs
        assert kwargs["verify_ssl"] is True

    def test_init_action_poller_reads_from_siemplify_when_no_creds(self):
        cfg = {
            "API login": "u",
            "API key": "k",
            "API URL": "https://drp.example.com/api/",
            "Verify SSL": False,
        }
        siemplify = self._make_siemplify_with_config(cfg)
        with patch("group_ib_drp.core.UtilsManager.create_drp_poller") as create_drp_poller_mock:
            with patch("group_ib_drp.core.UtilsManager.extract_configuration_param") as extract_param_mock:
                extract_param_mock.side_effect = lambda *_a, **kw: cfg.get(kw["param_name"])
                GIBConnector(siemplify).init_action_poller()
        create_drp_poller_mock.assert_called_once()
        kwargs = create_drp_poller_mock.call_args.kwargs
        assert kwargs["username"] == "u"
        assert kwargs["api_key"] == "k"
        assert kwargs["api_url"] == "https://drp.example.com/api/"
        assert kwargs["verify_ssl"] is False


class TestCaseProcessor:
    """``CaseProcessor.add_to_case`` proxies to ``siemplify.add_entity_to_case``
    with a translated entity-type code; verify the translation and that the
    feed ID is forwarded as a property."""

    def test_add_to_case_translates_url_type_and_forwards_property(self):
        siemplify = MagicMock(name="SiemplifyAction")
        cp = CaseProcessor(siemplify)
        cp.add_to_case(
            case_id=42,
            alert_id="alert-123",
            entity="https://bad.example.com",
            entity_type="URL",
            property_value="feed-7",
        )
        siemplify.add_entity_to_case.assert_called_once()
        kwargs = siemplify.add_entity_to_case.call_args.kwargs
        assert kwargs["case_id"] == "42"
        assert kwargs["entity_identifier"] == "https://bad.example.com"
        assert kwargs["entity_type"] == "DestinationURL"
        assert kwargs["alert_identifier"] == "alert-123"
        assert kwargs["properties"] == {"property": "feed-7"}

    def test_add_to_case_assigns_random_alert_id_when_none(self):
        siemplify = MagicMock(name="SiemplifyAction")
        CaseProcessor(siemplify).add_to_case(
            case_id=1,
            alert_id=None,
            entity="https://bad.example.com",
            entity_type="URL",
        )
        kwargs = siemplify.add_entity_to_case.call_args.kwargs
        assert isinstance(kwargs["alert_identifier"], str)
        assert kwargs["alert_identifier"]
