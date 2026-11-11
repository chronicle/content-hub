from __future__ import annotations

import re

import bs4

from scc_enterprise.core.SCCEnterpriseConsts import (
    BACKTICK_WRAPPED_REGEXP,
    CODE_BLOCK_DOUBLE_NL,
    CODE_BLOCK_STYLE,
    CODE_TICK_WRAPPED_REGEXP,
    MD_ORDERED_LIST,
    MD_STRONG_REGEXP,
    NESTED_ORDERED_LIST_REGEXP,
    NESTED_UNORDERED_LIST_REGEXP,
    TWO_INDENT_NESTED_ORDERED_LIST_REGEXP,
    TWO_INDENT_NESTED_UNORDERED_LIST_REGEXP,
    TWO_STAR_WRAPPED_REGEXP,
    URL_REGEXP,
)
from scc_enterprise.core.SCCEnterpriseDescParams import (
    CloudProviderEnum,
    DescriptionOutputType,
    DescriptionParamsCreator,
    GCP_EVENT_KEYS,
    HtmlMarkdownParser,
    JwmMarkdownParser,
    NON_GCP_EVENT_KEYS,
    ParseStringFn,
    get_desc_parameter_creator,
)
from TIPCommon.types import SingleJson
from scc_enterprise.tests.test_description.conftest import ParamCreatorFn


DESCRIPTION_BASED_PARAMS: tuple[str, str, str] = (
    "documentation",
    "statement",
    "mitigation",
)


class TestGetDescriptionParameterCreator:

    def test_create_gcp_html_template_params_does_not_fail(self) -> None:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            cloud_provider=CloudProviderEnum.GCP,
            output_type=DescriptionOutputType.HTML,
            event_data={},
        )

        assert param_creator.key_map == GCP_EVENT_KEYS

    def test_create_gcp_jwm_template_params_does_not_fail(self) -> None:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            cloud_provider=CloudProviderEnum.GCP,
            output_type=DescriptionOutputType.JWM,
            event_data={},
        )

        assert param_creator.key_map == GCP_EVENT_KEYS

    def test_create_aws_html_template_params_does_not_fail(self) -> None:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            cloud_provider=CloudProviderEnum.AWS,
            output_type=DescriptionOutputType.HTML,
            event_data={},
        )

        assert param_creator.key_map == NON_GCP_EVENT_KEYS

    def test_create_aws_jwm_template_params_does_not_fail(self) -> None:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            cloud_provider=CloudProviderEnum.AWS,
            output_type=DescriptionOutputType.JWM,
            event_data={},
        )

        assert param_creator.key_map == NON_GCP_EVENT_KEYS

    def test_create_azure_html_template_params_does_not_fail(self) -> None:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            cloud_provider=CloudProviderEnum.AZURE,
            output_type=DescriptionOutputType.HTML,
            event_data={},
        )

        assert param_creator.key_map == NON_GCP_EVENT_KEYS

    def test_create_azure_jwm_template_params_does_not_fail(self) -> None:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            cloud_provider=CloudProviderEnum.AZURE,
            output_type=DescriptionOutputType.JWM,
            event_data={},
        )

        assert param_creator.key_map == NON_GCP_EVENT_KEYS

    def test_create_other_html_template_params_does_not_fail(self) -> None:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            cloud_provider=CloudProviderEnum.OTHER,
            output_type=DescriptionOutputType.HTML,
            event_data={},
        )

        assert param_creator.key_map == NON_GCP_EVENT_KEYS

    def test_create_other_jwm_template_params_does_not_fail(self) -> None:
        param_creator: DescriptionParamsCreator = get_desc_parameter_creator(
            cloud_provider=CloudProviderEnum.OTHER,
            output_type=DescriptionOutputType.JWM,
            event_data={},
        )

        assert param_creator.key_map == NON_GCP_EVENT_KEYS


class TestHtmlMarkdownParsing:

    def test_links_are_wrapped_with_a_href(self) -> None:
        link: str = "https://www.google.com"
        parser: HtmlMarkdownParser = HtmlMarkdownParser(link)

        result: str = parser.anchor_links_in_string().value
        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(result, features="html.parser")
        anchor: bs4.element.Tag = soup.a
        href: str = anchor["href"]

        assert (
            anchor
            and link == href
            and result.count("href") == 1
            and anchor.contents[0] == link
        )

    def test_links_wrapped_with_parenthesis_work(self) -> None:
        link: str = "https://www.google.com"
        paren_link = f"({link})"
        parser: HtmlMarkdownParser = HtmlMarkdownParser(paren_link)

        result: str = parser.anchor_links_in_string().value
        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(result, features="html.parser")
        anchor: bs4.element.Tag = soup.a
        href: str = anchor["href"]
        print(result)

        assert (
            anchor
            and link == href
            and result.count("href") == 1
            and anchor.contents[0] == link
            and result.startswith("(")
            and result.endswith(")")
        )

    def test_markdown_hyperlinks_are_transformed(self) -> None:
        content: str = "instructions to upgrade your NodePool"
        link: str = (
            "https://cloud.google.com/kubernetes-engine/docs/how-to/upgrading-a-cluster"
            "#upgrading-nodes"
        )
        md_link: str = f"[{content}]({link})"
        parser: HtmlMarkdownParser = HtmlMarkdownParser(md_link)

        result: str = parser.replace_md_hyperlinks_with_regular_link().value

        assert result == f"{content} ({link})"

    def test_markdown_hyperlinks_where_text_is_url_are_not_transformed(self) -> None:
        content: str = (
            "https://cloud.google.com/kubernetes-engine/docs/how-to/upgrading-a-cluster"
            "#upgrading-nodes"
        )
        link: str = content
        md_link: str = f"[{content}]({link})"
        parser: HtmlMarkdownParser = HtmlMarkdownParser(md_link)

        result: str = parser.replace_md_hyperlinks_with_regular_link().value

        assert result == f"{content}"

    def test_ordered_lists_items_are_not_in_a_p_tag(self) -> None:
        parser: HtmlMarkdownParser = HtmlMarkdownParser(
            "1. <p><a>a</a></p>\n2. <p><b></b></p>\n3. <p>c</p>\n"
        )

        result: str = (
            parser.parse_markdown_to_html().remove_p_from_ordered_list_items().value
        )
        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(result, features="html.parser")
        ordered_list: bs4.element.Tag = soup.ol
        list_item: bs4.element.Tag = ordered_list.find("li")

        assert not list_item.find("p")

    def test_unordered_lists_items_are_not_in_a_p_tag(self) -> None:
        parser: HtmlMarkdownParser = HtmlMarkdownParser("* <p>a</p>")

        result: str = (
            parser.parse_markdown_to_html().remove_p_from_unordered_list_items().value
        )
        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(result, features="html.parser")
        unordered_list: bs4.element.Tag = soup.ul
        list_item: bs4.element.Tag = unordered_list.find("li")

        assert not list_item.find("p")

    def test_non_p_tags_in_ordered_lists_are_not_removed(self) -> None:
        parser: HtmlMarkdownParser = HtmlMarkdownParser("1. <p><a>a</a></p>")

        result: str = (
            parser.parse_markdown_to_html().remove_p_from_ordered_list_items().value
        )
        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(result, features="html.parser")
        ordered_list: bs4.element.Tag = soup.ol
        list_item: bs4.element.Tag = ordered_list.find("li")

        assert list_item.find("a")

    def test_nested_unordered_list_with_2_space_indent_transformed_to_4(self) -> None:
        parser: HtmlMarkdownParser = HtmlMarkdownParser("* part one\n  * part two")

        result: str = parser.change_unordered_nested_list_2_indent_to_4().value

        assert result == "* part one\n    * part two"

    def test_nested_ordered_list_with_2_space_indent_transformed_to_4(self) -> None:
        parser: HtmlMarkdownParser = HtmlMarkdownParser("1. part one\n  1. part two")

        result: str = parser.change_ordered_nested_list_2_indent_to_4().value

        assert result == "1. part one\n    1. part two"

    def test_non_p_tags_in_unordered_lists_are_not_removed(self) -> None:
        parser: HtmlMarkdownParser = HtmlMarkdownParser("* <p><a>a</a></p>")

        result: str = (
            parser.parse_markdown_to_html().remove_p_from_ordered_list_items().value
        )
        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(result, features="html.parser")
        ordered_list: bs4.element.Tag = soup.ul
        list_item: bs4.element.Tag = ordered_list.find("li")

        assert list_item.find("a")

    def test_markdown_bold_is_replaced_with_b(self) -> None:
        content: str = "bold content"
        parser: HtmlMarkdownParser = HtmlMarkdownParser(f"a**{content}**a")

        result: str = parser.transform_md_bold_to_html_b().value
        soup: bs4.BeautifulSoup = bs4.BeautifulSoup(result, features="html.parser")
        b_content: bs4.PageElement = soup.find("b").contents[0]

        assert (
            re.match(TWO_STAR_WRAPPED_REGEXP, result) is None and content == b_content
        )

    def test_markdown_code_block_style_is_removed(self) -> None:
        parser: HtmlMarkdownParser = HtmlMarkdownParser("```specifier\ncd content\n```")

        result: str = parser.remove_md_code_block_style().value

        assert (
            re.match(CODE_BLOCK_STYLE, result) is None
            and result.find("specifier") == -1
            and result.find("```\ncd content\n```") != -1
        )

    def test_markdown_change_double_new_lines_in_code_blocks_to_one_new_line(
        self,
    ) -> None:
        parser: HtmlMarkdownParser = HtmlMarkdownParser("```a\nHello\n\nWorld\n\n```")

        result: str = parser.remove_double_new_line_in_code_block().value

        assert (
            re.match(CODE_BLOCK_DOUBLE_NL, result) is None
            and result.find("```a\nHello\nWorld\n```") != -1
        )

    def test_markdown_line_breaks_in_code_blocks_are_changed_to_br(self) -> None:
        parser: HtmlMarkdownParser = HtmlMarkdownParser(
            "<code>Hello\nWorld\n!\n</code>"
        )

        result: str = parser.replace_new_line_with_br_in_code_blocks().value

        assert (
            result.find("\n") == -1
            and result.find("<code>Hello<br />World<br />!") != -1
        )

    def test_markdown_strong_is_removed(self) -> None:
        parser: HtmlMarkdownParser = HtmlMarkdownParser(
            "__some__ a __strong__ a __value__"
        )

        result: str = parser.remove_markdown_strong().value

        assert (
            result.find("_") == -1
            and result.find(
                '<b style="font-size: 11pt">some</b> a '
                '<b style="font-size: 11pt">strong</b> a '
                '<b style="font-size: 11pt">value</b>'
            )
            != -1
        )

    def test_all_markdown_processed_together(
        self,
        parse_markdown_to_html: ParseStringFn,
    ) -> None:
        result: str = parse_markdown_to_html(
            "```shell\nHello\n\nWorld\n!\n``` **content** __st__ "
            "[instructions to upgrade your NodePool](https://cloud.google.com/"
            "kubernetes-engine/docs/how-to/upgrading-a-cluster#upgrading-nodes)\n\n"
            "* list item\n  * nested list item\n\n1. list item\n  1. nested list item\n"
        )

        assert re.match(URL_REGEXP, result) is None
        assert re.match(TWO_STAR_WRAPPED_REGEXP, result) is None
        assert re.match(CODE_BLOCK_STYLE, result) is None
        assert re.match(CODE_BLOCK_DOUBLE_NL, result) is None
        assert re.match(MD_STRONG_REGEXP, result) is None
        assert re.match(TWO_INDENT_NESTED_ORDERED_LIST_REGEXP, result) is None
        assert re.match(TWO_INDENT_NESTED_UNORDERED_LIST_REGEXP, result) is None
        assert result.find("shell") == -1
        assert result.count("href=") == 1
        assert result.count("<ul>") == 2


class TestJwmMarkdownParsing:

    def test_double_start_is_replaced(self) -> None:
        parser: JwmMarkdownParser = JwmMarkdownParser("a**bold**a")

        result: str = parser.transform_md_bold_to_jwm().value

        assert result == "a*bold*a"

    def test_md_hyperlinks_are_transformed_to_jwm(self) -> None:
        content: str = "Some text"
        link: str = (
            "https://cloud.google.com/kubernetes-engine/docs/how-to/upgrading-a-cluster"
            "#upgrading-nodes"
        )
        md_link: str = f"[{content}]({link})"
        parser: JwmMarkdownParser = JwmMarkdownParser(md_link)

        result: str = parser.transform_md_hyperlinks_to_jwm().value

        assert result == f"[{content}|{link}]"

    def test_markdown_nested_unordered_list_transformed_to_jwm(self) -> None:
        parser: JwmMarkdownParser = JwmMarkdownParser(
            "* regular list\n  * nested list\n"
        )

        result: str = parser.transform_nested_unordered_list_to_jwm_list().value

        assert re.match(NESTED_UNORDERED_LIST_REGEXP, result) is None
        assert result == "* regular list\n** nested list\n"

    def test_markdown_nested_ordered_list_transformed_to_jwm(self) -> None:
        parser: JwmMarkdownParser = JwmMarkdownParser(
            "# regular list\n  # nested list\n"
        )

        result: str = parser.transform_nested_ordered_list_to_jwm_list().value

        assert re.match(NESTED_ORDERED_LIST_REGEXP, result) is None
        assert result == "# regular list\n## nested list\n"

    def test_markdown_ordered_list_transformed_to_jwm(self) -> None:
        parser: JwmMarkdownParser = JwmMarkdownParser(
            "some text\n\n1. item one\n2. item two\n  1. nested\n\ntext"
        )

        result: str = parser.transform_ordered_lists_to_jwm().value

        assert re.match(MD_ORDERED_LIST, result) is None
        assert result == "some text\n\n# item one\n# item two\n  # nested\n\ntext"

    def test_markdown_code_block_style_is_removed(self) -> None:
        parser: JwmMarkdownParser = JwmMarkdownParser("```specifier\ncd content\n```")

        result: str = parser.remove_md_code_block_style().value

        assert re.match(CODE_BLOCK_STYLE, result) is None
        assert result.find("specifier") == -1
        assert result.find("```\ncd content\n```") != -1

    def test_markdown_code_block_transformed_to_jwm(self) -> None:
        parser: JwmMarkdownParser = JwmMarkdownParser("```\nsome code\n```")

        result: str = parser.transform_code_to_jwm_code().value

        assert re.match(CODE_TICK_WRAPPED_REGEXP, result) is None
        assert result == "{code:shell}\nsome code\n{code}"

    def test_backtick_is_replaced_with_jwm_mono(self) -> None:
        parser: JwmMarkdownParser = JwmMarkdownParser("`some code`")

        result: str = parser.transform_backtick_to_jwm_mono().value

        assert re.match(BACKTICK_WRAPPED_REGEXP, result) is None
        assert result == "{{some code}}"

    def test_md_strong_is_replaced_with_jwm_bold(self) -> None:
        parser: JwmMarkdownParser = JwmMarkdownParser("__strong__")

        result: str = parser.replace_md_strong_with_jwm_bold().value

        assert re.match(BACKTICK_WRAPPED_REGEXP, result) is None
        assert result == "*strong*"

    def test_all_markdown_processed_together(
        self,
        parse_markdown_to_jwm: ParseStringFn,
    ) -> None:
        result: str = parse_markdown_to_jwm(
            "```python\nHello World\n``` **bold** `code`\n\n* regular\n  * nested\n\n"
            "[content](https://www.link.com)\n\n1. regular\n  2. nested\n\n"
        )

        assert re.match(TWO_STAR_WRAPPED_REGEXP, result) is None
        assert re.match(NESTED_UNORDERED_LIST_REGEXP, result) is None
        assert re.match(NESTED_ORDERED_LIST_REGEXP, result) is None
        assert re.match(MD_ORDERED_LIST, result) is None
        assert re.match(CODE_BLOCK_STYLE, result) is None
        assert re.match(CODE_TICK_WRAPPED_REGEXP, result) is None
        assert re.match(BACKTICK_WRAPPED_REGEXP, result) is None
        assert result.find("python") == -1
        assert result.find("{code:shell}\nHello World\n{code}") != -1
        assert result.find("{{code}}") != -1
        assert result.find("[content|https://www.link.com]") != -1


class TestGcpHtmlParameters:

    def test_non_markdown_parameter_default_value(
        self,
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params({})

        for k, v in params.items():
            if k not in GCP_EVENT_KEYS:
                continue

            param_details: SingleJson = GCP_EVENT_KEYS[k]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if not is_markdown:
                assert default_value == v

    def test_markdown_parameter_default_value(
        self,
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params({})

        for name, value in params.items():
            if name not in GCP_EVENT_KEYS:
                continue

            param_details: SingleJson = GCP_EVENT_KEYS[name]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if is_markdown:
                assert isinstance(value, str) and value.find(default_value) != -1

    def test_non_md_event_based_param_values_are_extracted_correctly(
        self,
        event_keys_and_values: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params(event_keys_and_values)

        for param_name, param_details in GCP_EVENT_KEYS.items():
            should_skip: bool = param_details.get("markdown", False)
            if should_skip:
                continue

            param_key: str = param_details["key"]
            event_value: str = event_keys_and_values.get(param_key)
            assert params[param_name] == event_value

    def test_markdown_event_based_param_values_are_extracted_from_event_correctly(
        self,
        event_keys_and_values: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params(event_keys_and_values)

        for param_name, param_details in GCP_EVENT_KEYS.items():
            if not param_details.get("markdown", False):
                continue

            param_value: str = params[param_name]
            assert isinstance(param_value, str) and param_value

    def test_links_are_parsed_successfully_in_event_keys(
        self,
        event_keys_and_link_values: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params(event_keys_and_link_values)

        for param_name, parsed_link in params.items():
            key: str = GCP_EVENT_KEYS.get(param_name, {}).get("key")
            if not parsed_link or key is None:
                continue

            event_link: str = event_keys_and_link_values[key]
            pattern: str = (
                rf'<a( class="[\w -]+")? href="{event_link}" '
                rf'target="_blank">{event_link}</a>'
            )

            assert re.search(pattern, parsed_link) is not None

    def test_desc_based_param_default_value(
        self,
        event_without_source_properties: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params(event_without_source_properties)

        for param_name in DESCRIPTION_BASED_PARAMS:
            assert params[param_name] == ""

    def test_desc_based_params_values_are_extracted_correctly(
        self,
        event_without_source_properties: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        event_without_source_properties[
            "description"
        ]: str = "DOCUMENTATION:d STATEMENT:s MITIGATION:m"
        params: SingleJson = get_gcp_html_params(event_without_source_properties)

        assert (
            params["documentation"] == "d"
            and params["statement"] == "s"
            and params["mitigation"] == "m"
        )

    def test_cve_default_values(
        self,
        event_without_source_properties: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params(event_without_source_properties)

        assert params["cve"] == {}

    def test_cve_are_extracted_correctly(
        self,
        event_without_source_properties: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params(event_without_source_properties)

        assert params["cve"] == {}

    def test_references_default_values(
        self,
        event_without_source_properties: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params(event_without_source_properties)

        assert params["references"] == []

    def test_references_are_extracted_correctly(
        self,
        event_with_cve_cvss_and_references: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params(event_with_cve_cvss_and_references)

        references: list[dict[str, str]] = params["references"]

        assert isinstance(references, list)
        for reference in references:
            assert (
                isinstance(reference, dict)
                and "uri" in reference
                and "source" in reference
                and isinstance(reference["uri"], str)
                and isinstance(reference["source"], str)
                and reference["uri"]
                and reference["source"]
            )

    def test_cve_map_are_extracted_correctly(
        self,
        event_with_cve_cvss_and_references: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params(event_with_cve_cvss_and_references)

        cve_map: dict[str, str] = params["cve"]

        assert isinstance(cve_map, dict)
        for cve_name, cve_value in cve_map.items():
            assert (
                isinstance(cve_name, str)
                and isinstance(cve_value, str)
                and cve_name
                and cve_value
            )

    def test_cvss_map_are_extracted_correctly(
        self,
        event_with_cve_cvss_and_references: dict[str, str],
        get_gcp_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_html_params(event_with_cve_cvss_and_references)

        cve_map: dict[str, str] = params["cve"]

        assert isinstance(cve_map, dict)
        for cve_name, cve_value in cve_map.items():
            assert (
                isinstance(cve_name, str)
                and isinstance(cve_value, str)
                and cve_name
                and cve_value
            )


class TestGcpJwmParameters:

    def test_non_markdown_parameter_default_value(
        self,
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params({})

        for k, v in params.items():
            if k not in GCP_EVENT_KEYS:
                continue

            param_details: SingleJson = GCP_EVENT_KEYS[k]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)

            if not is_markdown:
                assert default_value == v

    def test_markdown_parameter_default_value(
        self,
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params({})

        for name, value in params.items():
            if name not in GCP_EVENT_KEYS:
                continue

            param_details: SingleJson = GCP_EVENT_KEYS[name]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if is_markdown:
                assert isinstance(value, str) and value.find(default_value) != -1

    def test_non_md_event_based_param_values_are_extracted_correctly(
        self,
        event_keys_and_values: SingleJson,
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params(event_keys_and_values)

        for param_name, param_details in GCP_EVENT_KEYS.items():
            should_skip: bool = param_details.get("markdown", False)
            if should_skip:
                continue

            param_key: str = param_details["key"]
            event_value: str = event_keys_and_values.get(param_key)
            assert params[param_name] == event_value

    def test_markdown_event_based_param_values_are_extracted_from_event_correctly(
        self,
        event_keys_and_values: SingleJson,
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params(event_keys_and_values)

        for param_name, param_details in GCP_EVENT_KEYS.items():
            if not param_details.get("markdown", False):
                continue

            param_value: str = params[param_name]
            assert isinstance(param_value, str) and param_value

    def test_links_are_parsed_successfully_in_event_keys(
        self,
        event_keys_and_link_values: dict[str, str],
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params(event_keys_and_link_values)

        for param_name, parsed_link in params.items():
            key: str = GCP_EVENT_KEYS.get(param_name, {}).get("key")
            if not parsed_link or key is None:
                continue

            event_link: str = event_keys_and_link_values[key]
            pattern: str = (
                rf'<a( class="[\w -]+")? href="{event_link}" '
                rf'target="_blank">{event_link}</a>'
            )

            assert re.search(pattern, parsed_link) is not None

    def test_desc_based_param_default_value(
        self,
        event_without_source_properties: dict[str, str],
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params(event_without_source_properties)

        for param_name in DESCRIPTION_BASED_PARAMS:
            assert params[param_name] == ""

    def test_desc_based_params_values_are_extracted_correctly(
        self,
        event_without_source_properties: dict[str, str],
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        event_without_source_properties[
            "description"
        ]: str = "DOCUMENTATION:d STATEMENT:s MITIGATION:m"
        params: SingleJson = get_gcp_jwm_params(event_without_source_properties)

        assert (
            params["documentation"] == "d"
            and params["statement"] == "s"
            and params["mitigation"] == "m"
        )

    def test_references_default_values(
        self,
        event_without_source_properties: dict[str, str],
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params(event_without_source_properties)

        assert params["references"] == []

    def test_cve_default_values(
        self,
        event_without_source_properties: dict[str, str],
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params(event_without_source_properties)

        assert params["cve"] == {}

    def test_cve_are_extracted_correctly(
        self,
        event_without_source_properties: dict[str, str],
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params(event_without_source_properties)

        assert params["cve"] == {}

    def test_references_are_extracted_correctly(
        self,
        event_with_cve_cvss_and_references: dict[str, str],
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params(event_with_cve_cvss_and_references)

        references: list[dict[str, str]] = params["references"]

        assert isinstance(references, list)
        for reference in references:
            assert (
                isinstance(reference, dict)
                and "uri" in reference
                and "source" in reference
                and isinstance(reference["uri"], str)
                and isinstance(reference["source"], str)
                and reference["uri"]
                and reference["source"]
            )

    def test_cve_map_are_extracted_correctly(
        self,
        event_with_cve_cvss_and_references: dict[str, str],
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params(event_with_cve_cvss_and_references)

        cve_map: dict[str, str] = params["cve"]

        assert isinstance(cve_map, dict)
        for cve_name, cve_value in cve_map.items():
            assert (
                isinstance(cve_name, str)
                and isinstance(cve_value, str)
                and cve_name
                and cve_value
            )

    def test_cvss_map_are_extracted_correctly(
        self,
        event_with_cve_cvss_and_references: dict[str, str],
        get_gcp_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_gcp_jwm_params(event_with_cve_cvss_and_references)

        cve_map: dict[str, str] = params["cve"]

        assert isinstance(cve_map, dict)
        for cve_name, cve_value in cve_map.items():
            assert (
                isinstance(cve_name, str)
                and isinstance(cve_value, str)
                and cve_name
                and cve_value
            )


class TestAwsHtmlParameters:

    def test_non_markdown_parameter_default_value(
        self,
        get_aws_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_aws_html_params({})

        for k, v in params.items():
            if k not in NON_GCP_EVENT_KEYS:
                continue

            param_details: dict[str, str] = NON_GCP_EVENT_KEYS[k]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if not is_markdown:
                assert default_value == v

    def test_markdown_parameter_default_value(
        self,
        get_aws_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_aws_html_params({})

        for name, value in params.items():
            if name not in NON_GCP_EVENT_KEYS:
                continue

            param_details: dict[str, str] = NON_GCP_EVENT_KEYS[name]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if is_markdown:
                assert isinstance(value, str) and value.find(default_value) != -1

    def test_non_md_event_based_param_values_are_extracted_correctly(
        self,
        event_keys_and_values: SingleJson,
        get_aws_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_aws_html_params(event_keys_and_values)

        for param_name, param_details in NON_GCP_EVENT_KEYS.items():
            should_skip: bool = param_details.get("markdown", False)
            if should_skip:
                continue

            param_key: str = param_details["key"]
            event_value: str = event_keys_and_values.get(param_key)
            assert params[param_name] == event_value

    def test_md_event_based_param_values_are_extracted_from_event_correctly(
        self,
        event_keys_and_values: SingleJson,
        get_aws_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_aws_html_params(event_keys_and_values)

        for param_name, param_details in NON_GCP_EVENT_KEYS.items():
            if not param_details.get("markdown", False):
                continue

            param_value: str = params[param_name]
            assert isinstance(param_value, str) and param_value

    def test_links_are_parsed_successfully_in_event_keys(
        self,
        event_keys_and_link_values: dict[str, str],
        get_aws_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_aws_html_params(event_keys_and_link_values)

        for param_name, parsed_link in params.items():
            key: str = GCP_EVENT_KEYS.get(param_name, {}).get("key")
            if not parsed_link or key is None:
                continue

            event_link: str = event_keys_and_link_values[key]
            pattern: str = (
                rf'<a( class="[\w -]+")? href="{event_link}" '
                rf'target="_blank">{event_link}</a>'
            )

            assert re.search(pattern, parsed_link) is not None


class TestAwsJwmParameters:

    def test_non_markdown_parameter_default_value(
        self,
        get_aws_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_aws_jwm_params({})

        for k, v in params.items():
            if k not in NON_GCP_EVENT_KEYS:
                continue

            param_details: dict[str, str] = NON_GCP_EVENT_KEYS[k]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if not is_markdown:
                assert default_value == v

    def test_markdown_parameter_default_value(
        self,
        get_aws_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_aws_jwm_params({})

        for name, value in params.items():
            if name not in NON_GCP_EVENT_KEYS:
                continue

            param_details: dict[str, str] = NON_GCP_EVENT_KEYS[name]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if is_markdown:
                assert isinstance(value, str) and value.find(default_value) != -1

    def test_non_md_event_based_param_values_are_extracted_correctly(
        self,
        event_keys_and_values: SingleJson,
        get_aws_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_aws_jwm_params(event_keys_and_values)

        for param_name, param_details in NON_GCP_EVENT_KEYS.items():
            should_skip: bool = param_details.get("markdown", False)
            if should_skip:
                continue

            param_key: str = param_details["key"]
            event_value: str = event_keys_and_values.get(param_key)
            assert params[param_name] == event_value

    def test_markdown_event_based_param_values_are_extracted_from_event_correctly(
        self,
        event_keys_and_values: SingleJson,
        get_aws_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_aws_jwm_params(event_keys_and_values)

        for param_name, param_details in NON_GCP_EVENT_KEYS.items():
            if not param_details.get("markdown", False):
                continue

            param_value: str = params[param_name]
            assert isinstance(param_value, str) and param_value


class TestAzureHtmlParameters:

    def test_non_markdown_parameter_default_value(
        self,
        get_azure_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_azure_html_params({})

        for k, v in params.items():
            if k not in NON_GCP_EVENT_KEYS:
                continue

            param_details: dict[str, str] = NON_GCP_EVENT_KEYS[k]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if not is_markdown:
                assert default_value == v


class TestAzureJwmParameters:

    def test_non_markdown_parameter_default_value(
        self,
        get_azure_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_azure_jwm_params({})

        for k, v in params.items():
            if k not in NON_GCP_EVENT_KEYS:
                continue

            param_details: dict[str, str] = NON_GCP_EVENT_KEYS[k]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if not is_markdown:
                assert default_value == v


class TestOtherHtmlParameters:

    def test_non_markdown_parameter_default_value(
        self,
        get_other_html_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_other_html_params({})

        for k, v in params.items():
            if k not in NON_GCP_EVENT_KEYS:
                continue

            param_details: dict[str, str] = NON_GCP_EVENT_KEYS[k]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if not is_markdown:
                assert default_value == v


class TestOtherJwmParameters:

    def test_non_markdown_parameter_default_value(
        self,
        get_other_jwm_params: ParamCreatorFn,
    ) -> None:
        params: SingleJson = get_other_jwm_params({})

        for k, v in params.items():
            if k not in NON_GCP_EVENT_KEYS:
                continue

            param_details: dict[str, str] = NON_GCP_EVENT_KEYS[k]
            default_value: str = param_details.get("default", "")
            is_markdown: bool = param_details.get("markdown", False)
            if not is_markdown:
                assert default_value == v
