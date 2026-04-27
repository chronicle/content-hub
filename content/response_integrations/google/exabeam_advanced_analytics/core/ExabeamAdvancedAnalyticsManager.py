# ============================================================================#
# title           :ExabeamAdvancedAnalyticsManager.py
# description     :This Module contain all Exabeam Advanced Analytics operations functionality
# author          :gabriel.munits@siemplify.co
# date            :18-01-2021
# python_version  :3.7
# product_version :1.0
# ============================================================================#

from __future__ import annotations
from typing import List, Optional, Union
from urllib.parse import urljoin

# ============================= IMPORTS ===================================== #
import requests
from . import datamodels
from .ExabeamAdvancedAnalyticsParser import ExabeamAdvancedAnalyticsParser
from .consts import (
    INTEGRATION_DISPLAY_NAME,
    WATCHLIST_USERS_TYPE,
    DEFAULT_WATCHLIST_LIST_ITEMS_MAX_DAYS_BACKWARDS,
    ENTITY_USER_TYPE,
)
from .exceptions import (
    ExabeamAdvancedAnalyticsManagerError,
    ExabeamAdvancedAnalyticsUnsuccessfulOperationError,
)
from .utils import remove_empty_kwargs


# ============================= CONSTS ===================================== #

ENDPOINTS = {
    "get_session_cookies": "api/auth/login",
    "ping": "uba/api/ping",
    "list_watchlists": "uba/api/watchlist",
    "add_entity_comment": "uba/api/comments/add",
    "get_users_watchlist_details": "uba/api/watchlist/users/{watchlist_id}/",
    "get_assets_watchlist_details": "uba/api/watchlist/assets/{watchlist_id}/",
    "add_entities_to_watchlist": "uba/api/watchlist/{watchlist_id}/add",
    "create_watchlist": "uba/api/watchlist",
    "remove_entities_from_watchlist": "uba/api/watchlist/{watchlist_id}/remove",
    "delete_watchlist": "uba/api/watchlist/{watchlist_id}/",
    "get_entity_comments": "uba/api/comments/get",
    "get_asset_sequences": "uba/api/asset/{asset_id}/sequences",
    "get_user_sequences": "uba/api/user/{username}/sequences",
    "get_asset_details": "uba/api/asset/{asset_id}/info",
    "get_user_details": "uba/api/user/{username}/info",
    "get_user_timeline_events": "uba/api/timeline/events/start",
    "get_asset_timeline_events": "uba/api/asset/timeline/events/start",
    "get_notable_users": "uba/api/users/notable",
    "get_notable_assets": "uba/api/assets/notable",
}


# ============================= CLASSES ===================================== #


class ExabeamAdvancedAnalyticsManager:
    """
    Exabeam Advanced Analytics Manager
    """

    def __init__(self, api_root: str, verify_ssl: bool, api_token: str, logger=None):
        """
        The method is used to instantiate an object of Manager class
        :param api_root: {str} The API root of the Exabeam Advanced Analytics instance.
        :param username: {str} The username of the Exabeam Advanced Analytics account.
        :param password: {str} The password of the Exabeam Advanced Analytics account.
        :param verify_ssl: {bool} True if to verify the SSL certificate for the connection to the Exabeam Advanced Analytics server.
        Otherwise False
        """
        self.api_root = api_root if api_root.endswith("/") else api_root + "/"
        self.api_token = api_token
        self.verify_ssl = verify_ssl
        self.logger = logger

        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = {"Csrf-Token": "nocheck", "ExaAuthToken": api_token}

        self.parser = ExabeamAdvancedAnalyticsParser()

    def _get_full_url(self, url_key, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_key].format(**kwargs))

    def test_connectivity(self):
        """
        Test connectivity with Exabeam Advanced Analytics server
        :return: raise Exception if failed to validate response
        """
        request_url = self._get_full_url("ping")
        response = self.session.get(request_url)
        self.validate_response(
            response,
            error_msg=f"Failed to connect to {INTEGRATION_DISPLAY_NAME} server",
        )

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate a response
        :param response: {requests.Response} The response
        :param error_msg: {str} The error message to display on failure
        """
        try:

            response.raise_for_status()

        except requests.HTTPError as error:
            try:
                response.json()
                raise ExabeamAdvancedAnalyticsManagerError(
                    f"{error_msg}: {error} {response.json()}"
                )
            except ExabeamAdvancedAnalyticsManagerError:
                raise

            except:
                raise ExabeamAdvancedAnalyticsManagerError(
                    f"{error_msg}: {error} - {response.text}"
                )

    def list_watchlists(
        self, max_results: Optional[int] = None
    ) -> List[datamodels.Watchlist]:
        """
        List available watchlists in Exabeam Advanced Analytics.
        :param max_results: {int} Max watchlists to return. If nothing is specified all available watchlists will be returned.
        :return:  {[datamodels.Watchlist]} List of watch lists data models
        """
        request_url = self._get_full_url("list_watchlists")
        response = self.session.get(request_url)
        self.validate_response(
            response,
            error_msg=f"Failed to list watchlists in {INTEGRATION_DISPLAY_NAME}",
        )
        return self.parser.build_watchlist_obj_list(response.json(), limit=max_results)

    def add_entity_comment(
        self, entity_type: str, entity_identifier: str, comment: str
    ) -> datamodels.EntityComment:
        """
        Add entity comment.
        :param entity_type: {str} Entity type, can be "user" of "asset"
        :param entity_identifier: {str} Entity unique identifier
        :param comment: {str} The comment to add
        :return: {datamodels.EntityComment} An EntityComment data models representing the created comment
        """
        request_url = self._get_full_url("add_entity_comment")
        payload = {
            "commentObjectType": entity_type,
            "commentObjectId": entity_identifier.lower(),
            "commentText": comment,
        }
        response = self.session.post(request_url, data=payload)
        self.validate_response(
            response, error_msg=f"Failed to add comment to entity {entity_identifier}"
        )
        return self.parser.build_entity_comment_obj(response.json())

    def get_users_watchlist_details(
        self, watchlist_id: str, max_days_backwards: int, limit: int
    ) -> datamodels.UsersWatchlistDetails:
        """
        Get Users watchlist
        :param watchlist_id: {int} Watchlist unique identifier
        :param max_days_backwards: {int} Max days backwards to fetch items from
        :param limit: {int} Max items to return in a watchlist
        :return: {datamodels.UsersWatchlistDetails} UsersWatchlistDetails data model
        """
        request_url = self._get_full_url(
            "get_users_watchlist_details", watchlist_id=watchlist_id
        )
        payload = {"numberOfResults": limit, "unit": "d", "num": max_days_backwards}
        response = self.session.get(request_url, params=payload)
        self.validate_response(
            response,
            error_msg=f"Failed to get details of users watchlist {watchlist_id}",
        )
        return self.parser.build_users_watchlist_obj(response.json())

    def get_assets_watchlist_details(
        self, watchlist_id, max_days_backwards: int, limit: int
    ) -> datamodels.AssetsWatchlistDetails:
        """
        Get Assets watchlist
        :param watchlist_id: {int} Watchlist unique identifier
        :param max_days_backwards: {int} Max days backwards to fetch items from
        :param limit: {int} Max items to return in a watchlist
        :return: {datamodels.AssetsWatchlistDetails} AssetsWatchlistDetails data model
        """
        request_url = self._get_full_url(
            "get_assets_watchlist_details", watchlist_id=watchlist_id
        )
        payload = {"numberOfResults": limit, "unit": "d", "num": max_days_backwards}
        response = self.session.get(request_url, params=payload)
        self.validate_response(
            response,
            error_msg=f"Failed to get details of assets watchlist {watchlist_id}",
        )
        return self.parser.build_assets_watchlist_obj(response.json())

    def get_watchlist(
        self,
        watchlist_type: str,
        watchlist_id,
        items_limit: int,
        max_days_backwards: Optional[
            int
        ] = DEFAULT_WATCHLIST_LIST_ITEMS_MAX_DAYS_BACKWARDS,
    ) -> Union[datamodels.UsersWatchlistDetails, datamodels.AssetsWatchlistDetails]:
        """
        Get Assets or Users watchlist
        :param watchlist_type: {str} Watchlist type, can be "users" or "assets"
        :param watchlist_id: {int} Watchlist unique identifier
        :param max_days_backwards: {int} Max days backwards to list items
        :param items_limit: {int} Max items to return in a watchlist
        :return: {datamodels.UsersWatchlistDetails / datamodels.AssetsWatchlistDetails} UsersWatchlistDetails or AssetsWatchlistDetails
            data models.
        """
        if watchlist_type == WATCHLIST_USERS_TYPE:
            return self.get_users_watchlist_details(
                watchlist_id, max_days_backwards, items_limit
            )

        return self.get_assets_watchlist_details(
            watchlist_id, max_days_backwards, items_limit
        )

    def add_entities_to_watchlist(
        self, watchlist_id: str, watchlist_category: str, entities: List[str]
    ) -> int:
        """
        Add entities to a watchlist
        :param watchlist_id: {str} Watchlist unique identifier
        :param watchlist_category: {str} Watchlist category, can be only "Users" or "Assets"
        :param entities: {[str]} List of entities to add
        :return: {int} Number of successfully added entities
        """
        request_url = self._get_full_url(
            "add_entities_to_watchlist", watchlist_id=watchlist_id
        )
        payload = {
            "items[]": [
                entity.lower() for entity in entities
            ],  # Entities must be passed as lower cased
            "category": watchlist_category,
        }
        response = self.session.put(request_url, data=payload)
        self.validate_response(
            response, error_msg=f"Failed to add entities to watchlist {watchlist_id}"
        )
        return response.json().get("numberAdded", 0)

    def create_watchlist(
        self,
        watchlist_title: str,
        watchlist_category: str,
        watchlist_access_control: str,
        watchlist_description: Optional[str] = None,
    ) -> datamodels.Watchlist:
        """
        Create a watchlist
        :param watchlist_title: {str} Watchlist title
        :param watchlist_category: {str} Watchlist category. Can be 'Users', 'Assets', 'UserLabels' or 'AssetLabels'
        :param watchlist_access_control: {str} Watchlist access control permissions. Can be 'public' or 'private'
        :param watchlist_description: {str} Watchlist description
        :return:
                raise ExabeamAdvancedAnalyticsUnsuccessfulOperationError if failed to create watchlist
                raise ExabeamAdvancedAnalyticsManagerError exception if failed to validate response
        """
        request_url = self._get_full_url("create_watchlist")
        payload = {
            "title": watchlist_title,
            "category": watchlist_category,
            "items": [],
            "description": watchlist_description,
            "accessControl": watchlist_access_control,
        }
        response = self.session.post(request_url, json=remove_empty_kwargs(**payload))
        try:
            if response.json().get("_apiErrorCode"):
                raise ExabeamAdvancedAnalyticsUnsuccessfulOperationError(
                    response.json().get("internalError")
                )
        except ExabeamAdvancedAnalyticsUnsuccessfulOperationError:
            raise
        except Exception:
            pass
        self.validate_response(
            response, error_msg=f"Failed to create watchlist {watchlist_title}"
        )
        return self.parser.build_watchlist_obj(response.json())

    def remove_entities_from_watchlist(
        self, watchlist_id: str, watchlist_category: str, entities: List[str]
    ) -> int:
        """
        Remove entities from a watchlist
        :param watchlist_id: {str} Watchlist unique identifier
        :param watchlist_category: {str} Watchlist category, can be only "Users" or "Assets"
        :param entities: {[str]} List of entities to remove
        :return: {int} Number of successfully removed entities
        """
        request_url = self._get_full_url(
            "remove_entities_from_watchlist", watchlist_id=watchlist_id
        )
        payload = {
            "items[]": [
                entity.lower() for entity in entities
            ],  # Entities must be passed as lower cased
            "category": watchlist_category,
        }
        response = self.session.put(request_url, data=payload)
        self.validate_response(
            response,
            error_msg=f"Failed to remove entities from watchlist {watchlist_id}",
        )
        return response.json().get("numberRemoved", 0)

    def delete_watchlist(self, watchlist_id: str):
        """
        Delete a watchlist
        :param watchlist_id: {str} Watchlist id
        :return: raise ExabeamAdvancedAnalyticsManagerError exception if failed to validate response
        """
        request_url = self._get_full_url("delete_watchlist", watchlist_id=watchlist_id)
        response = self.session.delete(request_url)
        self.validate_response(
            response, error_msg=f"Failed to delete watchlist with id {watchlist_id}"
        )

    def get_user_details(self, username) -> datamodels.UserDetails:
        """
        Get user details
        :param username: {str} Username for which to fetch details
        :return: {datamodels.UserDetails} User details data model
        """
        request_url = self._get_full_url("get_user_details", username=username.lower())
        payload = {"maxNumberOfUsers": 1}
        response = self.session.get(request_url, params=payload)
        self.validate_response(
            response, error_msg=f"Failed to get details for user {username}"
        )
        return self.parser.build_user_details_obj(
            response.json(), api_root=self.api_root
        )

    def get_asset_details(self, asset_id) -> datamodels.AssetDetails:
        """
        Get asset details
        :param asset_id: {str} Asset for which to fetch details
        :return: {datamodels.AssetDetails} Asset details data model
        """
        request_url = self._get_full_url("get_asset_details", asset_id=asset_id.lower())
        payload = {"maxNumberOfUsers": 1}
        response = self.session.get(request_url, params=payload)
        self.validate_response(
            response, error_msg=f"Failed to get details for asset {asset_id}"
        )
        return self.parser.build_asset_details_obj(
            response.json(), api_root=self.api_root
        )

    def get_entity_details(
        self, entity_type: str, entity_identifier
    ) -> Union[datamodels.UserDetails, datamodels.AssetDetails]:
        """
        Get entity details
        :param entity_type: {str} Can be 'user' or 'asset'. 'user' referring to entities of type User and 'asset' refers to entities of
        type IP address or Hostnames
        :param entity_identifier: {str} entity identifier
        :return: {datamodels.UserDetails or datamodels.AssetDetails} UserDetails data model if entity type is 'user', otherwise
            AssetDetails
        """
        if entity_type == ENTITY_USER_TYPE:
            return self.get_user_details(username=entity_identifier.strip())
        return self.get_asset_details(asset_id=entity_identifier.strip())

    def get_entity_comments(
        self, entity_type: str, entity_identifier: str, limit: Optional[int] = None
    ) -> List[datamodels.EntityComment]:
        """
        Get entity comments. Comments will be returned from newest to oldest.
        :param entity_type: {str} Entity type, can be "user" of "asset"
        :param entity_identifier: {str} Entity unique identifier
        :param limit: {int} Max comments to return. If limit is not specified all comments will be returned
        :return: {[datamodels.EntityComment]} List of EntityComment data models representing comments of the entity
        """
        request_url = self._get_full_url("get_entity_comments")
        params = {
            "commentObjectType": entity_type,
            "commentObjectId": entity_identifier.lower(),
        }
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to get comments for entity {entity_identifier}"
        )
        comments = sorted(
            self.parser.build_entity_comment_obj_list(response.json()),
            key=lambda comment: comment.create_time,
            reverse=True,
        )

        return comments[:limit] if limit is not None else comments

    def get_user_sequences(
        self, username: str, start_time: int, end_time: int
    ) -> datamodels.UserSequences:
        """
        Get user timeline sequence data
        :param username: {str} Username for which to fetch sequence data
        :param start_time: {int} Start unix timestamp of a sequence in milliseconds.
        :param end_time: {int} End unix timestamp of a sequence in milliseconds.
        :return: {datamodels.UserSequences} User sequences data model
        """
        request_url = self._get_full_url(
            "get_user_sequences", username=username.lower()
        )
        payload = {"startTime": start_time, "endTime": end_time}
        response = self.session.get(request_url, params=payload)
        self.validate_response(
            response, error_msg=f"Failed to get sequences for user {username}"
        )

        return self.parser.build_user_sequences_obj(response.json())

    def get_asset_sequences(
        self, asset_id: str, start_time: int, end_time: int
    ) -> datamodels.AssetSequences:
        """
        Get asset timeline sequence data
        :param asset_id: {str} Asset's id
        :param start_time: {int} Start unix timestamp of a sequence in milliseconds.
        :param end_time: {int} End unix timestamp of a sequence in milliseconds.
        :return: {datamodels.AssetSequences} Asset sequences data model
        """
        request_url = self._get_full_url(
            "get_asset_sequences", asset_id=asset_id.lower()
        )
        payload = {"startTime": start_time, "endTime": end_time}
        response = self.session.get(request_url, params=payload)
        self.validate_response(
            response, error_msg=f"Failed to get sequences for asset {asset_id}"
        )

        return self.parser.build_asset_sequences_obj(response.json())

    def get_entity_sequences(
        self, entity_type: str, entity_identifier: str, start_time: int, end_time: int
    ) -> Union[datamodels.UserSequences, datamodels.AssetSequences]:
        """
        Get entity sequences
        :param entity_type: {str} Can be 'user' or 'asset'. 'user' referring to entities of type User and 'asset' refers to entities of
        type IP address or Hostnames
        :param entity_identifier: {str} Entity identifier to get sequences for
        :param start_time: {int} Start unix timestamp of a sequence in milliseconds.
        :param end_time: {int} End unix timestamp of a sequence in milliseconds.
        :return: {datamodels.AssetSequences or datamodels.UserSequences} UserDetails data model if entity type is 'user', otherwise
            AssetDetails
        """
        if entity_type == ENTITY_USER_TYPE:
            return self.get_user_sequences(
                username=entity_identifier.strip(),
                start_time=start_time,
                end_time=end_time,
            )
        return self.get_asset_sequences(
            asset_id=entity_identifier.strip(), start_time=start_time, end_time=end_time
        )

    def get_user_timeline_events(
        self, username: str, sequence_id: str, anomaly_only: bool, limit: int
    ) -> datamodels.UserEvents:
        """
        Get user timeline events, sorted from newest to oldest.
        :param username: {str} The username for which to get timeline events
        :param sequence_id: {str} Sequence id of the events
        :param anomaly_only: {bool} True if to return anomaly events only, otherwise False
        :param limit: {int} Max number of timeline events to return
        :return: {datamodels.UserEvents} User timeline events data model
        """
        request_url = self._get_full_url("get_user_timeline_events")
        params = {
            "username": username.lower(),
            "startSequenceType": "session",
            "startSequenceId": sequence_id,
            "preferredNumberOfEvents": limit,
            "anomalyOnly": "true" if anomaly_only else "false",
            "sequenceTypes": "session",
        }
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to get timeline events for user {username}"
        )

        return self.parser.build_user_events(response.json())

    def get_asset_timeline_events(
        self, asset_id: str, sequence_id: str, anomaly_only: bool, limit: int
    ) -> datamodels.AssetEvents:
        """
        Get asset timeline events
        :param asset_id: {str} Asset's id for which to get timeline events
        :param sequence_id: {str} Sequence id of the events
        :param anomaly_only: {bool} True if to return only anomaly events, otherwise False
        :param limit: {int} Max number of timeline events to return
        :return: {datamodels.AssetEvents} Asset timeline events data model
        """
        request_url = self._get_full_url("get_asset_timeline_events")
        params = {
            "assetId": asset_id.lower(),
            "startSequenceType": "session",
            "startAssetSequenceId": sequence_id,
            "preferredNumberOfEvents": limit,
            "anomalyOnly": "true" if anomaly_only else "false",
            "sequenceTypes": "session",
            "eventTypeInclude": "false",
        }
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to get timeline events for asset {asset_id}"
        )

        return self.parser.build_asset_events(response.json())

    def get_entity_events(
        self,
        entity_type: str,
        entity_identifier: str,
        sequence_id: str,
        anomaly_only: bool,
        limit: int,
    ):
        """
        Get entity events
        :param entity_type: {str} Can be 'user' or 'asset'. 'user' referring to entities of type User and 'asset' refers to entities of
        type IP address or Hostnames
        :param entity_identifier: {str} Entity identifier to events for
        :param sequence_id: {str} Sequence id of the events
        :param anomaly_only: {bool} True if to return only anomaly events, otherwise False
        :param limit: {int} Max number of timeline events to return
        :return: {datamodels.AssetEvents or datamodels.UserEvents} AssetEvents data model if entity type is 'user', otherwise UserEvents
        """
        if entity_type == ENTITY_USER_TYPE:
            return self.get_user_timeline_events(
                username=entity_identifier.strip(),
                sequence_id=sequence_id,
                anomaly_only=anomaly_only,
                limit=limit,
            )
        return self.get_asset_timeline_events(
            asset_id=entity_identifier.strip(),
            sequence_id=sequence_id,
            anomaly_only=anomaly_only,
            limit=limit,
        )

    def get_notable_users(self) -> List[datamodels.NotableUser]:
        """
        Get notable users
        :return: {[NotableUser]} List of notable user data models
        """
        request_url = self._get_full_url("get_notable_users")
        params = {"numberOfResults": 100, "unit": "M", "num": 1}
        response = self.session.get(request_url, params=params)
        self.validate_response(response, error_msg="Failed to get notable users")

        return self.parser.build_notable_users_obj_list(response.json())

    def get_notable_assets(self) -> List[datamodels.NotableAsset]:
        """
        Get notable assets
        :return: {[NotableAsset]} List of notable asset data models
        """
        request_url = self._get_full_url("get_notable_assets")
        params = {"numberOfResults": 100, "unit": "M", "num": 1}
        response = self.session.get(request_url, params=params)
        self.validate_response(response, error_msg="Failed to get notable assets")

        return self.parser.build_notable_asset_obj_list(response.json())
