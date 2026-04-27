from __future__ import annotations
from . import consts
from .datamodels import *


class LogPointParser:
    """
    LogPoint Parser
    """

    @staticmethod
    def build_repo_objs(response, max_repos=consts.DEFAULT_MAX_REPOS):
        repos_data = response.json().get("allowed_repos", [])
        return [
            LogPointParser.build_repo_obj(repo_raw_data)
            for repo_raw_data in repos_data[:max_repos]
        ]

    @staticmethod
    def build_repo_obj(repo_raw_data):
        return Repo(
            raw_data=repo_raw_data,
            repo=repo_raw_data.get("repo", ""),
            address=repo_raw_data.get("address", ""),
        )

    @staticmethod
    def build_query_job_obj(raw_data) -> QueryJob:
        return QueryJob(
            raw_data=raw_data,
            search_id=raw_data.get("search_id"),
            client_type=raw_data.get("client_type"),
            query_filter=raw_data.get("query_filter"),
            latest=raw_data.get("latest"),
            lookup=raw_data.get("lookup"),
            query_type=raw_data.get("query_type"),
            time_range=raw_data.get("time_range"),
            success=raw_data.get("success"),
        )

    @staticmethod
    def build_query_results_row_obj(raw_data) -> QueryResults.QueryRow:
        return QueryResults.QueryRow(raw_data=raw_data)

    @staticmethod
    def build_query_results_row_obj_list(raw_data) -> List[QueryResults.QueryRow]:
        return [
            LogPointParser.build_query_results_row_obj(raw_row_data)
            for raw_row_data in raw_data
        ]

    @staticmethod
    def build_query_results_obj(raw_data) -> QueryResults:
        raw_data = raw_data.json()
        return QueryResults(
            raw_data=raw_data,
            query_type=raw_data.get("query_type"),
            query_rows=LogPointParser.build_query_results_row_obj_list(
                raw_data.get("rows", [])
            ),
            original_search_id=raw_data.get("orig_search_id"),
            final=raw_data.get("final"),
            success=raw_data.get("success"),
        )

    @staticmethod
    def build_incident_raw_obj(raw_data) -> IncidentDetails:
        return IncidentDetails(
            raw_data,
            participating_events=[
                LogPointParser.build_incident_event_obj(event_data)
                for event_data in (raw_data.get("_participating_events", []))
            ],
        )

    @staticmethod
    def build_incident_information(raw_data) -> List[IncidentDetails]:
        return [
            LogPointParser.build_incident_raw_obj(raw_row_data)
            for raw_row_data in raw_data.get("rows", [])
        ]

    @staticmethod
    def build_incident_obj(raw_data) -> Incident:
        return Incident(
            raw_data=raw_data,
            id=raw_data.get("id"),
            detection_id=raw_data.get("id"),
            type=raw_data.get("type"),
            incident_id=raw_data.get("incident_id"),
            alert_obj_id=raw_data.get("alert_obj_id"),
            detection_timestamp=raw_data.get("detection_timestamp"),
            name=raw_data.get("name"),
            description=raw_data.get("description"),
            status=raw_data.get("status"),
            risk_level=raw_data.get("risk_level"),
            rows_count=raw_data.get("rows_count"),
            time_range=raw_data.get("time_range"),
            query=raw_data.get("query"),
            user_id=raw_data.get("username"),
        )

    @staticmethod
    def build_incidents_list(raw_data) -> List[Incident]:
        return [
            LogPointParser.build_incident_obj(raw_row_data)
            for raw_row_data in raw_data.get("incidents", [])
        ]

    @staticmethod
    def build_incident_events_list(raw_data) -> List[IncidentEvent]:
        return [
            LogPointParser.build_incident_event_obj(raw_row_data.as_json())
            for raw_row_data in raw_data
        ]

    @staticmethod
    def build_incident_event_obj(raw_data) -> IncidentEvent:
        return IncidentEvent(raw_data)

    @staticmethod
    def build_user_objects(raw_data):
        return [
            LogPointParser.build_user_object(item) for item in raw_data.get("users", [])
        ]

    @staticmethod
    def build_user_object(raw_data):
        return User(
            raw_data=raw_data, user_id=raw_data.get("id"), username=raw_data.get("name")
        )
