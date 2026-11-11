from __future__ import annotations

from scc_enterprise.core.SCCEnterpriseConsts import NOT_AVAILABLE
from scc_enterprise.core.SCCEnterpriseDescCreation import (
    CreateDescFn,
    DescriptionOutputType,
    get_create_desc_fn,
)
from TIPCommon.types import SingleJson
from scc_enterprise.tests.test_description.conftest import ParamCreatorFn


class TestGetCreateDescFn:

    def test_get_create_html_description_functions(self) -> None:
        fn = get_create_desc_fn(DescriptionOutputType.HTML)

        assert callable(fn)

    def test_get_create_jwm_description_functions(self) -> None:
        fn = get_create_desc_fn(DescriptionOutputType.JWM)

        assert callable(fn)


class TestHtmlGcpTemplateBusinessLogic:

    def test_using_source_properties_keys_shows_source_properties_sections(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_with_source_properties: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(event_with_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Explanation") != -1
            and description.rfind("Exception Instructions") != -1
            and description.rfind("Recommended Steps") != -1
        )

    def test_missing_source_properties_are_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Explanation") == -1
            and description.rfind("Exception Instructions") == -1
            and description.rfind("Recommended Steps") == -1
        )

    def test_missing_source_properties_uses_description(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Finding Description") != -1

    def test_missing_source_properties_uses_next_steps(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Next Steps") != -1

    def test_desc_has_document_statement_mitigation_keys_sections_are_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_with_document_statement_mitigation_description: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(
            event_with_document_statement_mitigation_description
        )
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") != -1
            and description.rfind("Finding Statement") != -1
            and description.rfind("Finding Mitigation") != -1
        )

    def test_desc_without_document_statement_mitigation_keys_sections_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") == -1
        )

    def test_only_documentation_description_sections_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "DOCUMENTATION: doc"
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") != -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") == -1
        )

    def test_only_statement_description_sections_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "STATEMENT: statement"
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") != -1
            and description.rfind("Finding Mitigation") == -1
        )

    def test_only_mitigation_description_sections_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "MITIGATION: mitigation"
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") != -1
        )

    def test_desc_starts_with_text_contain_mitigation_keys_sections_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "text MITIGATION: mitigation"
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Finding Mitigation") == -1

    def test_desc_starts_with_text_contain_doc_keys_sections_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "text DOCUMENTATION: doc"
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Finding Documentation") == -1

    def test_desc_starts_with_text_contain_statement_keys_sections_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "text STATEMENT: statement"
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Finding Statement") == -1

    def test_source_properties_event_doc_statement_mitigation_keys_sections_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_with_source_properties_and_doc_statement_mitigation_desc: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(
            event_with_source_properties_and_doc_statement_mitigation_desc
        )
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") == -1
        )

    def test_no_next_steps_shown_na(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        del event_without_source_properties["nextSteps"]
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Next Steps") != -1
            and description.count(NOT_AVAILABLE) == 1
        )

    def test_no_description_shown_na(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        del event_without_source_properties["description"]
        parameters: SingleJson = get_gcp_html_params(event_without_source_properties)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Description") != -1
            and description.count(NOT_AVAILABLE) == 1
        )

    def test_missing_cve_are_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(
            event_without_cve_cvss_and_references
        )
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Additional Information") == -1

    def test_missing_cvss_are_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(
            event_without_cve_cvss_and_references
        )
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("CVSS V3 Information") == -1

    def test_missing_references_are_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_without_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(
            event_without_cve_cvss_and_references
        )
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Reference Links") == -1

    def test_cve_exists_section_is_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_with_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(event_with_cve_cvss_and_references)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Additional Information") != -1

    def test_cvss_exists_section_is_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_with_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(event_with_cve_cvss_and_references)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("CVSS V3 Information") != -1

    def test_reference_exists_section_is_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_gcp_html_params: ParamCreatorFn,
        event_with_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_html_params(event_with_cve_cvss_and_references)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Reference Links") != -1


class TestJwmGcpTemplateBusinessLogic:

    def test_using_source_properties_keys_shows_source_properties_sections(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_with_source_properties: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(event_with_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Explanation") != -1
            and description.rfind("Exception Instructions") != -1
            and description.rfind("Recommended Steps") != -1
        )

    def test_missing_source_properties_are_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Explanation") == -1
            and description.rfind("Exception Instructions") == -1
            and description.rfind("Recommended Steps") == -1
        )

    def test_missing_source_properties_uses_description(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Finding Description") != -1

    def test_missing_source_properties_uses_next_steps(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Next Steps") != -1

    def test_desc_has_document_statement_mitigation_keys_sections_are_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_with_document_statement_mitigation_description: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(
            event_with_document_statement_mitigation_description
        )
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") != -1
            and description.rfind("Finding Statement") != -1
            and description.rfind("Finding Mitigation") != -1
        )

    def test_desc_without_document_statement_mitigation_keys_sections_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") == -1
        )

    def test_only_documentation_description_sections_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "DOCUMENTATION: docs"
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") != -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") == -1
        )

    def test_only_statement_description_sections_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "STATEMENT: statement"
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") != -1
            and description.rfind("Finding Mitigation") == -1
        )

    def test_only_mitigation_description_keys_sections_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "MITIGATION: mitigation"
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") != -1
        )

    def test_desc_starts_with_text_contain_mitigation_keys_sections_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "text MITIGATION: mitigation"
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Finding Mitigation") == -1

    def test_desc_starts_with_text_contain_doc_keys_sections_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "text DOCUMENTATION: doc"
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Finding Documentation") == -1

    def test_desc_starts_with_text_contain_statement_keys_sections_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        event_without_source_properties["description"] = "text STATEMENT: statement"
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Finding Statement") == -1

    def test_source_properties_event_doc_statement_mitigation_keys_sections_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_with_source_properties_and_doc_statement_mitigation_desc: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(
            event_with_source_properties_and_doc_statement_mitigation_desc
        )
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") == -1
        )

    def test_no_next_steps_shown_na(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        del event_without_source_properties["nextSteps"]
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Next Steps") != -1
            and description.count(NOT_AVAILABLE) == 1
        )

    def test_no_description_shown_na(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_source_properties: dict[str, str],
    ) -> None:
        del event_without_source_properties["description"]
        parameters: SingleJson = get_gcp_jwm_params(event_without_source_properties)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Description") != -1
            and description.count(NOT_AVAILABLE) == 1
        )

    def test_missing_cve_are_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(
            event_without_cve_cvss_and_references
        )
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Additional Information") == -1

    def test_missing_cvss_are_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(
            event_without_cve_cvss_and_references
        )
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("CVSS V3 Information") == -1

    def test_missing_references_are_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_without_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(
            event_without_cve_cvss_and_references
        )
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Reference Links") == -1

    def test_cve_exists_section_is_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_with_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(event_with_cve_cvss_and_references)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Additional Information") != -1

    def test_cvss_exists_section_is_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_with_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(event_with_cve_cvss_and_references)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("CVSS V3 Information") != -1

    def test_reference_exists_section_is_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_gcp_jwm_params: ParamCreatorFn,
        event_with_cve_cvss_and_references: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_gcp_jwm_params(event_with_cve_cvss_and_references)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Reference Links") != -1


class TestHtmlNonGcpTemplateBusinessLogic:

    def test_event_shows_description(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        aws_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_html_params(aws_event)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Finding Description") != -1

    def test_non_description_sections_are_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        aws_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_html_params(aws_event)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") == -1
            and description.rfind("Finding Explanation") == -1
            and description.rfind("Exception Instructions") == -1
            and description.rfind("Recommended Steps") == -1
        )

    def test_event_shows_next_steps(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        aws_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_html_params(aws_event)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Next Steps") != -1

    def test_event_without_description_shown_na(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        aws_event: dict[str, str],
    ) -> None:
        del aws_event["description"]
        parameters: SingleJson = get_aws_html_params(aws_event)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Description") != -1
            and description.count(NOT_AVAILABLE) >= 1
        )

    def test_event_without_next_steps_shown_na(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        aws_event: dict[str, str],
    ) -> None:
        del aws_event["nextSteps"]
        parameters: SingleJson = get_aws_html_params(aws_event)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Next Steps") != -1
            and description.count(NOT_AVAILABLE) >= 1
        )

    def test_event_ciem_aws(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        aws_event_ciem: SingleJson,
    ) -> None:
        parameters: SingleJson = get_aws_html_params(aws_event_ciem)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Next Steps") != -1
            and description.count(NOT_AVAILABLE) >= 1
        )


class TestJwmNonGcpTemplateBusinessLogic:

    def test_event_shows_description(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        aws_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_jwm_params(aws_event)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Finding Description") != -1

    def test_non_description_sections_are_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        aws_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_jwm_params(aws_event)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") == -1
            and description.rfind("Finding Explanation") == -1
            and description.rfind("Exception Instructions") == -1
            and description.rfind("Recommended Steps") == -1
        )

    def test_event_shows_next_steps(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        aws_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_jwm_params(aws_event)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Next Steps") != -1

    def test_event_without_description_shown_na(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        aws_event: dict[str, str],
    ) -> None:
        del aws_event["description"]
        parameters: SingleJson = get_aws_jwm_params(aws_event)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Description") != -1
            and description.count(NOT_AVAILABLE) >= 1
        )

    def test_event_without_next_steps_shown_na(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        aws_event: dict[str, str],
    ) -> None:
        del aws_event["nextSteps"]
        parameters: SingleJson = get_aws_jwm_params(aws_event)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Next Steps") != -1
            and description.count(NOT_AVAILABLE) >= 1
        )

    def test_event_ciem_aws(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        aws_event_ciem: SingleJson,
    ) -> None:
        parameters: SingleJson = get_aws_jwm_params(aws_event_ciem)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Next Steps") != -1
            and description.count(NOT_AVAILABLE) >= 1
        )


class TestHtmlUndeterminedCloudProviderTemplateBusinessLogic:

    def test_event_shows_description(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        undetermined_cloud_provider_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_html_params(undetermined_cloud_provider_event)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Finding Description") != -1

    def test_non_description_sections_are_not_shown(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        undetermined_cloud_provider_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_html_params(undetermined_cloud_provider_event)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") == -1
            and description.rfind("Finding Explanation") == -1
            and description.rfind("Exception Instructions") == -1
            and description.rfind("Recommended Steps") == -1
        )

    def test_event_shows_next_steps(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        undetermined_cloud_provider_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_html_params(undetermined_cloud_provider_event)
        description: str = html_create_desc_fn(parameters)

        assert description.rfind("Next Steps") != -1

    def test_event_without_description_shown_na(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        undetermined_cloud_provider_event: dict[str, str],
    ) -> None:
        del undetermined_cloud_provider_event["description"]
        parameters: SingleJson = get_aws_html_params(undetermined_cloud_provider_event)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Description") != -1
            and description.count(NOT_AVAILABLE) >= 1
        )

    def test_event_without_next_steps_shown_na(
        self,
        html_create_desc_fn: CreateDescFn,
        get_aws_html_params: ParamCreatorFn,
        undetermined_cloud_provider_event: dict[str, str],
    ) -> None:
        del undetermined_cloud_provider_event["nextSteps"]
        parameters: SingleJson = get_aws_html_params(undetermined_cloud_provider_event)
        description: str = html_create_desc_fn(parameters)

        assert (
            description.rfind("Next Steps") != -1
            and description.count(NOT_AVAILABLE) >= 1
        )


class TestJwmUndeterminedCloudProviderTemplateBusinessLogic:

    def test_event_shows_description(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        undetermined_cloud_provider_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_jwm_params(undetermined_cloud_provider_event)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Finding Description") != -1

    def test_non_description_sections_are_not_shown(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        undetermined_cloud_provider_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_jwm_params(undetermined_cloud_provider_event)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Documentation") == -1
            and description.rfind("Finding Statement") == -1
            and description.rfind("Finding Mitigation") == -1
            and description.rfind("Finding Explanation") == -1
            and description.rfind("Exception Instructions") == -1
            and description.rfind("Recommended Steps") == -1
        )

    def test_event_shows_next_steps(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        undetermined_cloud_provider_event: dict[str, str],
    ) -> None:
        parameters: SingleJson = get_aws_jwm_params(undetermined_cloud_provider_event)
        description: str = jwm_create_desc_fn(parameters)

        assert description.rfind("Next Steps") != -1

    def test_event_without_description_shown_na(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        undetermined_cloud_provider_event: dict[str, str],
    ) -> None:
        del undetermined_cloud_provider_event["description"]
        parameters: SingleJson = get_aws_jwm_params(undetermined_cloud_provider_event)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Finding Description") != -1
            and description.count(NOT_AVAILABLE) >= 1
        )

    def test_event_without_next_steps_shown_na(
        self,
        jwm_create_desc_fn: CreateDescFn,
        get_aws_jwm_params: ParamCreatorFn,
        undetermined_cloud_provider_event: dict[str, str],
    ) -> None:
        del undetermined_cloud_provider_event["nextSteps"]
        parameters: SingleJson = get_aws_jwm_params(undetermined_cloud_provider_event)
        description: str = jwm_create_desc_fn(parameters)

        assert (
            description.rfind("Next Steps") != -1
            and description.count(NOT_AVAILABLE) >= 1
        )
