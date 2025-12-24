from __future__ import annotations

import dataclasses
import datetime
from collections import defaultdict

from TIPCommon.types import SingleJson

from sample_integration.tests.core.constants import KNOWN_SYMBOLS
from sample_integration.tests.core.datamodels import MockBaseRate


@dataclasses.dataclass(slots=True)
class VatComply:
    rates: list[MockBaseRate] = dataclasses.field(default_factory=list)
    cases: dict[int, SingleJson] = dataclasses.field(default_factory=dict)
    tags: dict[int, list[str]] = dataclasses.field(default_factory=lambda: defaultdict(list))

    def get_rates(
        self,
        base: str | None = None,
        symbols: str | None = None,
        date: str | None = None,
    ) -> SingleJson:
        _base = self._validate_base(base)
        _symbols = self._validate_symbols(symbols)
        _date = self._validate_date(date)

        result: MockBaseRate = next(
            filter(
                lambda r: r.date == _date and r.base == _base,
                self.rates,
            ),
            None,
        )
        if not result:
            raise ValueError(f"Value error, Unknown base currency {_base} or date {_date}")
        return result.to_json(_symbols)

    def set_rates(self, mock_rates: SingleJson) -> None:
        self.rates.append(MockBaseRate.from_json(mock_rates))

    @staticmethod
    def _validate_base(symbol: str | None) -> str:
        if not symbol:
            return "EUR"
        if symbol not in KNOWN_SYMBOLS:
            raise ValueError(f"Value error, Base currency {symbol} is not supported.")
        return symbol

    @staticmethod
    def _validate_symbols(symbols: str | None) -> list[str]:
        if not symbols:
            return []
        symbols = symbols.split(",")
        for symbol in symbols:
            if symbol not in KNOWN_SYMBOLS:
                raise ValueError(f"Value error, Currency {symbol} is not supported.")
        return symbols

    @staticmethod
    def _validate_date(date_str: str | None) -> datetime.date:
        if not date_str:
            return datetime.date.today()
        try:
            return datetime.date.fromisoformat(date_str)
        except ValueError as e:
            raise ValueError(f"Input should be a valid date or datetime, {e}")

    def get_case_details(self, case_id: int) -> SingleJson:
        if case_id not in self.cases:
            raise ValueError(f"Case ID {case_id} not found.")
        return self.cases[case_id]

    def get_case_ids(self) -> list[int]:
        return list(self.cases.keys())

    def add_case_details(self, case_id: int, details: SingleJson) -> None:
        self.cases[case_id] = details

    def add_tag(self, case_id: int, tag: str) -> None:
        self.tags[case_id].append(tag)

    def get_tags(self, case_id: int) -> list[str] | None:
        if case_id not in self.tags:
            return None
        return self.tags[case_id]

    def add_tags_to_case(self, case_id: int, tags: list[str]) -> None:
        if case_id not in self.cases:
            raise ValueError(f"Case ID {case_id} not found.")
        case_details = self.cases[case_id]
        case_details["tags"].extend(tags)
