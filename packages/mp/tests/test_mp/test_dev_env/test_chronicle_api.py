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
import typer
from typer.testing import CliRunner

from mp.dev_env import chronicle_api, utils
from mp.dev_env.sub_commands.login import login_app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def _fake_response(
    *,
    json_body: dict[str, Any] | None = None,
    content: bytes = b"",
    content_type: str = "application/json",
) -> mock.MagicMock:
    resp = mock.MagicMock()
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
    monkeypatch.setattr("google.auth.default", lambda scopes=None: (mock.MagicMock(), "proj"))
    monkeypatch.setattr(chronicle_api, "AuthorizedSession", lambda credentials: session)
    return chronicle_api.ChronicleClient(project="my-proj", location=location, instance="iid-123")


# --- ChronicleClient construction & auth ---


def test_init_builds_urls_and_session(monkeypatch: pytest.MonkeyPatch) -> None:
    session = mock.MagicMock()
    client = _make_client(monkeypatch, session)
    assert client.base_url == "https://us-chronicle.googleapis.com"
    assert client.instance_name == "projects/my-proj/locations/us/instances/iid-123"
    assert client.session is session
    assert client.scopes == [chronicle_api.CLOUD_PLATFORM_SCOPE]


def test_init_uses_credentials_file(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    def fake_load(path: str, scopes: list[str] | None = None) -> tuple[mock.MagicMock, str]:
        seen["path"] = path
        seen["scopes"] = scopes
        return (mock.MagicMock(), "proj")

    monkeypatch.setattr("google.auth.load_credentials_from_file", fake_load)
    monkeypatch.setattr(chronicle_api, "AuthorizedSession", lambda credentials: mock.MagicMock())
    chronicle_api.ChronicleClient(project="p", location="us", instance="i", credentials_file="/tmp/sa.json")  # noqa: S108
    assert seen["path"] == "/tmp/sa.json"  # noqa: S108
    assert seen["scopes"] == [chronicle_api.CLOUD_PLATFORM_SCOPE]


def test_init_credential_failure_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("google.auth.default", mock.Mock(side_effect=RuntimeError("no creds")))
    with pytest.raises(typer.Exit):
        chronicle_api.ChronicleClient(project="p", location="us", instance="i")


def test_login_hits_list_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    session = mock.MagicMock()
    session.get.return_value = _fake_response(json_body={"integrations": []})
    client = _make_client(monkeypatch, session)
    client.login()
    url = session.get.call_args.args[0]
    assert url == "https://us-chronicle.googleapis.com/v1/projects/my-proj/locations/us/instances/iid-123/integrations"


# --- listing & resolution (via public download path) ---


def test_list_integrations_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    session = mock.MagicMock()
    page1 = _fake_response(json_body={"integrations": [{"name": "a"}], "nextPageToken": "tok"})
    page2 = _fake_response(json_body={"integrations": [{"name": "b"}]})
    session.get.side_effect = [page1, page2]
    client = _make_client(monkeypatch, session)
    result = client.list_integrations()
    assert [i.name for i in result] == ["a", "b"]
    assert session.get.call_count == 2


def test_download_integration_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    session = mock.MagicMock()
    list_resp = _fake_response(
        json_body={
            "integrations": [
                {"name": "projects/p/locations/us/instances/i/integrations/alexa", "displayName": "Alexa"},
            ],
        },
    )
    export_resp = _fake_response(content=b"PKZIPDATA", content_type="application/zip")
    session.get.side_effect = [list_resp, export_resp]
    client = _make_client(monkeypatch, session)

    assert client.download_integration("Alexa") == b"PKZIPDATA"
    export_url = session.get.call_args_list[1].args[0]
    assert export_url.endswith("/integrations/alexa:export")


def test_download_integration_json_base64(monkeypatch: pytest.MonkeyPatch) -> None:
    session = mock.MagicMock()
    zip_bytes = b"PKZIPBYTES"
    list_resp = _fake_response(
        json_body={"integrations": [{"name": ".../integrations/alexa", "displayName": "Alexa"}]},
    )
    export_resp = _fake_response(json_body={"media": {"inline": base64.b64encode(zip_bytes).decode()}})
    session.get.side_effect = [list_resp, export_resp]
    client = _make_client(monkeypatch, session)

    assert client.download_integration("alexa") == zip_bytes


def test_download_integration_not_found_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    session = mock.MagicMock()
    session.get.return_value = _fake_response(json_body={"integrations": []})
    client = _make_client(monkeypatch, session)
    with pytest.raises(typer.Exit):
        client.download_integration("missing")


def test_download_integration_unknown_media_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    session = mock.MagicMock()
    list_resp = _fake_response(
        json_body={"integrations": [{"name": ".../integrations/x", "displayName": "X"}]},
    )
    export_resp = _fake_response(json_body={"media": {"unexpected": 1}})
    session.get.side_effect = [list_resp, export_resp]
    client = _make_client(monkeypatch, session)
    with pytest.raises(typer.Exit):
        client.download_integration("x")


def test_not_implemented_methods_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(monkeypatch, mock.MagicMock())
    with pytest.raises(NotImplementedError):
        client.get_integration_details(mock.MagicMock())
    with pytest.raises(NotImplementedError):
        client.upload_integration(mock.MagicMock(), "id")
    with pytest.raises(NotImplementedError):
        client.upload_playbook(mock.MagicMock())
    with pytest.raises(NotImplementedError):
        client.list_playbooks()
    with pytest.raises(NotImplementedError):
        client.download_playbook("id")


# --- get_backend_api dispatch & backward-compat ---


def test_get_backend_api_gcp(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_client = mock.MagicMock()
    seen: dict[str, Any] = {}

    def fake_chronicle(**kwargs: str | None) -> mock.MagicMock:
        seen.update(kwargs)
        return fake_client

    monkeypatch.setattr(utils.chronicle_api, "ChronicleClient", fake_chronicle)
    result = utils.get_backend_api({"auth_mode": "gcp", "project": "p", "location": "us", "instance": "i"})
    assert result is fake_client
    fake_client.login.assert_called_once()
    assert seen == {"project": "p", "location": "us", "instance": "i", "credentials_file": None}


def test_get_backend_api_legacy_api_key_infers_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ctor = mock.MagicMock(return_value=mock.MagicMock())
    monkeypatch.setattr(utils.api, "BackendAPI", fake_ctor)
    utils.get_backend_api({"api_root": "https://x", "api_key": "k"})
    fake_ctor.assert_called_once_with(api_root="https://x", api_key="k")


def test_get_backend_api_legacy_user_pass_infers_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_ctor = mock.MagicMock(return_value=mock.MagicMock())
    monkeypatch.setattr(utils.api, "BackendAPI", fake_ctor)
    utils.get_backend_api({"api_root": "https://x", "username": "u", "password": "p"})
    fake_ctor.assert_called_once_with(api_root="https://x", username="u", password="p")  # noqa: S106


def test_get_backend_api_unknown_mode_exits() -> None:
    with pytest.raises(typer.Exit):
        utils.get_backend_api({"auth_mode": "bogus"})


# --- login command (invoke single-command app without the command name) ---


def test_login_gcp_writes_config_and_skips_verify(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / ".mp_dev_env.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)
    fake_verify = mock.MagicMock()
    monkeypatch.setattr(utils, "get_backend_api", fake_verify)

    result = runner.invoke(
        login_app,
        ["--gcp", "--project", "p", "--location", "us", "--instance", "iid", "--no-verify"],
    )

    assert result.exit_code == 0
    assert json.loads(config_path.read_text()) == {
        "auth_mode": "gcp",
        "project": "p",
        "location": "us",
        "instance": "iid",
    }
    fake_verify.assert_not_called()


def test_login_gcp_verifies_by_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(utils, "CONFIG_PATH", tmp_path / ".mp_dev_env.json")
    fake_verify = mock.MagicMock()
    monkeypatch.setattr(utils, "get_backend_api", fake_verify)

    result = runner.invoke(login_app, ["--gcp", "--project", "p", "--location", "us", "--instance", "iid"])

    assert result.exit_code == 0
    fake_verify.assert_called_once()


def test_login_conflicting_modes_exits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(utils, "CONFIG_PATH", tmp_path / ".mp_dev_env.json")
    monkeypatch.setattr(utils, "get_backend_api", mock.MagicMock())

    result = runner.invoke(
        login_app,
        ["--gcp", "--api-key", "k", "--project", "p", "--location", "us", "--instance", "i"],
    )

    assert result.exit_code == 1


def test_login_api_key_writes_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path = tmp_path / ".mp_dev_env.json"
    monkeypatch.setattr(utils, "CONFIG_PATH", config_path)
    monkeypatch.setattr(utils, "get_backend_api", mock.MagicMock())

    result = runner.invoke(login_app, ["--api-root", "https://x", "--api-key", "k", "--no-verify"])

    assert result.exit_code == 0
    assert json.loads(config_path.read_text()) == {
        "api_root": "https://x",
        "auth_mode": "api_key",
        "api_key": "k",
    }
