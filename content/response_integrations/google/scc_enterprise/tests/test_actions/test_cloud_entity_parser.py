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

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import EntityTypesEnum

from scc_enterprise.actions.CloudEntityParser import (
    ADDITIONAL_PROPERTY_AWS_EC2_SHORTNAME,
    ADDITIONAL_PROPERTY_GCP_RESOURCE_NAME,
    EVENT_AWS_ACCOUNT_ID,
    EVENT_AWS_REGION,
    EVENT_PRINCIPAL_EMAIL_KEY,
    SA_EMAIL_RE_PATTERN,
    CloudEntityParser,
)
from scc_enterprise.core.SCCEnterpriseConsts import CLOUD_ENTITY_PARSER_SCRIPT_NAME

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class TestGetEntityTypeFromEventProperty:
    @pytest.mark.parametrize(
        ("property_key", "property_value", "expected_type"),
        [
            (
                "resource",
                "//cloudresourcemanager.googleapis.com/projects/123456",
                EntityTypesEnum.DEPLOYMENT,
            ),
            (
                "resource",
                "//storage.googleapis.com/my-bucket",
                EntityTypesEnum.DATABASE,
            ),
            (
                "resource",
                "//compute.googleapis.com/projects/p1/zones/us-central1-a/instances/vm-1",
                EntityTypesEnum.HOST_NAME,
            ),
            (
                "resource",
                "//compute.googleapis.com/projects/p1/global/firewalls/fw-1",
                EntityTypesEnum.DEPLOYMENT,
            ),
            (
                "resource",
                "//bigquery.googleapis.com/projects/p1/datasets/ds1",
                EntityTypesEnum.DATABASE,
            ),
            (
                "resource",
                "//k8s.io/rbac.authorization.k8s.io/v1/clusterroles/admin",
                EntityTypesEnum.DEPLOYMENT,
            ),
            (
                "resource",
                "//container.googleapis.com/projects/p1/locations/us-central1/clusters/c1",
                EntityTypesEnum.CONTAINER,
            ),
            (
                "resource",
                "//iam.googleapis.com/projects/p1/serviceAccounts/sa@p1.iam.gserviceaccount.com",
                EntityTypesEnum.USER,
            ),
            (
                "resource",
                "//accesscontextmanager.googleapis.com/accessPolicies/123",
                EntityTypesEnum.DEPLOYMENT,
            ),
            (
                "resource",
                "//cloudsql.googleapis.com/projects/p1/instances/sql-1",
                EntityTypesEnum.DATABASE,
            ),
            (
                "resource",
                "arn:aws:iam::123456789012:user/alice",
                EntityTypesEnum.USER,
            ),
            (
                "resource",
                "arn:aws:s3:::prod-logs-bucket",
                EntityTypesEnum.DATABASE,
            ),
            (
                "resource",
                "arn:aws:ec2:us-east-1:123456789012:instance/i-0123456789abcdef0",
                EntityTypesEnum.HOST_NAME,
            ),
            (
                "resource",
                "arn:aws:guardduty:us-east-1:123456789012:detector/12abc/finding/34def",
                None,
            ),
            (
                "resource",
                "/subscriptions/0000-1111/resourceGroups/rg1/providers/Microsoft.Compute/virtualMachines/vm1",
                EntityTypesEnum.DEPLOYMENT,
            ),
            (
                "entity_entity_hostname",
                "web-prod-01",
                EntityTypesEnum.HOST_NAME,
            ),
            (
                "event_target_resource_name",
                "custom-deployment",
                EntityTypesEnum.DEPLOYMENT,
            ),
        ],
    )
    def test_valid_resource_mappings(
        self,
        property_key: str,
        property_value: str,
        expected_type: EntityTypesEnum | None,
    ) -> None:
        result = CloudEntityParser.get_entity_type_from_event_property(
            property_key,
            property_value,
        )
        assert result == expected_type

    @pytest.mark.parametrize(
        "spoofed_value",
        [
            "//k8s.io.evil.example/clusterroles/admin",
            "//storage.googleapis.com.evil.example/bucket",
            "//evil-storage.googleapis.com/bucket",
            "//storage.googleapis.com@evil.example/bucket",
            "//storage.googleapis.com:8080/bucket",
            "//evil.example///storage.googleapis.com/bucket",
            "https://evil.example/redirect?target=//storage.googleapis.com/bucket",
            "https://storage.googleapis.com/bucket",
            "//storage.googleapis.com",
            "//k8s.io/namespaces/default/pods/pod-1",
            "//k8s.io",
        ],
    )
    def test_rejects_spoofed_or_malformed_gcp_urls(self, spoofed_value: str) -> None:
        result = CloudEntityParser.get_entity_type_from_event_property(
            "resource",
            spoofed_value,
        )
        assert result is None


class TestServiceAccountEmailPattern:
    def test_matches_valid_gcp_service_account_email(self) -> None:
        email = "serviceAccount:runner-sa_01@my-project-123.iam.gserviceaccount.com"
        assert SA_EMAIL_RE_PATTERN.search(email) is not None

    def test_rejects_unescaped_dot_spoofed_domain(self) -> None:
        spoofed = "runner-sa@my-project-123XiamYgserviceaccountZcom"
        assert SA_EMAIL_RE_PATTERN.search(spoofed) is None


class TestCloudEntityParserAction:
    @set_metadata
    def test_perform_action_extracts_valid_entities_and_ignores_spoofed_urls(
        self,
        mocker: MockerFixture,
    ) -> None:
        parser = CloudEntityParser(CLOUD_ENTITY_PARSER_SCRIPT_NAME)

        event = MagicMock()
        event.additional_properties = {
            EVENT_PRINCIPAL_EMAIL_KEY: "serviceAccount:ci-bot@secops-proj.iam.gserviceaccount.com",
            EVENT_AWS_REGION: "us-east-1",
            EVENT_AWS_ACCOUNT_ID: "123456789012",
            "gcp_bucket": "//storage.googleapis.com/audit-bucket",
            "spoofed_gcp": "//storage.googleapis.com@evil.example/audit-bucket",
            "spoofed_k8s": "//k8s.io.evil.example/clusterroles/cluster-admin",
            "aws_user": "arn:aws:iam::123456789012:user/sec-admin",
            "aws_ec2": "i-0abc1234def567890",
        }

        soar_action = MagicMock()
        soar_action.case_id = "101"
        soar_action.target_entities = []
        soar_action.current_alert.identifier = "alert-1"
        soar_action.current_alert.security_events = [event]
        parser._soar_action = soar_action

        add_entity_mock = mocker.patch.object(parser, "_add_entity_to_case")
        create_entity_mock = mocker.patch("scc_enterprise.actions.CloudEntityParser.create_entity")

        parser._perform_action()

        created = parser.json_results["created"]
        assert created == {
            "ci-bot@secops-proj.iam.gserviceaccount.com": EntityTypesEnum.USER,
            "//storage.googleapis.com/audit-bucket": EntityTypesEnum.DATABASE.value,
            "arn:aws:iam::123456789012:user/sec-admin": EntityTypesEnum.USER.value,
            "arn:aws:ec2:us-east-1:123456789012:instance/i-0abc1234def567890": (
                EntityTypesEnum.HOST_NAME.value
            ),
        }
        assert "//storage.googleapis.com@evil.example/audit-bucket" not in created
        assert "//k8s.io.evil.example/clusterroles/cluster-admin" not in created
        assert parser.json_results["relationships"] == [
            [
                "arn:aws:iam::123456789012:user/sec-admin",
                "arn:aws:ec2:us-east-1:123456789012:instance/i-0abc1234def567890",
            ],
        ]
        assert add_entity_mock.call_count == len(created)
        create_entity_mock.assert_called_once()

        added_props_by_id = {
            call.kwargs["entity_identifier"]: call.kwargs["properties"]
            for call in add_entity_mock.call_args_list
        }
        assert added_props_by_id["//storage.googleapis.com/audit-bucket"] == {
            ADDITIONAL_PROPERTY_GCP_RESOURCE_NAME: "//storage.googleapis.com/audit-bucket",
        }
        assert added_props_by_id[
            "arn:aws:ec2:us-east-1:123456789012:instance/i-0abc1234def567890"
        ] == {
            ADDITIONAL_PROPERTY_AWS_EC2_SHORTNAME: "i-0abc1234def567890",
        }
