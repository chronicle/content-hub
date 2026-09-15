"""Tests for the invariant that one connector execution writes one package.

The platform parses a connector's *entire* stdout as a single JSON document, and
``return_package`` writes that document with no trailing separator. A second
``return_package`` call therefore appends a second document and corrupts the
whole payload, which SecOps reports as::

    Dynamic script connector ... returned unexpected output. No cases created;
    Exception: System.ArgumentNullException: Value cannot be null. (Parameter 'value')

or as "The connector logic executed. The result of running is empty or null."
Either way every alert in the cycle is dropped, even though the connector logged
that it built them.

This is reachable in production because progress commits (``save_timestamp`` /
``set_connector_context_property``) are SOAR API calls that deliberately run
*after* delivery, so any transient API failure used to trigger the second write.
"""

from __future__ import annotations

import pytest

from spy_cloud_enterprise.connectors import SpyCloudConnector as connector_module


class _Logger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def _record(self, message: str) -> None:
        self.messages.append(str(message))

    info = warn = warning = error = _record


class _RecordingSiemplify:
    """Captures every return_package call instead of writing to stdout."""

    def __init__(self) -> None:
        self.LOGGER = _Logger()
        self.script_name = ""
        self.packages: list[list] = []

    def return_package(self, cases: list, *_: object, **__: object) -> None:
        self.packages.append(list(cases))


@pytest.fixture
def siemplify(monkeypatch: pytest.MonkeyPatch) -> _RecordingSiemplify:
    instance = _RecordingSiemplify()
    monkeypatch.setattr(
        connector_module,
        "SiemplifyConnectorExecution",
        lambda *_, **__: instance,
    )
    return instance


class TestSingleReturnPackage:
    def test_commit_failure_keeps_the_delivered_package(
        self,
        siemplify: _RecordingSiemplify,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A post-delivery commit failure must not emit a second, empty package."""
        monkeypatch.setattr(
            connector_module,
            "_collect_alerts",
            lambda *_: (object(), ["alert-1", "alert-2"], "2026-08-19T18:00:00Z"),
        )

        def _boom(*_: object) -> None:
            raise RuntimeError("SOAR API unavailable")

        monkeypatch.setattr(connector_module, "_commit_progress", _boom)

        connector_module.main(False)

        assert siemplify.packages == [["alert-1", "alert-2"]]

    def test_collection_failure_emits_one_empty_package_and_commits_nothing(
        self,
        siemplify: _RecordingSiemplify,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def _boom(*_: object) -> None:
            raise RuntimeError("SpyCloud API unreachable")

        monkeypatch.setattr(connector_module, "_collect_alerts", _boom)

        commits: list[object] = []
        monkeypatch.setattr(
            connector_module,
            "_commit_progress",
            lambda *args: commits.append(args),
        )

        connector_module.main(False)

        assert siemplify.packages == [[]]
        # Undelivered records must be re-fetched next cycle, not checkpointed past.
        assert commits == []

    def test_successful_cycle_delivers_once_then_commits(
        self,
        siemplify: _RecordingSiemplify,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        manager = object()
        monkeypatch.setattr(
            connector_module,
            "_collect_alerts",
            lambda *_: (manager, ["alert-1"], "2026-08-19T18:00:00Z"),
        )

        commits: list[tuple] = []
        monkeypatch.setattr(
            connector_module,
            "_commit_progress",
            lambda *args: commits.append(args),
        )

        connector_module.main(False)

        assert siemplify.packages == [["alert-1"]]
        assert len(commits) == 1
        assert commits[0][1] is manager
        assert commits[0][2] == "2026-08-19T18:00:00Z"

    def test_test_run_delivers_once_and_never_commits(
        self,
        siemplify: _RecordingSiemplify,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            connector_module,
            "_collect_alerts",
            lambda *_: (object(), [], None),
        )

        commits: list[object] = []
        monkeypatch.setattr(
            connector_module,
            "_commit_progress",
            lambda *args: commits.append(args),
        )

        connector_module.main(True)

        assert siemplify.packages == [[]]
        assert commits == []
