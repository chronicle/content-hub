from __future__ import annotations
from .datamodels import User, Channel, Message


class SlackTransformationLayer:
    """
    Slack Transformation Layer.
    Class for object building from raw_data with static methods build_siemplify_{object}_obj.
    """

    @staticmethod
    def build_siemplify_user_obj(user_data):
        return User(raw_data=user_data, **user_data)

    @staticmethod
    def build_siemplify_channel_obj(channel_data):
        return Channel(raw_data=channel_data, **channel_data)

    @staticmethod
    def build_siemplify_message_obj(message_data):
        return Message(raw_data=message_data, **message_data)

    @staticmethod
    def build_siemplify_message_obj_from_new_message(message_data):
        return Message(raw_data=message_data, **(message_data.get("message", {})))
