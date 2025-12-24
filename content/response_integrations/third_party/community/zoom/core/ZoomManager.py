from __future__ import annotations

import logging
from http import HTTPStatus

import arrow
import requests

from .constants import (
    API_ROOT,
    AUTO_RECORDING_TYPES,
    HEADERS,
    OAUTH_TOKEN_URL,
    SUPPORTED_MEETING_TYPES,
    TIMEZONES,
    USER_TYPES,
    Meeting,
    UserAction,
)


class ZoomAPIError(Exception):
    """Couldn't get correct response from Zoom API"""

    @classmethod
    def invalid_json(cls, response: requests.Response):
        """Formats information about wrong response to a user-friendly representation.
        Used if the response doesn't contain a valid json
        """
        return cls(
            f"Response from {response.url} is not a valid json: {response.content}",
        )


class UserAlreadyExists(Exception):
    """Trying to create a user for already existing credentials"""


class NotFoundError(Exception):
    """Trying to perform an action for not existing resource"""


class ZoomManager:
    """Zoom Manager"""

    # TODO: jwt auth support wil be deprecated in june 2023.
    def __init__(
        self,
        jwt_token: str = None,
        account_id: str = None,
        client_id: str = None,
        client_secret: str = None,
        logger: logging.Logger = None,
    ):
        """- Zoom JWT_ authentication docs.
        - Zoom OAuth_ docs.

        :param jwt_token: for JWT authentication.
        :param account_id: for OAuth authentication.
        :param client_id: for OAuth authentication.
        :param client_secret: for OAuth authentication.
        :param logger: if a custom logger must be used
        :raises IOError: If not enough arguments provided.

        .. _JWT: https://marketplace.zoom.us/docs/api-reference/using-zoom-apis/#using-jwt-apps
        .. _OAuth: https://marketplace.zoom.us/docs/guides/build/server-to-server-oauth-app/
        """
        self.session: requests.Session = requests.Session()
        self.session.headers.update(HEADERS)
        self.logger = logger or logging.getLogger(__name__)

        if all((account_id, client_id, client_secret)):
            self.logger.info("Authentication: using OAuth credentials")
            self.login(account_id, client_id, client_secret)
        elif jwt_token:  # Remove after completely moving to oAuth
            self.logger.info("Authentication: using JWT token")
            self.jwt_token = jwt_token
            self.session.headers["Authorization"] = f"Bearer {jwt_token}"
        else:  # Since all creds are optional, make sure at least one is provided
            raise OSError(
                "Missing credentials. "
                "Either jwt_token or (account_id, client_id, client_secret) must be provided",
            )

    def login(self, account_id: str, client_id: str, client_secret: str):
        """Login to Zoom

        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.
        """
        params = {"grant_type": "account_credentials", "account_id": account_id}
        try:
            self.logger.info(
                f"Authentication: requesting access token, params: {params}",
            )
            response = self.session.post(
                OAUTH_TOKEN_URL,
                params=params,
                auth=(client_id, client_secret),
            )
        except Exception as e:
            raise requests.ConnectionError(
                "Error during http request \n"
                f"URL: {OAUTH_TOKEN_URL} \n"
                f"params: {params} \n"
                f"error: {e}",
            )

        if response.status_code != HTTPStatus.OK:
            raise ZoomAPIError(
                "Authentication: "
                f"Unexpected response status code: {response.status_code} \n"
                f"Content: {response.content} \n"
                f"Url: {OAUTH_TOKEN_URL} \n"
                f"Params: {params} \n"
                f"Client ID: {client_id} \n"
                f"Client Secret: {client_secret}",
            )
        try:
            access_token = response.json().get("access_token")
        except Exception:
            raise ZoomAPIError.invalid_json(response)

        if not access_token:
            raise ZoomAPIError(
                f"Access token not provided in response: {response.json()}",
            )

        self.session.headers["Authorization"] = f"Bearer {access_token}"

        self.logger.info("Authentication: success")

    def test_connectivity(self) -> bool:
        """Test connectivity to Zoom

        :return: True if successful, exception otherwise.
        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.
        """
        url = f"{API_ROOT}/users?status=active&page_size=30&page_number=1"
        response_json = self._get_request(url)
        if not response_json:
            raise ZoomAPIError(
                "Test connectivity: Response doesn't contain any content",
            )
        return True

    def get_user_details(self, user_email: str) -> dict:
        """Getting a specific user details. Returns data according to endpoint documentation_

        :return: Response from api endpoint deserialized to dict
        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.
        :raises NotFoundError: Couldn't find requested user details

        .. _documentation: https://marketplace.zoom.us/docs/api-reference/zoom-api/methods/#operation/user
        """
        url = f"{API_ROOT}/users/{user_email}"
        path_params = {"id": user_email}
        return self._get_request(url, path_params)

    def list_meetings(self, user_email: str) -> dict | None:
        """Listing all the user's meetings saved on cloud. Returns data according to endpoint documentation_

        :return: Response from api endpoint deserialized to dict if any meetings planned.
        Else returns None
        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.

        .. _documentation: https://marketplace.zoom.us/docs/api-reference/zoom-api/methods/#operation/meetings
        """
        list_meeting_url = f"{API_ROOT}/users/{user_email}/meetings"
        response_json = self._get_request(list_meeting_url)
        return response_json if response_json.get("total_records") else None

    def list_webinars(self, user_email: str) -> dict | None:
        """Listing all the user's webinars saved on cloud. Returns data according to endpoint documentation_

        :return: Response from api endpoint deserialized to dict if any webinar found.
        Else returns None
        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.

        .. _documentation: https://marketplace.zoom.us/docs/api-reference/zoom-api/methods/#operation/webinars
        """
        list_webinars_url = f"{API_ROOT}/users/{user_email}/webinars"
        response_json = self._get_request(list_webinars_url)
        return (
            None
            if "Webinar plan is missing" in response_json.get("message")
            else response_json
        )

    def list_recordings(self, user_email: str) -> dict | None:
        """Listing all the user's recordings saved on cloud. Returns data according to endpoint documentation_

        :return: Response from api endpoint deserialized to dict if any records found.
        Else returns None
        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.

        .. _documentation: https://marketplace.zoom.us/docs/api-reference/zoom-api/methods/#operation/recordingsList
        """
        list_all_recordings_url = f"{API_ROOT}/users/{user_email}/recordings"
        response_json = self._get_request(list_all_recordings_url)
        return response_json if response_json.get("total_records") else None

    def create_meeting(
        self,
        meeting_topic: str,
        meeting_type: str,
        meeting_start_time: str,
        meeting_duration: str,
        timezone: str,
        auto_record_meeting_type: str,
        host_email: str,
    ) -> dict:
        """Create a Zoom meeting. Returns data according to endpoint documentation_

        :return: Response from api endpoint deserialized to dict if any records found.
        :raises IOError: invalid input

        .. _documentation: https://marketplace.zoom.us/docs/api-reference/zoom-api/methods/#operation/meetingCreate
        """
        if meeting_type not in SUPPORTED_MEETING_TYPES.keys():
            raise OSError(
                f"Meeting type should be one of {SUPPORTED_MEETING_TYPES.keys()}",
            )

        if auto_record_meeting_type not in AUTO_RECORDING_TYPES:
            raise OSError(
                f"Auto recording type should be one of {AUTO_RECORDING_TYPES}",
            )

        if meeting_type == Meeting.SCHEDULED:
            self.logger.info('Meeting type is "scheduled". Parsing start_time')

            if timezone and timezone not in TIMEZONES:
                raise OSError(f"Timezone should be one of {TIMEZONES}")

            meeting_start_time = arrow.get(meeting_start_time, "YYYY-MM-DD HH:mm:ss")

        create_meeting_url = f"{API_ROOT}/users/{host_email}/meetings"

        payload = {
            "topic": meeting_topic,
            "type": SUPPORTED_MEETING_TYPES.get(meeting_type),
            "start_time": str(meeting_start_time),
            "duration": meeting_duration,
            "timezone": timezone,
            "settings": {"auto_recording": auto_record_meeting_type},
        }

        try:
            self.logger.info(
                f"Performing POST request. URL: {create_meeting_url}, payload: {payload}",
            )
            response = self.session.post(create_meeting_url, json=payload)
        except Exception as e:
            raise requests.ConnectionError(
                "Error during http request \n"
                f"URL: {create_meeting_url} \n"
                f"Payload: {payload} \n"
                f"Error: {e}",
            )

        if response.status_code != HTTPStatus.CREATED:
            if response.status_code is HTTPStatus.NOT_FOUND:
                raise NotFoundError(f"Cannot create a meeting: {response.content}")
            if response.status_code is HTTPStatus.MULTIPLE_CHOICES:
                raise ZoomAPIError(
                    "Maximum limit of meetings created by user per day is reached",
                )
            raise ZoomAPIError(
                "Unexpected response from Zoom API \n"
                f"Status code: {response.status_code} \n"
                f"Content: {response.content} \n"
                f"URL: {create_meeting_url} \n"
                f"Payload: {payload}",
            )

        try:
            return response.json()
        except Exception:
            raise ZoomAPIError.invalid_json(response)

    def create_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        user_type: str,
    ) -> dict:
        """Creating a new user in zoom. Returns data according to API documentation_

        :param user_type: One of the values: ("Basic", "Licensed", "On-prem")

        :raises IOError: invalid input
        :raises UserAlreadyExists: Trying to create a user, whose email already registered
        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.

        .. _documentation: https://marketplace.zoom.us/docs/api-reference/zoom-api/methods/#operation/userCreate
        """
        try:
            if self.get_user_details(email).get("email") == email:
                raise UserAlreadyExists(f"The user {email} already exists")
        except NotFoundError:  # Raised when user not found, this is a normal flow here
            pass

        if user_type not in USER_TYPES.keys():
            raise OSError(f"User type should be one of {USER_TYPES}")

        create_user_url = f"{API_ROOT}/users"

        payload = {
            "action": "create",
            "user_info": {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "type": USER_TYPES[user_type],
            },
        }

        try:
            self.logger.info(
                f"Performing POST request. URL: {create_user_url}, payload: {payload}",
            )
            response = self.session.post(create_user_url, json=payload)
        except Exception as e:
            raise requests.ConnectionError(
                "Trying to create a user \n"
                f"URL: {create_user_url} \n"
                f"Payload: {payload} \n"
                f"Error: {e}",
            )

        if response.status_code != HTTPStatus.CREATED:
            # Probably a lot of http statuses may be returned, so no point of specifying if
            raise ZoomAPIError(
                "Unexpected response from Zoom API \n"
                f"Status code: {response.status_code} \n"
                f"Content: {response.text} \n"
                f"URL: {create_user_url} \n"
                f"Payload: {payload}",
            )

        try:
            return response.json()
        except Exception:
            raise ZoomAPIError.invalid_json(response)

    def delete_user(
        self,
        user_email: str,
        transfer_recording: str,
        transfer_webinar: str,
        transfer_meeting: str,
        transfer_email: str,
    ) -> bytes:
        """This method does not permanently delete the user, but disassociating the user. API documentation_
        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.
        :raises UserNotFound: Trying to delete a user, whose email doesn't registered.

        .. _documentation: https://marketplace.zoom.us/docs/api-reference/zoom-api/methods/#operation/userDelete
        """
        action = UserAction.DELETE
        user_email = user_email.strip()
        transfer_email = transfer_email.strip()

        delete_user_url = (
            f"{API_ROOT}/Users/{user_email}"
            f"?action={action}"
            f"&transfer_email={transfer_email}"
            f"&transfer_meeting={transfer_meeting}"
            f"&transfer_recording={transfer_recording}"
            f"&transfer_webinar={transfer_webinar}"
        )

        try:
            self.logger.info(f"Performing POST request. URL: {delete_user_url}")
            response = self.session.delete(delete_user_url)
        except Exception as e:
            raise requests.ConnectionError(
                f"Trying to delete a user \nURL: {delete_user_url} \nError: {e}",
            )

        if response.status_code != HTTPStatus.NO_CONTENT:
            if response.status_code == HTTPStatus.NOT_FOUND:
                raise NotFoundError(f"User with email {user_email} not found")
            raise ZoomAPIError(
                "Unexpected response from Zoom API \n"
                f"Status code: {response.status_code} \n"
                f"Content: {response.text} \n"
                f"URL: {delete_user_url} \n",
            )

        return response.content

    def get_meeting_detail(self, meeting_id: str) -> dict:
        """Getting all the meeting details in json. Past or future meetings. API documentation_

        :return: Response from api endpoint deserialized to dict according to API
        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.

        .. _documentation: https://marketplace.zoom.us/docs/api-reference/zoom-api/methods/#operation/meeting
        """
        get_meeting_detail_url = f"{API_ROOT}/meetings/{meeting_id}"
        response_json = self._get_request(get_meeting_detail_url)
        return response_json

    def get_meeting_recording(self, meeting_id: str) -> dict:
        """Get the meeting record. Only the recordings on cloud. API documentation_

        :return: Response from api endpoint deserialized to dict according to API
        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.

        .. _documentation: https://marketplace.zoom.us/docs/api-reference/zoom-api/methods/#operation/recordingGet
        """
        get_meeting_recording_url = f"{API_ROOT}/meetings/{meeting_id}/recordings"
        response_json = self._get_request(get_meeting_recording_url)
        return response_json

    def _get_request(self, url: str, path_params: dict = None) -> dict:
        """Process GET request to a given url and handle possible exceptions

        :return: Response from api endpoint deserialized to dict

        :raises requests.ConnectionError: Couldn't get response from Zoom server.
        :raises ZoomAPIError: API response doesn't match expected pattern.
        """
        try:
            self.logger.info(
                f"Performing GET request. URL: {url}, path_params: {path_params}",
            )
            response = self.session.get(url, json=path_params)
        except Exception as e:
            raise requests.ConnectionError(
                f"Error querying Zoom API \n"
                f"URL: {url} \n"
                f"Path parameters: {path_params} \n"
                f"Error: {e}",
            )

        if response.status_code != HTTPStatus.OK:
            if response.status_code == HTTPStatus.NOT_FOUND:
                raise NotFoundError(
                    "Requested resource not found. \n"
                    f"URL: {url} \n"
                    f"Content: {response.text}",
                )

            raise ZoomAPIError(
                f"Unexpected response status code: {response.status_code} \n"
                f"Url: {url} \n"
                f"Content: {response.text} \n",
            )

        try:
            return response.json()
        except Exception:
            raise ZoomAPIError.invalid_json(response)
