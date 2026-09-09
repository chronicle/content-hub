from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TIPCommon.base.job.job_case import JobCase

_MENTION_PATTERN = re.compile(r"<@>(.*?)</@>", flags=re.DOTALL)
_LINE_BREAK_PATTERN = re.compile(r"<br\s*/?>", flags=re.IGNORECASE)
_PARAGRAPH_BREAK_PATTERN = re.compile(
    r"</(?:p|div)>\s*<(?:p|div)[^>]*>", flags=re.IGNORECASE
)
_TRAILING_CONTAINER_PATTERN = re.compile(
    r"(?:</(?:p|div|span)>\s*)+$", flags=re.IGNORECASE
)
_ANCHOR_TAG_PATTERN = re.compile(r"</?a\b[^<>]*>", flags=re.IGNORECASE)
_HTML_TAG_PATTERN = re.compile(
    r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s+[^<>]*)?/?>|<!--.*?-->",
    flags=re.DOTALL,
)


def _normalize_mentions(text: str) -> str:
    """Converts SecOps user mention wrappers to standard @mentions."""

    def _replace(match: re.Match[str]) -> str:
        content = match.group(1).strip()
        if not content:
            return ""
        if content.startswith("@"):
            return content
        return f"@{content}"

    return _MENTION_PATTERN.sub(_replace, text)


def _convert_line_breaks(text: str) -> str:
    """Converts HTML break and paragraph tags to newline characters."""
    text = _LINE_BREAK_PATTERN.sub("\n", text)
    return _PARAGRAPH_BREAK_PATTERN.sub("\n", text)


def _strip_html_tags(text: str) -> str:
    """Strips all HTML tags from the string."""
    return _HTML_TAG_PATTERN.sub("", text)


def _decode_html_entities(text: str) -> str:
    """Decodes standard HTML entities and normalizes non-breaking spaces."""
    decoded = html.unescape(text)
    return decoded.replace("\xa0", " ")


def escape_comment_for_secops(text: str) -> str:
    """Escapes HTML special characters in comments before posting to SecOps.

    Prevents SecOps Case Wall HTML sanitizer from interpreting or stripping
    special characters (such as angle brackets, e.g. '<<qAA') as HTML tags.

    Args:
        text: The raw plain text comment from PagerDuty.

    Returns:
        The HTML-escaped string safe for the SecOps Case Wall.
    """
    if not text:
        return ""
    return html.escape(text)


def clean_pagerduty_comment(text: str) -> str:
    """Cleans a PagerDuty comment on the SecOps Case Wall.

    Extracts the PagerDuty payload starting at the 'PagerDuty:' prefix,
    normalizes line breaks, and strips outer container tags added by the SecOps
    platform without stripping internal content.

    Args:
        text: The raw comment string from the Case Wall.

    Returns:
        The clean plain text string matching the original PagerDuty note.
    """
    if not text:
        return ""

    idx = text.find("PagerDuty:")
    if idx != -1:
        text = text[idx:]

    text = _TRAILING_CONTAINER_PATTERN.sub("", text)
    text = _convert_line_breaks(text)
    text = _ANCHOR_TAG_PATTERN.sub("", text)
    return _decode_html_entities(text).strip()


def clean_secops_comment(text: str) -> str:
    """Converts a rich-text/HTML SecOps comment into clean plain text for PagerDuty.

    Args:
        text: The raw comment string from SecOps.

    Returns:
        The clean plain text string.
    """
    if not text:
        return ""

    text = _normalize_mentions(text)
    text = _convert_line_breaks(text)
    text = _strip_html_tags(text)
    text = _decode_html_entities(text)
    return text.strip()


def sanitize_case_comments(job_case: JobCase) -> None:
    """Sanitizes SecOps case comments in-place.

    Comments originating from PagerDuty have their payload extracted at the
    'PagerDuty:' boundary, while SecOps analyst comments have rich-text
    markup converted to plain text.

    Args:
        job_case: The SecOps case containing comments to sanitize.
    """
    if not job_case.case_comments:
        return

    sanitized_comments = []
    for comment in job_case.case_comments:
        if isinstance(comment, dict):
            sanitized_dict = dict(comment)
            raw_text = sanitized_dict.get("comment")
            if isinstance(raw_text, str):
                if "PagerDuty:" in raw_text:
                    sanitized_dict["comment"] = clean_pagerduty_comment(
                        raw_text
                    )
                else:
                    sanitized_dict["comment"] = clean_secops_comment(raw_text)
            sanitized_comments.append(sanitized_dict)
        else:
            sanitized_comments.append(comment)

    job_case.case_comments = sanitized_comments
