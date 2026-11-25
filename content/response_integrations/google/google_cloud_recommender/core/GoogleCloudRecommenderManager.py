# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import abc
import datetime
import json
import urllib.parse
from typing import Any

from soar_sdk.SiemplifyLogger import SiemplifyLogger

import TIPCommon.base
import TIPCommon.utils
from TIPCommon.types import SingleJson
from . import authentication
from . import consts
from . import datamodels
from . import exceptions
from . import UtilsManager
from .GoogleCloudRecommenderParser import GoogleCloudRecommenderParser


# ============================= CLASSES ===================================== #


class GoogleCloudBaseManager(abc.ABC):

    def __init__(
        self,
        api_root: str,
        verify_ssl: bool,
        siemplify_logger: SiemplifyLogger | TIPCommon.base.NewLineLogger,
        user_service_account: SingleJson,
        organization_id: str,
        project_id: str,
        workload_identity_email: str,
        quota_project_id: str | None = None,
    ) -> None:
        """
        The method is used to init an object of Manager class
        Args:
            api_root (str): API root
            user_service_account (str): JSON string containing service account info
            verify_ssl (bool): Specifies if certificate that is configured on the api
            root should be validated
            siemplify_logger: Siemplify logger
        """
        self.api_root = api_root
        self.siemplify_logger = siemplify_logger
        self.resource_name = authentication.create_resource_name(
            project_id=project_id,
            organization_id=organization_id,
            user_service_account=user_service_account,
            workload_identity_email=workload_identity_email,
        )

        credentials = authentication.get_authentication_credentials_or_raise_error(
            quota_project_id=quota_project_id,
            user_service_account=user_service_account,
            workload_identity_email=workload_identity_email,
            verify_ssl=verify_ssl,
        )
        self.session = authentication.create_session(credentials, verify_ssl)
        self.parser = GoogleCloudRecommenderParser()
        self.endpoints = self.load_endpoints()

        # Only used by update_recommendation_status, so it can create its own session
        # Consider creating a new manager obj for it in the action that uses it instead
        self.verify_ssl = verify_ssl
        self.credentials = credentials

    @abc.abstractmethod
    def load_endpoints(self) -> dict[str, str]:
        """Load endpoints that particular manager will use for API calls"""
        raise NotImplementedError()

    @abc.abstractmethod
    def test_connectivity(self) -> None:
        raise NotImplementedError()

    def _get_full_url(self, url_id: str, **kwargs: str) -> str:
        """Get full url from url identifier.

        Args:
            url_id (str): The id of url
            kwargs (str): Variables passed for string formatting
        Returns:
            (str): The full url
        """
        return urllib.parse.urljoin(
            self.api_root, self.endpoints[url_id].format(**kwargs)
        )


class GoogleCloudRecommenderManager(GoogleCloudBaseManager):

    def load_endpoints(self) -> dict[str, str]:
        return consts.RECOMMENDER_ENDPOINTS

    def test_connectivity(self) -> None:
        self.list_recommendations(
            resource_name=None,
            recommendation_location=consts.LOCATION,
            recommendation_state=consts.DEFAULT_STATE,
            recommendation_priority=consts.DEFAULT_PRIORITY,
            recommender_subtype=consts.DEFAULT_SUBTYPE,
            limit=consts.DEFAULT_LIMIT_1,
        )

    def list_recommendations(
        self,
        resource_name: str | None,
        recommendation_location: str,
        recommendation_state: str,
        recommendation_priority: str,
        recommender_subtype: str,
        limit: str,
    ) -> datamodels.ListRecommendations:
        """
        The method is used to get list recommendations.
        Args:
            resource_name: Organization or Project name, examples:
                [organizations/{id} | projects/{id}]
            recommendation_location (str): Recommendation location
            recommendation_state (str): Recommendation State
            recommendation_priority (str): Recommendation Priority
            recommender_subtype (str): Recommender Subtype
            limit (str): Max Graph To Return
        Returns:
            (ListRecommendations): List Recommendations
        """
        if TIPCommon.utils.is_empty_string_or_none(resource_name):
            resource_name = self.resource_name

        state_info = (
            "stateInfo.state = ACTIVE OR stateInfo.state = DISMISSED"
            if recommendation_state == "Not Specified"
            else "stateInfo.state = " + recommendation_state.upper()
        )
        sub_type = (
            ""
            if recommender_subtype == "Not Specified"
            else " AND recommenderSubtype = " + recommender_subtype
        )
        priority = self.get_priority(recommendation_priority)  # FIXME: Pass a list

        if (
            recommendation_state == "Not Specified"
            and recommender_subtype == "Not Specified"
            and not recommendation_priority
        ):
            state_info = ""
            priority = ""

        url = self._get_full_url(
            "list_recommendations",
            resource_name=resource_name,
            locations=recommendation_location,
            recommenders=consts.GOOGLE_SERVICE_RECOMMENDER_ACCOUNT_VALUE,
            limit=limit,
            stateInfo=state_info,
            subType=sub_type,
            priority=priority,
        )
        response_info, content = self.session.request(url, "GET")
        UtilsManager.validate_response(response_info, content)
        return self.parser.build_list_recommendations_obj(json.loads(content))

    def get_recommendation(self, recommendation_name: str) -> datamodels.Recommendation:
        """
        The method is used to get recommendation.
        Args:
            recommendation_name (str): Recommendation Name
        Returns:
            (GetRecommendations): Get Recommendation
        """
        url = self._get_full_url(
            consts.GET_RECOMMENDATION_API, recommendation_name=recommendation_name
        )
        response_info, content = self.session.request(url, "GET")
        UtilsManager.validate_response(response_info, content)
        return self.parser.build_recommendation_object(json.loads(content))

    def update_recommendation(
        self, recommendation_name: str, recommendation_type: str, etag: str
    ) -> datamodels.Recommendation:
        """Update recommendation with recommendation type provided in parameter.

        Args:
            recommendation_name (str): Recommendation name from action parameter
            recommendation_type (str): Recommendation type from action
                parameters "Recommendation State", "Recommendation Result"
            etag (str): etag from get recommendation api for the
                recommendation name.

        Returns:
            datamodels.Recommendation: datamodels.Recommendation object.
        """
        url = self._get_full_url(
            "update_recommendation_status",
            recommendation_name=recommendation_name,
            state_change=recommendation_type,
        )
        json_data = json.dumps({"etag": etag})
        response_info, content = self.session.request(url, "POST", json_data)
        UtilsManager.validate_response(response_info, content)
        return self.parser.build_recommendation_object(json.loads(content))

    # FIXME: b/327898018
    @staticmethod
    def get_priority(recommendation_priority: list) -> str:
        """
        The method is used to get priority
        Args:
            recommendation_priority (str): Recommendation Priority
        Returns:
            (str): Priority Query
        """
        if len(recommendation_priority) > 0:
            return (
                " AND ("
                + " OR ".join(
                    f"priority = {p.upper()}" for p in recommendation_priority
                )
                + ")"
            )
        else:
            return ""

    def parse_recommendations(
        self, recommendation_to_be_applied: list[dict[str, Any]]
    ) -> list[datamodels.Recommendation]:
        """
        Parse recommendations JSON into data model,
        extract recommendation actions and check integrity.

        Args:
            recommendation_to_be_applied: Recommendations list parsed from json

        Returns:
            List of datamodels.Recommendation
        """
        recommendations = []

        for recommendation_data in recommendation_to_be_applied:
            recommendation = self.parser.build_recommendation_object(
                recommendation_data
            )
            recommendation.extract_recommendation()
            recommendation.check_integrity()
            recommendations.append(recommendation)

        return recommendations

    def update_recommendation_status(
        self, recommendation: dict[str, Any], metadata: dict[str, Any]
    ) -> datamodels.Recommendation:
        """Update the recommendation status for the recommendations.

        Args:
            recommendation: Recommendation on IAM policy.
            metadata: (Dict) metadata to update the recommendation state.

        Returns:
            Recommendation with updated status.
        """
        # Need to create a new client on each call to ensure thread safety, for more info:
        # https://github.com/googleapis/google-api-python-client/blob/main/docs/thread_safety.md#thread-safety
        session = authentication.create_session(self.credentials, self.verify_ssl)

        url = self._get_full_url(
            "update_recommendation_status",
            recommendation_name=recommendation["name"],
            state_change="markSucceeded",
        )

        json_data = json.dumps(
            {"etag": recommendation["etag"], "stateMetadata": metadata}
        )
        response_info, content = session.request(url, "POST", json_data)
        UtilsManager.validate_response(response_info, content)
        return self.parser.build_recommendation_object(json.loads(content))

    def update_recommendation_status_after_apply(
        self,
        recommendations: list[datamodels.Recommendation],
        success_status: list[bool],
    ) -> tuple[list[datamodels.Recommendation, list[SingleJson]]]:
        """
        Update recommendation status after they were applied on the policy.

        Args:
            recommendations: List of recommendations to be applied
            success_status: Correspondent list of statuses after each recommendation was applied on policy

        Returns:
             Tuple[List[Recommendation], List[Dict]] List of successfully update recommendations and failed ones

        """
        successful_recommendations = []
        failed_recommendations = []
        for r, status in zip(recommendations, success_status):
            if status:
                successful_recommendations.append(r)
                continue
            failed_recommendations.append(r)

        metadata = {
            "applied_by": f"bulk_apply_by_automated_script-{datetime.datetime.now().strftime('%Y-%m-%d')}"
        }
        recommendation_after_status_change = [
            self.update_recommendation_status(r.to_json(), metadata=metadata)
            for r in successful_recommendations
        ]
        return recommendation_after_status_change, failed_recommendations


class GoogleCloudResourceManager(GoogleCloudBaseManager):

    def load_endpoints(self):
        return consts.RESOURCE_MANAGER_ENDPOINTS

    def test_connectivity(self):
        try:
            self.get_current_policy(resource_name=None)
        except exceptions.GoogleCloudRecommenderError as e:
            raise exceptions.GoogleCloudRecommenderError(
                f"Unable to connect to Google Cloud Resource Manager, error is: {e}"
            ) from e

    def get_current_policy(self, resource_name: str | None) -> datamodels.Policy:
        """Get current organization or project policy.

        Args:
            resource_name: Organization or Project name, examples:
                [organizations/{id} | projects/{id}]

        Returns:
            Policy
        """
        if TIPCommon.utils.is_empty_string_or_none(resource_name):
            resource_name = self.resource_name

        url = self._get_full_url("get_iam_policy", resource_name=resource_name)
        response_info, content = self.session.request(url, "POST")
        UtilsManager.validate_response(response_info, content)
        return self.parser.build_policy_object(json.loads(content))

    def update_policy(
        self, resource_name: str | None, new_policy: dict[str, Any]
    ) -> datamodels.Policy:
        """Set current organization or project policy to the one provided.

        Args:
            resource_name: Organization or Project name, examples:
                [organizations/{id} | projects/{id}]
            new_policy: New policy to be applied

        Returns:
            Policy
        """
        if TIPCommon.utils.is_empty_string_or_none(resource_name):
            resource_name = self.resource_name

        url = self._get_full_url("set_iam_policy", resource_name=resource_name)
        json_data = json.dumps({"policy": new_policy})
        response_info, content = self.session.request(url, "POST", json_data)
        UtilsManager.validate_response(response_info, content)

        return self.parser.build_policy_object(json.loads(content))
