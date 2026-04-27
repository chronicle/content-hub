from __future__ import annotations
import copy
from typing import List, Optional

from TIPCommon import dict_to_flat

from soar_sdk.SiemplifyUtils import add_prefix_to_dict
from .consts import (
    ENRICHMENT_PREFIX,
    ASSET_INSIGHT_HTML,
    USER_INSIGHT_HTML,
    RED,
    NO_COLOR,
    NO_COMMENT_FOUND_HTML,
    NO_EVENTS_WERE_FOUND_HTML,
    NOT_ASSIGNED,
    RISK_SCORE_HTML,
    COMMENTS_TABLE_TITLE,
    EVENTS_TABLE_TITLE,
)
from .utils import (
    remove_empty_kwargs,
    convert_timestamp_to_iso_date_format,
    build_html_table,
)


class Watchlist:
    """
    Watchlist data model
    """

    def __init__(
        self,
        raw_data,
        watchlist_id: Optional[str] = None,
        title: Optional[str] = None,
        category: Optional[str] = None,
    ):
        self.raw_data = raw_data
        self.watchlist_id = watchlist_id
        self.title = title
        self.category = category

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return {
            "Watchlist ID": self.watchlist_id,
            "Title": self.title,
            "Category": self.category,
        }


class EntityComment:
    """
    Entity comment data model
    """

    def __init__(
        self,
        raw_data,
        comment_id: Optional[str] = None,
        comment_type: Optional[str] = None,
        comment_object_id: Optional[str] = None,
        text: Optional[str] = None,
        exa_user: Optional[str] = None,
        create_time: Optional[int] = None,
        update_time: Optional[int] = None,
        edited: Optional[bool] = False,
    ):
        self.raw_data = raw_data
        self.comment_id = comment_id
        self.comment_type = comment_type
        self.comment_object_id = (
            comment_object_id  # Entity identifier the comment attached to
        )
        self.text = text
        self.exa_user = exa_user
        self.create_time = create_time
        self.update_time = update_time
        self.edited = edited

    def as_csv(self) -> dict:
        return {"User": self.exa_user, "Comment": self.text}

    def as_table_row(self, row_index: int) -> dict:
        return {"Index": row_index, "User": self.exa_user, "Comment": self.text}

    def as_json(self) -> dict:
        payload = copy.deepcopy(self.raw_data)
        payload.pop("success", None)
        return payload


class WatchlistDetails:
    """
    Watchlist Details data model
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def as_json(self):
        payload = copy.deepcopy(self.raw_data)
        payload.pop("totalNumberOfItems", None)
        return payload


class AssetsWatchlistDetails(WatchlistDetails):
    """
    Assets watchlist details data model
    """

    class Item:
        """
        Watchlist Asset Item
        """

        def __init__(
            self,
            raw_data,
            asset_type: Optional[str] = None,
            host_name: Optional[str] = None,
            ip_address: Optional[str] = None,
            highest_risk_score: Optional[float] = None,
        ):
            self.raw_data = raw_data
            self.asset_type = asset_type
            self.host_name = host_name
            self.ip_address = ip_address
            self.highest_risk_score = highest_risk_score

        @property
        def endpoint(self):
            return self.host_name or self.ip_address

        def as_csv(self):
            return {
                "Type": self.asset_type if self.asset_type is not None else "",
                "Endpoint": self.endpoint if self.endpoint is not None else "",
                "Risk Score": (
                    str(self.highest_risk_score)
                    if self.highest_risk_score is not None
                    else ""
                ),
            }

    def __init__(
        self, raw_data, name: Optional[str] = None, items: Optional[List[Item]] = None
    ):
        super(AssetsWatchlistDetails, self).__init__(raw_data)
        self.items = items
        self.name = name


class UsersWatchlistDetails(WatchlistDetails):
    """
    Users watchlist details data model
    """

    class Item:
        """
        Watchlist User Item
        """

        def __init__(
            self,
            raw_data,
            username: Optional[str] = None,
            risk_score: Optional[float] = None,
        ):
            self.raw_data = raw_data
            self.username = username
            self.risk_score = risk_score

        def as_csv(self):
            return {
                "Username": self.username if self.username is not None else "",
                "Risk Score": (
                    str(self.risk_score) if self.risk_score is not None else ""
                ),
            }

    def __init__(
        self, raw_data, name: Optional[str] = None, items: Optional[List[Item]] = None
    ):
        super(UsersWatchlistDetails, self).__init__(raw_data)
        self.items = items
        self.name = name


class SequenceEvent:
    """
    Sequence Event base class
    """

    def __init__(
        self, raw_data, event_id: Optional[str] = None, time: Optional[int] = None
    ):
        self.raw_data = raw_data
        self.event_id = event_id
        self.time = time  # Unix time in milliseconds

        self.risk_score = None  # Event's risk score

    def as_json(self):
        raw_data = copy.deepcopy(self.raw_data)
        raw_event = raw_data.get("fields", {})
        if self.risk_score is not None:
            raw_event["risk_score"] = self.risk_score
        return raw_event


class EntityDetails:
    """
    Entity Details base class
    """

    def __init__(self, raw_data, api_root):
        self.raw_data = raw_data
        self.api_root = api_root
        self.entity_comments = []
        self.entity_events = []

    def set_comments(self, entity_comments: List[EntityComment]):
        self.entity_comments = entity_comments

    def set_events(self, entity_events: List[SequenceEvent]):
        self.entity_events = entity_events

    def as_json(self):
        raw_data = copy.deepcopy(self.raw_data)
        if self.entity_comments:
            raw_data["comments"] = [
                comment.as_json() for comment in self.entity_comments
            ]
        if self.entity_events:
            raw_data["events"] = [
                entity_event.as_json() for entity_event in self.entity_events
            ]
        return raw_data


class AssetDetails(EntityDetails):
    """
    Asset details data model
    """

    def __init__(
        self,
        raw_data,
        api_root,
        risk_score: Optional[int] = None,
        first_seen: Optional[int] = None,
        last_seen: Optional[int] = None,
        last_sequence_id: Optional[str] = None,
        host_name: Optional[str] = None,
        asset_type: Optional[str] = None,
        ip_address: Optional[str] = None,
        labels: Optional[str] = None,
        comment_count: Optional[str] = None,
        account_names: Optional[List[str]] = None,
    ):
        super(AssetDetails, self).__init__(raw_data, api_root)
        self.risk_score = risk_score
        self.first_seen = first_seen  # Unix timestamp in milliseconds
        self.last_seen = last_seen  # Unix timestamp in milliseconds
        self.last_sequence_id = last_sequence_id
        self.host_name = host_name
        self.ip_address = ip_address
        self.asset_type = asset_type
        self.labels = labels or []

        self.comment_count = comment_count
        self.account_names = account_names or []
        self.is_notable = None

    @property
    def exists(self):
        return bool(self.last_sequence_id)

    def case_wall_report_link(self):
        return f"{self.api_root}uba/#asset/{self.host_name}"

    def as_enrichment(self):
        enrichment = {
            "riskScore": self.risk_score,
            "hostname": self.host_name,
            "ipAddress": self.ip_address,
            "assetType": self.asset_type,
            "lastSessionId": self.last_sequence_id,
            "firstSeen": convert_timestamp_to_iso_date_format(self.first_seen),
            "lastSeen": convert_timestamp_to_iso_date_format(self.last_seen),
            "labels": self.labels,
            "commentCount": self.comment_count,
            "accountNames": self.account_names or None,
            "isNotable": self.is_notable,
        }
        return add_prefix_to_dict(
            dict_to_flat(remove_empty_kwargs(**enrichment)), ENRICHMENT_PREFIX
        )

    def as_enrichment_csv_table(self):
        enrichment = {
            "riskScore": self.risk_score,
            "hostname": self.host_name,
            "ipAddress": self.ip_address,
            "assetType": self.asset_type or None,
            "lastSessionId": self.last_sequence_id,
            "firstSeen": convert_timestamp_to_iso_date_format(self.first_seen),
            "lastSeen": convert_timestamp_to_iso_date_format(self.last_seen),
            "labels": self.labels or None,
            "commentCount": self.comment_count,
            "accountNames": self.account_names or None,
            "isNotable": self.is_notable,
        }
        flattened_table = dict_to_flat(remove_empty_kwargs(**enrichment))
        return [{"Key": key, "Value": value} for key, value in flattened_table.items()]

    def as_insight(self, show_comments: bool, show_events: bool):
        comments_table = events_table = ""

        if show_comments:
            if self.entity_comments:
                comments_table = build_html_table(
                    title=COMMENTS_TABLE_TITLE,
                    column_headers=list(self.entity_comments[0].as_table_row(0).keys()),
                    rows_data=[
                        entity_comment.as_table_row(index + 1)
                        for index, entity_comment in enumerate(self.entity_comments)
                    ],
                )
            else:
                comments_table = NO_COMMENT_FOUND_HTML

        if show_events:
            if self.entity_events:
                events_table = build_html_table(
                    title=EVENTS_TABLE_TITLE,
                    column_headers=list(self.entity_events[0].as_table_row().keys()),
                    rows_data=[
                        entity_event.as_table_row()
                        for entity_event in self.entity_events
                    ],
                )
            else:
                events_table = NO_EVENTS_WERE_FOUND_HTML

        return ASSET_INSIGHT_HTML.format(
            risk=(
                RISK_SCORE_HTML.format(
                    risk_score=self.risk_score,
                    risk_color=RED if self.risk_score > 0 else NO_COLOR,
                )
                if self.risk_score is not None
                else ""
            ),
            is_notable=self.is_notable,
            ip_address=self.ip_address,
            host_name=self.host_name,
            asset_type=self.asset_type,
            first_seen=convert_timestamp_to_iso_date_format(self.first_seen),
            last_seen=convert_timestamp_to_iso_date_format(self.last_seen),
            last_session_id=self.last_sequence_id,
            labels=", ".join(self.labels) if self.labels else NOT_ASSIGNED,
            report_link=self.case_wall_report_link(),
            comments_table=comments_table if show_comments else "",
            events_table=events_table if show_events else "",
        )


class UserDetails(EntityDetails):
    """
    User details data model
    """

    class Info:
        """
        User Info data model
        """

        def __init__(
            self,
            raw_data,
            username: Optional[str] = None,
            risk_score: Optional[float] = None,
            average_risk_score: Optional[float] = None,
            past_scores: Optional[List[float]] = None,
            last_session_id: Optional[str] = None,
            first_seen: Optional[int] = None,
            last_seen: Optional[int] = None,
            last_activity_type: Optional[str] = None,
            last_activity_time: Optional[int] = None,
            labels: Optional[str] = None,
        ):
            self.raw_data = raw_data
            self.username = username
            self.risk_score = risk_score
            self.average_risk_score = average_risk_score
            self.past_scores = past_scores or []
            self.last_session_id = last_session_id
            self.labels = labels or []

            self.first_seen = first_seen  # Unix timestamp in milliseconds
            self.last_seen = last_seen  # Unix timestamp in milliseconds

            self.last_activity_type = last_activity_type
            self.last_activity_time = (
                last_activity_time  # Unix timestamp in milliseconds
            )

    def __init__(
        self,
        raw_data,
        api_root,
        username: Optional[str] = None,
        user_info: Optional[Info] = None,
        is_executive: Optional[bool] = None,
        comment_count: Optional[int] = None,
        account_names: Optional[List[str]] = None,
    ):
        super(UserDetails, self).__init__(raw_data, api_root)
        self.username = username
        self.user_info = user_info
        self.is_executive = is_executive

        self.comment_count = comment_count
        self.account_names = account_names or []
        self.is_notable = None

    @property
    def exists(self):
        return bool(self.user_info)

    def case_wall_report_link(self):
        return f"{self.api_root}uba/#user/{self.username}"

    def as_enrichment(self):
        enrichment = {
            "riskScore": self.user_info.risk_score,
            "pastScores": self.user_info.past_scores or None,
            "lastSessionId": self.user_info.last_session_id,
            "firstSeen": convert_timestamp_to_iso_date_format(self.user_info.first_seen)
            or None,
            "lastSeen": convert_timestamp_to_iso_date_format(self.user_info.last_seen)
            or None,
            "lastActivityType": self.user_info.last_activity_type or None,
            "lastActivityTime": convert_timestamp_to_iso_date_format(
                self.user_info.last_activity_time
            )
            or None,
            "labels": self.user_info.labels or None,
            "commentCount": self.comment_count,
            "isExecutive": self.is_executive,
            "accountNames": self.account_names or None,
            "isNotable": self.is_notable,
        }
        return add_prefix_to_dict(
            dict_to_flat(remove_empty_kwargs(**enrichment)), ENRICHMENT_PREFIX
        )

    def as_enrichment_csv_table(self):
        enrichment = {
            "riskScore": self.user_info.risk_score,
            "pastScores": self.user_info.past_scores or None,
            "lastSessionId": self.user_info.last_session_id,
            "firstSeen": convert_timestamp_to_iso_date_format(self.user_info.first_seen)
            or None,
            "lastSeen": convert_timestamp_to_iso_date_format(self.user_info.last_seen)
            or None,
            "lastActivityType": self.user_info.last_activity_type or None,
            "lastActivityTime": convert_timestamp_to_iso_date_format(
                self.user_info.last_activity_time
            )
            or None,
            "labels": self.user_info.labels or None,
            "commentCount": self.comment_count,
            "isExecutive": self.is_executive,
            "accountNames": self.account_names or None,
            "isNotable": self.is_notable,
        }
        flattened_table = dict_to_flat(remove_empty_kwargs(**enrichment))
        return [{"Key": key, "Value": value} for key, value in flattened_table.items()]

    def as_insight(self, show_comments: bool, show_events: bool):
        comments_table = events_table = ""

        if show_comments:
            if self.entity_comments:
                comments_table = build_html_table(
                    title=COMMENTS_TABLE_TITLE,
                    column_headers=list(self.entity_comments[0].as_table_row(0).keys()),
                    rows_data=[
                        entity_comment.as_table_row(index + 1)
                        for index, entity_comment in enumerate(self.entity_comments)
                    ],
                )
            else:
                comments_table = NO_COMMENT_FOUND_HTML

        if show_events:
            if self.entity_events:
                events_table = build_html_table(
                    title=EVENTS_TABLE_TITLE,
                    column_headers=list(self.entity_events[0].as_table_row().keys()),
                    rows_data=[
                        entity_event.as_table_row()
                        for entity_event in self.entity_events
                    ],
                )
            else:
                events_table = NO_EVENTS_WERE_FOUND_HTML

        return USER_INSIGHT_HTML.format(
            risk=(
                RISK_SCORE_HTML.format(
                    risk_score=self.user_info.risk_score,
                    risk_color=RED if self.user_info.risk_score > 0 else NO_COLOR,
                )
                if self.user_info.risk_score is not None
                else ""
            ),
            is_notable=self.is_notable,
            is_executive=self.is_executive,
            last_activity_type=self.user_info.last_activity_type,
            last_activity_time=convert_timestamp_to_iso_date_format(
                self.user_info.last_activity_time
            ),
            last_session_id=self.user_info.last_session_id,
            labels=(
                ", ".join(self.user_info.labels)
                if self.user_info.labels
                else NOT_ASSIGNED
            ),
            report_link=self.case_wall_report_link(),
            comments_table=comments_table if show_comments else "",
            events_table=events_table if show_events else "",
        )


class EntitySequence:
    """
    Entity sequence
    """

    def __init__(
        self,
        raw_data,
        sequence_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        num_of_events: Optional[int] = None,
    ):
        self.raw_data = raw_data
        self.sequence_id = sequence_id
        self.entity_id = entity_id
        self.start_time = start_time  # Unix timestamp in milliseconds
        self.end_time = end_time  # Unix timestamp in milliseconds

        self.num_of_events = num_of_events


class EntitySequences:
    """
    Entity sequences
    """

    def __init__(self, raw_data, sequences: Optional[List[EntitySequence]] = None):
        self.raw_data = raw_data
        self.sequences = sequences or []


class UserSequences(EntitySequences):
    """
    User sequences data model
    """

    class Session(EntitySequence):
        """
        User session data model
        """

        def __init__(
            self,
            raw_data,
            session_id: Optional[str] = None,
            username: Optional[str] = None,
            start_time: Optional[int] = None,
            end_time: Optional[int] = None,
            num_of_zones: Optional[int] = None,
            num_of_assets: Optional[int] = None,
            num_of_events: Optional[int] = None,
            num_of_security_events: Optional[int] = None,
        ):
            super(UserSequences.Session, self).__init__(
                raw_data=raw_data,
                sequence_id=session_id,
                entity_id=username,
                start_time=start_time,
                end_time=end_time,
                num_of_events=num_of_events,
            )
            self.num_of_zones = num_of_zones
            self.num_of_assets = num_of_assets
            self.num_of_security_events = num_of_security_events

    def __init__(self, raw_data, sequences: Optional[List[Session]] = None):
        super(UserSequences, self).__init__(raw_data=raw_data, sequences=sequences)


class AssetSequences(EntitySequences):
    """
    Asset sequence data model
    """

    class SequenceInfo(EntitySequence):
        def __init__(
            self,
            raw_data,
            start_time: Optional[int] = None,
            end_time: Optional[int] = None,
            risk_score: Optional[int] = None,
            num_of_reasons: Optional[int] = None,
            num_of_events: Optional[int] = None,
            num_of_users: Optional[int] = None,
            num_of_security_events: Optional[int] = None,
            num_of_zones: Optional[int] = None,
            sequence_id: Optional[str] = None,
            asset_id: Optional[str] = None,
        ):
            super(AssetSequences.SequenceInfo, self).__init__(
                raw_data=raw_data,
                sequence_id=sequence_id,
                entity_id=asset_id,
                start_time=start_time,
                end_time=end_time,
                num_of_events=num_of_events,
            )

            self.risk_score = risk_score
            self.num_of_reasons = num_of_reasons

            self.num_of_users = num_of_users
            self.num_of_security_events = num_of_security_events
            self.num_of_zones = num_of_zones
            self.asset_id = asset_id

    def __init__(self, raw_data, sequences: List[SequenceInfo] = None):
        super(AssetSequences, self).__init__(raw_data=raw_data, sequences=sequences)


class UserSessionEvent(SequenceEvent):
    """
    User session event data model
    """

    def __init__(
        self,
        raw_data,
        event_id: Optional[str] = None,
        time: Optional[int] = None,
        event_code: Optional[str] = None,
        event_type: Optional[str] = None,
        host: Optional[str] = None,
        source: Optional[str] = None,
        session_id: Optional[str] = None,
        user: Optional[str] = None,
    ):
        super(UserSessionEvent, self).__init__(
            raw_data=raw_data, event_id=event_id, time=time
        )
        self.event_code = event_code
        self.event_type = event_type
        self.host = host
        self.user = user
        self.source = source
        self.session_id = session_id

    def as_table_row(self):
        return {
            "Time": (
                convert_timestamp_to_iso_date_format(self.time)
                if self.time
                else self.time
            ),
            "Type": self.event_type,
            "Risk Score": (
                f"{self.risk_score:.2f}"
                if self.risk_score is not None
                else NOT_ASSIGNED
            ),
            "Host": self.host,
            "Source": self.source,
        }

    def as_csv(self):
        return {
            "Time": (
                convert_timestamp_to_iso_date_format(self.time)
                if self.time
                else self.time
            ),
            "Type": self.event_type,
            "Risk Score": (
                f"{self.risk_score:.2f}"
                if self.risk_score is not None
                else NOT_ASSIGNED
            ),
            "Host": self.host,
            "Source": self.source,
        }


class AssetSessionEvent(SequenceEvent):
    """
    Asset session event data model
    """

    def __init__(
        self,
        raw_data,
        event_id: Optional[str] = None,
        time: Optional[int] = None,
        event_code: Optional[str] = None,
        event_type: Optional[str] = None,
        host: Optional[str] = None,
        source: Optional[str] = None,
        session_id: Optional[str] = None,
        user: Optional[str] = None,
    ):
        super(AssetSessionEvent, self).__init__(
            raw_data=raw_data, event_id=event_id, time=time
        )
        self.event_code = event_code
        self.event_type = event_type
        self.host = host
        self.source = source
        self.user = user
        self.session_id = session_id

    def as_table_row(self):
        return {
            "Time": (
                convert_timestamp_to_iso_date_format(self.time)
                if self.time
                else self.time
            ),
            "Type": self.event_type,
            "Risk Score": (
                f"{self.risk_score:.2f}"
                if self.risk_score is not None
                else NOT_ASSIGNED
            ),
            "User": self.user,
            "Source": self.source,
        }

    def as_csv(self):
        return {
            "Time": (
                convert_timestamp_to_iso_date_format(self.time)
                if self.time
                else self.time
            ),
            "Type": self.event_type,
            "Risk Score": (
                f"{self.risk_score:.2f}"
                if self.risk_score is not None
                else NOT_ASSIGNED
            ),
            "User": self.user,
            "Source": self.source,
        }


class TriggeredRuleByEventID:
    """
    Triggered rule by event id data model
    """

    def __init__(
        self,
        raw_data,
        event_id: Optional[str] = None,
        risk_score: Optional[float] = None,
    ):
        self.raw_data = raw_data
        self.event_id = event_id
        self.risk_score = risk_score or 0


class EntityEvents:
    """
    Entity events base class
    """

    def __init__(
        self,
        raw_data,
        entity_events: Optional[List[SequenceEvent]] = None,
        triggered_rules_by_event_id: Optional[List[TriggeredRuleByEventID]] = None,
    ):
        self.raw_data = raw_data
        self.entity_events = entity_events
        self.triggered_rules_by_event_id = triggered_rules_by_event_id

    def get_event_risk_score(self, event_id: str) -> (int, bool):
        """
        Return event's risk score.
        :param event_id: {str} Event id to search for risk score
        :return: {int} Risk score of the event. True if found risk score, otherwise false
        """
        risk_score = 0
        found = False
        for triggered_rule in self.triggered_rules_by_event_id:
            if event_id == triggered_rule.event_id:
                found = True
                risk_score += triggered_rule.risk_score
        return risk_score, found


class UserEvents(EntityEvents):
    """
    User events data model
    """

    def __init__(
        self,
        raw_data,
        user_session_events: Optional[List[UserSessionEvent]] = None,
        triggered_rules_by_event_id: Optional[List[TriggeredRuleByEventID]] = None,
    ):
        super(UserEvents, self).__init__(
            raw_data=raw_data,
            entity_events=user_session_events,
            triggered_rules_by_event_id=triggered_rules_by_event_id,
        )


class AssetEvents(EntityEvents):
    """
    Asset events data model
    """

    def __init__(
        self,
        raw_data,
        asset_session_events: Optional[List[AssetSessionEvent]] = None,
        triggered_rules_by_event_id: Optional[List[TriggeredRuleByEventID]] = None,
    ):
        super(AssetEvents, self).__init__(
            raw_data=raw_data,
            entity_events=asset_session_events,
            triggered_rules_by_event_id=triggered_rules_by_event_id,
        )


class NotableAsset:
    """
    Notable asset data model
    """

    def __init__(
        self,
        raw_data,
        host_name: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        self.raw_data = raw_data
        self.host_name = host_name
        self.ip_address = ip_address


class NotableUser:
    """
    Notable user data model
    """

    def __init__(self, raw_data, username: Optional[str]):
        self.raw_data = raw_data
        self.username = username
