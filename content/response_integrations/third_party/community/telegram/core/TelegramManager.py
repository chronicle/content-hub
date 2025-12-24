from __future__ import annotations

import json

import requests


def get_unicode(telegram):
    return str(telegram)


class TelegramManager:
    def __init__(self, bot_api_token):
        """Init function
        :param token: String, the personal access token (PAT)
        """
        self.token = bot_api_token
        self.base = f"https://api.telegram.org/bot{bot_api_token}"
        self.session = requests.Session()

    def test_connectivity(self):
        """Test connectivity to Telegram
        :return: {bool} True if successful, exception otherwise.
        """
        url = f"{self.base}/getMe"

        response = self.session.get(url, timeout=5.0)
        response.raise_for_status()

        if response.json()["ok"]:
            return True
        raise Exception(f"Error conecting to telegram API: {response.text}")

    def get_updates(self, limit=None, offset=None, allowed_updates=None):
        """Receives messages from a group, channel, or or private chat.
        :param offsetparam: String, the last update id to get messages from,
                            enables us to control which message to present.
        :param allowed_updates: List of the allowed updates to retrieve
        :return: Return all the messages content according to a given offset
        """
        url = f"{self.base}/getUpdates?"
        param_dict = {
            "limit": limit,
            "offset": offset,
            "allowed_updates": allowed_updates,
        }

        for param in param_dict:
            if param_dict[param] is not None:
                url += f"{param}={param_dict[param]}&"

        url = url[:-1]  # remove last rebundant char

        response = self.session.get(url, timeout=5.0)

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)
        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return json_res

    def get_messages(self, offsetparam, allowed_updates):
        """Receives messages from a group, channel, or private chat.
        :param offsetparam: String, the last update id to get messages from,
                            enables us to control which message to present.
        :param allowed_updates: List of the allowed updates to retrieve
        :return: Return all the messages content according to a given offset
        """
        url = f"{self.base}/getUpdates"
        params = {"allowed_updates": allowed_updates}

        if offsetparam is not None:
            params["offset"] = offsetparam

        response = self.session.get(url, timeout=5.0, params=params)

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)
        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return json_res

    def get_bot_details(self):
        """Get the configured bot details
        :return: Json, the bot details
        """
        url = f"{self.base}/getMe"

        response = self.session.get(url, timeout=5.0)

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)
        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return json_res

    def get_chat_details(self, chat_id):
        """Get the chat details by a unique ID or username
        :param chat_id: String,the unique identifier or username
        :return: Json, the chat details
        """
        url = f"{self.base}/getChat"

        response = self.session.get(url, timeout=5.0, params={"chat_id": chat_id})

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)
        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return json_res

    def telegram_bot_sendmessage(self, chat_id, bot_message):
        """Send message by the bot to a given chat_id
        :param chat_id: String,the unique identifier or username
        :param bot_message: The message content you want to send
        :return: Json, the sent message details
        """
        params = {"chat_id": chat_id, "text": bot_message}

        url = f"{self.base}/sendMessage"

        response = self.session.get(url, timeout=5.0, params=params)

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)
        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return json_res

    def ask_question(self, chat_id, question_to_ask, answer_options, is_anonymous):
        """Sending question to a given chat with pre-made answer options
        :param chat_id: String,the unique identifier or username
        :param question_to_ask: String, the question you want to send to a given chat
        :param answer_options: List, the answer options you want to set to the question
        :param is_anonymous: Boolean, determines if the answers will be anonymous
        :param allows_multiple_answers: Boolean, allows multiple answers
        :return: Json, the question that was sent
        """
        json_res = {}
        params = {
            "chat_id": chat_id,
            "question": question_to_ask,
            "options": answer_options,
            "is_anonymous": is_anonymous,
        }

        url = f"{self.base}/sendPoll"

        response = self.session.get(url, timeout=5.0, params=params)

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)
        if not json_res.get("ok"):
            raise Exception(json_res.get("description"))
        response.raise_for_status()

        return json_res

    def send_location(self, chat_id, location_latitude, location_longitude):
        """Send a location to a chat by the latitude and the longitude
        :param chat_id: String,the unique identifier or username
        :param location_latitude: String, the latitude of the location
        :param location_longitude: String, the longitude of the location
        :return: Json, the location that was sent.
        """
        params = {
            "chat_id": chat_id,
            "latitude": location_latitude,
            "longitude": location_longitude,
        }

        url = f"{self.base}/sendLocation"

        response = self.session.get(url, timeout=5.0, params=params)

        try:
            json_res = response.json()
        except Exception:
            raise Exception(str(response.content))
        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return json_res

    def send_photo(self, chat_id, photo_url):
        """Send photo to a chat
        :param chat_id: String,the unique identifier or username
        :param photo_url: String, the url of the photo to send
        :return: Json, the details of the photo that was sent
        """
        params = {"chat_id": chat_id, "photo": photo_url}

        url = f"{self.base}/sendPhoto"

        response = self.session.get(url, timeout=5.0, params=params)

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)
        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return json_res

    def send_doc(self, chat_id, doc_url):
        """Send document by URL to a chat
        :param chat_id: String,the unique identifier or username
        :param doc_url: String, the url of the doc to send
        :return: Json, the details of the photo that was sent
        """
        response = self.session.get(
            f"{self.base}/sendDocument",
            timeout=5.0,
            params={"chat_id": chat_id, "document": doc_url},
        )

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)
        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return json_res

    def set_user_permissions(
        self,
        chat_id,
        user_id,
        is_anonymous,
        can_change_info,
        can_post_messages,
        can_edit_messages,
        can_delete_messages,
        can_invite_users,
        can_restrict_users,
        can_pin_messages,
        can_promote_members,
    ):
        """Promote or demote a user in a supergroup or a channel
        :param chat_id: String, the unique identifier or username
        :param user_id:  String,the unique identifier of the user
        :param is_anonymous: Boolean, the user will be displayed as anonymous
        :param can_change_info: Boolean, the user can change info
        :param can_post_messages: Boolean, the user can post messages
        :param can_edit_messages: Boolean, the user can edit messages
        :param can_delete_messages: Boolean, the user can delete messages
        :param can_invite_users: Boolean, the user can invite other users
        :return: Json, the new permissions details
        """
        data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "is_anonymous": is_anonymous,
            "can_change_info": can_change_info,
            "can_post_messages": can_post_messages,
            "can_edit_messages": can_edit_messages,
            "can_delete_messages": can_delete_messages,
            "can_invite_users": can_invite_users,
            "can_restrict_users": can_restrict_users,
            "can_pin_messages": can_pin_messages,
            "can_promote_members": can_promote_members,
        }

        url = f"{self.base}/promoteChatMember"

        response = self.session.get(url, timeout=5.0, data=data)

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)
        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return response.json()

    def set_default_chat_permissions(
        self,
        chat_id,
        can_send_polls,
        can_pin_messages,
        can_invite_users,
        can_edit_the_info,
        can_post_messages,
    ):
        """Promote or demote a user in a supergroup or a channel
        :param chat_id: String, the unique identifier or username
        :param can_send_polls:  String,the unique identifier of the user
        :param can_pin_messages: Boolean, the user will be displayed as anonymous
        :param can_invite_users: Boolean, the user can invite other users
        :param can_edit_the_info: Boolean, the user can change info
        :param can_post_messages: Boolean, the user can post messages
        :param can_edit_messages: Boolean, the user can edit messages
        :return: Json, the new permissions details
        """
        params = {
            "chat_id": chat_id,
            "can_send_polls": can_send_polls,
            "can_pin_messages": can_pin_messages,
            "can_invite_users": can_invite_users,
            "can_change_info": can_edit_the_info,
            "can_send_messages": can_post_messages,
        }

        url = f"{self.base}/setChatPermissions"

        response = self.session.get(url, timeout=5.0, params=params)

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)

        response.raise_for_status()

        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return json_res

    def export_chat_invite_link(self, chat_id):
        """Export invite link in order to enable the access of the bot.
        After exporting, the link can be found in the function get_chat()
        :param chat_id: String,the unique identifier or username
        :return: Json, the invite link details for a given chat
        """
        params = {"chat_id": chat_id}

        url = f"{self.base}/exportChatInviteLink"

        response = self.session.get(url, timeout=5.0, params=params)

        try:
            json_res = response.json()
        except Exception:
            raise Exception(response.content)
        if not json_res.get("ok"):
            raise Exception(json.dumps(json_res))

        return json_res
