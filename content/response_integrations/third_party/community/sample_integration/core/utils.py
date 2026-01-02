from __future__ import annotations

import datetime as dt
from base64 import b64encode
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyDataModel import Attachment

if TYPE_CHECKING:
    from collections.abc import Iterator


def date_range(start_date: dt.date, end_date: dt.date) -> Iterator[dt.date]:
    """Generator function to iterate over a range of dates."""
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += dt.timedelta(days=1)


def create_secops_attachment_object(file_name: str, file_content: bytes) -> Attachment:
    """Create attachment object for Siemplify alert.

    Args:
        file_name: {str} Full name of the file including `.json` extension.
        file_content: {bytes} File content in bytes.

    Returns:
        Attachment: Attachment object.
    """
    base64_blob = b64encode(file_content).decode()
    attachment_object = Attachment(
        case_identifier=None,
        alert_identifier=None,
        base64_blob=base64_blob,
        attachment_type="json",
        name=file_name,
        description="Exchange rate data in JSON format",
        is_favorite=False,
        orig_size=len(file_content),
        size=len(base64_blob),
    )

    return attachment_object
