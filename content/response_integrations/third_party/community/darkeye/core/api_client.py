from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple
from urllib.parse import quote, urljoin

import requests
from TIPCommon.base.interfaces import Apiable

from .constants import (
    BREACH_HOUSE,
    BREACH_HOUSE_API_ROOT,
    BREACH_HOUSE_CATEGORIES,
    ENDPOINTS,
    HAVEIBEENRANSOM,
    HAVEIBEENRANSOM_API_ROOT,
    HAVEIBEENRANSOM_CATEGORIES,
    HAVEIBEENRANSOM_DEFAULT_CATEGORY,
    PING_DOMAIN,
    REQUEST_TIMEOUT,
)
from .data_models import ProductResult, Record
from .exceptions import DarkEyeProductError
from .utils import clean, has_next_page, status_message

if TYPE_CHECKING:
    from collections.abc import Callable

    from requests import Response, Session
    from TIPCommon.base.interfaces.logger import ScriptLogger


class ApiParameters(NamedTuple):
    haveibeenransom_api_key: str
    breach_house_api_key: str


class DarkEyeApiClient(Apiable):
    """Client for the DarkEye products that have a public API: HaveIBeenRansom and Breach House."""

    def __init__(
        self,
        authenticated_session: Session,
        configuration: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,
            configuration=configuration,
        )
        self.logger: ScriptLogger = logger
        self.api_keys: dict[str, str] = {
            HAVEIBEENRANSOM: configuration.haveibeenransom_api_key,
            BREACH_HOUSE: configuration.breach_house_api_key,
        }

    @property
    def products(self) -> list[str]:
        """The products that have an API key, in query order."""
        return [product for product, key in self.api_keys.items() if key]

    def test_connectivity(self) -> None:
        """Check every configured API key.

        Raises:
            DarkEyeProductError: If a product does not answer.
        """
        for product in self.products:
            if product == HAVEIBEENRANSOM:
                self._get_json(product, self._haveibeenransom_url("domain", PING_DOMAIN))
            else:
                self._get_json(product, urljoin(BREACH_HOUSE_API_ROOT, ENDPOINTS["breach-house-me"]))

    def search_haveibeenransom(
        self,
        field: str,
        term: str,
        max_pages: int,
        max_records: int,
    ) -> ProductResult:
        """Search the HaveIBeenRansom listing metadata, 20 sources per page.

        Args:
            field: "domain" or "email".
            term: The normalized domain or email address.
            max_pages: Maximum number of pages to read. Each page is one request.
            max_records: Maximum number of records to keep.

        Returns:
            ProductResult: The records and whether more exist than were read.

        Raises:
            DarkEyeProductError: If a page cannot be read.
        """
        result = ProductResult()
        seen: set[str] = set()
        for page in range(1, max_pages + 1):
            data: dict[str, Any] = self._get_json(HAVEIBEENRANSOM, self._haveibeenransom_url(field, term, page))
            sources: Any = data.get("sources", data.get("results"))
            if not isinstance(sources, list):
                raise DarkEyeProductError(HAVEIBEENRANSOM, "returned an unexpected response.")
            for leak in sources:
                if not isinstance(leak, dict):
                    continue
                # A leak indexed while paging can show up again on the next page.
                leak_id: str = clean(leak.get("id_source") or leak.get("id"))
                if not leak_id or leak_id in seen:
                    continue
                seen.add(leak_id)
                leak_type: str = clean(leak.get("leak_type"))
                category: str = HAVEIBEENRANSOM_CATEGORIES.get(leak_type, HAVEIBEENRANSOM_DEFAULT_CATEGORY)
                result.records.append(Record.from_api(HAVEIBEENRANSOM, category, leak))
            if len(result.records) >= max_records:
                result.truncated = len(result.records) > max_records or has_next_page(data)
                result.records = result.records[:max_records]
                return result
            if not has_next_page(data):
                return result
        result.truncated = True
        return result

    def search_breach_house(
        self,
        term: str,
        limit: int,
        max_records: int,
        is_match: Callable[[Record, dict[str, Any]], bool],
    ) -> ProductResult:
        """Search every Breach House source in one request.

        The search matches free text, so only the records accepted by is_match are kept.

        Args:
            term: The normalized domain or email address.
            limit: Maximum number of results per source.
            max_records: Maximum number of records to keep.
            is_match: Tells whether a record is about the term.

        Returns:
            ProductResult: The records and whether more exist than were read.

        Raises:
            DarkEyeProductError: If the search cannot be read.
        """
        url: str = urljoin(BREACH_HOUSE_API_ROOT, ENDPOINTS["breach-house-search"])
        data: dict[str, Any] = self._get_json(BREACH_HOUSE, url, params={"q": term, "limit": limit})
        result = ProductResult()
        for section_name, category in BREACH_HOUSE_CATEGORIES.items():
            section: Any = data.get(section_name)
            total: Any = None
            if isinstance(section, list):
                items: list[Any] = section
            elif isinstance(section, dict) and isinstance(section.get("results"), list):
                items, total = section["results"], section.get("total")
            else:
                continue
            if len(items) >= limit or (isinstance(total, int) and total > len(items)):
                result.truncated = True
            for item in items:
                if not isinstance(item, dict):
                    continue
                record: Record = Record.from_api(BREACH_HOUSE, category, item)
                if is_match(record, item):
                    result.records.append(record)
        if len(result.records) > max_records:
            result.records = result.records[:max_records]
            result.truncated = True
        return result

    @staticmethod
    def _haveibeenransom_url(field: str, term: str, page: int = 1) -> str:
        endpoint_id: str = "haveibeenransom-search" if page == 1 else "haveibeenransom-search-page"
        endpoint: str = ENDPOINTS[endpoint_id].format(field=field, term=quote(term, safe="@"), page=page)
        return urljoin(HAVEIBEENRANSOM_API_ROOT, endpoint)

    def _get_json(self, product: str, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send one GET with the product's own key and return the JSON object.

        Redirects are not followed: a redirect is a failed lookup, so no second request goes out.

        Raises:
            DarkEyeProductError: On a connection error, a non-200 status or an unexpected body.
        """
        headers: dict[str, str] = {"Authorization": f"Bearer {self.api_keys[product]}"}
        try:
            response: Response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=False,
            )
        except requests.RequestException as error:
            # The exception names the error type only: its text can hold the request URL.
            msg: str = f"request failed ({type(error).__name__})."
            raise DarkEyeProductError(product, msg) from None
        if response.status_code != 200:
            raise DarkEyeProductError(product, status_message(response.status_code), response.status_code)
        try:
            data: Any = response.json()
        except ValueError:
            raise DarkEyeProductError(product, "returned invalid JSON.") from None
        if not isinstance(data, dict) or data.get("success") is False:
            raise DarkEyeProductError(product, "returned an unexpected response.")
        return data
