from __future__ import annotations

import copy
import re
from typing import Callable, Dict, List, Union

import bs4
import markdown

import TIPCommon.transformation
from TIPCommon.types import SingleJson
from scc_enterprise.core import SCCEnterpriseConsts
from scc_enterprise.core.SCCEnterpriseDatamodels import CloudProviderEnum, DescriptionOutputType


KeyMap = Dict[str, Dict[str, Union[str, bool]]]
ReferenceList = List[Dict[str, str]]
ParseStringFn = Callable[[str], str]

GCP_EVENT_KEYS: KeyMap = {
    "description": {
        "key": "description",
        "default": SCCEnterpriseConsts.NOT_AVAILABLE,
        "markdown": True,
    },
    "next_steps": {
        "key": "nextSteps",
        "default": SCCEnterpriseConsts.NOT_AVAILABLE,
        "markdown": True,
    },
    "exception_instructions": {"key": "sourceProperties_ExceptionInstructions"},
    "explanation": {"key": "sourceProperties_Explanation"},
    "recommended_steps": {"key": "sourceProperties_Recommendation"},
    "Base Score": {"key": "vulnerability_cve_cvssv3_baseScore", "cvss": True},
    "Attack Vector": {"key": "vulnerability_cve_cvssv3_attackVector", "cvss": True},
    "Attack Complexity": {
        "key": "vulnerability_cve_cvssv3_attackComplexity",
        "cvss": True,
    },
    "Privileges Required": {
        "key": "vulnerability_cve_cvssv3_privilegesRequired",
        "cvss": True,
    },
    "User Interaction": {
        "key": "vulnerability_cve_cvssv3_userInteraction",
        "cvss": True,
    },
    "Scope": {"key": "vulnerability_cve_cvssv3_scope", "cvss": True},
    "Confidentiality Impact": {
        "key": "vulnerability_cve_cvssv3_confidentialityImpact",
        "cvss": True,
    },
    "Integrity Impact": {
        "key": "vulnerability_cve_cvssv3_integrityImpact",
        "cvss": True,
    },
    "Availability Impact": {
        "key": "vulnerability_cve_cvssv3_availabilityImpact",
        "cvss": True,
    },
    "Upstream Fix Available": {
        "key": "vulnerability_cve_upstreamFixAvailable",
        "cve": True,
    },
    "Impact": {"key": "vulnerability_cve_impact", "cve": True},
    "Exploitation Activity": {
        "key": "vulnerability_cve_exploitationActivity",
        "cve": True,
    },
    "Zero Day": {"key": "vulnerability_cve_zeroDay", "cve": True},
    "Observed In The Wild": {"key": "vulnerability_cve_observedInTheWild", "cve": True},
}
NON_GCP_EVENT_KEYS: KeyMap = {
    "description": {
        "key": "description",
        "default": SCCEnterpriseConsts.NOT_AVAILABLE,
        "markdown": True,
    },
    "next_steps": {
        "key": "nextSteps",
        "default": SCCEnterpriseConsts.NOT_AVAILABLE,
        "markdown": True,
    },
}

_CLOUD_PROVIDER_TO_KEY_MAP: Dict[CloudProviderEnum, KeyMap] = {
    CloudProviderEnum.GCP: GCP_EVENT_KEYS,
    CloudProviderEnum.AWS: NON_GCP_EVENT_KEYS,
    CloudProviderEnum.AZURE: NON_GCP_EVENT_KEYS,
    CloudProviderEnum.OTHER: NON_GCP_EVENT_KEYS,
}


class DescriptionParamsCreator:

    def __init__(
        self,
        event_data: SingleJson,
        key_map: KeyMap,
        markdown_parser: ParseStringFn,
        non_markdown_parser: ParseStringFn | None = None,
    ) -> None:
        self.event_data: SingleJson = event_data
        self.key_map: KeyMap = key_map
        self.parse_markdown_fn: ParseStringFn = markdown_parser
        self.parse_non_markdown_fn: ParseStringFn = non_markdown_parser
        self._og_params: SingleJson = self._get_raw_parameters()
        self._params: SingleJson = {}

    def get_parameters(self) -> SingleJson:
        self._params: SingleJson = copy.deepcopy(self._og_params)
        self._parse_params()
        return self._params

    def _get_raw_parameters(self) -> SingleJson:
        return _get_event_value_using_description_key_map(self.event_data, self.key_map)

    def _parse_params(self) -> None:
        self._set_non_event_params()
        self._parse_non_markdown_keys()
        self._parse_markdown_keys()

    def _parse_non_markdown_keys(self) -> None:
        if self.parse_non_markdown_fn is None:
            return

        for param, value in self._params.items():
            if not self._is_markdown_key(param) and isinstance(value, str):
                self._params[param]: str = self.parse_non_markdown_fn(value)

    def _set_non_event_params(self) -> None:
        self._set_references()
        self._set_cvss()
        self._set_cve()
        self._set_description_based_params()

    def _parse_markdown_keys(self) -> None:
        for param, value in self._params.items():
            if self._is_markdown_key(param):
                self._params[param]: str = self.parse_markdown_fn(value)

    def _set_references(self) -> None:
        self._params["references"]: ReferenceList = _parse_reference_keys_to_list(
            self.event_data
        )

    def _set_cvss(self) -> None:
        self._params["cvss"]: dict[str, str] = {
            name: value
            for name, value in self._params.items()
            if self._is_cvss_key(name) and value
        }

    def _set_cve(self) -> None:
        self._params["cve"]: dict[str, str] = {
            name: value
            for name, value in self._params.items()
            if self._is_cve_key(name) and value
        }

    def _set_description_based_params(self) -> None:
        description: str = self._params.get("description", "")
        desc_based_params: dict[str, str] = _get_description_based_params(description)
        self._params.update(desc_based_params)

    def _is_markdown_key(self, key: str) -> bool:
        return self.key_map.get(key, {}).get("markdown", False)

    def _is_cvss_key(self, key: str) -> bool:
        return self.key_map.get(key, {}).get("cvss", False)

    def _is_cve_key(self, key: str) -> bool:
        return self.key_map.get(key, {}).get("cve", False)


def get_desc_parameter_creator(
    output_type: DescriptionOutputType,
    cloud_provider: CloudProviderEnum,
    event_data: SingleJson,
) -> DescriptionParamsCreator:
    """Get a description parameter creator object

    Args:
        output_type: The output type to parse markdown content
        cloud_provider: The cloud provider of event_data
        event_data: The event data that the parameters will be created from

    Returns:
        A DescriptionParamsCreator object with a get_parameters method that will return
        the parameters for event_data based on cloud_provider and output_type
    """
    key_map: KeyMap = _get_key_map(cloud_provider=cloud_provider, event_data=event_data)

    if output_type == DescriptionOutputType.HTML:
        return DescriptionParamsCreator(
            event_data=event_data,
            key_map=key_map,
            markdown_parser=_parse_markdown_to_html,
            non_markdown_parser=_anchor_links_in_string,
        )

    return DescriptionParamsCreator(event_data, key_map, _parse_markdown_to_jwm)


def _get_key_map(cloud_provider: CloudProviderEnum, event_data: SingleJson) -> KeyMap:
    """Get a KeyMap object based on cloud provider and event data.

    Args:
        cloud_provider: The cloud provider of the finding
        event_data: The event data that we need key map for

    Returns:
        (KeyMap) mapping between template placeholders and event data keys.
    """
    key_map: KeyMap = copy.deepcopy(_CLOUD_PROVIDER_TO_KEY_MAP[cloud_provider])
    if is_event_provider_ciem(event_data):
        del key_map["next_steps"]

    return key_map


def is_event_provider_ciem(event_data: SingleJson) -> bool:
    provider: str = _get_event_provider(event_data)
    return provider == SCCEnterpriseConsts.PROVIDER_NAME_CIEM


def _get_event_provider(event_data: SingleJson) -> str:
    return event_data.get("sourceProperties_Metadata_providerName", "")


def _get_non_gcp_params(event_data: SingleJson) -> SingleJson:
    return _get_event_value_using_description_key_map(event_data, NON_GCP_EVENT_KEYS)


def _get_event_value_using_description_key_map(
    event_data: SingleJson, key_map: KeyMap
) -> SingleJson:
    return {
        result_key: event_data.get(key_data["key"], key_data.get("default", ""))
        for result_key, key_data in key_map.items()
    }


def _get_description_based_params(description: str) -> dict[str, str]:
    indexes = _find_and_return_sorted_description_params_indexes(description)
    return _get_description_based_params_from_sorted_index_list(description, indexes)


def _find_and_return_sorted_description_params_indexes(
    description: str,
) -> list[tuple[int, str]]:
    doc_index = description.find("DOCUMENTATION:")
    mit_index = description.find("MITIGATION:")
    stat_index = description.find("STATEMENT:")
    indexes = [
        (doc_index, "DOCUMENTATION:"),
        (mit_index, "MITIGATION:"),
        (stat_index, "STATEMENT:"),
    ]
    found_indexes = [index for index in indexes if index[0] >= 0]
    return sorted(found_indexes)


def _get_description_based_params_from_sorted_index_list(
    description: str, indexes: list[tuple[int, str]]
) -> dict[str, str]:
    result = {
        "show_description_based_params": _should_show_desc_based_params(indexes),
        "documentation": "",
        "statement": "",
        "mitigation": "",
    }
    for i, (item_index, item_id) in enumerate(indexes):
        start_index = item_index + len(item_id)
        end_index = indexes[i + 1][0] if i < len(indexes) - 1 else len(description)
        val = description[start_index:end_index].strip()

        if item_id == "DOCUMENTATION:":
            result["documentation"] = val

        elif item_id == "MITIGATION:":
            result["mitigation"] = val

        else:
            result["statement"] = val

    return result


def _should_show_desc_based_params(indexes: list[tuple[int, str]]) -> bool:
    return not all(map(bool, [i for (i, _) in indexes]))


def _parse_reference_keys_to_list(event: SingleJson) -> ReferenceList:
    reference_list = [{} for _ in event]

    for k, v in event.items():
        if "references" not in k:
            continue

        match = re.search(r"\d+", k)

        if match is None:
            continue

        index = int(match.group())

        if "source" in k:
            reference_list[index]["source"] = v

        elif "uri" in k:
            reference_list[index]["uri"] = v

    return list(filter(bool, reference_list))


def _parse_markdown_to_jwm(s: str) -> str:
    return (
        JwmMarkdownParser(s)
        .transform_md_bold_to_jwm()
        .transform_ordered_lists_to_jwm()
        .transform_nested_ordered_list_to_jwm_list()
        .transform_nested_unordered_list_to_jwm_list()
        .transform_md_hyperlinks_to_jwm()
        .replace_md_strong_with_jwm_bold()
        .remove_md_code_block_style()
        .transform_code_to_jwm_code()
        .transform_backtick_to_jwm_mono()
        .value
    )


def _parse_markdown_to_html(s: str) -> str:
    return (
        HtmlMarkdownParser(s)
        .replace_md_hyperlinks_with_regular_link()
        .anchor_links_in_string()
        .remove_markdown_strong()
        .transform_md_bold_to_html_b()
        .remove_double_new_line_in_code_block()
        .remove_md_code_block_style()
        .change_unordered_nested_list_2_indent_to_4()
        .change_ordered_nested_list_2_indent_to_4()
        .parse_markdown_to_html()
        .replace_new_line_with_br_in_code_blocks()
        .remove_p_from_ordered_list_items()
        .remove_p_from_unordered_list_items()
        .value
    )


class JwmMarkdownParser:

    def __init__(self, s: str) -> None:
        self._s: str = s

    @property
    def value(self) -> str:
        return self._s

    def transform_md_bold_to_jwm(self) -> JwmMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.TWO_STAR_WRAPPED_REGEXP, _replace_md_bold_jwm, self._s
        )

        return self

    def transform_ordered_lists_to_jwm(self) -> JwmMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.MD_ORDERED_LIST, _replace_ordered_list_jwm, self._s
        )

        return self

    def transform_nested_unordered_list_to_jwm_list(self) -> JwmMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.NESTED_UNORDERED_LIST_REGEXP, "\n**", self._s
        )

        return self

    def transform_nested_ordered_list_to_jwm_list(self) -> JwmMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.NESTED_ORDERED_LIST_REGEXP, "\n##", self._s
        )

        return self

    def remove_md_code_block_style(self) -> JwmMarkdownParser:
        self._s: str = re.sub(SCCEnterpriseConsts.CODE_BLOCK_STYLE, "```\n", self._s)

        return self

    def transform_code_to_jwm_code(self) -> JwmMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.CODE_TICK_WRAPPED_REGEXP, _replace_jwm_code, self._s
        )

        return self

    def transform_md_hyperlinks_to_jwm(self) -> JwmMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.MD_HYPERLINK_REGEXP, _replace_md_hyperlink_jwm, self._s
        )

        return self

    def transform_backtick_to_jwm_mono(self) -> JwmMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.BACKTICK_WRAPPED_REGEXP, _replace_jwm_mono, self._s
        )

        return self

    def replace_md_strong_with_jwm_bold(self) -> JwmMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.MD_STRONG_REGEXP, _replace_md_strong_jwm_bold, self._s
        )

        return self


class HtmlMarkdownParser:

    def __init__(self, s: str) -> None:
        self._s: str = s

    @property
    def value(self) -> str:
        return self._s

    def _to_soup(self) -> bs4.BeautifulSoup:
        return bs4.BeautifulSoup(self._s, features="html.parser")

    def remove_md_code_block_style(self) -> HtmlMarkdownParser:
        self._s: str = re.sub(SCCEnterpriseConsts.CODE_BLOCK_STYLE, "```\n", self._s)

        return self

    def remove_double_new_line_in_code_block(self) -> HtmlMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.CODE_BLOCK_DOUBLE_NL, _replace_double_nl, self._s
        )

        return self

    def remove_markdown_strong(self) -> HtmlMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.MD_STRONG_REGEXP, _replace_md_strong, self._s
        )

        return self

    def transform_md_bold_to_html_b(self) -> HtmlMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.TWO_STAR_WRAPPED_REGEXP, _replace_md_bold_html, self._s
        )

        return self

    def parse_markdown_to_html(self) -> HtmlMarkdownParser:
        self._s: str = markdown.markdown(self._s, extensions=["nl2br"])

        return self

    def replace_md_hyperlinks_with_regular_link(self) -> HtmlMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.MD_HYPERLINK_REGEXP,
            _replace_md_url_with_html_url,
            self._s,
        )

        return self

    def anchor_links_in_string(self) -> HtmlMarkdownParser:
        self._s: str = _anchor_links_in_string(self._s)

        return self

    def change_unordered_nested_list_2_indent_to_4(self) -> HtmlMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.TWO_INDENT_NESTED_UNORDERED_LIST_REGEXP,
            "\n    *",
            self._s,
        )

        return self

    def change_ordered_nested_list_2_indent_to_4(self) -> HtmlMarkdownParser:
        self._s: str = re.sub(
            SCCEnterpriseConsts.TWO_INDENT_NESTED_ORDERED_LIST_REGEXP,
            _transform_ordered_nested_list_indent,
            self._s,
        )

        return self

    def remove_p_from_ordered_list_items(self) -> HtmlMarkdownParser:
        """Remove <p> tags from ordered list items (<ol><li><p>...</p></li?</ol>).

        Returns:
            str: The string with <p> tags removed from ordered list items
        """
        soup: bs4.BeautifulSoup = self._to_soup()
        ordered_lists: list[bs4.element.Tag] = soup.find_all("ol")
        results: dict[str, str] = _remove_p_from_list_items(ordered_lists)
        for original, replacement in results.items():
            self._s: str = self._s.replace(original, replacement)

        return self

    def remove_p_from_unordered_list_items(self) -> HtmlMarkdownParser:
        """Remove <p> tags from ordered list items (<ul><li><p>...</p></li?</ul>).

        Returns:
            str: The string with <p> tags removed from ordered list items
        """
        soup: bs4.BeautifulSoup = self._to_soup()
        unordered_lists: list[bs4.element.Tag] = soup.find_all("ul")
        results: dict[str, str] = _remove_p_from_list_items(unordered_lists)
        for original, replacement in results.items():
            self._s: str = self._s.replace(original, replacement)

        return self

    def replace_new_line_with_br_in_code_blocks(self) -> HtmlMarkdownParser:
        """Replace \n characters with <br /> in <code>...\n...</code> blocks

        Returns:
            str: The string with new line characters replaced with <br />
        """
        soup: bs4.BeautifulSoup = self._to_soup()
        codes: list[bs4.element.Tag] = soup.find_all("code")
        for code in codes:
            s_code: str = str(code)
            new_code: str = s_code.replace("\n", "<br />")
            self._s: str = self._s.replace(s_code, new_code)

        return self


def _anchor_links_in_string(s: str) -> str:
    return re.sub(SCCEnterpriseConsts.URL_REGEXP, _replace_with_link, s)


def _remove_p_from_list_items(list_tags: list[bs4.element.Tag]) -> dict[str, str]:
    """Remove <p> tags from list tags.

    Args:
        list_tags (list[bs4.element.Tag]): The lists to remove <p> tags from their items

    Returns:
        A list of tuples [("original string", "replacement string")]
    """
    results: dict[str, str] = {}
    for list_tag in list_tags:
        og_tag = str(list_tag)

        all_p = list_tag.find_all("p")
        for p in all_p:
            p.replace_with_children()

        results[og_tag] = str(list_tag)

    return results


def _is_overview_description(description: str) -> bool:
    return (
        "DOCUMENTATION" in description
        and "MITIGATION" in description
        and "STATEMENT" in description
    )


def _replace_double_nl(match: re.Match) -> str:
    return "" if match is None else _replace_double_new_line(match.group())


def _replace_md_strong(match: re.Match) -> str:
    if match is None:
        return ""

    replaced = _replace_md_strong_with_html_bold(match.group(2))
    return f"{match.group(1)}{replaced}{match.group(3)}"


def _replace_md_bold_html(match: re.Match) -> str:
    return "" if match is None else _replace_md_bold_with_html_bold(match.group())


def _replace_md_bold_jwm(match: re.Match) -> str:
    return "" if match is None else _replace_md_bold_with_jwm_bold(match.group())


def _replace_md_strong_jwm_bold(match: re.Match) -> str:
    return "" if match is None else _replace_md_strong_with_jwm_bold(match.group())


def _replace_with_link(match: re.Match) -> str:
    return "" if match is None else _create_html_link(match.group())


def _replace_md_hyperlink_jwm(match: re.Match) -> str:
    return "" if match is None else _transform_md_link_to_jwm_link(match.group())


def _transform_ordered_nested_list_indent(match: re.Match) -> str:
    return "" if match is None else _replace_ordered_nested_indent_2_to_4(match.group())


def _replace_jwm_mono(match: re.Match) -> str:
    return "" if match is None else _replace_md_code_line_with_jwm_mono(match.group())


def _replace_jwm_code(match: re.Match) -> str:
    return "" if match is None else _replace_md_code_with_jwm_code(match.group())


def _replace_ordered_list_jwm(match: re.Match) -> str:
    return "" if match is None else _replace_ordered_list_number_jwm(match.group())


def _replace_md_url_with_html_url(match: re.Match) -> str:
    return "" if match is None else _transform_md_link_to_html_link(match.group())


def _replace_md_code_line_with_jwm_mono(s: str) -> str:
    return f'{{{{{s.strip("`")}}}}}'


def _replace_md_code_with_jwm_code(s: str) -> str:
    return f'{{code:shell}}{s.strip("```")}{{code}}'


def _replace_md_bold_with_jwm_bold(s: str) -> str:
    return s.replace("**", "*")


def _replace_md_strong_with_jwm_bold(s: str) -> str:
    return s.replace("__", "*")


def _replace_ordered_list_number_jwm(s: str) -> str:
    return re.sub(SCCEnterpriseConsts.MD_ORDERED_LIST_NUMBER, "#", s)


def _replace_md_bold_with_html_bold(s: str) -> str:
    return _wrap_string_with_html_bold(s.strip("**"))


def _replace_md_strong_with_html_bold(s: str) -> str:
    return _wrap_string_with_html_bold(s.strip("__"))


def _wrap_string_with_html_bold(s: str) -> str:
    return f'<b style="font-size: 11pt">{s}</b>'


def _replace_double_new_line(s: str) -> str:
    return s.replace("\n\n", "\n")


def _transform_md_link_to_jwm_link(s: str) -> str:
    text, url = _get_link_and_text_from_md_link(s)
    return url if text == url else f"[{text}|{url}]"


def _replace_ordered_nested_indent_2_to_4(s: str) -> str:
    return s.replace("\n  ", "\n    ")


def _transform_md_link_to_html_link(s: str) -> str:
    text, url = _get_link_and_text_from_md_link(s)
    return url if text == url else f"{text} ({url})"


def _get_link_and_text_from_md_link(s: str) -> tuple[str, str]:
    parts = s.split("](")
    text = TIPCommon.transformation.removeprefix(parts[0], "[")
    url = TIPCommon.transformation.removesuffix(parts[-1], ")")
    return text, url


def _create_html_link(url: str) -> str:
    has_paren_suffix: bool = url.endswith(")")
    url: str = TIPCommon.transformation.removesuffix(url, ")")
    result: str = f'<a class="link text" href="{url}" target="_blank">{url}</a>'
    return f"{result})" if has_paren_suffix else result
