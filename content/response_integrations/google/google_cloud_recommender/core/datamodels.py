from __future__ import annotations

import re
from typing import Any

from TIPCommon.transformation import dict_to_flat
from google_cloud_recommender.core import consts
from google_cloud_recommender.core.exceptions import GoogleCloudRecommenderValidationError


class BaseModel:

    def __init__(self, raw_data: dict) -> None:
        self.raw_data = raw_data

    def to_json(self) -> dict:
        return self.raw_data

    def to_flat(self) -> dict:
        return dict_to_flat(self.to_json())


class ListRecommendations(BaseModel):
    """
    Class to create data model for List Recommendations
    """

    def __init__(self, raw_data: dict, recommendations) -> None:
        super().__init__(raw_data)
        self.recommendations = recommendations

    def get_recommendations(self):
        return self.recommendations


class Recommendation(BaseModel):
    """
    Class to create data model for Recommendation
    """

    def __init__(
        self,
        item_data: dict,
        name: str,
        state: str,
        priority: str,
        etag: str,
        recommender_subtype: str,
        category: str,
        description: str,
        last_refresh_time: str,
    ) -> None:
        super().__init__(item_data)
        self.name = name
        self.state = state
        self.priority = priority
        self.etag = etag
        self.recommender_subtype = recommender_subtype
        self.category = category
        self.description = description
        self.last_refresh_time = last_refresh_time
        self.principal: set[str] | str = set()
        self.remove_role = set()
        self.add_roles = set()
        self.resource = set()

        self.rec_resource = re.search(
            consts.RESOURCE_REGEX_PATTERN, item_data["content"]["overview"]["resource"]
        ).group()

    def to_csv(self):
        device_data = {
            "Name": self.name,
            "State": self.state,
            "Priority": self.priority,
            "Recommendation Subtype": self.recommender_subtype,
            "Category": self.category,
            "Description": self.description,
            "Last Refresh Time": self.last_refresh_time,
        }
        return device_data

    def extract_recommendation(self):
        """Populate recommendation data from a recommendation payload."""

        for op_grps in self.raw_data.get("content", {}).get("operationGroups", []):
            for op in op_grps["operations"]:
                if op["action"] == "remove":
                    self.principal.add(
                        op["pathFilters"]["/iamPolicy/bindings/*/members/*"]
                    )
                    self.resource.add(op["resource"])
                    self.remove_role.add(
                        op["pathFilters"]["/iamPolicy/bindings/*/role"]
                    )
                elif op["action"] == "add":
                    self.resource.add(op["resource"])
                    self.add_roles.add(op["pathFilters"]["/iamPolicy/bindings/*/role"])
                    self.principal.add(op["value"])
                else:
                    raise ValueError("Wrong action : " + op["action"])

    def check_integrity(self):
        """Check invariance of a recommendation payload."""
        if len(self.principal) != 1:
            raise GoogleCloudRecommenderValidationError(
                f"The recommendation “{self.name}” seems to be malformed, "
                f"recommendation should not have more than 1 principal"
            )
        self.principal = self.principal.pop()
        if len(self.remove_role) != 1:
            raise GoogleCloudRecommenderValidationError(
                f"The recommendation “{self.name}” seems to be malformed, "
                f"recommendation should refer to a single role if its removal"
            )
        if len(self.resource) != 1:
            raise GoogleCloudRecommenderValidationError(
                f"The recommendation “{self.name}” seems to be malformed, "
                f"recommendation should refer to a single resource"
            )


class PolicyBinding(BaseModel):
    """
    Dataclass for Policy bindings object
    """

    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.role: str = raw_data["role"]
        self.members: list[str] = raw_data["members"]
        self.condition: dict[str, Any] | None = raw_data.get("condition")

    def to_json(self) -> dict:
        json_data = {"role": self.role, "members": self.members}
        if self.condition is not None:
            json_data["condition"] = self.condition

        return json_data


class Policy(BaseModel):
    """
    Dataclass for IAM Policy with methods to update it acting on recommendation.
    """

    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.bindings = [PolicyBinding(binding) for binding in raw_data["bindings"]]
        self.etag = raw_data["etag"]
        self.version = raw_data["version"]

    def to_json(self) -> dict:
        return {
            "bindings": [binding.to_json() for binding in self.bindings],
            "etag": self.etag,
            "version": self.version,
        }

    def remove_role_from_policy(self, recommendation: Recommendation, logger) -> bool:
        """Remove roles for a policy based on recommendations.

        Args:
            recommendation: Recommendation on IAM policy.
            logger: Logger

        Returns:
            Whether recommendation was successfully applied
        """
        is_acted_recommendation = False
        acted_and_succeeded = False
        if not recommendation.remove_role:
            return True  # No role to be removed.
        for binding in self.bindings:
            if binding.role not in recommendation.remove_role:
                continue
            if binding.condition is not None:
                continue
            try:
                is_acted_recommendation = True
                binding.members.remove(recommendation.principal)
                recommendation.remove_role.remove(binding.role)
                acted_and_succeeded = True
            except ValueError:
                logger.error(
                    f"`{recommendation.principal}` does not have "
                    f"`role:{','.join(recommendation.remove_role)}`."
                )
        if not is_acted_recommendation:
            logger.error(
                f"`{recommendation.principal}` does not have "
                f"`role:{','.join(recommendation.remove_role)}`."
            )
        return is_acted_recommendation and acted_and_succeeded

    def add_roles_in_policy(self, recommendation: Recommendation) -> bool:
        """Add roles in the policy based on recommendations.

        Args:
            recommendation: Recommendation on IAM policy.

        Returns:
            Whether recommendation was successfully applied
        """
        roles_to_be_added = recommendation.add_roles
        for binding in self.bindings:
            if binding.role not in roles_to_be_added:
                continue
            if binding.condition is not None:
                continue
            binding.members.append(recommendation.principal)
            roles_to_be_added.remove(binding.role)
        for role in roles_to_be_added:
            self.bindings.append(
                PolicyBinding({"role": role, "members": [recommendation.principal]})
            )
        return True

    def update_policy_with_recommendations(
        self, recommendations: list[Recommendation], logger
    ):
        """Update the old policy based on recommendations.

        Args:
            recommendations: Recommendation on IAM policy.
            logger: Logger

        Returns:
            success status for each recommendation
        """
        success = []
        for recommendation in recommendations:
            is_success_add = self.add_roles_in_policy(recommendation)
            is_success_removed = self.remove_role_from_policy(recommendation, logger)
            success.append(is_success_removed and is_success_add)
        return success
