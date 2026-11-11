from __future__ import annotations
import abc

import ipaddress
import re
import base64

from TIPCommon.types import SingleJson
from google_threat_intelligence.tests.responses.api import common_responses


class GoogleThreatIntelligenceProduct(abc.ABC):

    def __init__(self) -> None:
        self.query_response = {}
        self._iocs: dict[str, dict[str, SingleJson | None]] = {}
        self._comments: dict[str, SingleJson] = {}
        self._asm_issues: list[SingleJson] = []
        self._asm_entities: list[SingleJson] = []
        self._asm_search_error: str | None = None
        self._analyses: dict[str, SingleJson] = {}

    def add_analysis(self, analysis_id: str, response: SingleJson) -> None:
        """Add an analysis response for a specific analysis ID."""
        self._analyses[analysis_id] = response

    def get_analysis(self, analysis_id: str) -> SingleJson | None:
        """Return the stored analysis response for the given analysis ID."""
        return self._analyses.get(analysis_id)

    def add_search_query_response(self, response: dict) -> dict:
        self.query_response = response

    def get_search_response(self):
        return self.query_response

    def add_ioc(
        self,
        ioc_identifier: str,
        response_type_json: SingleJson,
    ) -> None:
        """Add an IOC in Google Threat Intelligence"""
        self._iocs[ioc_identifier] = {
            "response_type": response_type_json,
        }

    def add_comments(
            self,
            ioc_identifier: str,
            response: SingleJson,
    ) -> None:
        """Add a comments for a specific IOC identifier."""
        self._comments[ioc_identifier] = response

    def get_comments(self, ioc_identifier: str) -> SingleJson | None:
        return self._comments.get(ioc_identifier)

    def get_ip_ioc(self, ioc_identifier: str) -> SingleJson:
        if is_valid_ip(ioc_identifier):
            return self._iocs[ioc_identifier]["response_type"]
        return common_responses.create_ip_error_response(ioc_identifier)

    def get_file_hash_ioc(self, ioc_identifier: str) -> SingleJson:
        if check_file_hash(ioc_identifier):
            return self._iocs[ioc_identifier]["response_type"]
        return common_responses.INVALID_FILE_HASH_RESPONSE

    def get_url_ioc(self, ioc_identifier: str) -> SingleJson:
        decoded_url: str = decode_url(ioc_identifier)
        if self._iocs.get(decoded_url, {}):
            return self._iocs[decoded_url]["response_type"]
        return common_responses.create_url_error_response(ioc_identifier)

    def get_domain_ioc(self, ioc_identifier: str) -> SingleJson:
        if self._iocs.get(ioc_identifier, {}):
            return self._iocs[ioc_identifier]["response_type"]
        return common_responses.create_domain_error_response(ioc_identifier)

    def add_asm_issues(self, issues: list[SingleJson]) -> None:
        """Add ASM issues that can be found by the issues search endpoint."""
        self._asm_issues.extend(issues)

    def add_asm_entities(self, entities: list[SingleJson]) -> None:
        """Add ASM entities that can be found by the entities search endpoint."""
        self._asm_entities.extend(entities)

    def set_asm_search_error(self, message: str) -> None:
        """Make the ASM search endpoints report a failed search."""
        self._asm_search_error = message

    def search_asm_issues(self, query: str, page: int, page_size: int) -> SingleJson:
        """Mimic the ASM issues search endpoint.

        Only the `last_seen_after`/`last_seen_before` tokens of the query are
        applied (inclusive bounds); the result is paginated like the live API.
        """
        last_seen_after: str | None = get_asm_query_value(query, "last_seen_after")
        last_seen_before: str | None = get_asm_query_value(query, "last_seen_before")
        hits: list[SingleJson] = [
            issue for issue in self._asm_issues
            if (last_seen_after is None or issue["last_seen"] >= last_seen_after)
            and (last_seen_before is None or issue["last_seen"] <= last_seen_before)
        ]
        return self._paginate_asm_search(hits, page, page_size)

    def search_asm_entities(self, page: int, page_size: int) -> SingleJson:
        """Mimic the ASM entities search endpoint (no query filtering)."""
        return self._paginate_asm_search(self._asm_entities, page, page_size)

    def _paginate_asm_search(self, hits: list[SingleJson], page: int, page_size: int) -> SingleJson:
        """Build an ASM search page with the same result keys as the live API
        (there is no `total` key)."""
        if self._asm_search_error is not None:
            return {"success": False, "message": self._asm_search_error}

        start: int = page * page_size
        more: bool = start + page_size < len(hits)
        return {
            "success": True,
            "message": "Search completed!",
            "result": {
                "hits": hits[start:start + page_size],
                "more": more,
                "page": page,
                "page_size": page_size,
                "timed_out": False,
                "total_hits": len(hits),
                "total_pages": -(-len(hits) // page_size) if page_size else 0,
                "next_page_token": f"token-{page + 1}" if more else None,
            },
        }

    def get_asm_issue(self, issue_id: str) -> SingleJson:
        """Mimic the ASM issue details endpoint."""
        for issue in self._asm_issues:
            if issue["id"] == issue_id:
                return {"success": True, "result": issue}

        return {"success": False, "message": f"Issue {issue_id} was not found"}


def get_asm_query_value(query: str, key: str) -> str | None:
    """Extract a `key:value` token value from an ASM search query string"""
    match: re.Match | None = re.search(rf"{key}:(\S+)", query)
    return match.group(1) if match else None


def is_valid_ip(ip: str) -> bool:
    """Check if the given ip address is valid"""
    try:
        ipaddress.ip_address(ip)
        return True

    except ValueError:
        return False


def decode_url(encoded_url: str) -> str:
    padding_needed = len(encoded_url) % 4
    if padding_needed != 0:
        encoded_url += "=" * (4 - padding_needed)
    return base64.urlsafe_b64decode(encoded_url.encode()).decode()


def check_file_hash(file_hash: str) -> bool:
    """Check if the file hash is a valid file hash"""
    ash_lengths = {32: "MD5", 40: "SHA-1", 64: "SHA-256"}
    if (len(file_hash) not in ash_lengths) or (
        not re.fullmatch(r"^[0-9a-fA-F]+$", file_hash)
    ):
        return False

    return True


class GoogleThreatIntelligenceSdkProduct(abc.ABC):

    def __init__(self) -> None:
        pass
