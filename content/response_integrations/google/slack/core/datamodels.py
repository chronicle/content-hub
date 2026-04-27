from __future__ import annotations
from abc import ABCMeta, abstractmethod
from datetime import datetime

from soar_sdk.SiemplifyUtils import dict_to_flat


class AbstractData(metaclass=ABCMeta):
    """
    Abstract Data Model for others Data Models
    """

    def to_table(self):
        return [self.to_json()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    @abstractmethod
    def to_json(self):
        pass

    @abstractmethod
    def to_enrichment_data(self):
        pass

    @staticmethod
    def get_value(item, item_key):
        res = item.get(item_key) if item else None
        return res


class Profile(AbstractData):
    """
    Profile Data Model
    """

    def __init__(
        self, team=None, real_name=None, skype=None, email=None, title=None, **kwargs
    ):
        self.team = team
        self.real_name = real_name
        self.skype = skype
        self.email = email
        self.title = title

    def to_json(self):
        return {
            "Team": self.team,
            "Real Name": self.real_name,
            "Skype": self.skype,
            "Email": self.email,
            "Title": self.title,
        }

    def to_enrichment_data(self):
        pass


class User(AbstractData):
    """
    User Data Model
    """

    def __init__(
        self,
        raw_data,
        name=None,
        real_name=None,
        id=None,
        deleted=None,
        is_app_user=None,
        is_bot=None,
        team_id=None,
        is_admin=None,
        is_restricted=None,
        is_ultra_restricted=None,
        is_owner=None,
        is_primary_owner=None,
        profile=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.name = name
        self.real_name = real_name
        self.id = id
        self.deleted = deleted
        self.is_app_user = is_app_user
        self.is_bot = is_bot
        self.team_id = team_id
        self.is_admin = is_admin
        self.is_restricted = is_restricted
        self.is_ultra_restricted = is_ultra_restricted
        self.is_owner = is_owner
        self.is_primary_owner = is_primary_owner
        if not profile:
            profile = raw_data.get("profile")
        self.profile = Profile(**profile)
        self.email = self.get_value(raw_data.get("profile"), "email")

    def to_json(self):
        return {
            "Name": self.name,
            "Real Name": self.real_name,
            "ID": self.id,
            "Is Deleted": self.deleted,
            "Is App User": self.is_app_user,
            "Is Bot": self.is_bot,
            "Team ID": self.team_id,
            "Is Admin": self.is_admin,
            "Is Restricted": self.is_restricted,
            "Is Ultra Restricted": self.is_ultra_restricted,
            "Is Owner": self.is_owner,
            "Is Primary Owner": self.is_primary_owner,
            "Profile": self.profile.to_json() if self.profile else None,
            "Email": self.email,
        }

    def to_json_detailed(self):
        updated = self.raw_data.get("updated")
        date_time = datetime.fromtimestamp(updated) if updated else None
        updated_time = date_time.strftime("%m/%d/%Y, %H:%M:%S") if date_time else None
        return {
            "ID": self.id,
            "Team ID": self.team_id,
            "Name": self.name,
            "Real Name": self.real_name,
            "Display Name": self.get_value(
                self.raw_data.get("profile"), "display_name"
            ),
            "First Name": self.get_value(self.raw_data.get("profile"), "first_name"),
            "Last Name": self.get_value(self.raw_data.get("profile"), "last_name"),
            "Updated Time": updated_time,
            "Timezone": self.raw_data.get("tz"),
            "Title": self.get_value(self.raw_data.get("profile"), "title"),
            "Phone": self.get_value(self.raw_data.get("profile"), "phone"),
            "Is Admin": self.is_admin,
            "Is Owner": self.is_owner,
            "Is Primary Owner": self.raw_data.get("is_primary_owner"),
            "Is Restricted": self.is_restricted,
            "Is Ultra Restricted": self.is_ultra_restricted,
            "Is Bot": self.is_bot,
            "Is App User": self.is_app_user,
            "Is Email Confirmed": self.raw_data.get("is_email_confirmed"),
        }

    def to_csv_detailed(self):
        return dict_to_flat(self.to_json_detailed())

    def to_enrichment_data(self):
        pass


class Channel(AbstractData):
    """
    Channel Data Model
    """

    def __init__(
        self,
        raw_data,
        name=None,
        name_normalized=None,
        creator=None,
        is_org_shared=None,
        is_channel=None,
        is_general=None,
        id=None,
        is_private=None,
        is_shared=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.name = name
        self.name_normalized = name_normalized
        self.creator = creator
        self.is_org_shared = is_org_shared
        self.is_channel = is_channel
        self.is_general = is_general
        self.id = id
        self.is_private = is_private
        self.is_shared = is_shared
        self.topic = self.get_value(raw_data.get("topic"), "value")
        self.purpose = self.get_value(raw_data.get("purpose"), "value")

    def to_json(self):
        return {
            "Name": self.name,
            "Normalized Name": self.name_normalized,
            "Creator": self.creator,
            "Is Org Shared": self.is_org_shared,
            "Is Channel": self.is_channel,
            "Is General": self.is_general,
            "ID": self.id,
            "Is Private": self.is_private,
            "Is Shared": self.is_shared,
            "Topic": self.topic,
            "Purpose": self.purpose,
        }

    def to_enrichment_data(self):
        pass


class Message(AbstractData):
    """
    Message Data Model
    """

    def __init__(self, raw_data, ts=None, text=None, user=None, type=None, **kwargs):
        self.raw_data = raw_data
        self.ts = ts
        self.text = text
        self.user = user
        self.type = type

    def to_enrichment_data(self):
        pass

    def to_json(self):
        return {
            "Timestamp": self.ts,
            "Text": self.text,
            "User": self.user,
            "Type": self.type,
        }
