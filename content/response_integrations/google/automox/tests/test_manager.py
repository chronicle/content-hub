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

# Integrations.Automox.Managers.
import json
import os
from unittest.mock import Mock, patch
import pytest
import random
import time
from typing import List

from automox.core.AutomoxManager import AutomoxManager


RANDOM_SAMPLE_SIZE = 2
MOCK_DATA = json.load(
    open(
        os.path.join(os.path.dirname(__file__), "mock_data.json")
    )
)

@pytest.mark.parametrize(
    "filter_key, filter_logics",
    [
        ("id", ["Equal", "Contains"]),
        ("name", ["Equal", "Contains"]),
        ("policy_type_name", ["Equal", "Contains"]),
        ("status", ["Equal", "Contains"]),
    ]
)
def test_get_policies_with_filters(manager_fixture: AutomoxManager,
                                   filter_key: str,
                                   filter_logics: List[str]):
    all_policies = manager_fixture.get_policies()
    chosen_policies = random.sample(all_policies, RANDOM_SAMPLE_SIZE)
    for policy in chosen_policies:
        filter_value = str(policy.raw_data[filter_key])

        for filter_logic in filter_logics:
            filtered_policies = manager_fixture.get_policies(
                filter_key=filter_key,
                filter_logic=filter_logic,
                filter_value=filter_value,
            )
            if filter_logic == "Contains":
                assert all(filter_value in str(policy.raw_data[filter_key]) for policy in filtered_policies)
            else:
                assert all(filter_value == str(policy.raw_data[filter_key]) for policy in filtered_policies)


@pytest.mark.parametrize(
    "max_records_to_return",
    [
        1, 3, 5, 7
    ]
)
def test_get_policies_max_records_to_return(manager_fixture: AutomoxManager,
                                            max_records_to_return: int):
    all_policies = manager_fixture.get_policies()
    policies_count = len(all_policies)
    sliced_policies = manager_fixture.get_policies(
        max_records_to_return=max_records_to_return,
    )
    assert len(sliced_policies) == min(policies_count, max_records_to_return)


@pytest.mark.parametrize(
    "filter_field",
    [
        "display_name",
        "ip_addrs_private",
    ]
)
def test_get_devices_with_filters(manager_fixture: AutomoxManager,
                                  filter_field: str):
    all_devices = manager_fixture.get_devices()
    chosen_devices = random.sample(all_devices, RANDOM_SAMPLE_SIZE)
    for device in chosen_devices:
        filter_value = device.raw_data[filter_field]

        filtered_devices = manager_fixture.get_devices(
            filter_value=filter_value,
            filter_field=filter_field,
        )
        assert all(filter_value == device.raw_data[filter_field] for device in filtered_devices)


@pytest.mark.parametrize(
    "action",
    [
        "remediateAll",
        "remediateServer"
    ]
)
def test_execute_policy(manager_fixture: AutomoxManager,
                        action: str):
    all_policies = manager_fixture.get_policies()
    chosen_policies = random.sample(all_policies, RANDOM_SAMPLE_SIZE)
    server_id = None
    for policy in chosen_policies:
        if action == "remediateServer":
            all_devices = manager_fixture.get_devices()
            chosen_device = random.choice(all_devices)
            server_id = chosen_device.raw_data["id"]

        assert manager_fixture.execute_policy(
            policy_id=policy.id,
            server_id=server_id,
            action=action
        )


@pytest.mark.parametrize(
    "max_records_to_return",
    [
        1, 3, 5, 7
    ]
)
def test_list_patches(manager_fixture: AutomoxManager,
                      max_records_to_return: int):
    devices = manager_fixture.get_devices()
    devices_to_check = random.sample(devices, RANDOM_SAMPLE_SIZE)
    for device in devices_to_check:
        all_patches = manager_fixture.get_patches(device.id)
        for patch in all_patches:
            assert not (patch.ignored or patch.installed)

        patches_with_limit = manager_fixture.get_patches(
            device_id=device.id,
            max_patches=max_records_to_return
        )
        assert len(patches_with_limit) == min(len(all_patches), max_records_to_return)


@pytest.mark.parametrize(
    "filter_value,expected",
    [
        ("ATMX-001", dict(display_name="ATMX-001", id=2465333)),
        ("172.30.201.191", dict(display_name="ATMX-08", id=2333821))
    ]
)
def test_get_devices(
    manager_fixture: AutomoxManager,
    filter_value: str,
    expected: dict
):
    mock_response = Mock()
    mock_response.json.return_value = [MOCK_DATA.get(
        'get_devices', {}
    ).get(filter_value, {})]
    mock_response.status_code = 200
    patch_object = patch.object(
        manager_fixture.session, "get", return_value=mock_response
    )
    with patch_object:
        device = manager_fixture.get_devices(filter_value=filter_value)[0]

        assert device.display_name == expected["display_name"]
        assert device.id == expected["id"]


@pytest.mark.xfail(reason="issue link: b/377237392")
@pytest.mark.parametrize(
    "device_id,command,args",
    [
        (2465333, "GetOS", "")
    ]
)
def test_execute_device_command(
    manager_fixture: AutomoxManager,
    device_id: int,
    command: str,
    args: str
):
    assert manager_fixture.execute_device_command(device_id=device_id, command=command, args=args)

    # give some time for an item to appear (API limitation)
    time.sleep(2)

    queue_items = manager_fixture.get_queue_data(device_id=device_id)
    filtered = list(
        filter(
            lambda q_item: q_item.command_type_name == command and q_item.args == args,
            queue_items
        )
    )[0]

    command_id = filtered.id

    assert filtered.command_type_name == command
    assert command_id is not None
    assert filtered.server_id == device_id

    # this can take a while
    mock_response = Mock()
    mock_response.json.return_value = MOCK_DATA.get('get_queue_data', [])
    mock_response.status_code = 200
    patch_object = patch.object(
        manager_fixture.session, "get", return_value=mock_response
    )

    with patch_object:
        while True:
            queue_item = manager_fixture.get_queue_data_single(device_id=device_id, command_id=command_id)

            assert queue_item.server_id == device_id

            if queue_item.response:
                assert queue_item.response
                break
            time.sleep(2)
