from __future__ import annotations

import requests

CD_MSG_TITLE = "Code Defender has detected a new incident"


class PerimeterXManagerException(Exception):
    """General Exception for PerimeterX manager"""


class PerimeterXManager:
    def __init__(
        self,
        slack_channel=None,
        slack_api_key=None,
        connector_type=None,
        offset_in_ms=0,
    ):
        self.slack_channel = slack_channel
        self.slack_api_key = slack_api_key
        self.slack_offset = self.convert_offset(offset_in_ms)
        self.connector_type = connector_type
        self.slack_cursor = ""
        self.paginated = False
        self.messages = []

    """ Siemplify cannot store microseconds like Slack requires
        so we take the offset_in_ms turn it into microseconds with *10000
        Next, we need to add a single microsecond to avoid a loop with the +1
        Finally, we /1000000 to generate the time format required for the slack API 
        If the offset is 0, then we just use 0"""

    def convert_offset(self, ms):
        if ms == 0:
            return ms
        return float(((ms * 10000) + 1) / 1000000)

    def get_slack_channel_id(self):
        response = requests.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": "Bearer " + self.slack_api_key},
        )
        # curl -H 'Authorization: Bearer slack_api_key' https://slack.com/api/conversations.list
        # foreach channels if name == slack_channel, then return id
        if response.status_code != 200:
            return False

        json_response = response.json()

        # check to make sure we've got a channels array
        if "channels" not in json_response:
            return False

        # check to make sure the channels is a list
        if type(json_response["channels"]) != list:
            return False

        # step through the channels looking for the one we want
        for x in json_response["channels"]:
            # if this is the channel we want then return the id
            if x["name"] == self.slack_channel:
                return x["id"]

        return False

    def f(self, x):
        return {"slack": self.get_slack_messages()}.get(x, False)

    def getItemFromList(self, list, searchItem, searchValue, returnValue):
        for x in list:
            if x[searchItem] == searchValue:
                return x[returnValue]
        return False

    def before(self, value, a):
        # Find first part and return slice before it.
        pos_a = value.find(a)
        if pos_a == -1:
            return value
        return value[0:pos_a]

    def formatSlackMsg(self, msg):
        return {
            "type": "slack",
            "ts": msg["ts"],
            "text": self.before(msg["attachments"][0]["text"], "\n"),
            "fullText": msg["attachments"][0]["text"],
            "title": msg["attachments"][0]["title"],
            "severity": self.getItemFromList(
                msg["attachments"][0]["fields"],
                "title",
                "Risk Level",
                "value",
            ),
            "script": self.getItemFromList(
                msg["attachments"][0]["fields"],
                "title",
                "Script",
                "value",
            ),
            "domain": self.getItemFromList(
                msg["attachments"][0]["fields"],
                "title",
                "Host Domain",
                "value",
            ),
            "deepLink": self.getItemFromList(
                msg["attachments"][0]["actions"],
                "text",
                "View in Console",
                "url",
            ),
        }

    def get_slack_messages(self):
        channelId = self.get_slack_channel_id()

        if channelId == False:
            return False

        response = requests.get(
            "https://api.slack.com/api/conversations.history",
            params={
                "channel": channelId,
                "limit": 100,
                "cursor": self.slack_cursor,
                "oldest": self.slack_offset,
            },
            headers={"Authorization": "Bearer " + self.slack_api_key},
        )

        if response.status_code != 200:
            return False

        json_response = response.json()

        if json_response["has_more"] == True:
            self.pagination = 1
            self.slack_cursor = json_response["response_metadata"]["next_cursor"]
        else:
            self.pagination = 0
            self.slack_cursor = ""

        if "messages" not in json_response:
            return False

        # Check to make sure we got some messages returned
        if json_response["messages"] == False:
            return False

        # Check to make sure there's messages in the list
        if len(json_response["messages"]) < 1:
            return False

        # walk through our retrieved messages to find CD related entries
        for x in json_response["messages"]:
            # Check for a Code Defender specific message
            if (
                x["type"] == "message"
                and "attachments" in x
                and x["attachments"][0]["title"] == CD_MSG_TITLE
            ):
                self.messages.append(self.formatSlackMsg(x))

        if self.pagination == 1:
            self.get_slack_messages()

        return self.messages

    def get_cd_alerts(self, integrationType):
        # Execute the desired message retrieval
        return self.f(integrationType)

    def get_connector_type(self):
        return self.connector_type

    def auth(self):
        response = requests.post(
            "https://slack.com/api/auth.test",
            headers={"Authorization": "Bearer " + self.slack_api_key},
        )
        if response.status_code != 200:
            return False

        json_response = response.json()
        if "ok" in json_response and json_response["ok"] == True:
            return True

        if "ok" in json_response and json_response["ok"] == False:
            return False

        return False
