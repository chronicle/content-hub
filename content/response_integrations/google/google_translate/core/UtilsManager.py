from __future__ import annotations
import requests
from .GoogleTranslateExceptions import GoogleTranslateException
from .constants import FILTER_KEY_MAPPING, FILTER_STRATEGY_MAPPING


def validate_response(response, api_key, error_msg="An error occurred"):
    """
    Validate response
    :param response: {requests.Response} The response to validate
    :param error_msg: {unicode} Default message to display on error
    """
    try:
        response.url = response.url.replace(api_key, "******")
        response.raise_for_status()
    except requests.HTTPError as error:
        try:
            response.json()
        except Exception:
            raise GoogleTranslateException(f"{error_msg}: {error.response.content}")

        raise GoogleTranslateException(
            f"{error_msg}: {response.json().get('error', {}).get('message') or response.content}"
        )


def filter_items(
    items, filter_key=None, filter_logic=None, filter_value=None, limit=None
):
    """
    Filter list of items
    :param items: {list} list of items to filter
    :param filter_key: {str} filter key that should be used for filtering
    :param filter_logic: {str} filter logic that should be applied
    :param filter_value: {str} filter value that should be used for filtering
    :param limit: {int} limit for items
    """
    if (
        FILTER_KEY_MAPPING.get(filter_key)
        and FILTER_STRATEGY_MAPPING.get(filter_logic)
        and filter_value
    ):
        items = [
            item
            for item in items
            if FILTER_STRATEGY_MAPPING[filter_logic](
                getattr(item, FILTER_KEY_MAPPING.get(filter_key)), filter_value
            )
        ]

    return items[:limit] if limit else items
