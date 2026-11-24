from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from tenable_io.actions.EnrichEntities import main
from tenable_io.tests.conftest import (
    LegacyActionOutput,
    LegacyJsonResults,
    MockSiemplifyEntity,
)
from tenable_io.tests.core.product import TenableIOProduct


class TestEnrichEntities:
    """Tests for the Tenable.io "Enrich Entities" action."""

    def test_enrich_entities_success(
        self,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test entity enrichment success path.

        Verifies that IP addresses and hostnames are correctly enriched and
        that insights are created when the option is enabled.

        Args:
            tenable_io_product: The mocked Tenable.io product instance.
            action_output: The captured action output.
            json_results: The captured JSON results.
            mock_siemplify: The mocked Siemplify API object.
            action_params: The parameters for the action.
        """
        _ = tenable_io_product
        action_params["Create Insight"] = True

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="1.1.1.1", entity_type="ADDRESS"),
            MockSiemplifyEntity(identifier="HOST1", entity_type="HOSTNAME"),
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched" in action_output.output_message
        assert action_output.result_value is True

        # The result might be a nested list, e.g., [[{...}, {...}]]
        results = json_results.json_results
        results_list = results[0] if results and isinstance(
            results[0],
            list
        ) else results

        found = False
        for item in results_list:
            if isinstance(item, dict) and item.get("Entity") == "1.1.1.1":
                found = True
                assert item["EntityResult"]["id"] == "asset_enrich_1"
                break

        assert found, "Enriched entity '1.1.1.1' not found in JSON results."

    def test_enrich_entities_not_found(
        self,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test entity enrichment when no matching assets are found.

        Verifies that the action completes with a message indicating no
        entities were enriched.

        Args:
            action_output: The captured action output.
            json_results: The captured JSON results.
            mock_siemplify: The mocked Siemplify API object.
            action_params: The parameters for the action.
        """
        action_params["Create Insight"] = True

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="1.2.3.4", entity_type="ADDRESS")
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        output_message = action_output.output_message
        assert "None of the provided entities were enriched" in output_message
        assert action_output.result_value is False
        assert not json_results.json_results

    def test_enrich_entities_no_entities(
        self,
        action_output: LegacyActionOutput,
        json_results: LegacyJsonResults,
        mock_siemplify: MagicMock,
    ) -> None:
        """Test entity enrichment when no entities are provided.

        Verifies that the action completes with a message indicating no
        entities were provided.

        Args:
            action_output: The captured action output.
            json_results: The captured JSON results.
            mock_siemplify: The mocked Siemplify API object.
        """
        mock_siemplify.target_entities = []

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        output_message = action_output.output_message
        assert "None of the provided entities were enriched" in output_message
        assert action_output.result_value is False
        assert not json_results.json_results

    def test_enrich_entities_hostname_matching(
        self,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test robust hostname matching (FQDN, NetBIOS, Short Hostname).

        Verifies that the action can match entities against an asset's FQDN,
        NetBIOS name, and short hostname.

        Args:
            tenable_io_product: The mocked Tenable.io product instance.
            action_output: The captured action output.
            mock_siemplify: The mocked Siemplify API object.
            action_params: The parameters for the action.
        """
        _ = tenable_io_product
        action_params["Create Insight"] = False

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier="server.domain.local",
                entity_type="HOSTNAME"
            ),
            MockSiemplifyEntity(identifier="SERVER-NB", entity_type="HOSTNAME"),
            MockSiemplifyEntity(identifier="server", entity_type="HOSTNAME"),
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched" in action_output.output_message
        assert action_output.result_value is True

        # Verify all matched entities are mentioned in the output
        output_message = action_output.output_message
        assert "server.domain.local" in output_message
        assert "SERVER-NB" in output_message
        assert "server" in output_message

    def test_enrich_entities_case_insensitivity_and_agent_name(
        self,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test case-insensitive matching and Agent Name support.

        Verifies that the action can match entities against an asset's Agent Name
        and handles mixed case identifiers correctly (e.g., matching 'special-agent-v2'
        against 'Special-Agent-V2').

        Args:
            tenable_io_product: The mocked Tenable.io product instance.
            action_output: The captured action output.
            mock_siemplify: The mocked Siemplify API object.
            action_params: The parameters for the action.
        """
        _ = tenable_io_product
        action_params["Create Insight"] = False

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(
                identifier="special-agent-v2",
                entity_type="HOSTNAME"
            ),
            MockSiemplifyEntity(
                identifier="v2-asset.corp.local",
                entity_type="HOSTNAME"
            ),
            MockSiemplifyEntity(
                identifier="Win-Agent-01",
                entity_type="HOSTNAME"
            ),
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched" in action_output.output_message
        assert action_output.result_value is True

        output_message = action_output.output_message
        assert "special-agent-v2" in output_message
        assert "v2-asset.corp.local" in output_message
        assert "Win-Agent-01" in output_message

    def test_enrich_entities_v2_aws_agent_name(
        self,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test matching AWS asset by Agent Name.

        Asset ID: 11111111-aaaa-bbbb-cccc-dddddddddddd
        Agent Name: aws-prod-linux-01
        """
        _ = tenable_io_product
        action_params["Create Insight"] = False

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="aws-prod-linux-01", entity_type="HOSTNAME"),
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched" in action_output.output_message
        assert action_output.result_value is True
        assert "aws-prod-linux-01" in action_output.output_message

    def test_enrich_entities_v2_azure_netbios(
        self,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test matching Azure asset by NetBIOS Name (from network object).

        Asset ID: 22222222-eeee-ffff-aaaa-bbbbbbbbbbbb
        NetBIOS Name: WORKSTATION-01 (in network.netbios_names)
        """
        _ = tenable_io_product
        action_params["Create Insight"] = False

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="WORKSTATION-01", entity_type="HOSTNAME"),
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched" in action_output.output_message
        assert action_output.result_value is True
        assert "WORKSTATION-01" in action_output.output_message

    def test_enrich_entities_v2_gcp_fqdn(
        self,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test matching GCP asset by FQDN (from network object).

        Asset ID: 33333333-1111-2222-3333-444444444444
        FQDN: app.example.com
        """
        _ = tenable_io_product
        action_params["Create Insight"] = False

        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier="app.example.com", entity_type="HOSTNAME"),
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched" in action_output.output_message
        assert action_output.result_value is True
        assert "app.example.com" in action_output.output_message

    def test_enrich_entities_semicolon_delimiter(
        self,
        tenable_io_product: TenableIOProduct,
        action_output: LegacyActionOutput,
        mock_siemplify: MagicMock,
        action_params: dict[str, Any],
    ) -> None:
        """Test that multiple values in entity table are separated by semicolons."""
        _ = tenable_io_product
        action_params["Create Insight"] = False

        entity_identifier = "aws-prod-linux-01"
        mock_siemplify.target_entities = [
            MockSiemplifyEntity(identifier=entity_identifier, entity_type="HOSTNAME"),
        ]

        main()

        assert action_output.status == EXECUTION_STATE_COMPLETED
        assert "Successfully enriched" in action_output.output_message

        table_calls = [
            c for c in mock_siemplify.result.add_entity_table.call_args_list
            if c[0][0] == entity_identifier
        ]
        assert len(table_calls) > 0

        csv_data = table_calls[0][0][1]

        assert "ipv4,10.0.1.50; 203.0.113.10" in csv_data
        assert ("OS,Amazon Linux 2; Linux Kernel 4.14.225-121.357.amzn2.x86_64" in
                csv_data)
        assert ("fqdn,prod-web-01.example.com; "
                "ec2-203-0-113-10.us-west-2.compute.amazonaws.com" in
                csv_data)
