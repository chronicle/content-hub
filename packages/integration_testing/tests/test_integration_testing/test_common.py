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

from __future__ import annotations

import dataclasses
import functools
import json
import os
import pathlib
import sys
import urllib.parse
from typing import TYPE_CHECKING

import pytest
import TIPCommon.utils
from soar_sdk.SiemplifyDataModel import DomainEntityInfo
from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.base.job import JobParameter
from TIPCommon.data_models import ConnectorParameter, ConnectorParamTypes, JobParamType

from integration_testing import common
from integration_testing.request import HttpMethod, MockRequest

from .test_set_meta import CONNECTOR_DEF, JOB_DEF

if TYPE_CHECKING:
    from TIPCommon.types import Entity


PYTHON_PROCESS_TIMEOUT_DEFAULT: int = 180


def test_create_entity() -> None:
    entity_identifier: str = "8.8.8.8"
    entity: Entity = common.create_entity(entity_identifier, EntityTypesEnum.ADDRESS)

    assert isinstance(entity, DomainEntityInfo)
    assert entity.identifier == entity_identifier
    assert entity.entity_type == EntityTypesEnum.ADDRESS.value


class TestPrepareConnectorParam:
    def test_return_list_of_connector_parameters(self) -> None:
        expected_parameter: dict[str, str] = {"n": "v"}

        results: list[ConnectorParameter] = common.prepare_connector_params(
            connector_def_file=None,
            params=expected_parameter,
        )

        assert isinstance(results, list)
        assert len(results) == len(expected_parameter) + 1
        for param in results:
            assert isinstance(param, ConnectorParameter)

    def test_without_connector_def_file_has_default_values(self) -> None:
        expected_parameter: dict[str, str] = {"n": "v"}

        results: list[ConnectorParameter] = common.prepare_connector_params(
            connector_def_file=None,
            params=expected_parameter,
        )

        assert results[0].name == "n" or results[1].name == "n"
        for parameter in results:
            if parameter.name == "n":
                assert not parameter.is_mandatory
                assert parameter.type is ConnectorParamTypes.STRING
                assert parameter.value in expected_parameter["n"]

    def test_python_script_timeout_is_added_if_missing(self) -> None:
        expected_parameter: dict[str, str] = {"n": "v"}

        results: list[ConnectorParameter] = common.prepare_connector_params(
            connector_def_file=None,
            params=expected_parameter,
        )
        assert (
            results[0].name == "PythonProcessTimeout" or results[1].name == "PythonProcessTimeout"
        )
        for parameter in results:
            if parameter.name == "PythonProcessTimeout":
                assert parameter.value == common.DEFAULT_PROCESS_TIMEOUT
                assert parameter.type is ConnectorParamTypes.INTEGER

    def test_with_pathlib_connector_def_file_path(self) -> None:
        expected_parameter: dict[str, str] = {"Username": "v1", "Password": "v2"}

        results: list[ConnectorParameter] = common.prepare_connector_params(
            connector_def_file=CONNECTOR_DEF,
            params=expected_parameter,
        )

        assert len(results) == len(expected_parameter) + 1
        for param in results:
            if param.name == "Username":
                assert param.is_mandatory
                assert param.value == expected_parameter["Username"]
                assert param.type is ConnectorParamTypes.STRING

            elif param.name == "PythonProcessTimeout":
                assert param.value == common.DEFAULT_PROCESS_TIMEOUT
                assert param.type is ConnectorParamTypes.INTEGER

            else:
                assert not param.is_mandatory
                assert param.value == expected_parameter["Password"]
                assert param.type is ConnectorParamTypes.PASSWORD

    def test_with_str_connector_def_file_path(self) -> None:
        expected_parameter: dict[str, str] = {"Username": "v1", "Password": "v2"}

        results: list[ConnectorParameter] = common.prepare_connector_params(
            connector_def_file=str(CONNECTOR_DEF),
            params=expected_parameter,
        )

        assert len(results) == len(expected_parameter) + 1
        for param in results:
            if param.name == "Username":
                assert param.is_mandatory
                assert param.value == expected_parameter["Username"]
                assert param.type is ConnectorParamTypes.STRING

            elif param.name == "PythonProcessTimeout":
                assert param.value == common.DEFAULT_PROCESS_TIMEOUT
                assert param.type is ConnectorParamTypes.INTEGER

            else:
                assert not param.is_mandatory
                assert param.value == expected_parameter["Password"]
                assert param.type is ConnectorParamTypes.PASSWORD


class TestPrepareJobParam:
    def test_return_list_of_job_parameters(self) -> None:
        expected_parameter: dict[str, str] = {"n": "v"}

        results: list[JobParameter] = common.prepare_job_params(
            job_def_file=None,
            params=expected_parameter,
        )

        assert isinstance(results, list)
        assert len(results) == len(expected_parameter)
        assert isinstance(results[0], JobParameter)

    def test_without_job_def_file_has_default_values(self) -> None:
        expected_parameter: dict[str, str] = {"n": "v"}

        results: list[JobParameter] = common.prepare_job_params(
            job_def_file=None,
            params=expected_parameter,
        )

        parameter: JobParameter = results[0]
        assert not parameter.is_mandatory
        assert parameter.type_ is JobParamType.STRING
        assert parameter.name in expected_parameter
        assert parameter.value in expected_parameter.values()

    def test_with_pathlib_job_def_file_path(self) -> None:
        expected_parameter: dict[str, str] = {"Username": "v1", "Password": "v2"}

        results: list[JobParameter] = common.prepare_job_params(
            job_def_file=JOB_DEF,
            params=expected_parameter,
        )

        assert len(results) == len(expected_parameter)
        for param in results:
            if param.name == "Username":
                assert param.is_mandatory
                assert param.value == expected_parameter["Username"]
                assert param.type_ is JobParamType.STRING

            else:
                assert not param.is_mandatory
                assert param.value == expected_parameter["Password"]
                assert param.type_ is JobParamType.PASSWORD

    def test_with_str_job_def_file_path(self) -> None:
        expected_parameter: dict[str, str] = {"Username": "v1", "Password": "v2"}

        results: list[JobParameter] = common.prepare_job_params(
            job_def_file=str(JOB_DEF),
            params=expected_parameter,
        )

        assert len(results) == len(expected_parameter)
        for param in results:
            if param.name == "Username":
                assert param.is_mandatory
                assert param.value == expected_parameter["Username"]
                assert param.type_ is JobParamType.STRING

            else:
                assert not param.is_mandatory
                assert param.value == expected_parameter["Password"]
                assert param.type_ is JobParamType.PASSWORD


class TestUseLiveApi:
    def test_envar_is_set_to_true_returns_true(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(os, "environ", {"USE_LIVE_API": True})

        use_live: bool = common.use_live_api()

        assert use_live is True

    def test_envar_is_set_to_false_returns_false(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(os, "environ", {"USE_LIVE_API": False})

        use_live: bool = common.use_live_api()

        assert use_live is False

    def test_envar_is_missing_returns_false(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(os, "environ", {})

        use_live: bool = common.use_live_api()

        assert use_live is False


class TestGetConfigFileJson:
    def test_returns_json_with_str_path(self) -> None:
        file_name: str = "mock.json"
        path: pathlib.Path = pathlib.Path(__file__).parent / file_name
        expected_content: dict[str, str] = json.loads(path.read_text())

        content: dict[str, str] = common.get_def_file_content(str(path))

        assert content == expected_content

    def test_returns_json_with_pathlib_path(self) -> None:
        file_name: str = "mock.json"
        path: pathlib.Path = pathlib.Path(__file__).parent / file_name
        expected_content: dict[str, str] = json.loads(path.read_text())

        content: dict[str, str] = common.get_def_file_content(path)

        assert content == expected_content

    def test_raises_file_not_found_if_the_file_is_missing(self) -> None:
        file_name: str = "FileNotFound.json"
        path: pathlib.Path = pathlib.Path(__file__).parent / file_name

        with pytest.raises(FileNotFoundError):
            _ = common.get_def_file_content(path)

    def test_raises_value_error_if_the_file_is_not_json_file(self) -> None:
        file_name: str = "mock.txt"
        path: pathlib.Path = pathlib.Path(__file__).parent / file_name

        with pytest.raises(ValueError, match="path is not a json file"):
            _ = common.get_def_file_content(path)


class TestSetSysArgv:
    def test_value_is_set(self) -> None:
        value: list[str] = ["hello", "world"]

        common.set_sys_argv(value)

        assert sys.argv == value


class TestSetIsFirsRun:
    def test_set_to_false_sets_to_false(self) -> None:
        common.set_is_first_run_to_false()

        is_first_run: bool = TIPCommon.utils.is_first_run(sys.argv)

        assert is_first_run is False

    def test_set_to_true_sets_to_true(self) -> None:
        common.set_is_first_run_to_true()

        is_first_run: bool = TIPCommon.utils.is_first_run(sys.argv)

        assert is_first_run is True


class TestSetIsTestRun:
    def test_set_to_false_sets_to_false(self) -> None:
        common.set_is_test_run_to_false()

        is_test_run: bool = TIPCommon.utils.is_test_run(sys.argv)

        assert is_test_run is False

    def test_set_to_true_sets_to_true(self) -> None:
        common.set_is_test_run_to_true()

        is_test_run: bool = TIPCommon.utils.is_test_run(sys.argv)

        assert is_test_run is True


@dataclasses.dataclass
class TestGetRequestPayload:
    empty_args: tuple[()] = ()
    empty_headers: dict[str, str] = dataclasses.field(default_factory=dict)
    parsed_url: urllib.parse.ParseResult = dataclasses.field(
        default_factory=functools.partial(urllib.parse.urlparse, "/test/url/"),
    )

    def test_returns_empty_dict_if_no_matching_keys(self) -> None:
        request: MockRequest = MockRequest(
            method=HttpMethod.GET,
            url=self.parsed_url,
            headers=self.empty_headers,
            args=self.empty_args,
            kwargs={"foo": "bar"},
        )
        assert common.get_request_payload(request) == {}

    def test_returns_payload_from_json_key(self) -> None:
        expected_payload: dict[str, str] = {"key1": "value1"}
        request: MockRequest = MockRequest(
            method=HttpMethod.POST,
            url=self.parsed_url,
            headers=self.empty_headers,
            args=self.empty_args,
            kwargs={"json": expected_payload},
        )
        assert common.get_request_payload(request) == expected_payload

    def test_returns_payload_from_payload_key(self) -> None:
        expected_payload: dict[str, str] = {"key2": "value2"}
        request: MockRequest = MockRequest(
            method=HttpMethod.POST,
            url=self.parsed_url,
            headers=self.empty_headers,
            args=self.empty_args,
            kwargs={"payload": expected_payload},
        )
        assert common.get_request_payload(request) == expected_payload

    def test_returns_payload_from_params_key(self) -> None:
        expected_payload: dict[str, str] = {"key3": "value3"}
        request: MockRequest = MockRequest(
            method=HttpMethod.GET,
            url=self.parsed_url,
            headers=self.empty_headers,
            args=self.empty_args,
            kwargs={"params": expected_payload},
        )
        assert common.get_request_payload(request) == expected_payload
