from __future__ import annotations
from typing import Any, Dict
from google_cloud_recommender.core.exceptions import GoogleCloudRecommenderValidationError
from google_cloud_recommender.core import datamodels


class GoogleCloudRecommenderParser:

    def build_list_recommendations_obj(
        self, raw_data: dict
    ) -> datamodels.ListRecommendations:
        """
        Builds List Recommendations dataclass

        Args:
            raw_data: Raw API data item

        Returns:
            List Recommendations object
        """
        return datamodels.ListRecommendations(
            raw_data=raw_data,
            recommendations=[
                self.build_recommendation_object(item)
                for item in raw_data.get("recommendations", [])
            ],
        )

    def build_recommendation_object(
        self, item_data: Dict[str, Dict[str, str]]
    ) -> datamodels.Recommendation:
        """
        Builds Recommendation data class

        Args:
            item_data: Raw API data item

        Returns:
            Recommendation object
        """
        if "google.iam.policy.Recommender" not in item_data.get("name", ""):
            raise GoogleCloudRecommenderValidationError(
                f"The object {item_data.get('name', '')} "
                f"isn't an instance of google.iam.policy.Recommender. "
            )

        return datamodels.Recommendation(
            item_data=item_data,
            name=item_data.get("name", ""),
            state=item_data.get("stateInfo", {}).get("state", ""),
            priority=item_data.get("priority", ""),
            etag=item_data.get("etag", ""),
            recommender_subtype=item_data.get("recommenderSubtype"),
            category=item_data.get("primaryImpact", {}).get("category", ""),
            description=item_data.get("description", ""),
            last_refresh_time=item_data.get("lastRefreshTime", ""),
        )

    @staticmethod
    def build_policy_object(raw_data: Dict[str, Any]) -> datamodels.Policy:
        """
        Builds Policy dataclass

        Args:
            raw_data: Raw API data item

        Returns:
            Policy object
        """
        return datamodels.Policy(raw_data=raw_data)
