import unittest.mock

import pytest
from google.cloud.exceptions import GoogleCloudError

from google_big_query.core.GoogleBigQueryManager import (
    GoogleBigQueryApiManager,
    GoogleBigQueryExceptions,
)


def test_init() -> None:
    manager: GoogleBigQueryApiManager = GoogleBigQueryApiManager("proj", None)

    assert manager is not None


class TestTestConnectivity:

    def test_test_connectivity_raises_manager_error_when_fail(self) -> None:
        manager: GoogleBigQueryApiManager = GoogleBigQueryApiManager("proj", None)
        with pytest.raises(
            GoogleBigQueryExceptions.GoogleBigQueryManagerError
        ), unittest.mock.patch.object(
            manager, "list_datasets", side_effect=GoogleCloudError("")
        ):
            manager.test_connectivity()
