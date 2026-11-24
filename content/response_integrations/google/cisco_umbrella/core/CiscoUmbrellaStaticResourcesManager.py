from __future__ import annotations
import dataclasses
import logging
from enum import Enum
from functools import partial
from io import BytesIO
from typing import Any, Callable, Iterator, List, Optional
from zipfile import ZipFile

from requests import Session, Response
from requests.exceptions import HTTPError

from cisco_umbrella.core.exceptions import CiscoUmbrellaManagerError


BASE_URL = "http://s3-us-west-1.amazonaws.com/umbrella-static/"


def _unzip(data: bytes) -> bytes:
    """Unzips the first file in a zip archive.

    Args:
        data: The zipped data.

    Returns:
        The unzipped data.
    """
    with ZipFile(BytesIO(data)) as zipped_data:
        return zipped_data.read(zipped_data.infolist()[0])


def _process_single_csv_row(row: str, separator: str = ",") -> List[str]:
    """Processes a single CSV row.

    Args:
        row: The CSV row.
        separator: The CSV separator.

    Returns:
        A list of values.
    """
    return [v.strip() for v in row.split(separator)]


def _split_csv_rows(data: bytes, separator: str = ",") -> Iterator[List[str]]:
    """Splits a CSV file into rows.

    Args:
        data: The CSV data.
        separator: The CSV separator.

    Yields:
        A list of values for each row.
    """
    for row in data.decode().splitlines():
        yield _process_single_csv_row(row, separator)


@dataclasses.dataclass
class OrderedDomain:
    order: int
    domain: str

    def __repr__(self) -> str:
        return f"{self.order}: {self.domain}"

    @staticmethod
    def from_csv_row(row: List[str]) -> OrderedDomain:
        """Creates an OrderedDomain from a CSV row.

        Args:
            row: CSV row.

        Yields:
            An OrderedDomain for each row.
        """
        if len(row) != 2:
            raise CiscoUmbrellaManagerError(f"Invalid CSV row: {row}")
        return OrderedDomain(order=int(row[0]), domain=row[1])


@dataclasses.dataclass
class Asset:
    """Represents a static asset.

    Attributes:
        path: The path to the asset.
        processors: A list of processors to apply to the asset.
    """

    path: str
    processors: list[Callable[..., Any]]

    def __str__(self) -> str:
        return self.path


class StaticAssets(Enum):
    """Enum for static assets."""

    TOP_1M_CSV_ZIP = Asset(
        path="top-1m.csv.zip",
        processors=[_unzip, _split_csv_rows, partial(map, OrderedDomain.from_csv_row)],
    )
    TOP_1M_TLD_CSV_ZIP = Asset(
        path="top-1m-TLD.csv.zip",
        processors=[_unzip, _split_csv_rows, partial(map, OrderedDomain.from_csv_row)],
    )

    def __str__(self) -> str:
        return str(self.value)


class CiscoUmbrellaStaticResourcesManager:
    """Manages Cisco Umbrella static resources."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        logger: Optional[logging.Logger] = None,
        session: Optional[Session] = None,
    ):
        """Initializes the manager.

        Args:
            base_url: The base URL for the static resources.
            logger: The logger to use.
            session: The session to use.
        """
        self._base_url = base_url
        self._session = session or Session()
        self._logger = logger or logging.getLogger(self.__class__.__name__)

    def get_asset(self, asset: StaticAssets) -> Iterator[Any]:
        """Gets a static asset.

        Args:
            asset: The asset to get.

        Yields:
            The processed asset data.
        """
        response_iterator: Any = self._fetch_asset(asset)
        for processor in asset.value.processors:
            response_iterator = processor(response_iterator)
        yield from response_iterator

    def _fetch_asset(self, asset: StaticAssets) -> bytes:
        """Fetches a static asset.

        Args:
            asset: The asset to fetch.

        Returns:
            The asset data.
        """
        asset_url = self._base_url + str(asset)
        self._logger.info(f"Fetching asset: {asset_url}")
        response = self._session.get(asset_url)
        CiscoUmbrellaStaticResourcesManager._validate_response(response)
        return response.content

    @staticmethod
    def _validate_response(response: Response) -> None:
        """Validates a response.

        Args:
            response: The response to validate.

        Raises:
            CiscoUmbrellaManagerError: If the response is not valid.
        """
        try:
            response.raise_for_status()
        except HTTPError as err:
            raise CiscoUmbrellaManagerError(err) from err
