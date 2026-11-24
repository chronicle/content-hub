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

"""Google Cloud Compute Manager tests."""
from typing import Type

import pytest_mock

from google_cloud_compute.core.GoogleCloudComputeManager import (
    GoogleCloudComputeManager
)
from google_cloud_compute.tests.factories import (
    OperationFactory,
    PatchJobFactory,
)


def test_delete_access_config(
        mocker,
        compute_manager,
        operation_factory,
):
    session = mocker.Mock()
    compute_manager.session = session

    operation = operation_factory()
    params = {
        'networkInterface': 'test-network-interface',
        'accessConfig': 'test-access-config'
    }

    mocker.patch.object(
        session,
        'post',
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: operation.raw_data
        )
    )
    result = compute_manager.delete_access_config(
        resource_path='test-resource-path',
        access_config='test-access-config',
        network_interface='test-network-interface'
    )

    assert session.post.call_args[1]['params'] == params
    assert (
        operation.__dict__ == result.__dict__
    )


def test_patch_network_interface(
        mocker,
        compute_manager,
        operation_factory,
):
    session = mocker.Mock()
    compute_manager.session = session

    operation = operation_factory()
    params = {
        'networkInterface': 'test-network-interface'
    }
    request_body = {
        'fingerprint': 'fingerprint',
        'stackType': 'IPV4_ONLY'
    }

    mocker.patch.object(
        session,
        'patch',
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: operation.raw_data
        )
    )
    result = compute_manager.patch_network_interface(
        resource_path='test-resource-path',
        network_interface='test-network-interface',
        fingerprint='fingerprint',
        stack_type='IPV4_ONLY'
    )

    assert session.patch.call_args[1]['params'] == params
    assert session.patch.call_args[1]['json'] == request_body
    assert (
        operation.__dict__ == result.__dict__
    )


def test_get_firewall_rule(
        mocker,
        compute_manager,
        firewall_rule_factory,
):
    session = mocker.Mock()
    compute_manager.session = session

    firewall_rule = firewall_rule_factory()

    mocker.patch.object(
        session,
        'get',
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: firewall_rule.raw_data
        )
    )
    result = compute_manager.get_firewall_rule(
        resource_path='test-resource-path',
    )

    assert session.get.call_count == 1
    assert (
        firewall_rule.__dict__ == result.__dict__
    )


def test_patch_firewall_rule(
        mocker,
        compute_manager,
        firewall_rule_factory,
        operation_factory
):
    session = mocker.Mock()
    compute_manager.session = session

    firewall_rule = firewall_rule_factory()
    firewall_rule.stack_type = 'IPV4_ONLY'

    operation = operation_factory()

    mocker.patch.object(
        session,
        'patch',
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: operation.raw_data
        )
    )
    result = compute_manager.patch_firewall_rule(
        resource_path='test-resource-path',
        firewall=firewall_rule
    )

    assert session.patch.call_args[1]['json'] == firewall_rule.as_dict()
    assert (
        operation.__dict__ == result.__dict__
    )


def test_execute_patch_job(
        mocker: pytest_mock.MockerFixture,
        compute_manager: GoogleCloudComputeManager,
        patch_job_factory: Type[PatchJobFactory],
):
    session = mocker.Mock()
    compute_manager.session = session

    patch_job = patch_job_factory()

    mocker.patch.object(
        session,
        'post',
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: {
                **patch_job.as_dict(),
                'name': patch_job.name,
                'state': 'STARTED'
            }
        )
    )
    result = compute_manager.execute_patch_job(patch_job)

    assert session.post.call_count == 1
    assert session.post.call_args[1]['json'] == patch_job.as_dict()
    assert result.name is not None


def test_get_patch_job(
        mocker: pytest_mock.MockerFixture,
        compute_manager: GoogleCloudComputeManager,
        patch_job_factory: Type[PatchJobFactory],
):
    session = mocker.Mock()
    compute_manager.session = session

    patch_job = patch_job_factory()

    mocker.patch.object(
        session,
        'get',
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: {
                **patch_job.as_dict(),
                'name': patch_job.name,
                'state': 'SUCCEEDED'
            }
        )
    )
    result = compute_manager.get_patch_job(patch_job.name)

    assert session.get.call_count == 1
    assert session.get.call_args[0][0].endswith(result.name)
    assert result.name is not None


def test_get_operation(
        mocker,
        compute_manager,
        operation_factory,
):
    session = mocker.Mock()
    compute_manager.session = session

    operation = operation_factory()

    mocker.patch.object(
        session,
        'get',
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: operation.raw_data
        )
    )
    result = compute_manager.get_operation(
        self_link='https://operation-self-link',
    )

    assert session.get.call_count == 1
    assert (
        operation.__dict__ == result.__dict__
    )


def test_set_instance_tags(
        mocker: pytest_mock.MockerFixture,
        compute_manager: GoogleCloudComputeManager,
        operation_factory: Type[OperationFactory],
):
    session = mocker.Mock()
    compute_manager.session = session

    operation = operation_factory()

    mocker.patch.object(
        session,
        'post',
        return_value=mocker.Mock(
            status_code=200,
            json=lambda: operation.raw_data
        )
    )
    result = compute_manager.set_instance_tags(
        resource_path='test-resource-path',
        tags=['tag1', 'tag2'],
        fingerprint='RC25UTaX1A0='
    )

    assert session.post.call_args[1]['json'] == {
        'items': ['tag1', 'tag2'],
        'fingerprint': 'RC25UTaX1A0='
    }
    assert (
        operation.__dict__ == result.__dict__
    )
