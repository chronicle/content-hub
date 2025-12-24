from __future__ import annotations

import dataclasses
import datetime
from typing import Iterable

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class MockBaseRate:
    date: datetime.date
    base: str
    rates: SingleJson

    @classmethod
    def from_json(cls, json_data: SingleJson) -> MockBaseRate:
        date = datetime.date.fromisoformat(json_data["date"])
        return cls(
            date=date,
            base=json_data["base"],
            rates=json_data["rates"],
        )

    def to_json(self, symbols: Iterable[str] = None) -> SingleJson:
        result = {
            "date": self.date.isoformat(),
            "base": self.base,
            "rates": self.rates,
        }
        if symbols:
            result["rates"] = {
                symbol: rate for symbol, rate in self.rates.items() if symbol in symbols
            }
        return result
