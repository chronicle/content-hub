from __future__ import annotations

import datetime as dt
import time
from typing import TYPE_CHECKING, NamedTuple

from TIPCommon.base.interfaces import Apiable

from ..constants import REQUEST_TIMEOUT
from ..data_models import BaseRate, DailyRates
from ..utils import date_range
from .api_utils import get_full_url, validate_response

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from requests import Response
    from TIPCommon.base.interfaces.logger import ScriptLogger
    from TIPCommon.types import SingleJson

    from .auth import AuthenticatedSession


class ApiParameters(NamedTuple):
    api_root: str


class SampleApiClient(Apiable):
    def __init__(
        self,
        authenticated_session: AuthenticatedSession,
        configuration: ApiParameters,
        logger: ScriptLogger,
    ) -> None:
        super().__init__(
            authenticated_session=authenticated_session,
            configuration=configuration,
        )
        self.logger: ScriptLogger = logger
        self.api_root: str = configuration.api_root

    def test_connectivity(self) -> None:
        """Test connectivity to API."""
        url: str = get_full_url(self.api_root, "ping")
        response: Response = self.session.get(url)
        validate_response(response)

    def get_rates(
        self,
        currencies: Iterable[str],
        start_date: dt.date,
        end_date: dt.date | None = None,
    ) -> Sequence[DailyRates]:
        """Get daily rates for a given date range and currencies.

        Args:
            currencies (Iterable[str]): list of currencies to get rates for
            start_date (dt.date): start date of the range
            end_date (dt.date, optional): end date of the range.
                Defaults to dt.date.today().

        Returns:
            Sequence[DailyRates]: list of daily rates
        """
        results: Sequence[DailyRates] = []

        if end_date is None:
            end_date: dt.date = dt.date.today()

        # Ideally, the API endpoint would accept a range of value per parameter in the
        # request. However, Vatcomply '/rates' endpoint only supports a single value
        # per base and date, so we have to do this ugly and risky nested for-loop on
        # dates and currencies
        for date in date_range(start_date, end_date):
            results.append(
                DailyRates(
                    date=date.isoformat(),
                    exchange_rates=[self.get_base_rate(base, date) for base in currencies],
                )
            )
        return results

    def get_connector_rates(
        self,
        currencies: Iterable[str],
        start_date: dt.date,
    ) -> DailyRates:
        """Get daily rates for a given date range and currencies for connector use.

        Args:
            currencies (Iterable[str]): list of currencies to get rates for
            start_date (dt.date): start date of the range

        Returns:
            DailyRates: list of daily rates
        """
        return DailyRates(
            date=start_date.isoformat(),
            exchange_rates=[self.get_base_rate(base, start_date) for base in currencies],
        )

    def get_job_rate(self) -> SingleJson:
        """Get job rate."""
        url: str = get_full_url(self.api_root, "ping")
        response: Response = self.session.get(url)
        validate_response(response)
        return response.json()

    def get_base_rate(self, base_symbol: str, date: dt.date) -> BaseRate:
        """Get base rate for a given currency and date.

        Args:
            base_symbol (str): currency to get rate for
            date (dt.date): date to get rate for

        Returns:
            BaseRate: base rate
        """
        time.sleep(2)  # Simulating API rate limit
        url: str = get_full_url(self.api_root, "get-base-rate")
        params: dict[str, str] = {
            "date": date.isoformat(),
            "base": base_symbol,
        }
        response: Response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        validate_response(response)
        return BaseRate(**response.json())
