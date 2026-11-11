import copy
import re

from scc_enterprise.core.SCCEnterpriseUtils import (
    _get_html_severity,
    _get_jwm_severity,
    create_finding_page_link,
    create_gcp_jwm_table,
    create_html_table,
    create_jwm_table,
    create_non_gcp_html_table,
    create_gcp_html_table,
    create_non_gcp_jwm_table,
    create_resource_link,
    get_finding_value_by_key,
)

PLATFORM_URI = "https://localhost/"


class TestCreateHtmlTableFunction:
    def test_create_html_table_function_non_gcp_flow(
        self,
        single_non_gcp_finding_state_context
    ) -> None:
        expected_result = create_non_gcp_html_table(
            copy.deepcopy(single_non_gcp_finding_state_context),
            PLATFORM_URI,
        )
        result = create_html_table(
            single_non_gcp_finding_state_context,
            PLATFORM_URI,
        )

        assert result == expected_result

    def test_create_html_table_function_gcp_flow(
        self,
        single_gcp_finding_state_context
    ) -> None:
        expected_result = create_gcp_html_table(
            copy.deepcopy(single_gcp_finding_state_context),
            PLATFORM_URI,
        )
        result = create_html_table(
            single_gcp_finding_state_context,
            PLATFORM_URI,
        )

        assert result == expected_result


class TestCreateJwmTableFunction:
    def test_create_jwm_table_function_non_gcp_flow(
        self,
        single_non_gcp_finding_state_context
    ) -> None:
        expected_result = create_non_gcp_jwm_table(
            copy.deepcopy(single_non_gcp_finding_state_context),
            PLATFORM_URI,
        )
        result = create_jwm_table(
            single_non_gcp_finding_state_context,
            PLATFORM_URI,
        )

        assert result == expected_result

    def test_create_jwm_table_function_gcp_flow(
        self,
        single_gcp_finding_state_context
    ) -> None:
        expected_result = create_gcp_jwm_table(
            copy.deepcopy(single_gcp_finding_state_context),
            PLATFORM_URI,
        )
        result = create_jwm_table(
            single_gcp_finding_state_context,
            PLATFORM_URI,
        )

        assert result == expected_result


class TestCreateNonGcpHtmlTableFunction:
    def test_create_non_gcp_html_table(
        self,
        single_non_gcp_finding_state_context
    ) -> None:
        result = create_non_gcp_html_table(
            single_non_gcp_finding_state_context,
            PLATFORM_URI,
        )
        assert (
            result.rfind("<strong>Impacted Resources</strong>") != -1
            and re.search('<th .*>Resource Name</th>', result)
            and re.search('<th .*">Status</th>', result)
            and re.search('<th .*">Severity</th>', result)
            and re.search('<th .*">Related TCs</th>', result)
            and re.search('<th .*">Source</th>', result)
        )

    def test_create_non_gcp_html_table_columns(
        self,
        single_non_gcp_finding_state_context
    ) -> None:
        result = create_non_gcp_html_table(
            single_non_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_non_gcp_finding_state_context[0]
        column_pattern = "<td>(?s:.)*{}(?s:.)*</td>"

        assert (
            re.search(column_pattern.format(item.resource_name), result)
            and re.search(column_pattern.format(item.severity.capitalize()), result)
            and re.search(column_pattern.format(item.status), result)
            and re.search(column_pattern.format("Explore"), result)
            and re.search(column_pattern.format(item.tc_count), result)
        )

    def test_create_non_gcp_html_table_finding_link(
        self,
        single_non_gcp_finding_state_context
    ) -> None:
        result = create_non_gcp_html_table(
            single_non_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_non_gcp_finding_state_context[0]

        finding_link = create_finding_page_link(
            finding_name=item.finding_id,
            chronicle_soar_platform_url=PLATFORM_URI,
        )

        assert result.rfind(finding_link) != -1

    def test_create_non_gcp_html_table_severity(
        self,
        single_non_gcp_finding_state_context
    ) -> None:
        result = create_non_gcp_html_table(
            single_non_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_non_gcp_finding_state_context[0]
        severity_html = _get_html_severity(item.severity)

        assert result.rfind(severity_html) != -1


class TestCreateGcpHtmlTableFunction:
    def test_create_gcp_html_table(
            self,
            single_gcp_finding_state_context
    ) -> None:
        result = create_gcp_html_table(
            single_gcp_finding_state_context,
            PLATFORM_URI,
        )

        assert (
            result.rfind("<strong>Impacted Resources</strong>") != -1
            and re.search('<th .*>Resource Name</th>', result)
            and re.search('<th .*">Status</th>', result)
            and re.search('<th .*">Severity</th>', result)
            and re.search('<th .*">Related TCs</th>', result)
            and re.search('<th .*">Source</th>', result)
        )

    def test_create_gcp_html_table_columns(
            self,
            single_gcp_finding_state_context
    ) -> None:
        result = create_gcp_html_table(
            single_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_gcp_finding_state_context[0]
        resource_link = create_resource_link(
            item.resource_name,
            PLATFORM_URI,
        )
        column_pattern = "<td>(?s:.)*{}(?s:.)*</td>"

        assert (
            result.rfind(resource_link) != -1
            and re.search(column_pattern.format(item.resource_name), result)
            and re.search(column_pattern.format(item.severity.capitalize()), result)
            and re.search(column_pattern.format(item.status), result)
            and re.search(column_pattern.format("Explore"), result)
            and re.search(column_pattern.format(item.tc_count), result)
        )

    def test_create_gcp_html_table_finding_link(
            self,
            single_gcp_finding_state_context
    ) -> None:
        result = create_gcp_html_table(
            single_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_gcp_finding_state_context[0]

        organization_id = get_finding_value_by_key(
            item.finding_id,
            key="organizations",
        )
        finding_link = create_finding_page_link(
            finding_name=item.finding_id,
            chronicle_soar_platform_url=PLATFORM_URI,
        )

        assert result.rfind(finding_link) != -1

    def test_create_gcp_html_table_severity(
            self,
            single_gcp_finding_state_context
    ) -> None:
        result = create_gcp_html_table(
            single_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_gcp_finding_state_context[0]
        severity_html = _get_html_severity(item.severity)

        assert result.rfind(severity_html) != -1


class TestCreateNonGcpJwmTableFunction:
    def test_create_non_gcp_jwm_table(
        self,
        single_non_gcp_finding_state_context
    ) -> None:
        result = create_non_gcp_jwm_table(
            single_non_gcp_finding_state_context,
            PLATFORM_URI,
        )

        assert (
            result.rfind("Resource Name") != -1
            and result.rfind("Status") != -1
            and result.rfind("Severity") != -1
            and result.rfind("Related TCs") != -1
            and result.rfind("Source") != -1
        )

    def test_create_non_gcp_jwm_table_columns(
        self,
        single_non_gcp_finding_state_context
    ) -> None:
        result = create_non_gcp_jwm_table(
            single_non_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_non_gcp_finding_state_context[0]

        assert (
            result.rfind(item.resource_name) != -1
            and result.rfind(item.severity.capitalize()) != -1
            and result.rfind(item.status) != -1
            and result.rfind("Source") != -1
            and result.rfind(str(item.tc_count)) != -1
        )

    def test_create_non_gcp_jwm_table_finding_link(
        self,
        single_non_gcp_finding_state_context
    ) -> None:
        result = create_non_gcp_jwm_table(
            single_non_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_non_gcp_finding_state_context[0]

        finding_link = create_finding_page_link(
            finding_name=item.finding_id,
            chronicle_soar_platform_url=PLATFORM_URI,
        )

        assert result.rfind(finding_link) != -1

    def test_create_non_gcp_jwm_table_severity(
        self,
        single_non_gcp_finding_state_context
    ) -> None:
        result = create_non_gcp_jwm_table(
            single_non_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_non_gcp_finding_state_context[0]
        severity_html = _get_jwm_severity(item.severity)

        assert result.rfind(severity_html) != -1


class TestCreateGcpJwmTableFunction:
    def test_create_gcp_jwm_table(
        self,
        single_gcp_finding_state_context
    ) -> None:
        result = create_gcp_jwm_table(
            single_gcp_finding_state_context,
            PLATFORM_URI,
        )

        assert (
            result.rfind("Resource Name") != -1
            and result.rfind("Status") != -1
            and result.rfind("Severity") != -1
            and result.rfind("Related TCs") != -1
            and result.rfind("Source") != -1
        )

    def test_create_gcp_jwm_table_columns(
        self,
        single_gcp_finding_state_context
    ) -> None:
        result = create_gcp_jwm_table(
            single_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_gcp_finding_state_context[0]
        resource_link = create_resource_link(
            item.resource_name,
            PLATFORM_URI,
        )

        assert (
            result.rfind(resource_link) != -1
            and result.rfind(item.resource_name) != -1
            and result.rfind(item.severity.capitalize()) != -1
            and result.rfind(item.status) != -1
            and result.rfind("Source") != -1
            and result.rfind(str(item.tc_count)) != -1
        )

    def test_create_gcp_jwm_table_finding_link(
        self,
        single_gcp_finding_state_context
    ) -> None:
        result = create_gcp_jwm_table(
            single_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_gcp_finding_state_context[0]

        finding_link = create_finding_page_link(
            finding_name=item.finding_id,
            chronicle_soar_platform_url=PLATFORM_URI,
        )

        assert result.rfind(finding_link) != -1

    def test_create_gcp_jwm_table_severity(
        self,
        single_gcp_finding_state_context
    ) -> None:
        result = create_gcp_jwm_table(
            single_gcp_finding_state_context,
            PLATFORM_URI,
        )
        item = single_gcp_finding_state_context[0]
        severity_html = _get_jwm_severity(item.severity)

        assert result.rfind(severity_html) != -1
