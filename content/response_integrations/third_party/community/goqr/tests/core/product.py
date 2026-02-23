from __future__ import annotations

from TIPCommon.types import SingleJson


class GOQR:
    def __init__(self):
        self.scan_qr: list[SingleJson] = []
        self.generate_qr: list[bytes] = []

    def get_scanned_qr(
        self,
    ) -> list[SingleJson]:
        return self.scan_qr

    def add_scanned_qr(self, qr: SingleJson) -> None:
        self.scan_qr.append(qr)

    def get_generated_qr(self) -> list[bytes]:
        return self.generate_qr

    def add_generated_qr(self, qr: bytes) -> None:
        self.generate_qr.append(qr)
