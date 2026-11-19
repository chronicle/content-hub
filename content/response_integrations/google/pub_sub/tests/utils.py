import re

from integration_testing.request import HttpMethod
from integration_testing.requests.session import HistoryRecord


def assert_get_subscription(
    history_records: list[HistoryRecord],
    index: int = 0,
):
    """Assert that a history record on given index is a get sub request."""
    assert re.search(
        r"/v1/projects/test-project/subscriptions/([a-zA-Z]|-)+",
        history_records[index].request.url.path
    )
    assert history_records[index].request.method == HttpMethod.GET

def assert_pull_messages(
    history_records: list[HistoryRecord],
    index: int = 0,
):
    """Assert that a history record on given index is a pull messages request."""
    assert re.search(
        r"/v1/projects/test-project/subscriptions/([a-zA-Z]|-)+:pull",
        history_records[index].request.url.path
    )
    assert history_records[index].request.method == HttpMethod.POST

def assert_ack_messages(
    history_records: list[HistoryRecord],
    index: int = 0,
):
    """Assert that a history record on given index is a ack messages request."""
    assert re.search(
        r"/v1/projects/test-project/subscriptions/([a-zA-Z]|-)+:acknowledge",
        history_records[index].request.url.path
    )
    assert history_records[index].request.method == HttpMethod.POST
