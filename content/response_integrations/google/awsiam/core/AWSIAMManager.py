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

"""AWS IAM API Manager module."""
from __future__ import annotations

from __future__ import annotations

import json
from typing import Optional

import boto3
import botocore
from . import consts
from . import datamodels
from . import utils
from .AWSIAMParser import AWSIAMParser
from .exceptions import (
    AWSIAMEntityAlreadyExistsException,
    AWSIAMEntityNotFoundException,
    AWSIAMInvalidInputException,
    AWSIAMLimitExceededException,
    AWSIAMMalformedPolicyDocument,
    AWSIAMStatusCodeException,
    AWSIAMValidationException,
)


class AWSIAMManager:
    """
    AWS IAM Manager
    """

    VALID_STATUS_CODES = (200,)

    def __init__(self, aws_access_key, aws_secret_key, verify_ssl=True):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key

        session = boto3.session.Session()

        self.client = session.client(
            "iam",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            verify=verify_ssl,
        )
        self.parser = AWSIAMParser()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate client response status code
        :param error_msg: {str} Error message to display in case of an error
        :param response: AWS IAM client response
        :return: raise AWSIAMStatusCodeException if status code is not 200
        """
        error_code = response.get("Error", {}).get("Code")
        extracted_error = response.get("Error", {}).get("Message")
        full_error_msg = f"{error_msg}. Response: {extracted_error}"

        if error_code == consts.ENTITY_ALREADY_EXISTS:
            raise AWSIAMEntityAlreadyExistsException(full_error_msg)
        if error_code == consts.VALIDATION_ERROR:
            raise AWSIAMValidationException(full_error_msg)
        if error_code == consts.LIMIT_EXCEEDED:
            raise AWSIAMLimitExceededException(extracted_error)
        if error_code == consts.NO_SUCH_ENTITY_ERROR:
            raise AWSIAMEntityNotFoundException(extracted_error)
        if error_code == consts.MALFORMED_POLICY_DOCUMENT_ERROR:
            raise AWSIAMMalformedPolicyDocument(extracted_error)
        if error_code == consts.INVALID_INPUT_ERROR:
            raise AWSIAMInvalidInputException(extracted_error)
        if (
            response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            not in AWSIAMManager.VALID_STATUS_CODES
        ):
            raise AWSIAMStatusCodeException(
                f"{error_msg}. Reason: {extracted_error} Response: {response}"
            )

    def test_connectivity(self):
        """
        Test connectivity to AWS IAM with parameters provided at the integration configuration page on Marketplace tab.
        @return: true if successfully tested connectivity
                raise botocore.exceptions.ClientError if connectivity failed
                raise AWSIAMStatusCodeException if connectivity failed to validate status code
        """
        response = self.client.get_account_summary()
        self.validate_response(
            response, error_msg="Failed to test connectivity with AWS IAM Service."
        )
        return True

    def create_user(self, username):
        """
        Create a new IAM user for your AWS account.
        :param username: Name of the user to create
        :return: {datamodels.User} User object
        """
        try:
            response = self.client.create_user(UserName=username)
            self.validate_response(response, error_msg="Unable to create a user.")
            return self.parser.build_user_obj(response)
        except botocore.exceptions.ClientError as error:
            self.validate_response(response=error.response)

    def create_group(self, group_name):
        """
        Create a new IAM group for your AWS account.
        :param group_name: Name of the group to create.
        :return: {datamodels.Group} Group object
        """
        try:
            response = self.client.create_group(GroupName=group_name)
            self.validate_response(response, error_msg="Unable to create a group.")
            return self.parser.build_group_obj(response)
        except botocore.exceptions.ClientError as error:
            self.validate_response(response=error.response)

    def list_users(self, max_users_to_return=consts.DEFAULT_MAX_RESULTS):
        """
        Get a list of all users in the IAM.
        :param max_users_to_return: {int} Specify how many users to return. Maximum is 100 users. Default is 50.
        :return: {[datamodels.User]} List of User data model objects
        """
        max_items = min(consts.PAGE_SIZE, max_users_to_return)

        response = self.client.list_users(MaxItems=max_items)
        self.validate_response(response)

        users = response.get("Users", [])
        marker = response.get("Marker")

        while marker and len(users) < max_users_to_return:
            response = self.client.list_users(
                MaxItems=max_items, Marker=response.get("Marker")
            )
            self.validate_response(response)
            marker = response.get("Marker")
            users.extend(response.get("Users", []))

        return self.parser.build_users_obj(users[:max_users_to_return])

    def list_groups(self, max_groups_to_return=consts.DEFAULT_MAX_RESULTS):
        """
        Get a list of all groups in the IAM.
        :param max_groups_to_return: {int} Specify how many groups to return. Maximum is 100 groups. Default is 50.
        :return: {[datamodels.Group]} List of Group data model objects
        """
        max_items = min(consts.PAGE_SIZE, max_groups_to_return)

        response = self.client.list_groups(MaxItems=max_items)
        self.validate_response(response)

        groups = response.get("Groups", [])
        marker = response.get("Marker")

        while marker and len(groups) < max_groups_to_return:
            response = self.client.list_group(
                MaxItems=max_groups_to_return, Marker=response.get("Marker")
            )
            self.validate_response(response)
            marker = response.get("Marker")
            groups.extend(response.get("Groups", []))

        return self.parser.build_groups_obj(groups[:max_groups_to_return])

    def add_user_to_group(self, group_name: str, user_name):
        """
        Add user to a group
        :param group_name: {str} Group name to add the user to
        :param user_name: {str} User name to add the user to
        :return:
                raise AWSIAMStatusCodeException if failed to validate status code
                raise AWSIAMLimitExceededException if exceeded limit in AWS IAM
                raise AWSIAMEntityNotFoundException if user/group was not found
        """
        try:
            response = self.client.add_user_to_group(
                GroupName=group_name, UserName=user_name
            )
            self.validate_response(
                response,
                error_msg=f"Failed to add user {user_name} to group {group_name}",
            )
        except botocore.exceptions.ClientError as error:
            self.validate_response(response=error.response)

    def remove_user_from_group(self, group_name: str, user_name):
        """
        Add user to a group
        :param group_name: {str} Group name to remove the user from
        :param user_name: {str} User name to remove from group
        :return:
                raise AWSIAMStatusCodeException if failed to validate status code
                raise AWSIAMLimitExceededException if exceeded limit in AWS IAM
                raise AWSIAMEntityNotFoundException if user/group was not found
        """
        try:
            response = self.client.remove_user_from_group(
                GroupName=group_name, UserName=user_name
            )
            self.validate_response(
                response,
                error_msg=f"Failed to remove user {user_name} from group {group_name}",
            )
        except botocore.exceptions.ClientError as error:
            self.validate_response(response=error.response)

    def create_policy(
        self, policy_name: str, policy_document: str, description: Optional[str] = None
    ) -> datamodels.Policy:
        """
        Creates a new managed policy for your AWS account.
        :param policy_name: {str} The friendly name of the policy. IAM user, group, role, and policy names must be unique within the
        account. Names are not distinguished by case. For example, you cannot create resources named both "MyResource" and "myresource".
        :param policy_document: {str} The JSON policy document that you want to use as the content for the new policy. You must provide
        policies in JSON format in IAM. However, for AWS CloudFormation templates formatted in YAML, you can provide the policy in JSON or YAML format.
        AWS CloudFormation always converts a YAML policy to JSON format before submitting it to IAM.
        :param description: {str} A friendly description of the policy. Typically used to store information about the permissions defined in
        the policy. For example, "Grants access to production DynamoDB tables."
        :return: {datamodels.Policy} Policy datamodel
                raise AWSIAMStatusCodeException if failed to validate status code
        """
        payload_kwargs = utils.remove_empty_kwargs(
            PolicyName=policy_name,
            PolicyDocument=policy_document,
            Description=description,
        )
        try:
            response = self.client.create_policy(**payload_kwargs)
            self.validate_response(
                response, error_msg=f"Failed to create policy {policy_name}"
            )
            return self.parser.build_policy_obj(response.get("Policy", {}))
        except botocore.exceptions.ClientError as error:
            self.validate_response(response=error.response)

    def list_policies(
        self, scope: str, only_attached: bool, max_to_return: Optional[int] = None
    ) -> (bool, [datamodels.Policy]):
        """
        Lists all the managed policies that are available in your AWS account, including your own customer-defined managed policies and all
        AWS managed policies.
        :param scope: {str} The scope to use for filtering the results.List only AWS managed policies, set Scope to AWS . To list only
        the customer managed policies in your AWS account, set Scope to Local .
        :param only_attached: {bool} A flag to filter the results to only the attached policies. When OnlyAttached is true ,
        the returned list contains only the policies that are attached to an IAM user, group, or role. When OnlyAttached is false , or when the parameter is not included, all policies are returned.
        :param max_to_return: {int} Max number of policies to return. If not specified, all results will be returned
        return: {{bool},[datamodels.Policy]} True if there are more available results, otherwise False. List of policies datamodels
                raise AWSIAMStatusCodeException if failed to validate status code
        """
        max_items = (
            min(consts.PAGE_SIZE, max_to_return) if max_to_return else consts.PAGE_SIZE
        )

        response = self.client.list_policies(
            Scope=scope, OnlyAttached=only_attached, MaxItems=max_items
        )
        self.validate_response(response)
        raw_policies = response.get("Policies", [])
        marker = response.get("Marker") if response.get("IsTruncated") else ""

        while marker:
            if max_to_return and len(raw_policies) >= max_to_return:
                break
            response = self.client.list_policies(
                Scope=scope,
                OnlyAttached=only_attached,
                MaxItems=max_items,
                Marker=marker,
            )
            self.validate_response(response)
            marker = response.get("Marker") if response.get("IsTruncated") else ""
            raw_policies.extend(response.get("Policies", []))

        policies_obj = [
            self.parser.build_policy_obj(policy) for policy in raw_policies
        ]

        return True if marker else False, (
            policies_obj[:max_to_return] if max_to_return else policies_obj
        )

    def get_policy_arn(self, policy_name: str) -> str:
        """
        Return policy ARN
        :param policy_name: {str} policy name to get ARN from
        :return: {str} the ARN of the policy. raises AWSIAMEntityNotFoundException exception if policy was not found
        """
        _, policies = self.list_policies(scope="All", only_attached=False)
        for policy in policies:
            if policy.policy_name == policy_name:
                return policy.arn
        raise AWSIAMEntityNotFoundException(
            f"Failed to find policy ARN for policy {policy_name}"
        )

    def attach_user_policy(self, user_name: str, policy_arn: str):
        """
        Attaches the specified managed policy to the specified user.
        :param user_name: {str} The name (friendly name, not ARN) of the IAM user to attach the policy to.
        :param policy_arn: {str} The Amazon Resource Name (ARN) of the IAM policy you want to attach.
        :return: raise AWSIAMEntityNotFoundException if policy/user does not exist
                 raise AWSIAMInvalidInputException if failed to validate input parameters
                 raise AWSIAMStatusCodeException if failed to validate status code
        """
        try:
            response = self.client.attach_user_policy(
                UserName=user_name, PolicyArn=policy_arn
            )
            self.validate_response(
                response, error_msg=f"Failed to attach policy to user {user_name}"
            )
        except botocore.exceptions.ClientError as error:
            self.validate_response(response=error.response)

    def attach_group_policy(self, group_name: str, policy_arn: str):
        """
        Attaches the specified managed policy to the specified IAM group.
        :param group_name: {str} The name (friendly name, not ARN) of the group to attach the policy to.
        :param policy_arn: {str} The Amazon Resource Name (ARN) of the IAM policy you want to attach.
        :return: raise AWSIAMEntityNotFoundException if policy/group does not exist
                 raise AWSIAMInvalidInputException if failed to validate input parameters
                 raise AWSIAMStatusCodeException if failed to validate status code
        """
        try:
            response = self.client.attach_group_policy(
                GroupName=group_name, PolicyArn=policy_arn
            )
            self.validate_response(
                response, error_msg=f"Failed to attach policy to group {group_name}"
            )
        except botocore.exceptions.ClientError as error:
            self.validate_response(response=error.response)

    def attach_role_policy(self, role_name, policy_arn: str):
        """
        Attaches the specified managed policy to the specified IAM role. When you attach a managed policy to a role,
        the managed policy becomes part of the role's permission (access) policy.
        :param role_name: {str} The name (friendly name, not ARN) of the role to attach the policy to. This parameter allows (through its
        regex pattern ) a string of characters consisting of upper and lowercase alphanumeric characters with no spaces.
        You can also include any of the following characters: _+=,.@-
        :param policy_arn: {str} The Amazon Resource Name (ARN) of the IAM policy you want to attach.
        :return: raise AWSIAMEntityNotFoundException if policy/role does not exist
                 raise AWSIAMInvalidInputException if failed to validate input parameters
                 raise AWSIAMStatusCodeException if failed to validate status code
        """
        try:
            response = self.client.attach_role_policy(
                RoleName=role_name, PolicyArn=policy_arn
            )
            self.validate_response(
                response, error_msg=f"Failed to attach policy to role {role_name}"
            )
        except botocore.exceptions.ClientError as error:
            self.validate_response(response=error.response)

    def disable_user_access(self, username: str) -> None:
        """Change a user's policy to DisableUserAccessPolicy.

        Args:
            username: The username of the user you want to disable.
        """
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}],
        }
        try:
            self.client.put_user_policy(
                UserName=username,
                PolicyName="DisableUserAccessPolicy",
                PolicyDocument=json.dumps(policy_document),
            )

        except botocore.exceptions.ClientError as error:
            self.validate_response(response=error.response)
