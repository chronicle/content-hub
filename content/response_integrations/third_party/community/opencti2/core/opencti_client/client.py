from pycti import OpenCTIApiClient


class OpenCTIClientError(Exception):
    pass


class OpenCTIClient:
    def __init__(self, base_url: str, api_token: str, ssl_verify: bool = True) -> None:
        try:
            # Note: a health check is performed during OpenCTIApiClient initialization
            self._api_client = OpenCTIApiClient(
                base_url,
                api_token,
                ssl_verify=ssl_verify,
            )
        except ValueError as e:
            raise OpenCTIClientError(
                f"Failed to establish connection with OpenCTI: {str(e)}"
            ) from e
