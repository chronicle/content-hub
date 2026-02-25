from __future__ import annotations

from typing import TYPE_CHECKING, BinaryIO, List, NamedTuple

from TIPCommon.base.interfaces import Apiable

from ..data_models import DecodedQrCode
from .api_utils import get_full_url, validate_response

if TYPE_CHECKING:
    from requests import Response
    from TIPCommon.base.interfaces.logger import ScriptLogger

    from ..auth import AuthenticatedSession


class ApiParameters(NamedTuple):
    api_root: str


class GOQRApiClient(Apiable):
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

    def ping(self) -> None:
        """Test connectivity to API."""
        url: str = get_full_url(self.api_root, "ping")
        response: Response = self.session.get(url)
        validate_response(response, "Failed to connect to the API.")

    def generate_qr_code(
        self,
        data: str,
        size: str,
        image_format: str,
        error_correction: str,
        margin: int,
        foreground_color: str,
        background_color: str,
    ) -> bytes:
        """Generate a QR code."""
        url: str = get_full_url(self.api_root, "create_qr_code")
        params = {
            "data": data,
            "size": size,
            "format": image_format,
            "ecc": error_correction,
            "margin": margin,
            "color": foreground_color,
            "bgcolor": background_color,
        }
        response: Response = self.session.get(url, params=params)
        validate_response(response, "Failed to generate QR code.")
        return response.content

    def read_qr_code(self, file: BinaryIO) -> List[DecodedQrCode]:
        """Read a QR code from an image."""
        url: str = get_full_url(self.api_root, "read_qr_code")
        files = {"file": file}
        response: Response = self.session.post(url, files=files)
        validate_response(response, "Failed to read QR code.")

        return [DecodedQrCode.from_dict(item) for item in response.json()]
