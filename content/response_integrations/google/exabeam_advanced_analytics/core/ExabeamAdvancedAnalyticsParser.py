from __future__ import annotations
from collections import defaultdict
from typing import List

from .datamodels import (
    Watchlist,
    EntityComment,
    AssetsWatchlistDetails,
    UsersWatchlistDetails,
    UserDetails,
    AssetDetails,
    UserSequences,
    AssetSequences,
    UserEvents,
    AssetEvents,
    UserSessionEvent,
    AssetSessionEvent,
    TriggeredRuleByEventID,
    NotableUser,
    NotableAsset,
)


class ExabeamAdvancedAnalyticsParser:
    """
    Exabeam Advanced Analytics Transformation Layer
    """

    @staticmethod
    def build_watchlist_obj(raw_data) -> Watchlist:
        return Watchlist(
            raw_data=raw_data,
            watchlist_id=raw_data.get("watchlistId"),
            title=raw_data.get("title"),
            category=raw_data.get("category"),
        )

    @staticmethod
    def build_watchlist_obj_list(raw_data, limit=None) -> List[Watchlist]:
        raw_data = raw_data[:limit] if limit is not None else raw_data
        return [
            ExabeamAdvancedAnalyticsParser.build_watchlist_obj(raw_watchlist)
            for raw_watchlist in raw_data
        ]

    @staticmethod
    def build_entity_comment_obj(raw_data) -> EntityComment:
        return EntityComment(
            raw_data=raw_data,
            comment_id=raw_data.get("commentId"),
            comment_type=raw_data.get("commentType"),
            comment_object_id=raw_data.get("commentObjectId"),
            text=raw_data.get("text"),
            exa_user=raw_data.get("exaUser"),
            create_time=raw_data.get("createTime"),
            update_time=raw_data.get("updateTime"),
            edited=raw_data.get("edited"),
        )

    @staticmethod
    def build_entity_comment_obj_list(raw_data) -> List[EntityComment]:
        return [
            ExabeamAdvancedAnalyticsParser.build_entity_comment_obj(comment)
            for comment in raw_data.get("comments", [])
        ]

    @staticmethod
    def build_assets_watchlist_obj(raw_data) -> AssetsWatchlistDetails:
        return AssetsWatchlistDetails(
            raw_data=raw_data,
            name=raw_data.get("title"),
            items=[
                ExabeamAdvancedAnalyticsParser.build_watchlist_asset_item_obj(item)
                for item in raw_data.get("items", [])
            ],
        )

    @staticmethod
    def build_users_watchlist_obj(raw_data) -> UsersWatchlistDetails:
        return UsersWatchlistDetails(
            raw_data=raw_data,
            name=raw_data.get("title"),
            items=[
                ExabeamAdvancedAnalyticsParser.build_watchlist_user_item_obj(item)
                for item in raw_data.get("items", [])
            ],
        )

    @staticmethod
    def build_watchlist_asset_item_obj(raw_item) -> AssetsWatchlistDetails.Item:
        return AssetsWatchlistDetails.Item(
            raw_data=raw_item,
            asset_type=raw_item.get("asset", {}).get("assetType"),
            host_name=raw_item.get("asset", {}).get("hostName"),
            ip_address=raw_item.get("asset", {}).get("ipAddress"),
            highest_risk_score=raw_item.get("highestRiskScore"),
        )

    @staticmethod
    def build_watchlist_user_item_obj(raw_item) -> UsersWatchlistDetails.Item:
        return UsersWatchlistDetails.Item(
            raw_data=raw_item,
            username=raw_item.get("username"),
            risk_score=raw_item.get("user", {}).get("riskScore"),
        )

    @staticmethod
    def build_user_info_obj(raw_data):
        return UserDetails.Info(
            raw_data=raw_data,
            username=raw_data.get("username"),
            risk_score=raw_data.get("riskScore"),
            average_risk_score=raw_data.get("averageRiskScore"),
            past_scores=raw_data.get("pastScores"),
            last_session_id=raw_data.get("lastSessionId"),
            first_seen=raw_data.get("firstSeen"),
            last_seen=raw_data.get("lastSeen"),
            last_activity_type=raw_data.get("lastActivityType"),
            last_activity_time=raw_data.get("lastActivityTime"),
            labels=raw_data.get("labels", []),
        )

    @staticmethod
    def build_user_details_obj(raw_data, api_root) -> UserDetails:
        return UserDetails(
            raw_data=raw_data,
            api_root=api_root,
            username=raw_data.get("username"),
            user_info=(
                ExabeamAdvancedAnalyticsParser.build_user_info_obj(
                    raw_data.get("userInfo", {})
                )
                if raw_data.get("userInfo", {})
                else None
            ),
            is_executive=raw_data.get("isExecutive"),
            comment_count=raw_data.get("commentCount"),
            account_names=raw_data.get("accountNames"),
        )

    @staticmethod
    def build_asset_details_obj(raw_data, api_root) -> AssetDetails:
        return AssetDetails(
            raw_data=raw_data,
            api_root=api_root,
            risk_score=raw_data.get("info", {}).get("riskScore"),
            asset_type=raw_data.get("info", {}).get("assetType"),
            first_seen=raw_data.get("info", {}).get("firstSeen"),
            last_seen=raw_data.get("info", {}).get("lastSeen"),
            host_name=raw_data.get("info", {}).get("hostName"),
            ip_address=raw_data.get("info", {}).get("ipAddress"),
            last_sequence_id=raw_data.get("info", {}).get("latestSequenceId"),
            labels=raw_data.get("labels", []),
            comment_count=raw_data.get("info", {}).get("commentCount"),
            account_names=raw_data.get("info", {}).get("accountNames"),
        )

    @staticmethod
    def build_user_sequence_session_obj(raw_data) -> UserSequences.Session:
        return UserSequences.Session(
            raw_data=raw_data,
            session_id=raw_data.get("sessionId"),
            username=raw_data.get("username"),
            start_time=raw_data.get("startTime"),
            end_time=raw_data.get("endTime"),
            num_of_zones=raw_data.get("numOfZones"),
            num_of_assets=raw_data.get("numOfAssets"),
            num_of_events=raw_data.get("numOfEvents"),
            num_of_security_events=raw_data.get("numOfSecurityEvents"),
        )

    @staticmethod
    def build_user_sequences_session_obj_list(raw_data) -> List[UserSequences.Session]:
        return [
            ExabeamAdvancedAnalyticsParser.build_user_sequence_session_obj(raw_session)
            for raw_session in raw_data
        ]

    @staticmethod
    def build_user_sequences_obj(raw_data) -> UserSequences:
        return UserSequences(
            raw_data=raw_data,
            sequences=ExabeamAdvancedAnalyticsParser.build_user_sequences_session_obj_list(
                raw_data.get("sessions", [])
            ),
        )

    @staticmethod
    def build_asset_sequence_info_obj(raw_data) -> AssetSequences.SequenceInfo:
        return AssetSequences.SequenceInfo(
            raw_data=raw_data,
            risk_score=raw_data.get("sequenceInfo", {}).get("riskScore"),
            start_time=raw_data.get("sequenceInfo", {}).get("startTime"),
            end_time=raw_data.get("sequenceInfo", {}).get("endTime"),
            num_of_reasons=raw_data.get("sequenceInfo", {}).get("numOfReasons"),
            num_of_events=raw_data.get("sequenceInfo", {}).get("numOfEvents"),
            num_of_users=raw_data.get("sequenceInfo", {}).get("numOfUsers"),
            num_of_security_events=raw_data.get("sequenceInfo", {}).get(
                "numOfSecurityEvents"
            ),
            num_of_zones=raw_data.get("sequenceInfo", {}).get("numOfZones"),
            asset_id=raw_data.get("sequenceInfo", {}).get("assetId"),
            sequence_id=raw_data.get("sequenceId"),
        )

    @staticmethod
    def build_asset_sequences_obj(raw_data) -> AssetSequences:
        return AssetSequences(
            raw_data=raw_data,
            sequences=[
                ExabeamAdvancedAnalyticsParser.build_asset_sequence_info_obj(
                    raw_sequence
                )
                for raw_sequence in raw_data
            ],
        )

    @staticmethod
    def build_user_event_session_obj(raw_data) -> UserSessionEvent:
        return UserSessionEvent(
            raw_data=raw_data,
            event_id=raw_data.get("fields", {}).get("event_id"),
            time=raw_data.get("fields", {}).get("time"),
            event_code=raw_data.get("fields", {}).get("event_code"),
            event_type=raw_data.get("fields", {}).get("event_type"),
            source=raw_data.get("fields", {}).get("source"),
            session_id=raw_data.get("fields", {}).get("session_id"),
            host=raw_data.get("fields", {}).get("host"),
            user=raw_data.get("fields", {}).get("user"),
        )

    @staticmethod
    def build_user_event_session_obj_list(raw_data) -> List[UserSessionEvent]:
        user_session_events = []
        for raw_aggregated_event in raw_data:
            user_session_events.extend(
                [
                    ExabeamAdvancedAnalyticsParser.build_user_event_session_obj(
                        raw_event_session
                    )
                    for raw_event_session in raw_aggregated_event.get("es", [])
                ]
            )

        return user_session_events

    @staticmethod
    def build_asset_event_session_obj(raw_data) -> AssetSessionEvent:
        return AssetSessionEvent(
            raw_data=raw_data,
            event_id=raw_data.get("fields", {}).get("event_id"),
            time=raw_data.get("fields", {}).get("time"),
            event_code=raw_data.get("fields", {}).get("event_code"),
            event_type=raw_data.get("fields", {}).get("event_type"),
            source=raw_data.get("fields", {}).get("source"),
            session_id=raw_data.get("fields", {}).get("session_id"),
            host=raw_data.get("fields", {}).get("host"),
            user=raw_data.get("fields", {}).get("user"),
        )

    @staticmethod
    def build_asset_event_session_obj_list(raw_data) -> List[AssetSessionEvent]:
        asset_session_events = []
        for raw_aggregated_event in raw_data:
            asset_session_events.extend(
                [
                    ExabeamAdvancedAnalyticsParser.build_asset_event_session_obj(
                        raw_event_session
                    )
                    for raw_event_session in raw_aggregated_event.get("es", [])
                ]
            )

        return asset_session_events

    @staticmethod
    def build_triggered_rule_by_event_id_obj(raw_data) -> TriggeredRuleByEventID:
        return TriggeredRuleByEventID(
            raw_data=raw_data,
            event_id=raw_data.get("eventId"),
            risk_score=raw_data.get("riskScore"),
        )

    @staticmethod
    def build_user_events(raw_data) -> UserEvents:
        raw_triggered_rules = raw_data.get("triggeredRulesByEventId", defaultdict(list))

        triggered_rules = []
        for event_id, rules in raw_triggered_rules.items():
            triggered_rules.extend(
                [
                    ExabeamAdvancedAnalyticsParser.build_triggered_rule_by_event_id_obj(
                        raw_rule
                    )
                    for raw_rule in rules
                ]
            )

        return UserEvents(
            raw_data=raw_data,
            user_session_events=ExabeamAdvancedAnalyticsParser.build_user_event_session_obj_list(
                raw_data.get("aggregatedEvents", [])
            ),
            triggered_rules_by_event_id=triggered_rules,
        )

    @staticmethod
    def build_asset_events(raw_data) -> AssetEvents:
        raw_triggered_rules = raw_data.get("triggeredRulesByEventId", defaultdict(list))

        triggered_rules = []
        for event_id, rules in raw_triggered_rules.items():
            triggered_rules.extend(
                [
                    ExabeamAdvancedAnalyticsParser.build_triggered_rule_by_event_id_obj(
                        raw_rule
                    )
                    for raw_rule in rules
                ]
            )

        return AssetEvents(
            raw_data=raw_data,
            asset_session_events=ExabeamAdvancedAnalyticsParser.build_asset_event_session_obj_list(
                raw_data.get("aggregatedEvents", [])
            ),
            triggered_rules_by_event_id=triggered_rules,
        )

    @staticmethod
    def build_notable_user_obj(raw_data) -> NotableUser:
        return NotableUser(
            raw_data=raw_data, username=raw_data.get("user", {}).get("username")
        )

    @staticmethod
    def build_notable_users_obj_list(raw_data) -> List[NotableUser]:
        return [
            ExabeamAdvancedAnalyticsParser.build_notable_user_obj(raw_user_info)
            for raw_user_info in raw_data.get("users", [])
        ]

    @staticmethod
    def build_notable_asset_obj(raw_data) -> NotableAsset:
        return NotableAsset(
            raw_data=raw_data,
            ip_address=raw_data.get("asset", {}).get("ipAddress"),
            host_name=raw_data.get("asset", {}).get("hostName"),
        )

    @staticmethod
    def build_notable_asset_obj_list(raw_data) -> List[NotableAsset]:
        return [
            ExabeamAdvancedAnalyticsParser.build_notable_asset_obj(raw_asset_info)
            for raw_asset_info in raw_data.get("assets", [])
        ]
