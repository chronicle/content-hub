import datetime as dt
from collections.abc import Iterable

from TIPCommon.base.utils import NewLineLogger
from requests import Session

from .api_utils import get_full_url, validate_response
from .constants import REQUEST_TIMEOUT
from .data_models import BaseRate, DailyRates
from .utils import date_range


class ApiManager:
    def __init__(
        self,
        api_root: str,
        session: Session,
        logger: NewLineLogger,
    ) -> None:
        """Manager for handling API interactions

        Args:
            session (Session): initialized session object to be used in API session
            logger (NewLineLogger): logger object

        """
        self.api_root = api_root
        self.session = session
        self.logger = logger

    def test_connectivity(self) -> None:
        """Test connectivity to API."""
        url = get_full_url(self.api_root, "ping")
        response = self.session.get(url)
        validate_response(response)

    def get_rates(
        self,
        currencies: Iterable[str],
        start_date: dt.date,
        end_date: dt.date = dt.date.today(),
    ) -> list[DailyRates]:
        """Get daily rates for a given date range and currencies.

        Args:
            currencies (Iterable[str]): list of currencies to get rates for
            start_date (dt.date): start date of the range
            end_date (dt.date, optional): end date of the range.
                Defaults to dt.date.today().

        Returns:
            list[DailyRates]: list of daily rates
        """
        results = []

        # Ideally, the API endpoint would accept range of value per parameter in request
        # But Vatcomply '/rates' endpoint only supports a single value per base & date,
        # so we have to do this ugly and risky nested for-loop on dates & currencies
        for date in date_range(start_date, end_date):
            results.extend(
                DailyRates(
                    date=date.isoformat(),
                    exchange_rates=[
                        self.get_base_rate(base, date) for base in currencies
                    ],
                )
            )
        return results

    def get_base_rate(self, base_symbol: str, date: dt.date) -> BaseRate:
        """Get base rate for a given currency and date.

        Args:
            base_symbol (str): currency to get rate for
            date (dt.date): date to get rate for

        Returns:
            BaseRate: base rate
        """
        url = get_full_url(self.api_root, "get-base-rate")
        params = {
            "date": date.isoformat(),
            "base": base_symbol,
        }
        response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        validate_response(response)
        return BaseRate(**response.json())
