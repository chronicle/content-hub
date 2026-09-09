# Copyright 2026 Google LLC
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

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest
import requests
import typer
from typer.testing import CliRunner

from mp.dev_env import chronicle_api, utils
from mp.dev_env.sub_commands.integration import utils as integration_utils
from mp.dev_env.sub_commands.login import login_app, parse_chronicle_api_root

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.custom_types import SingleJson

runner: CliRunner = CliRunner()


def _fake_response(
    *,
    json_body: SingleJson | None = None,
    content: bytes = b"",
    content_type: str = "application/json",
) -> mock.MagicMock:
    resp: mock.MagicMock = mock.MagicMock()
    resp.headers = {"Content-Type": content_type}
    resp.content = content
    resp.json.return_value = json_body
    resp.raise_for_status.return_value = None
    return resp


def _make_client(
    monkeypatch: pytest.MonkeyPatch,
    session: mock.MagicMock,
    *,
    location: str = "US",
) -> chronicle_api.ChronicleClient:
    monkeypatch.setattr(
        "google.auth.default",
        lambda scopes=None: (mock.MagicMock(), "proj"),
    )
    monkeypatch.setattr(
        chronicle_api,
        "AuthorizedSession",
        lambda credentials: session,
    )
    return chronicle_api.ChronicleClient(
        project="my-proj",
        location=location,
        instance="iid-123",
    )


def test_init_builds_urls_and_session(monkeypatch: pytest.MonkeyPatch) -> None:
    session: mock.MagicMock = mock.MagicMock()
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)
    assert client.base_url == "https://us-chronicle.googleapis.com"
    assert client.instance_name == (
        "projects/my-proj/locations/us/instances/iid-123"
    )
    assert client.session is session
    assert client.scopes == [chronicle_api.CLOUD_PLATFORM_SCOPE]


def test_init_uses_credentials_file(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: SingleJson = {}

    def fake_load(
        path: str,
        scopes: list[str] | None = None,
    ) -> tuple[mock.MagicMock, str]:
        seen["path"] = path
        seen["scopes"] = scopes
        return (mock.MagicMock(), "proj")

    monkeypatch.setattr("google.auth.load_credentials_from_file", fake_load)
    monkeypatch.setattr(
        chronicle_api,
        "AuthorizedSession",
        lambda credentials: mock.MagicMock(),
    )
    chronicle_api.ChronicleClient(
        project="p",
        location="us",
        instance="i",
        credentials_file="/tmp/sa.json",  # ruff:ignore[hardcoded-temp-file]
    )
    assert seen["path"] == "/tmp/sa.json"  # ruff:ignore[hardcoded-temp-file]
    assert seen["scopes"] == [chronicle_api.CLOUD_PLATFORM_SCOPE]


def test_init_credential_failure_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "google.auth.default",
        mock.Mock(side_effect=RuntimeError("no creds")),
    )
    with pytest.raises(typer.Exit):
        chronicle_api.ChronicleClient(project="p", location="us", instance="i")


def test_login_makes_cheap_integrations_call(monkeypatch: pytest.MonkeyPatch) -> None:
    session: mock.MagicMock = mock.MagicMock()
    session.get.return_value = _fake_response(json_body={"integrations": []})
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    client.login()

    expected_url: str = (
        "https://us-chronicle.googleapis.com/v1/projects/my-proj/"
        "locations/us/instances/iid-123/integrations"
    )
    session.get.assert_called_once_with(
        expected_url,
        params={"pageSize": 1},
    )


def test_list_integrations_single_page(monkeypatch: pytest.MonkeyPatch) -> None:
    session: mock.MagicMock = mock.MagicMock()
    session.get.return_value = _fake_response(
        json_body={
            "integrations": [
                {
                    "name": "projects/p/locations/l/instances/i/integrations/int1",
                    "displayName": "Int One",
                },
                {
                    "name": "projects/p/locations/l/instances/i/integrations/int2",
                    "displayName": "Int Two",
                },
            ]
        }
    )
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    res: list[chronicle_api.Integration] = client.list_integrations()
    assert len(res) == 2
    assert res[0].display_name == "Int One"
    assert res[1].display_name == "Int Two"


def test_list_integrations_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    session: mock.MagicMock = mock.MagicMock()
    session.get.side_effect = [
        _fake_response(
            json_body={
                "integrations": [
                    {"name": "projects/p/locations/l/instances/i/integrations/int1"}
                ],
                "nextPageToken": "tok-1",
            }
        ),
        _fake_response(
            json_body={
                "integrations": [
                    {"name": "projects/p/locations/l/instances/i/integrations/int2"}
                ],
            }
        ),
    ]
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    res: list[chronicle_api.Integration] = client.list_integrations()
    assert len(res) == 2
    assert session.get.call_count == 2
    assert session.get.call_args_list[1].kwargs["params"]["pageToken"] == "tok-1"


def test_download_integration_raw_zip(monkeypatch: pytest.MonkeyPatch) -> None:
    session: mock.MagicMock = mock.MagicMock()
    list_resp: mock.MagicMock = _fake_response(
        json_body={
            "integrations": [
                {
                    "name": (
                        "projects/my-proj/locations/us/instances/iid-123/"
                        "integrations/integ-uuid"
                    ),
                    "displayName": "VirusTotal",
                    "identifier": "VirusTotal",
                }
            ]
        }
    )
    download_resp: mock.MagicMock = _fake_response(
        content=b"PK\x03\x04zipdata",
        content_type="application/zip",
    )
    session.get.side_effect = [list_resp, download_resp]
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    zip_bytes: bytes = client.download_integration("VirusTotal")
    assert zip_bytes == b"PK\x03\x04zipdata"
    expected_url: str = (
        "https://us-chronicle.googleapis.com/v1/projects/my-proj/"
        "locations/us/instances/iid-123/integrations/integ-uuid:export"
    )
    session.get.assert_called_with(
        expected_url,
        params={"alt": "media"},
    )


def test_download_integration_json_media_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    session: mock.MagicMock = mock.MagicMock()
    raw: bytes = b"PK\x03\x04payload"
    b64: str = base64.b64encode(raw).decode()
    list_resp: mock.MagicMock = _fake_response(
        json_body={
            "integrations": [
                {
                    "name": (
                        "projects/my-proj/locations/us/instances/iid-123/"
                        "integrations/uuid-x"
                    ),
                    "identifier": "splunk",
                }
            ]
        }
    )
    download_resp: mock.MagicMock = _fake_response(
        json_body={"media": {"inline": b64, "contentType": "application/zip"}},
        content_type="application/json",
    )
    session.get.side_effect = [list_resp, download_resp]
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    assert client.download_integration("splunk") == raw


def test_download_integration_not_found_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    session: mock.MagicMock = mock.MagicMock()
    session.get.return_value = _fake_response(json_body={"integrations": []})
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    with pytest.raises(typer.Exit):
        client.download_integration("does-not-exist")


def test_get_integration_details_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session: mock.MagicMock = mock.MagicMock()
    session.post.return_value = _fake_response(
        json_body={"identifier": "VirusTotal", "version": "1.0"}
    )
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    dummy_zip: Path = tmp_path / "vt.zip"
    dummy_zip.write_bytes(b"PKdummy")

    details: SingleJson = client.get_integration_details(dummy_zip, is_staging=True)
    assert details["identifier"] == "VirusTotal"

    call_args: Any = session.post.call_args
    expected_url: str = (
        "https://us-chronicle.googleapis.com/upload/v1alpha/projects/my-proj/"
        "locations/us/instances/iid-123/integrations:extractIntegrationDetails"
    )
    assert call_args.args[0] == expected_url
    assert call_args.kwargs["params"] == {"staging": "true"}
    assert "file" in call_args.kwargs["files"]


def test_upload_integration_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session: mock.MagicMock = mock.MagicMock()
    session.post.return_value = _fake_response(
        json_body={"importedIdentifier": "vt", "isSuccessful": True}
    )
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    dummy_zip: Path = tmp_path / "vt.zip"
    dummy_zip.write_bytes(b"PKdummy")

    res: SingleJson = client.upload_integration(
        dummy_zip,
        "VirusTotal",
        is_staging=False,
    )
    assert res["isSuccessful"] is True

    call_args: Any = session.post.call_args
    expected_url: str = (
        "https://us-chronicle.googleapis.com/upload/v1alpha/projects/my-proj/"
        "locations/us/instances/iid-123/integrations:import"
    )
    assert call_args.args[0] == expected_url
    assert call_args.kwargs["params"] == {"staging": "false"}


def test_upload_playbook_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session: mock.MagicMock = mock.MagicMock()
    session.post.return_value = _fake_response(json_body={"imported": ["pb-1"]})
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    pb_zip: Path = tmp_path / "pb.zip"
    pb_zip.write_bytes(b"PKpb")

    res: SingleJson = client.upload_playbook(pb_zip)
    assert res == {"imported": ["pb-1"]}
    expected_url: str = (
        "https://us-chronicle.googleapis.com/upload/v1alpha/projects/my-proj/"
        "locations/us/instances/iid-123/legacyPlaybooks:legacyImportDefinitions"
    )
    assert session.post.call_args.args[0] == expected_url


def test_list_playbooks_extracts_name_and_id(monkeypatch: pytest.MonkeyPatch) -> None:
    session: mock.MagicMock = mock.MagicMock()
    session.post.return_value = _fake_response(
        json_body={
            "payload": [
                {"name": "PB One", "identifier": "id-1"},
                {"name": "PB Two", "identifier": "id-2"},
                {"name": None, "identifier": "skip-me"},
            ]
        }
    )
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    cards: list[SingleJson] = client.list_playbooks()
    assert cards == [
        {"name": "PB One", "identifier": "id-1"},
        {"name": "PB Two", "identifier": "id-2"},
    ]
    expected_url: str = (
        "https://us-chronicle.googleapis.com/v1alpha/projects/my-proj/"
        "locations/us/instances/iid-123/legacyPlaybooks:legacyGetWorkflowMenuCardsWithEnvFilter"
    )
    session.post.assert_called_once_with(
        expected_url,
        json={"legacyPayload": ["REGULAR", "NESTED"]},
    )


def test_download_playbook_encodes_blob(monkeypatch: pytest.MonkeyPatch) -> None:
    session: mock.MagicMock = mock.MagicMock()
    session.get.return_value = _fake_response(
        content=b"PKpbdata",
        content_type="application/zip",
    )
    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)

    res: SingleJson = client.download_playbook("pb-id-123")
    assert base64.b64decode(res["blob"]) == b"PKpbdata"
    expected_url: str = (
        "https://us-chronicle.googleapis.com/v1alpha/projects/my-proj/"
        "locations/us/instances/iid-123/legacyPlaybooks:legacyExportDefinitions"
    )
    session.get.assert_called_once_with(
        expected_url,
        params={"identifiers": "pb-id-123", "alt": "media"},
    )


def test_get_backend_api_dispatches_to_chronicle(monkeypatch: pytest.MonkeyPatch) -> None:
    session: mock.MagicMock = mock.MagicMock()
    session.get.return_value = _fake_response(json_body={"integrations": []})
    monkeypatch.setattr(
        "google.auth.default",
        lambda scopes=None: (mock.MagicMock(), "proj"),
    )
    monkeypatch.setattr(
        chronicle_api,
        "AuthorizedSession",
        lambda credentials: session,
    )

    cfg: SingleJson = {
        "auth_mode": "gcp",
        "project": "my-proj",
        "location": "us",
        "instance": "iid-456",
    }
    client: utils.interfaces.DevEnvClient = utils.get_backend_api(cfg)
    assert isinstance(client, chronicle_api.ChronicleClient)
    assert client.base_url == "https://us-chronicle.googleapis.com"


def test_get_backend_api_legacy_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg: SingleJson = {"api_root": "https://localhost", "api_key": "dummy"}
    mock_login: mock.MagicMock = mock.MagicMock()
    monkeypatch.setattr("mp.dev_env.api.BackendAPI.login", mock_login)

    client: utils.interfaces.DevEnvClient = utils.get_backend_api(cfg)
    assert isinstance(client, utils.api.BackendAPI)
    mock_login.assert_called_once()


def test_login_cli_gcp_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file: Path = tmp_path / ".mp_dev_env.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", cfg_file)

    session: mock.MagicMock = mock.MagicMock()
    session.get.return_value = _fake_response(json_body={"integrations": []})
    monkeypatch.setattr(
        "google.auth.default",
        lambda scopes=None: (mock.MagicMock(), "p"),
    )
    monkeypatch.setattr(
        chronicle_api,
        "AuthorizedSession",
        lambda creds: session,
    )

    result = runner.invoke(
        login_app,
        ["--gcp", "--project", "test-p", "--location", "us", "--instance", "iid-999"],
    )
    assert result.exit_code == 0
    saved: SingleJson = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert saved["auth_mode"] == "gcp"
    assert saved["project"] == "test-p"
    assert saved["location"] == "us"
    assert saved["instance"] == "iid-999"


def test_parse_chronicle_api_root() -> None:
    url: str = (
        "https://us-chronicle.googleapis.com/v1alpha/projects/84044654851/"
        "locations/us/instances/1ce5182d-fdba-4dca-a71f-1b748e42f580"
    )
    parsed_proj: str | None
    parsed_loc: str | None
    parsed_inst: str | None
    parsed_proj, parsed_loc, parsed_inst = parse_chronicle_api_root(url)
    assert parsed_proj == "84044654851"
    assert parsed_loc == "us"
    assert parsed_inst == "1ce5182d-fdba-4dca-a71f-1b748e42f580"

    unmatched_proj: str | None
    unmatched_loc: str | None
    unmatched_inst: str | None
    unmatched_proj, unmatched_loc, unmatched_inst = parse_chronicle_api_root(
        "https://legacy.siemplify.com"
    )
    assert unmatched_proj is None
    assert unmatched_loc is None
    assert unmatched_inst is None


def test_login_cli_api_root_chronicle_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cfg_file: Path = tmp_path / ".mp_dev_env.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", cfg_file)

    session: mock.MagicMock = mock.MagicMock()
    session.get.return_value = _fake_response(json_body={"integrations": []})
    monkeypatch.setattr(
        "google.auth.default",
        lambda scopes=None: (mock.MagicMock(), "p"),
    )
    monkeypatch.setattr(
        chronicle_api,
        "AuthorizedSession",
        lambda creds: session,
    )

    url: str = (
        "https://us-chronicle.googleapis.com/v1alpha/projects/84044654851/"
        "locations/us/instances/1ce5182d-fdba-4dca-a71f-1b748e42f580"
    )
    result = runner.invoke(login_app, ["--api-root", url])
    assert result.exit_code == 0
    saved: SingleJson = json.loads(cfg_file.read_text(encoding="utf-8"))
    assert saved["auth_mode"] == "gcp"
    assert saved["project"] == "84044654851"
    assert saved["location"] == "us"
    assert saved["instance"] == "1ce5182d-fdba-4dca-a71f-1b748e42f580"


def test_upload_integration_recovers_on_503_if_installed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session: mock.MagicMock = mock.MagicMock()
    err_resp: mock.MagicMock = mock.MagicMock()
    err_resp.status_code = 503
    http_err = requests.exceptions.HTTPError(response=err_resp)
    session.post.side_effect = http_err

    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)
    monkeypatch.setattr(client, "_wait_for_integration_installed", lambda _: True)

    zip_file: Path = tmp_path / "pkg.zip"
    zip_file.write_bytes(b"PK")
    res: SingleJson = client.upload_integration(zip_file, "Wiz")
    assert res == {"integration": "Wiz", "status": "installed"}


def test_upload_integration_raises_on_503_if_not_installed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    session: mock.MagicMock = mock.MagicMock()
    err_resp: mock.MagicMock = mock.MagicMock()
    err_resp.status_code = 503
    http_err = requests.exceptions.HTTPError(response=err_resp)
    session.post.side_effect = http_err

    client: chronicle_api.ChronicleClient = _make_client(monkeypatch, session)
    monkeypatch.setattr(client, "_wait_for_integration_installed", lambda _: False)

    zip_file: Path = tmp_path / "pkg.zip"
    zip_file.write_bytes(b"PK")
    with pytest.raises(requests.exceptions.HTTPError):
        client.upload_integration(zip_file, "Wiz")


def test_normalize_connector_def_null_description() -> None:
    raw_def = {
        "DisplayName": "My Connector",
        "Parameters": [
            {
                "DisplayName": "Param 1",
                "Description": None,
                "Type": "String",
            }
        ],
    }
    integration_utils._normalize_connector_def(raw_def, "MyIntegration")  # ruff:ignore[private-member-access]
    assert raw_def["Parameters"][0]["Description"] == ""
    assert raw_def["Parameters"][0]["Name"] == "Param 1"
