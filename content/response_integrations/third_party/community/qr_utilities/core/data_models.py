from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class QrSymbol:
    """Represents a single symbol (decoded data) from a QR code."""

    seq: int
    data: str
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QrSymbol:
        return cls(
            seq=data.get("seq"),
            data=data.get("data"),
            error=data.get("error"),
        )


@dataclass
class DecodedQrCode:
    """Represents the full result of a QR code read operation."""

    type: str
    symbols: List[QrSymbol]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecodedQrCode:
        return cls(
            type=data.get("type"),
            symbols=[QrSymbol.from_dict(symbol) for symbol in data.get("symbol", [])],
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "symbols": [symbol.__dict__ for symbol in self.symbols],
        }
    
    @property
    def first_symbol_data(self) -> Optional[str]:
        """Helper to get the data from the first symbol, which is the most common case."""
        if self.symbols:
            return self.symbols[0].data
        return None
