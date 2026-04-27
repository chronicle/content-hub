from __future__ import annotations
import os
from slack import WebClient
from slack.errors import SlackApiError

from .SlackTransformationLayer import SlackTransformationLayer
from soar_sdk.SiemplifyUtils import unix_now
from .datamodels import Message

MESSAGE_ATTACHMENTS = [
    {
        "fallback": "Upgrade your Slack client to use messages like these.",
        "color": "#3AA3E3",
        "attachment_type": "default",
        "callback_id": "button_ask1",
        "actions": [
            {"name": "yes", "text": "Yes", "type": "button"},
            {"name": "no", "text": "No", "type": "button"},
        ],
    }
]

PAGE_SIZE = 100
EQUAL = "Equal"
CONTAINS = "Contains"


class BaseURLException(Exception):
    """Exception when base url is not specified"""

    pass


class SlackManagerException(Exception):
    """General Exception for Slack manager"""

    pass


class UserNotFoundException(Exception):
    """Exception when a user was not found"""

    pass


class ChannelNotFoundException(Exception):
    """Exception when a channel was not found"""

    pass


class UserAuthException(Exception):
    """Exception when a user authorization failed"""

    pass


class MaxRecordsException(Exception):
    """Exception when the max records to return is negative"""

    pass


class SlackManager:
    def __init__(self, token, siemplify=None):
        self.client = WebClient(token=token)
        self.tl = SlackTransformationLayer()
        self.siemplify = siemplify

    def __make_request(self, request_method, **kwargs):
        try:
            response = getattr(self.client, request_method)(**kwargs)
        except SlackApiError as e:
            response = e.response
        return response

    def upload_file(self, file_name, file_path, channel):
        """
        Upload file to Slack channel
        :param file_name: {string} Displayed file name
        :param file_path: {string} Path to file.
        :param channel: {string} Name of the channel in Slack.
        :return: {string} Private file url.
        """
        if not os.access(file_path, os.R_OK):
            raise SlackManagerException(f"Permissions denied for path: {file_path}")

        if not os.path.exists(file_path):
            raise SlackManagerException(f"Path {file_path} does not exist")

        response = self.client.files_upload(
            file=file_path, title=file_name, channels=channel
        )

        self._validate_response(response)

        return response.get("file", {}).get("url_private_download")

    def send_message(
        self, channel: str, message: str, message_type: str = "text", **kwargs
    ) -> Message:
        """
        Send message to Slack channel
        :param channel: {string} Name of the channel or User ID in Slack
        :param message: {string} Text to send.
        :param message_type: {string} Message Type to send.
        :return: {Message} Message details
        """
        msg_dict = {"channel": channel, message_type: message}
        kwargs.update(msg_dict)
        response = self.__make_request("chat_postMessage", **kwargs)

        self._validate_response(response)
        return self.tl.build_siemplify_message_obj_from_new_message(response)

    def get_user_details_by_id(self, user_id):
        """
        Get specific user by ID
        :param user_id: {string} ID of the user
        :return: {dict} User details.
        """
        response = self.__make_request("users_info", user=user_id)

        self._validate_response(response)

        return self.tl.build_siemplify_user_obj(response["user"])

    def get_user_details_by_email(self, email):
        """
        Get specific user by email
        :param email: {string} Email of the user
        :return: {User} User details.
        """
        response = self.__make_request("users_lookupByEmail", email=email)

        self._validate_response(response)

        return self.tl.build_siemplify_user_obj(response["user"])

    def list_users(self, max_records_to_return=None):
        """
        Get all Users
        :param max_records_to_return: {int} Number of records
        :return: {list[dict]} All users details.
        """

        kwargs = {"limit": max_records_to_return} if max_records_to_return else {}
        response = self.client.users_list(**kwargs)

        self._validate_response(response)

        users = [
            self.tl.build_siemplify_user_obj(user_data)
            for user_data in response["members"]
        ]

        while response.get("response_metadata", {}).get("next_cursor"):

            if max_records_to_return and len(users) >= max_records_to_return:
                break

            cursor = response.get("response_metadata", {}).get("next_cursor")
            response = self.client.users_list(limit=200, cursor=cursor)

            self._validate_response(response)

            res = [
                self.tl.build_siemplify_user_obj(user_data)
                for user_data in response["members"]
            ]
            users.extend(res)

        return users[:max_records_to_return] if max_records_to_return else users

    @staticmethod
    def get_users_by_name(users, username):
        """
        Get Users by username
        :param users {list[User]} List of users
        :param username: {str} The name of user
        :return: {list[User]} Users details.
        """
        res = []
        for user in users:
            if username.lower() == user.name.lower():
                res.append(user)
        return res

    @staticmethod
    def filter_users_by_real_name(users, search_value):
        """
        Get Users by Real Name
        :param users {list[User]} List of users
        :param search_value: {str} The Real Name of user
        :return: {list[User]} Users details.
        """
        res = []
        for user in users:
            has_user = search_value.lower() == user.real_name.lower()
            if not has_user:
                profile = user.profile
                profile_real_name = profile.real_name if profile else None
                has_user = (
                    search_value.lower() == profile_real_name.lower()
                    if profile_real_name
                    else False
                )
            if has_user:
                res.append(user)
        return res

    @staticmethod
    def get_user_by_name(users, username):
        """
        Get User by username
        :param users {list[User]} List of users
        :param username: {str} The name of user
        :return: {User} User details.
        """
        for user in users:
            if username.lower() == user.name.lower():
                return user
        return None

    def list_channels(self, max_records_to_return=None, types=None):
        """
        Get all Channels
        :param max_records_to_return {int} The Limit of records to return
        :param types: {Any} The list of types
        :return: {list[dict]} All users details.
        """
        common_types = "public_channel,private_channel,mpim,im"
        kwargs = {"limit": max_records_to_return} if max_records_to_return else {}
        response = self.client.conversations_list(
            types=types if types else common_types, **kwargs
        )

        self._validate_response(response)

        channels = [
            self.tl.build_siemplify_channel_obj(channel_data)
            for channel_data in response["channels"]
        ]

        while response.get("response_metadata", {}).get("next_cursor"):

            if max_records_to_return and len(channels) >= max_records_to_return:
                break

            cursor = response.get("response_metadata", {}).get("next_cursor")
            response = self.client.conversations_list(
                limit=200, cursor=cursor, types=types if types else common_types
            )

            self._validate_response(response)

            res = [
                self.tl.build_siemplify_channel_obj(channel_data)
                for channel_data in response["channels"]
            ]
            channels.extend(res)

        return channels[:max_records_to_return] if max_records_to_return else channels

    def get_conversations_history(
        self, channel, max_records_to_return=None, oldest=0, latest=0
    ):
        """
        Get the conversation history of the channel
        :param channel: {string} Conversation ID in Slack to fetch history for
        :param max_records_to_return: {int} Limit of number of records
        :param oldest: {datetime} The timestamp in MILLISECONDS for oldest conversation to fetch
        :param latest: {datetime} The timestamp in MILLISECONDS for latest conversation to fetch
        :return: {list[Message]} List of the Messages.
        """
        latest = latest or unix_now()
        # Convert the milliseconds into seconds
        oldest = oldest / 1000
        latest = latest / 1000
        kwargs = {"channel": channel, "oldest": oldest, "latest": latest}
        if max_records_to_return:
            kwargs.update({"limit": max_records_to_return})
        self.siemplify.LOGGER.info(f"conversations history payload: {kwargs}")
        response = self.__make_request("conversations_history", **kwargs)
        self._validate_response(response)

        conversation_history = [
            self.tl.build_siemplify_message_obj(item) for item in response["messages"]
        ]

        while response.get("response_metadata", {}).get("next_cursor"):

            if len(conversation_history) >= max_records_to_return:
                break

            cursor = response.get("response_metadata", {}).get("next_cursor")
            response = self.__make_request(
                "conversations_history",
                channel=channel,
                limit=100,
                cursor=cursor,
                oldest=oldest,
                latest=latest,
            )
            self._validate_response(response)

            res = [
                self.tl.build_siemplify_message_obj(item)
                for item in response["messages"]
            ]
            conversation_history.extend(res)

        return (
            conversation_history[:max_records_to_return]
            if max_records_to_return
            else conversation_history
        )

    def get_users_conversations(self, user, max_records_to_return=None):
        """
        Get the conversations of users
        :param user: {string} User ID in Slack
        :param max_records_to_return {int} Limit of number of records
        :return: {list[Channel]} List of the Channels.
        """
        search_types = "im"
        kwargs = {"user": user, "types": search_types}
        self.siemplify.LOGGER.info(f"users conversations payload: {kwargs}")
        response = self.__make_request("users_conversations", **kwargs)
        self._validate_response(response)

        conversations = [
            self.tl.build_siemplify_channel_obj(item) for item in response["channels"]
        ]

        while response.get("response_metadata", {}).get("next_cursor"):

            if max_records_to_return and len(conversations) >= max_records_to_return:
                break

            cursor = response.get("response_metadata", {}).get("next_cursor")
            response = self.__make_request(
                "users_conversations",
                user=user,
                limit=100,
                types=search_types,
                cursor=cursor,
            )

            self._validate_response(response)

            res = [
                self.tl.build_siemplify_message_obj(item)
                for item in response["channels"]
            ]
            conversations.extend(res)

        return (
            conversations[:max_records_to_return]
            if max_records_to_return
            else conversations
        )

    def get_channel_by_name(self, channel_name):
        """
        Get a channel by its name
        :param channel_name: {str} The name of the channel
        :return: {Channel} The found channel, or exception if a matching channel was not found
        """

        try:
            channels = self.list_channels(types="public_channel, private_channel")
            for channel in channels:
                if channel.name.lower() == channel_name.lower():
                    return channel

        except Exception:
            raise SlackManagerException(
                f"Channel {channel_name} was not found. "
                f"Please ensure the channel exists and "
                f"that the token has permissions to access it,"
            )

    def get_message_replies(self, conversation_id, message_ts):
        """
        Get the replies of a specific message (the messages in its thread)
        :param conversation_id: {str} The ID of the conversation to which the message belongs
        :param message_ts: {float} The timestamp of the message (milliseconds)
        :return: {[Message]} The replies of the message
        """
        response = self.client.conversations_replies(
            channel=conversation_id, ts=message_ts
        )

        self._validate_response(response)
        messages = response["messages"]

        if not messages:
            raise SlackManagerException(
                f"No messages were found with timestamp {message_ts} "
                f"in the given conversation"
            )

        # Build the reply messages objects
        return [
            self.tl.build_siemplify_message_obj(message) for message in messages[1:]
        ]

    def ask_question(self, channel, message):
        """
        Send message to Slack channel
        :param channel: {string} Name of the channel or User ID in Slack
        :param message: {string} Text to send
        """
        response = self.client.chat_postMessage(
            channel=channel, text=message, attachments=MESSAGE_ATTACHMENTS
        )

        self._validate_response(response)

    def test_connectivity(self):
        """
        Test connection
        """
        response = self.client.api_test()

        self._validate_response(response)

    @staticmethod
    def _validate_response(response):
        if not response.get("ok"):

            error = response.get("error")
            error_msg = error.replace("_", " ").capitalize()

            if error in ["invalid_auth"]:
                raise UserAuthException(error_msg)

            elif error in ["user_not_found", "users_not_found"]:
                raise UserNotFoundException(error_msg)

            elif error in ["channel_not_found"]:
                raise ChannelNotFoundException(error_msg)

            raise SlackManagerException(error_msg)

    @staticmethod
    def validate_max_records(max_records_to_return):
        if (
            max_records_to_return == 0
            or max_records_to_return
            and max_records_to_return < 1
        ):
            raise MaxRecordsException(
                f"Invalid value was provided for "
                f"“Max Records to Return”: {max_records_to_return}. "
                f"Positive number should be provided"
            )

    def create_channel(self, channel_name, is_private=False):
        """
        Create Channel on Slack
        :param channel_name: {string} Name of the channel
        :param is_private: {bool} True if the new channel should be private
        """
        response = self.client.conversations_create(
            name=channel_name, is_private=is_private
        )

        self._validate_response(response)
        return self.tl.build_siemplify_channel_obj(response["channel"])

    def invite_to_channel(self, channel_id, user_ids):
        """
        Invite Users to a Slack channel
        :param channel_id: {string} ID of the channel
        :param user_ids: {string} Comma separated list of User IDs.
        """
        response = self.client.conversations_invite(channel=channel_id, users=user_ids)

        self._validate_response(response)

    def rename_channel_by_id(self, channel_id, new_name):
        """
        Rename Channel
        :param channel_id: {string} ID of the channel that will be renamed
        :param new_name: {string} New name of the channel
        """
        response = self.client.conversations_rename(channel=channel_id, name=new_name)

        self._validate_response(response)
        return self.tl.build_siemplify_channel_obj(response["channel"])

    def filter_list_items(
        self,
        items,
        filter_key=None,
        filter_value=None,
        filter_logic=None,
        max_records_to_return=None,
    ):
        if filter_key == "Select One" and filter_logic in [EQUAL, CONTAINS]:
            raise SlackManagerException(
                "you need to select a field from the “Filter Key” parameter"
            )
        if filter_logic == "Not Specified" or not filter_value:
            return items[:max_records_to_return] if max_records_to_return else items
        filtered_items = []
        for item in items:
            if max_records_to_return and len(filtered_items) >= max_records_to_return:
                break
            item_data = item.to_json()
            item_value = item_data.get(filter_key)
            is_equal = filter_logic == EQUAL and item_value == filter_value
            is_contains = (
                item_value and filter_logic == CONTAINS and filter_value in item_value
            )
            if is_equal or is_contains:
                filtered_items.append(item)
        return (
            filtered_items[:max_records_to_return]
            if max_records_to_return
            else filtered_items
        )

    def get_user_ids_by_emails(self, user_emails):
        """
        Get IDs of Users by emails
        :param user_emails: {string} Comma separated emails of Users.
        :return: {string} Comma separated list of User IDs.
        """
        emails = user_emails.replace(" ", "").split(",")

        user_ids = []
        for email in emails:
            try:
                user = self.get_user_details_by_email(email)
                user_id = user.id
                user_ids.append(user_id)
            except UserNotFoundException as _:
                pass
        res = ",".join(user_ids)

        return res

    def logger(self, msg):
        if self.siemplify:
            self.siemplify.LOGGER.info(msg)

    @staticmethod
    def get_json_channel_message(raw_data):
        res = {
            "channel": raw_data.get("channel"),
            "message": raw_data.get("message"),
            "ts": raw_data.get("ts"),
            "ok": raw_data.get("ok"),
        }
        return res
