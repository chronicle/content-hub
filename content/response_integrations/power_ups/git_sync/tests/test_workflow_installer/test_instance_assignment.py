# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for WorkflowInstaller integration-instance assignment logic.

These tests validate that GitSync only assigns **configured** integration
instances to playbook steps.  Tests marked "BUG TEST" assert the correct
behavior and are expected to FAIL against the pre-fix code (where
``_find_integration_instances_for_step`` returns unconfigured instances as
a fallback).  After the fix they must all pass.

The tests exercise three internal methods:
- ``_find_integration_instances_for_step``
- ``_is_valid_existing_instance``
- ``_assign_integration_instance_to_step``
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, create_autospec

from ...core.GitSyncManager import WorkflowInstaller
from ...core.SiemplifyApiClient import SiemplifyApiClient
from ...core.constants import ALL_ENVIRONMENTS_IDENTIFIER

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INTEGRATION = "VirusTotal"
_ENV_PROD = "Prod"
_ENV_STAGING = "Staging"


def _make_instance(
    integration: str,
    identifier: str,
    name: str,
    *,
    configured: bool,
) -> dict[str, Any]:
    """Build a minimal integration-instance dict matching the API shape.

    Args:
        integration: The integrationIdentifier value.
        identifier: UUID string used as the instance key.
        name: Human-readable instanceName.
        configured: Whether the instance has API keys set up.

    Returns:
        A mapping mirroring SiemplifyApiClient.get_integrations_instances output.
    """
    return {
        "integrationIdentifier": integration,
        "identifier": identifier,
        "instanceName": name,
        "isConfigured": configured,
    }


def _make_step(
    integration: str,
    *,
    instance_value: str | None = None,
    instance_display: str | None = None,
    fallback_value: str | None = None,
    fallback_display: str | None = None,
) -> dict[str, Any]:
    """Build a minimal playbook action-step dict.

    Args:
        integration: The integration name for this step.
        instance_value: Current value of the IntegrationInstance parameter.
        instance_display: InstanceDisplayName for the IntegrationInstance param.
        fallback_value: Current value of FallbackIntegrationInstance.
        fallback_display: FallbackInstanceDisplayName for the fallback param.

    Returns:
        A step dict shaped for _assign_integration_instance_to_step.
    """
    return {
        "integration": integration,
        "type": 0,
        "actionProvider": "Scripts",
        "instanceName": "Scan IP",
        "parameters": [
            {
                "name": "IntegrationInstance",
                "value": instance_value,
                "InstanceDisplayName": instance_display,
            },
            {
                "name": "FallbackIntegrationInstance",
                "value": fallback_value,
                "FallbackInstanceDisplayName": fallback_display,
            },
        ],
    }


def _make_installer() -> WorkflowInstaller:
    """Create a WorkflowInstaller wired with MagicMock dependencies.

    Returns:
        A WorkflowInstaller with mocked api, logger, chronicle_soar, and an
        empty dict as mod_time_cache.  api.get_integration_instance_id_by_name
        returns None by default.
    """
    chronicle_soar = MagicMock()
    api = create_autospec(SiemplifyApiClient, instance=True)
    api.get_integration_instance_id_by_name.return_value = None
    logger = MagicMock()
    mod_time_cache: dict = {}
    return WorkflowInstaller(chronicle_soar, api, logger, mod_time_cache)


def _get_param_value(step: dict[str, Any], name: str) -> str | None:
    """Extract the 'value' field from a named step parameter.

    Args:
        step: The step dict to inspect.
        name: The parameter name to find.

    Returns:
        The value, or None if not found.
    """
    for p in step.get("parameters", []):
        if p.get("name") == name:
            return p.get("value")
    return None


# ---------------------------------------------------------------------------
# TestFindIntegrationInstancesForStep
# ---------------------------------------------------------------------------


class TestFindIntegrationInstancesForStep:
    """Unit tests for WorkflowInstaller._find_integration_instances_for_step."""

    def test_only_configured_returned_sorted(self) -> None:
        """Only configured instances exist: all returned, sorted by name."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(_INTEGRATION, "uuid-z", "Zebra Instance", configured=True),
            _make_instance(_INTEGRATION, "uuid-a", "Alpha Instance", configured=True),
        ]

        result = installer._find_integration_instances_for_step(
            _INTEGRATION,
            _ENV_PROD,
        )

        assert [x["identifier"] for x in result] == ["uuid-a", "uuid-z"]

    def test_only_unconfigured_returns_empty_list(self) -> None:
        """Only unconfigured instances exist: MUST return [].

        BUG TEST — PR #660 returns the unconfigured instances here, causing
        callers to write a dead UUID into playbook steps.  The SOAR engine
        then crashes on automated triggers.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-unconf",
                "Bad Instance",
                configured=False,
            ),
        ]

        result = installer._find_integration_instances_for_step(
            _INTEGRATION,
            _ENV_PROD,
        )

        assert result == []

    def test_mix_returns_only_configured(self) -> None:
        """Mixed list: only configured instances returned."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "Good Instance",
                configured=True,
            ),
            _make_instance(
                _INTEGRATION,
                "uuid-unconf",
                "Bad Instance",
                configured=False,
            ),
        ]

        result = installer._find_integration_instances_for_step(
            _INTEGRATION,
            _ENV_PROD,
        )

        assert len(result) == 1
        assert result[0]["identifier"] == "uuid-conf"

    def test_no_instances_returns_empty_list(self) -> None:
        """Empty environment cache: returns []."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = []

        result = installer._find_integration_instances_for_step(
            _INTEGRATION,
            _ENV_PROD,
        )

        assert result == []

    def test_filters_to_correct_integration(self) -> None:
        """Multiple integrations in env: only the requested one returned."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(_INTEGRATION, "uuid-vt", "VT Instance", configured=True),
            _make_instance(
                "OtherIntegration",
                "uuid-other",
                "Other Instance",
                configured=True,
            ),
        ]

        result = installer._find_integration_instances_for_step(
            _INTEGRATION,
            _ENV_PROD,
        )

        assert len(result) == 1
        assert result[0]["identifier"] == "uuid-vt"

    def test_cache_prevents_second_api_call(self) -> None:
        """Second call for the same env uses cache, not the API."""
        installer = _make_installer()
        installer.api.get_integrations_instances.return_value = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "Good Instance",
                configured=True,
            ),
        ]

        installer._find_integration_instances_for_step(_INTEGRATION, _ENV_PROD)
        installer._find_integration_instances_for_step(_INTEGRATION, _ENV_PROD)

        installer.api.get_integrations_instances.assert_called_once_with(_ENV_PROD)


# ---------------------------------------------------------------------------
# TestIsValidExistingInstance
# ---------------------------------------------------------------------------


class TestIsValidExistingInstance:
    """Unit tests for WorkflowInstaller._is_valid_existing_instance."""

    def test_configured_instance_returns_true(self) -> None:
        """Instance exists and is configured: True."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "Good Instance",
                configured=True,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []

        result = installer._is_valid_existing_instance(
            _INTEGRATION,
            "uuid-conf",
            [_ENV_PROD],
        )

        assert result is True

    def test_unconfigured_instance_returns_false(self) -> None:
        """Instance exists but is unconfigured: MUST return False.

        BUG TEST — _find currently leaks unconfigured instances, so this
        returns True and the poisoned UUID is preserved on subsequent pulls.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-unconf",
                "Bad Instance",
                configured=False,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []

        result = installer._is_valid_existing_instance(
            _INTEGRATION,
            "uuid-unconf",
            [_ENV_PROD],
        )

        assert result is False

    def test_missing_instance_returns_false(self) -> None:
        """UUID not present in any environment: False."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "Good Instance",
                configured=True,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []

        result = installer._is_valid_existing_instance(
            _INTEGRATION,
            "uuid-missing",
            [_ENV_PROD],
        )

        assert result is False

    def test_shared_env_instance_valid_for_specific_env(self) -> None:
        """Configured instance in shared (*) env is valid for a specific env query."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = []
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-shared",
                "Shared Instance",
                configured=True,
            ),
        ]

        result = installer._is_valid_existing_instance(
            _INTEGRATION,
            "uuid-shared",
            [_ENV_PROD],
        )

        assert result is True

    def test_unconfigured_in_all_envs_returns_false(self) -> None:
        """Unconfigured instance in all environments: MUST return False.

        BUG TEST — even though the UUID appears in every env cache, an
        unconfigured instance must never be considered valid.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-unconf",
                "Bad Instance",
                configured=False,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-unconf",
                "Bad Instance",
                configured=False,
            ),
        ]

        result = installer._is_valid_existing_instance(
            _INTEGRATION,
            "uuid-unconf",
            [_ENV_PROD],
        )

        assert result is False


# ---------------------------------------------------------------------------
# TestAssignIntegrationInstanceToStep — single-environment playbooks
# ---------------------------------------------------------------------------


class TestAssignInstanceSingleEnv:
    """Tests for _assign_integration_instance_to_step with single-env playbooks."""

    def test_configured_instance_assigned(self) -> None:
        """Configured instance available: its UUID is set on IntegrationInstance."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "Good Instance",
                configured=True,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(step, [_ENV_PROD])

        assert _get_param_value(step, "IntegrationInstance") == "uuid-conf"

    def test_only_unconfigured_leaves_none(self) -> None:
        """Only unconfigured instances: IntegrationInstance must stay None.

        BUG TEST — current code writes the unconfigured UUID here, causing
        the SOAR engine to crash: "The chosen fallback integration instance
        is missing / invalid."
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-unconf",
                "Bad Instance",
                configured=False,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(step, [_ENV_PROD])

        assert _get_param_value(step, "IntegrationInstance") is None

    def test_no_instance_in_specific_env_uses_shared(self) -> None:
        """No instances in specific env, configured in shared env: shared used."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = []
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-shared",
                "Shared Instance",
                configured=True,
            ),
        ]
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(step, [_ENV_PROD])

        assert _get_param_value(step, "IntegrationInstance") == "uuid-shared"

    def test_no_instances_anywhere_leaves_none(self) -> None:
        """No instances in specific or shared env: IntegrationInstance stays None."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = []
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(step, [_ENV_PROD])

        assert _get_param_value(step, "IntegrationInstance") is None


# ---------------------------------------------------------------------------
# TestAssignIntegrationInstanceToStep — multi-env / All-Environments playbooks
# ---------------------------------------------------------------------------


class TestAssignInstanceMultiEnv:
    """Tests for _assign_integration_instance_to_step with multi/all-env playbooks."""

    def test_all_envs_configured_shared_instance(self) -> None:
        """All-envs playbook with configured shared instance.

        IntegrationInstance = AutomaticEnvironment, Fallback = shared UUID.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-shared",
                "Shared Instance",
                configured=True,
            ),
        ]
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [ALL_ENVIRONMENTS_IDENTIFIER],
        )

        assert _get_param_value(step, "IntegrationInstance") == "AutomaticEnvironment"
        assert _get_param_value(step, "FallbackIntegrationInstance") == "uuid-shared"

    def test_all_envs_only_unconfigured_sets_fallback_none(self) -> None:
        """All-envs playbook, only unconfigured shared: fallback stays None.

        BUG TEST — current code writes the unconfigured UUID to
        FallbackIntegrationInstance, which crashes automated triggers.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-unconf",
                "Bad Shared",
                configured=False,
            ),
        ]
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [ALL_ENVIRONMENTS_IDENTIFIER],
        )

        assert _get_param_value(step, "IntegrationInstance") == "AutomaticEnvironment"
        assert _get_param_value(step, "FallbackIntegrationInstance") is None

    def test_multi_env_no_shared_uses_individual_env(self) -> None:
        """Multi-env: no shared instances, individual env has configured one."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-env",
                "Env Instance",
                configured=True,
            ),
        ]
        installer._cache[f"integration_instances_{_ENV_STAGING}"] = []
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [_ENV_PROD, _ENV_STAGING],
        )

        assert _get_param_value(step, "IntegrationInstance") == "AutomaticEnvironment"
        assert _get_param_value(step, "FallbackIntegrationInstance") == "uuid-env"

    def test_all_envs_no_instances_fallback_none(self) -> None:
        """All-envs with no instances anywhere: fallback stays None."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [ALL_ENVIRONMENTS_IDENTIFIER],
        )

        assert _get_param_value(step, "IntegrationInstance") == "AutomaticEnvironment"
        assert _get_param_value(step, "FallbackIntegrationInstance") is None


# ---------------------------------------------------------------------------
# TestAssignIntegrationInstanceToStep — display name resolution
# ---------------------------------------------------------------------------


class TestAssignInstanceDisplayNameResolution:
    """Tests for _assign_integration_instance_to_step when display name lookup
    returns a real instance ID via get_integration_instance_id_by_name.

    This exercises the code path where the SOAR API resolves an instance by
    its display name.  The resolved ID takes priority over the first instance
    from _find_integration_instances_for_step.
    """

    def test_single_env_display_name_preferred_over_first_instance(self) -> None:
        """Display name resolves to a configured instance: that ID is used.

        When get_integration_instance_id_by_name returns a UUID, it takes
        priority over integration_instances[0].  This tests that the display
        name path works correctly for single-env playbooks.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-first",
                "Alpha Instance",
                configured=True,
            ),
            _make_instance(
                _INTEGRATION,
                "uuid-named",
                "Named Instance",
                configured=True,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        step = _make_step(
            _INTEGRATION,
            instance_display="Named Instance",
        )
        installer.api.get_integration_instance_id_by_name.return_value = "uuid-named"

        installer._assign_integration_instance_to_step(step, [_ENV_PROD])

        assert _get_param_value(step, "IntegrationInstance") == "uuid-named"

    def test_single_env_display_name_none_falls_back_to_first(self) -> None:
        """Display name lookup returns None: first configured instance used."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-first",
                "Alpha Instance",
                configured=True,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        step = _make_step(_INTEGRATION)
        installer.api.get_integration_instance_id_by_name.return_value = None

        installer._assign_integration_instance_to_step(step, [_ENV_PROD])

        assert _get_param_value(step, "IntegrationInstance") == "uuid-first"

    def test_multi_env_fallback_display_name_preferred(self) -> None:
        """Multi-env: fallback display name resolves to a configured ID.

        The fallback_instance_id from get_integration_instance_id_by_name
        takes priority over integration_instances[0] on line 976.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-first",
                "Alpha Shared",
                configured=True,
            ),
            _make_instance(
                _INTEGRATION,
                "uuid-named",
                "Named Shared",
                configured=True,
            ),
        ]
        step = _make_step(
            _INTEGRATION,
            fallback_display="Named Shared",
        )
        installer.api.get_integration_instance_id_by_name.return_value = "uuid-named"

        installer._assign_integration_instance_to_step(
            step,
            [ALL_ENVIRONMENTS_IDENTIFIER],
        )

        assert _get_param_value(step, "IntegrationInstance") == "AutomaticEnvironment"
        assert _get_param_value(step, "FallbackIntegrationInstance") == "uuid-named"


# ---------------------------------------------------------------------------
# TestAssignIntegrationInstanceToStep — existing_step edge cases
# ---------------------------------------------------------------------------


class TestAssignInstanceExistingStepEdgeCases:
    """Tests for existing_step edge cases derived from the b/507812579 chat.

    These cover scenarios reported by Anna Johnson during the investigation:
    - Existing step with None/empty instance value
    - Re-pull after manually nulling the fallback (Anna's workaround)
    """

    def test_existing_step_none_instance_falls_through(self) -> None:
        """Existing step has instance_value=None: skips validation, runs discovery.

        When instance_to_validate is falsy (None or empty string), the code
        skips the _is_valid_existing_instance check entirely and falls through
        to the instance-discovery logic.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "Good Instance",
                configured=True,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        existing_step = _make_step(_INTEGRATION, instance_value=None)
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [_ENV_PROD],
            existing_step,
        )

        assert _get_param_value(step, "IntegrationInstance") == "uuid-conf"

    def test_existing_step_empty_string_instance_falls_through(self) -> None:
        """Existing step has instance_value='': skips validation, runs discovery.

        Same as None — an empty string is falsy, so the validation guard
        (``if instance_to_validate and ...``) skips and falls through.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "Good Instance",
                configured=True,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        existing_step = _make_step(_INTEGRATION, instance_value="")
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [_ENV_PROD],
            existing_step,
        )

        assert _get_param_value(step, "IntegrationInstance") == "uuid-conf"

    def test_repull_after_manual_null_fix_picks_configured(self) -> None:
        """Anna's workaround: manually null the fallback, then re-pull.

        The existing step has AutomaticEnvironment + null fallback (after
        Anna manually set it to null).  On re-pull, since
        instance_to_validate is None (fallback is None when instance is
        AutomaticEnvironment), the code falls through to discovery and
        correctly picks the only configured instance.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "IngestionPlaybookTools_1",
                configured=True,
            ),
        ]
        existing_step = _make_step(
            _INTEGRATION,
            instance_value="AutomaticEnvironment",
            fallback_value=None,
        )
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [ALL_ENVIRONMENTS_IDENTIFIER],
            existing_step,
        )

        assert _get_param_value(step, "IntegrationInstance") == "AutomaticEnvironment"
        assert _get_param_value(step, "FallbackIntegrationInstance") == "uuid-conf"

    def test_repull_after_null_fix_only_unconfigured_stays_none(self) -> None:
        """Re-pull after null fix but only unconfigured instances exist.

        Same scenario as above, but no configured instance is available.
        The fallback must remain None — not be filled with an unconfigured ID.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-unconf",
                "IngestionPlaybookTools_1",
                configured=False,
            ),
        ]
        existing_step = _make_step(
            _INTEGRATION,
            instance_value="AutomaticEnvironment",
            fallback_value=None,
        )
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [ALL_ENVIRONMENTS_IDENTIFIER],
            existing_step,
        )

        assert _get_param_value(step, "IntegrationInstance") == "AutomaticEnvironment"
        assert _get_param_value(step, "FallbackIntegrationInstance") is None


# ---------------------------------------------------------------------------
# TestAssignIntegrationInstanceToStep — existing_step reuse
# ---------------------------------------------------------------------------


class TestAssignInstanceExistingStep:
    """Tests for _assign_integration_instance_to_step with existing_step arg."""

    def test_valid_configured_instance_reused(self) -> None:
        """Existing step has a valid configured instance: reused as-is."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "Good Instance",
                configured=True,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        existing_step = _make_step(_INTEGRATION, instance_value="uuid-conf")
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [_ENV_PROD],
            existing_step,
        )

        assert _get_param_value(step, "IntegrationInstance") == "uuid-conf"

    def test_unconfigured_instance_falls_through(self) -> None:
        """Existing step has unconfigured UUID: must fall through to discovery.

        BUG TEST — _is_valid_existing_instance uses _find which leaks
        unconfigured instances, so the poisoned UUID is considered "valid"
        and preserved.  After fix, it fails validation and discovery finds
        the real configured instance.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "Good Instance",
                configured=True,
            ),
            _make_instance(
                _INTEGRATION,
                "uuid-unconf",
                "Bad Instance",
                configured=False,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        existing_step = _make_step(_INTEGRATION, instance_value="uuid-unconf")
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [_ENV_PROD],
            existing_step,
        )

        assert _get_param_value(step, "IntegrationInstance") == "uuid-conf"

    def test_stale_instance_falls_through(self) -> None:
        """Existing step has UUID not present in any env: falls through."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{_ENV_PROD}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-conf",
                "Good Instance",
                configured=True,
            ),
        ]
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = []
        existing_step = _make_step(
            _INTEGRATION,
            instance_value="uuid-stale-deleted",
        )
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [_ENV_PROD],
            existing_step,
        )

        assert _get_param_value(step, "IntegrationInstance") == "uuid-conf"

    def test_automatic_env_valid_fallback_reused(self) -> None:
        """Existing multi-env step with configured fallback: both values copied."""
        installer = _make_installer()
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-shared",
                "Shared Instance",
                configured=True,
            ),
        ]
        existing_step = _make_step(
            _INTEGRATION,
            instance_value="AutomaticEnvironment",
            fallback_value="uuid-shared",
        )
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [ALL_ENVIRONMENTS_IDENTIFIER],
            existing_step,
        )

        assert _get_param_value(step, "IntegrationInstance") == "AutomaticEnvironment"
        assert _get_param_value(step, "FallbackIntegrationInstance") == "uuid-shared"

    def test_automatic_env_unconfigured_fallback_falls_through(self) -> None:
        """Existing multi-env step has unconfigured fallback: must fall through.

        BUG TEST — the poisoned fallback UUID passes _is_valid because _find
        leaks unconfigured instances.  After fix, validation rejects it and
        discovery runs, finding no configured shared instance => fallback=None.
        """
        installer = _make_installer()
        installer._cache[f"integration_instances_{ALL_ENVIRONMENTS_IDENTIFIER}"] = [
            _make_instance(
                _INTEGRATION,
                "uuid-unconf",
                "Bad Shared",
                configured=False,
            ),
        ]
        existing_step = _make_step(
            _INTEGRATION,
            instance_value="AutomaticEnvironment",
            fallback_value="uuid-unconf",
        )
        step = _make_step(_INTEGRATION)

        installer._assign_integration_instance_to_step(
            step,
            [ALL_ENVIRONMENTS_IDENTIFIER],
            existing_step,
        )

        assert _get_param_value(step, "IntegrationInstance") == "AutomaticEnvironment"
        assert _get_param_value(step, "FallbackIntegrationInstance") is None
