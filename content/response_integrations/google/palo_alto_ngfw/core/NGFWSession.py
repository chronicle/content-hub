from __future__ import annotations
import requests

from soar_sdk.SiemplifyLogger import SiemplifyLogger as Logger


class NGFWSession(requests.Session):
    def __init__(self, logger: Logger):
        super().__init__()
        self.logger = logger

    def request(self, method, url, **kwargs):  # pylint: disable=arguments-differ
        """Override request to handle 403 by refreshing token."""
        is_retry = kwargs.pop("is_retry", False)

        response = super().request(method, url, **kwargs)

        if response.status_code == 403 and not is_retry:
            self.logger.warn(
                "Received 403. Attempting token refresh."
            )
            self.auth.refresh_key()

            kwargs["is_retry"] = True
            return self.request(method, url, **kwargs)

        return response
