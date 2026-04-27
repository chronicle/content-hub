# ============================================================================#
# title           :AWSWAFManager.py
# description     :This Module contain all AWS WAF operations functionality
# author          :gabriel.munits@siemplify.co
# date            :12-10-2020
# python_version  :3.7
# libraries       :boto3
# requirements     :
# product_version :1.0
# ============================================================================#

from __future__ import annotations
from typing import List, Optional

# ============================= IMPORTS ===================================== #
import boto3
import botocore
from . import consts
from . import datamodels
from .AWSWAFParser import AWSWAFParser
from .exceptions import (
    AWSWAFStatusCodeException,
    AWSWAFDuplicateItemException,
    AWSWAFLimitExceededException,
)
from .utils import remove_empty_kwargs


class AWSWAFManager:
    """
    AWS WAF Manager
    """

    VALID_STATUS_CODES = (200,)

    def __init__(self, aws_access_key, aws_secret_key, aws_default_region):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_default_region = aws_default_region

        session = boto3.session.Session()

        self.clients = {
            consts.REGIONAL_SCOPE: session.client(
                "wafv2",
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_default_region,
            ),
            consts.CLOUDFRONT_SCOPE: session.client(
                "wafv2",
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name="us-east-1",
            ),
        }
        self.parser = AWSWAFParser()

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate client WAF response status code
        :param response: client Security Hub response
        :return: raise AWSWAFStatusCodeException if status code is not 200
        """
        if (
            response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            not in AWSWAFManager.VALID_STATUS_CODES
        ):
            raise AWSWAFStatusCodeException(f"{error_msg}. Response: {response}")

    @staticmethod
    def validate_duplicate(response, error_msg="An error occurred"):
        """
        Validate if client error response code is of WAFDuplicateItemException
        :param response: client WAF response
        :return: raise AWSWAFDuplicateItemException if WAFDuplicateItemException exception type was found
        """
        if response.get("Error", {}).get("Code") == "WAFDuplicateItemException":
            raise AWSWAFDuplicateItemException(
                f"{error_msg}. Response: {response.get('Message')}"
            )

    @staticmethod
    def validate_limitation(response, error_msg="An error occurred"):
        """
        Validate if client error response code is WAFLimitsExceededException.
        Will be usually thrown when an update operation exceeding resource limit in AWS WAF
        :param response: client WAF response
        :param error_msg: {str} error message to provide with exception
        :return: raise AWSWAFLimitExceededException if WAFLimitsExceededException exception type was found
        """
        if response.get("Error", {}).get("Code") == "WAFLimitsExceededException":
            raise AWSWAFLimitExceededException(
                f"{error_msg}. Response: {response.get('Message')}"
            )

    def _get_client(self, scope: str) -> boto3.client:
        return self.clients[scope.upper()]

    def test_connectivity(self) -> bool:
        """
        Test connectivity with AWS WAF service by calling list_ip_sets method with limit of 1
        :return: true if successfully tested connectivity
                raise botocore.exceptions.ClientError if connectivity failed
                raise AWSWAFStatusCodeException if connectivity failed to validate status code
        """
        errors = []
        for scope, client in self.clients.items():
            try:
                response = client.list_ip_sets(Scope=scope, Limit=1)
                self.validate_response(
                    response,
                    error_msg="Failed to test connectivity with AWS WAF Service.",
                )
            except (
                AWSWAFStatusCodeException,
                botocore.exceptions.ClientError,
                botocore.exceptions.BotoCoreError,
            ) as e:
                errors.append(str(e))
        # At least one connectivity should pass
        if len(errors) > 1:
            raise AWSWAFStatusCodeException("\n".join(errors))
        return True

    def list_ip_sets(
        self, scope: str, limit: Optional[int] = None, next_marker: Optional[str] = None
    ) -> List[datamodels.IPSet]:
        """
        Return list of all ip sets in scope that you manage.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param limit: {int} The maximum number of objects that you want AWS WAF to return for this request.
                            If more objects are available, in the response, AWS WAF provides a NextMarker value that you
                            can use in a subsequent call to get the next batch of objects.
                            Max number of IP Sets per region is 100 and this quota can be increased.
        :param next_marker: {str} When you request a list of objects with a Limit setting, if the number of objects that
                            are still available for retrieval exceeds the limit, AWS WAF returns a NextMarker value in
                            the response. To retrieve the next batch of objects, provide the marker from the prior call
                            in your next request.
        :return:  {[datamodels.IPSet]} of  of IPSet data models.
                raise AWSWAFStatusCodeException if failed to validate response status code
        """
        page_size = (
            min(limit, consts.PAGE_SIZE) if limit is not None else consts.PAGE_SIZE
        )
        err_msg = f"Failed to list IP Sets in scope {scope}."

        payload_kwargs = remove_empty_kwargs(
            Scope=scope, Limit=page_size, NextMarker=next_marker
        )
        client = self._get_client(scope)
        response = client.list_ip_sets(**payload_kwargs)
        self.validate_response(response, error_msg=err_msg)
        ip_sets = self.parser.build_ip_set_list(raw_data=response, scope=scope)
        next_marker = response.get("NextMarker")

        while next_marker:
            if limit is not None and len(ip_sets) >= limit:
                break
            payload_kwargs.update({"NextMarker": next_marker})
            response = client.list_ip_sets(**payload_kwargs)
            self.validate_response(response, error_msg=err_msg)

            ip_sets.extend(
                self.parser.build_ip_set_list(raw_data=response, scope=scope)
            )
            next_marker = response.get("NextMarker")

        return ip_sets[:limit] if limit is not None else ip_sets

    def get_ip_set(self, name: str, scope: str, id: str) -> (str, datamodels.IPSet):
        """
        Retrieves the specified IPSet.
        :param name: {str} The name of the IP set. You cannot change the name of an IPSet after you create it.
        :param id: {str} A unique identifier for the set. This ID is returned in the responses to create and list commands.
                         You provide it to operations like update and delete.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: {({str} lock token, datamodels.IPSet)} Tuple of a string lock token, and an IPSet datamodel.
                raise AWSWAFStatusCodeException if failed to validate response status code
        """
        response = self._get_client(scope).get_ip_set(Name=name, Scope=scope, Id=id)
        self.validate_response(response, error_msg=f"Failed to get ip set {name}")
        ip_set = self.parser.build_ip_set(raw_data=response.get("IPSet"), scope=scope)
        lock_token = response.get("LockToken")

        return lock_token, ip_set

    def update_ip_set(
        self, scope: str, name: str, id: str, addresses: List[str], lock_token: str
    ) -> bool:
        """
        Updates the specified IPSet
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param name: {str} The name of the IP set. You cannot change the name of an IPSet after you create it.
        :param id: {str} A unique identifier for the set. This ID is returned in the responses to create and list commands.
                         You provide it to operations like update and delete.
        :param addresses: {list} Contains an array of strings that specify one or more IP addresses or blocks of IP addresses
                                 in Classless Inter-Domain Routing (CIDR) notation.
                                 AWS WAF supports all address ranges for IP versions IPv4 and IPv6.
                                 IP addresses must be masked.
        :param lock_token: {str} A token used for optimistic locking. AWS WAF returns a token to your get and list
                                 requests, to mark the state of the entity at the time of the request. To make changes
                                 to the entity associated with the token, you provide the token to operations like update
                                 and delete. AWS WAF uses the token to ensure that no changes have been made to the entity
                                 since you last retrieved it.
        :return: {bool} true if succeeded
                    raise AWSWAFStatusCodeException if failed to validate response status code
        """

        try:
            response = self._get_client(scope).update_ip_set(
                Name=name, Scope=scope, Id=id, Addresses=addresses, LockToken=lock_token
            )
        except botocore.exceptions.ClientError as error:
            self.validate_limitation(
                error.response,
                error_msg=f"{scope} IP Set {name} exceeded resource limit in AWS WAF",
            )
            raise error
        self.validate_response(response, error_msg=f"Failed to update ip set {name}")
        return True

    def create_ip_set(
        self,
        name: str,
        scope: str,
        ip_version: int,
        addresses: List[str],
        tags: Optional[dict] = None,
        description: Optional[str] = None,
    ) -> datamodels.IPSet:
        """
        Creates an IPSet , which you use to identify web requests that originate from specific IP addresses or ranges
        of IP addresses. For example, if you're receiving a lot of requests from a ranges of IP addresses, you can
        configure AWS WAF to block them using an IPSet that lists those IP addresses.
        :param name: {str} The name of the IP set. You cannot change the name of an IPSet after you create it.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param ip_version: {int} Specify 4 or 6
        :param addresses: {list} Contains a list of strings that specify one or more IP addresses or blocks of IP addresses in Classless Inter-Domain Routing (CIDR) notation. AWS WAF supports all address ranges for IP versions IPv4 and IPv6.
        :param tags: {dict} An dictionary of key:value pairs to associate with the resource.
        :param description: {str} A description of the IP set that helps with identification. You cannot change the description of an IP set after you create it.
        :return: IPSet data model
                    raise AWSWAFStatusCodeException if failed to validate response status code
                    raise AWSDuplicateItemException exception if IP set already exists

        """
        payload_kwargs = remove_empty_kwargs(
            Name=name,
            Scope=scope,
            Description=description,
            IPAddressVersion=consts.UNMAPPED_IPV.get(ip_version),
            Addresses=addresses,
            Tags=[{"Key": k, "Value": v} for k, v in tags.items()] if tags else None,
        )
        try:
            response = self._get_client(scope).create_ip_set(**payload_kwargs)
        except botocore.exceptions.ClientError as error:
            self.validate_duplicate(
                error.response,
                error_msg=f"{scope} IP Set {name} already exists in AWS WAF",
            )  # catch DuplicateItem exception
            raise error
        self.validate_response(response, error_msg=f"Failed to create IP set {name}")
        return self.parser.build_ip_set(raw_data=response.get("Summary"), scope=scope)

    def create_regex_pattern_set(
        self,
        name: str,
        scope: str,
        regex_list: List[str],
        tags: Optional[dict] = None,
        description: Optional[str] = None,
    ) -> datamodels.RegexSet:
        """
        Creates a RegexPatternSet, which you reference in a RegexPatternSetReferenceStatement , to have AWS WAF inspect
        a web request component for the specified patterns.
        :param name: {str} The name of the set. You cannot change the name after you create the set.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param regex_list: {list} list of regular expressions
        :param tags: {dict} An dictionary of key:value pairs to associate with the resource.
        :param description: {str} A description of the IP set that helps with identification. You cannot change the description of an IP set after you create it.
        :return: {datamodels.RegexSet} data model
                    raise AWSWAFStatusCodeException if failed to validate response status code
                    raise AWSDuplicateItemException exception if Regex Set already exists
        """
        payload_kwargs = remove_empty_kwargs(
            Name=name,
            Scope=scope,
            Description=description,
            RegularExpressionList=[{"RegexString": regex} for regex in regex_list],
            Tags=[{"Key": k, "Value": v} for k, v in tags.items()] if tags else None,
        )
        try:
            response = self._get_client(scope).create_regex_pattern_set(
                **payload_kwargs
            )
        except botocore.exceptions.ClientError as error:
            self.validate_duplicate(
                error.response,
                error_msg=f"{scope} Regex Pattern Set {name} already exists in AWS WAF",
            )  # catch DuplicateItem exception
            self.validate_limitation(
                error.response,
                error_msg=f"{scope} Regex Pattern Set {name} exceeded resource limit in AWS WAF",
            )
            raise error
        self.validate_response(
            response, error_msg=f"Failed to create Regex Pattern set {name}"
        )
        return self.parser.build_regex_set(
            raw_data=response.get("Summary"), scope=scope
        )

    def get_regex_pattern_set(
        self, name: str, scope: str, id: str
    ) -> (str, datamodels.RegexSet):
        """
        Retrieves the specified RegexPatternSet.
        :param name: {str} The name of the Regex Pattern set. You cannot change the name after you create the set.
        :param id: {str} A unique identifier for the set. This ID is returned in the responses to create and list commands.
                         You provide it to operations like update and delete.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: {({str} lock token, datamodels.RegexSet)} Tuple of a string lock token, and a RegexSet datamodel.
                raise AWSWAFStatusCodeException if failed to validate response status code
        """
        response = self._get_client(scope).get_regex_pattern_set(
            Name=name, Scope=scope, Id=id
        )
        self.validate_response(
            response, error_msg=f"Failed to get regex pattern set {name}"
        )
        regex_set = self.parser.build_regex_set(
            raw_data=response.get("RegexPatternSet", {}), scope=scope
        )
        lock_token = response.get("LockToken")

        return lock_token, regex_set

    def update_regex_pattern_set(
        self, scope: str, name: str, id: str, regex_list: List[str], lock_token: str
    ) -> bool:
        """
        Updates the specified RegexPatternSet.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param name: {str} The name of the Regex Pattern set. You cannot change the name after you create the set.
        :param id: {str} A unique identifier for the set. This ID is returned in the responses to create and list commands.
                         You provide it to operations like update and delete.
        :param regex_list: {list} list of updated regular expressions.
        :param lock_token: {str} A token used for optimistic locking. AWS WAF returns a token to your get and list
                                 requests, to mark the state of the entity at the time of the request. To make changes
                                 to the entity associated with the token, you provide the token to operations like update
                                 and delete. AWS WAF uses the token to ensure that no changes have been made to the entity
                                 since you last retrieved it.
        :return: {bool} true if succeeded
                    raise AWSWAFStatusCodeException if failed to validate response status code
        """
        try:
            response = self._get_client(scope).update_regex_pattern_set(
                Name=name,
                Scope=scope,
                Id=id,
                LockToken=lock_token,
                RegularExpressionList=[{"RegexString": regex} for regex in regex_list],
            )
        except botocore.exceptions.ClientError as error:
            self.validate_limitation(
                error.response,
                error_msg=f"{scope} Regex Pattern Set {name} exceeded resource limit in AWS WAF",
            )
            raise error

        self.validate_response(
            response, error_msg=f"Failed to update regex pattern set {name}"
        )
        return True

    def list_regex_pattern_sets(
        self, scope: str, limit: Optional[int] = None, next_marker: Optional[str] = None
    ) -> List[datamodels.RegexSet]:
        """
        Retrieves regex pattern sets that you manage. If limit is not specified, all available Regex Pattern Sets will be returned
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param limit: {int} The maximum number of objects that you want AWS WAF to return for this request.
                            If more objects are available, in the response, AWS WAF provides a NextMarker value that you
                            can use in a subsequent call to get the next batch of objects.
                            Max number of REGEX Pattern Sets per region is 10 and this quota cannot be changed.
        :param next_marker: {str} When you request a list of objects with a Limit setting, if the number of objects that
                            are still available for retrieval exceeds the limit, AWS WAF returns a NextMarker value in
                            the response. To retrieve the next batch of objects, provide the marker from the prior call
                            in your next request.
        :return:  {[datamodels.RegexSet]} list of RegexSet data models.
                raise AWSWAFStatusCodeException if failed to validate response status code
        """
        page_size = (
            min(limit, consts.PAGE_SIZE_10)
            if limit is not None
            else consts.PAGE_SIZE_10
        )
        err_msg = f"Failed to list Regex Pattern sets in scope {scope}."

        payload_kwargs = remove_empty_kwargs(
            Scope=scope, Limit=page_size, NextMarker=next_marker
        )

        response = self._get_client(scope).list_regex_pattern_sets(**payload_kwargs)
        self.validate_response(response, error_msg=err_msg)
        regex_sets = self.parser.build_regex_set_list(raw_data=response, scope=scope)
        next_marker = response.get("NextMarker")

        while next_marker:
            if limit is not None and len(regex_sets) >= limit:
                break
            payload_kwargs.update({"NextMarker": next_marker})
            response = self._get_client(scope).list_regex_pattern_sets(**payload_kwargs)
            self.validate_response(response, error_msg=err_msg)

            regex_sets.extend(
                self.parser.build_regex_set_list(raw_data=response, scope=scope)
            )
            next_marker = response.get("NextMarker")

        return regex_sets[:limit] if limit is not None else regex_sets

    def create_rule_group(
        self,
        name: str,
        scope: str,
        capacity: int,
        sampled_requests_enabled: bool,
        cloudwatch_metrics_enabled: bool,
        cloudwatch_metric_name: str,
        tags: Optional[dict] = None,
        description: Optional[str] = None,
    ) -> datamodels.RuleGroup:
        """
        Creates a RuleGroup per the specifications provided. A rule group defines a collection of rules to inspect and control web requests
        that you can use in a WebACL . When you create a rule group, you define an immutable capacity limit. If you update a rule group, you
        must stay within the capacity. This allows others to reuse the rule group with confidence in its capacity requirements.
        :param name: {str} The name of the rule group. You cannot change the name of a rule group after you create it.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param capacity: {int} The web ACL capacity units (WCUs) required for this rule group. When you create your own rule group, you define
                               this, and you cannot change it after creation. When you add or modify the rules in a rule group, AWS WAF
                               enforces this limit. You can check the capacity for a set of rules using CheckCapacity.
                               AWS WAF uses WCUs to calculate and control the operating resources that are used to run your rules, rule groups,
                               and web ACLs. AWS WAF calculates capacity differently for each rule type, to reflect the relative cost of each rule.
                               Simple rules that cost little to run use fewer WCUs than more complex rules that use more processing power.
                               Rule group capacity is fixed at creation, which helps users plan their web ACL WCU usage when they use a rule group.
                               The WCU limit for web ACLs is 1,500.
        :param sampled_requests_enabled: {bool} A boolean indicating whether AWS WAF should store a sampling of the web requests that match
                            the rules. You can view the sampled requests through the AWS WAF console.
        :param cloudwatch_metrics_enabled: {bool} A boolean indicating whether the associated resource sends metrics to CloudWatch.
                            For the list of available metrics, see: https://docs.aws.amazon.com/waf/latest/developerguide/monitoring-cloudwatch.html#waf-metrics
        :param cloudwatch_metric_name: {str} A name of the CloudWatch metric. The name can contain only the characters: A-Z, a-z, 0-9, -
                            (hyphen), and _ (underscore). The name can be from one to 128 characters long. It can't contain whitespace or
                            metric names reserved for AWS WAF, for example "All" and "Default_Action."
        :param tags: {dict} An dictionary of key:value pairs to associate with the resource.
        :param description: {str} A description of the rule group that helps with identification. You cannot change the description of a rule group after you create it.
        :return: {datamodels.RuleGroup} data model
                    raise AWSWAFStatusCodeException if failed to validate response status code
                    raise AWSDuplicateItemException exception if Rule Group already exists in AWS WAF.
        """
        payload_kwargs = remove_empty_kwargs(
            Name=name,
            Scope=scope,
            Capacity=capacity,
            VisibilityConfig={
                "SampledRequestsEnabled": sampled_requests_enabled,
                "CloudWatchMetricsEnabled": cloudwatch_metrics_enabled,
                "MetricName": cloudwatch_metric_name,
            },
            Description=description,
            Tags=[{"Key": k, "Value": v} for k, v in tags.items()] if tags else None,
        )
        try:
            response = self._get_client(scope).create_rule_group(**payload_kwargs)
        except botocore.exceptions.ClientError as error:
            self.validate_duplicate(
                error.response,
                error_msg=f"{scope} Rule Group {name} already exists in AWS WAF",
            )  # catch DuplicateItem exception
            raise error
        self.validate_response(
            response, error_msg=f"Failed to create Rule Group {name}"
        )
        return self.parser.build_rule_group(
            raw_data=response.get("Summary"), scope=scope
        )

    def list_rule_groups(
        self,
        scope: str,
        limit: Optional[int] = None,
        next_marker: Optional[str] = None,
        max_results_to_return: Optional[int] = None,
    ) -> List[datamodels.RuleGroup]:
        """
        Retrieves an array of RuleGroupSummary objects for the rule groups that you manage.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param limit: {int} The maximum number of objects that you want AWS WAF to return for this request.
                            If more objects are available, in the response, AWS WAF provides a NextMarker value that you
                            can use in a subsequent call to get the next batch of objects.
                            Max number of REGEX Pattern Sets per region is 10 and this quota cannot be changed.
        :param next_marker: {str} When you request a list of objects with a Limit setting, if the number of objects that
                            are still available for retrieval exceeds the limit, AWS WAF returns a NextMarker value in
                            the response. To retrieve the next batch of objects, provide the marker from the prior call
                            in your next request.
        :param max_results_to_return: {str} Specifies the max Rule Groups to return
        :return:  {[datamodels.RuleGroup]} list of RuleGroup data models.
                raise AWSWAFStatusCodeException if failed to validate response status code
        """
        payload_kwargs = remove_empty_kwargs(
            Scope=scope, Limit=limit, NextMarker=next_marker
        )
        response = self._get_client(scope).list_rule_groups(**payload_kwargs)
        self.validate_response(response, error_msg="Failed to list Rule Groups.")
        rule_groups = [
            self.parser.build_rule_group(raw_data=rule_group, scope=scope)
            for rule_group in response.get("RuleGroups")
        ]
        next_marker = response.get("NextMarker")

        while next_marker:
            payload_kwargs = remove_empty_kwargs(
                Scope=scope, Limit=limit, NextMarker=next_marker
            )
            response = self._get_client(scope).list_rule_groups(**payload_kwargs)
            self.validate_response(response, error_msg="Failed to list Rule Groups.")
            rule_groups += [
                self.parser.build_rule_group(raw_data=rule_group, scope=scope)
                for rule_group in response.get("RuleGroups")
            ]
            next_marker = response.get("NextMarker")

            if max_results_to_return and len(rule_groups) > max_results_to_return:
                rule_groups = rule_groups[:max_results_to_return]
                break

        return rule_groups

    def get_rule_group(
        self, name: str, scope: str, id: str
    ) -> (str, datamodels.RuleGroup):
        """
        Retrieves the specified RuleGroup.
        :param name: {str} The name of the rule group. You cannot change the name of a rule group after you create it.
        :param id: {str} A unique identifier for the rule group. This ID is returned in the responses to create and list commands.
                         You provide it to operations like update and delete.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: {({str} lock token, datamodels.IPSet)} Tuple of a string lock token, and an IPSet datamodel.
                raise AWSWAFStatusCodeException if failed to validate response status code
        """
        response = self._get_client(scope).get_rule_group(Name=name, Scope=scope, Id=id)
        self.validate_response(response, error_msg=f"Failed to get rule group {name}")
        rule_group = self.parser.build_rule_group(
            raw_data=response.get("RuleGroup"), scope=scope
        )
        lock_token = response.get("LockToken")

        return lock_token, rule_group

    def update_rule_group(
        self,
        scope: str,
        name: str,
        id: str,
        rules: List[dict],
        sampled_requests_enabled: bool,
        cloudwatch_metrics_enabled: bool,
        cloudwatch_metric_name: str,
        lock_token: str,
    ) -> bool:
        """
        Updates the specified RuleGroup .
        A rule group defines a collection of rules to inspect and control web requests that you can use in a WebACL . When you create a rule
        group, you define an immutable capacity limit. If you update a rule group, you must stay within the capacity. This allows others to
        reuse the rule group with confidence in its capacity requirements.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param name: {str} The name of the rule group. You cannot change the name of a rule group after you create it.
        :param id: {str} A unique identifier for the rule group. This ID is returned in the responses to create and list commands. You
                         provide it to operations like update and delete.
        :param rules: {[{dict}]} list of updated rules in rule group. Each rule is represented as json of type dictionary.
                            The Rule statements used to identify the web requests that you want to allow, block, or count. Each rule includes
                            one top-level statement that AWS WAF uses to identify matching web requests, and parameters that govern how AWS
                            WAF handles them.
        :param sampled_requests_enabled: {bool} A boolean indicating whether AWS WAF should store a sampling of the web requests that match
                            the rules. You can view the sampled requests through the AWS WAF console.
        :param cloudwatch_metrics_enabled: {bool} A boolean indicating whether the associated resource sends metrics to CloudWatch.
                            For the list of available metrics, see: https://docs.aws.amazon.com/waf/latest/developerguide/monitoring-cloudwatch.html#waf-metrics
        :param cloudwatch_metric_name: {str} A name of the CloudWatch metric. The name can contain only the characters: A-Z, a-z, 0-9, -
                            (hyphen), and _ (underscore). The name can be from one to 128 characters long. It can't contain whitespace or
                            metric names reserved for AWS WAF, for example "All" and "Default_Action."
        :param lock_token: {str} A token used for optimistic locking. AWS WAF returns a token to your get and list
                                 requests, to mark the state of the entity at the time of the request. To make changes
                                 to the entity associated with the token, you provide the token to operations like update
                                 and delete. AWS WAF uses the token to ensure that no changes have been made to the entity
                                 since you last retrieved it.
        :return: {bool} true if succeeded
                    raise AWSWAFStatusCodeException if failed to validate response status code
        """
        try:
            response = self._get_client(scope).update_rule_group(
                Name=name,
                Scope=scope,
                Id=id,
                LockToken=lock_token,
                Rules=rules,
                VisibilityConfig={
                    "SampledRequestsEnabled": sampled_requests_enabled,
                    "CloudWatchMetricsEnabled": cloudwatch_metrics_enabled,
                    "MetricName": cloudwatch_metric_name,
                },
            )
        except botocore.exceptions.ClientError as error:
            self.validate_limitation(
                error.response,
                error_msg=f"{scope} Rule Group {name} exceeded resource limit in AWS WAF",
            )
            raise error

        self.validate_response(
            response, error_msg=f"Failed to update Rule Group {name}"
        )
        return True

    def create_web_acl(
        self,
        scope: str,
        name: str,
        rule_group_arn: Optional[str],
        sampled_requests_enabled: bool,
        cloudwatch_metrics_enabled: bool,
        cloudwatch_metric_name: str,
        rule_source_name: str,
        ip_set_arn: Optional[str],
        rule_priority: int,
        default_action: str,
        ip_set_action: Optional[str] = None,
        tags: Optional[dict] = None,
        description: Optional[str] = None,
    ) -> datamodels.WebACL:
        """
        Creates a WebACL per the specifications provided. If rule_group_arn is specified the web ACL will include a rule that is
        defined in the RuleGroup. If ip_set_arn is specified the Web ACL will detect web requests coming from particular IP addresses
        in the IP Set. Note: only one reference RuleGroup/IPSet will be added as a rule to web ACL. The action of the rule is 'Block'.

        A Web ACL defines a collection of rules to use to inspect and control web requests. Each rule has an action defined (allow, block, or count)
        for requests that match the statement of the rule. In the Web ACL, you assign a default action to take (allow, block) for any request
        that does not match any of the rules. The rules in a Web ACL can be a combination of the types Rule , RuleGroup , and managed rule group.
        You can associate a Web ACL with one or more AWS resources to protect. The resources can be Amazon CloudFront, an Amazon API Gateway REST API,
        an Application Load Balancer, or an AWS AppSync GraphQL API.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param name: {str} The name of the Wec ACL. You cannot change the name of a rule group after you create it.
        :param rule_source_name: {str} the name of the rule to add the created Web ACL.
        :param rule_group_arn: {str} A rule statement used to run the rules that are defined in a RuleGroup . To use this, create a rule group
                            with your rules, then provide the ARN of the rule group in this statement.
        :param ip_set_arn: {str} A rule statement used to detect web requests coming from particular IP addresses or address ranges. To use this, create an IPSet that specifies the addresses you want to detect, then use the ARN of that set in this statement. To create an IP set, see CreateIPSet .
                            Each IP set rule statement references an IP set. You create and maintain the set independent of your rules.
                            This allows you to use the single set in multiple rules. When you update the referenced set, AWS WAF automatically
                            updates all rules that reference it. The Amazon Resource Name (ARN) of the IPSet that this statement references.
        :param ip_set_action: {str} The action that AWS WAF should take on a web request when it matches the rule statement.
                            Settings at the web ACL level can override the rule action setting. Values can be 'Allow' 'Block' or 'Count'
        :param sampled_requests_enabled: {bool} A boolean indicating whether AWS WAF should store a sampling of the web requests that match
                            the rules. You can view the sampled requests through the AWS WAF console.
        :param cloudwatch_metrics_enabled: {bool} A boolean indicating whether the associated resource sends metrics to CloudWatch.
                            For the list of available metrics, see: https://docs.aws.amazon.com/waf/latest/developerguide/monitoring-cloudwatch.html#waf-metrics
        :param cloudwatch_metric_name: {str} A name of the CloudWatch metric. The name can contain only the characters: A-Z, a-z, 0-9, -
                            (hyphen), and _ (underscore). The name can be from one to 128 characters long. It can't contain whitespace or
                            metric names reserved for AWS WAF, for example "All" and "Default_Action."
        :param default_action: {str} The action to perform if none of the Rules contained in the WebACL match. Values can be 'Allow' or 'Block'
                            and are applied for IP Sets only.
        :param rule_priority: {int} If you define more than one Rule in a WebACL , AWS WAF evaluates each request against the Rules in order
                            based on the value of Priority . AWS WAF processes rules with lower priority first. The priorities don't need to be consecutive, but they must all be different.
        :param description: {str}  A description of the Web ACL that helps with identification. You cannot change the description of a Web ACL after you create it.
        :param tags: {dict} An dictionary of key:value pairs to associate with the resource.
        :return: {datamodels.WebAcl} data model
                    raise AWSWAFStatusCodeException if failed to validate response status code
                    raise AWSDuplicateItemException exception if Web ACL already exists in AWS WAF.
        """
        rule_payload = {
            "Name": rule_source_name,
            "Priority": rule_priority,
            "Statement": {},
            "VisibilityConfig": {
                "SampledRequestsEnabled": True,
                "CloudWatchMetricsEnabled": True,
                "MetricName": rule_source_name,
            },
        }
        if rule_group_arn:
            rule_payload["Statement"]["RuleGroupReferenceStatement"] = {
                "ARN": rule_group_arn,
                "ExcludedRules": [],
            }
            rule_payload["OverrideAction"] = {"None": {}}

        elif ip_set_arn:
            rule_payload["Statement"]["IPSetReferenceStatement"] = {"ARN": ip_set_arn}
            rule_payload["Action"] = {ip_set_action: {}}

        payload_kwargs = remove_empty_kwargs(
            Name=name,
            Scope=scope,
            DefaultAction={default_action: {}},
            VisibilityConfig={
                "SampledRequestsEnabled": sampled_requests_enabled,
                "CloudWatchMetricsEnabled": cloudwatch_metrics_enabled,
                "MetricName": cloudwatch_metric_name,
            },
            Description=description,
            Rules=[rule_payload] if ip_set_arn or rule_group_arn else None,
            Tags=[{"Key": k, "Value": v} for k, v in tags.items()] if tags else None,
        )
        try:
            response = self._get_client(scope).create_web_acl(**payload_kwargs)
        except botocore.exceptions.ClientError as error:
            self.validate_duplicate(
                error.response,
                error_msg=f"{scope} Web ACL {name} already exists in AWS WAF",
            )  # catch DuplicateItem exception
            raise error
        self.validate_response(response, error_msg=f"Failed to create Web ACL {name}")
        return self.parser.build_wec_acl(raw_data=response.get("Summary"), scope=scope)

    def list_web_acls(
        self,
        scope: str,
        limit: Optional[int] = None,
        next_marker: Optional[str] = None,
        max_results_to_return: Optional[int] = None,
    ) -> List[datamodels.WebACL]:
        """
        Retrieves an array of WebACLSummary objects for the web ACLs that you manage.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application. A regional application
                            can be an Application Load Balancer (ALB), an API Gateway REST API, or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param limit: {int} The maximum number of objects that you want AWS WAF to return for this request.
                            If more objects are available, in the response, AWS WAF provides a NextMarker value that you
                            can use in a subsequent call to get the next batch of objects.
                            Max number of REGEX Pattern Sets per region is 10 and this quota cannot be changed.
        :param next_marker: {str} When you request a list of objects with a Limit setting, if the number of objects that
                            are still available for retrieval exceeds the limit, AWS WAF returns a NextMarker value in
                            the response. To retrieve the next batch of objects, provide the marker from the prior call
                            in your next request.
        :param max_results_to_return: {str} Specifies the max web acls to return
        :return:  {[datamodels.WebACL]} list of RuleGroup data models.
                raise AWSWAFStatusCodeException if failed to validate response status code
        """
        payload_kwargs = remove_empty_kwargs(
            Scope=scope, Limit=limit, NextMarker=next_marker
        )
        response = self._get_client(scope).list_web_acls(**payload_kwargs)
        self.validate_response(response, error_msg="Failed to list Web ACLs.")
        web_acls = [
            self.parser.build_wec_acl(raw_data=web_acl, scope=scope)
            for web_acl in response.get("WebACLs")
        ]
        next_marker = response.get("NextMarker")
        while next_marker:
            payload_kwargs = remove_empty_kwargs(
                Scope=scope, Limit=limit, NextMarker=next_marker
            )
            response = self._get_client(scope).list_web_acls(**payload_kwargs)
            self.validate_response(response, error_msg="Failed to list Web ACLs.")
            web_acls += [
                self.parser.build_wec_acl(raw_data=web_acl, scope=scope)
                for web_acl in response.get("WebACLs")
            ]
            next_marker = response.get("NextMarker")

            if max_results_to_return and len(web_acls) > max_results_to_return:
                web_acls = web_acls[:max_results_to_return]
                break

        return web_acls

    def get_web_acl(self, name: str, scope: str, id: str) -> (str, datamodels.WebACL):
        """
        Retrieves the specified WebACL .
        :param name: {str} The name of the Web ACL. You cannot change the name of a Web ACL after you create it.
        :param id: {str} The unique identifier for the Web ACL. This ID is returned in the responses to create and list commands.
                         You provide it to operations like update and delete.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: {({str} lock token, datamodels.WebACL)} Tuple of a string lock token, and an IPSet datamodel.
                raise AWSWAFStatusCodeException if failed to validate response status code
        """
        response = self._get_client(scope).get_web_acl(Name=name, Scope=scope, Id=id)
        self.validate_response(response, error_msg=f"Failed to get Web ACL {name}")
        web_acl = self.parser.build_wec_acl(
            raw_data=response.get("WebACL"), scope=scope
        )
        lock_token = response.get("LockToken")

        return lock_token, web_acl

    def update_web_acl(
        self,
        scope: str,
        name: str,
        id: str,
        rules: List[dict],
        sampled_requests_enabled: bool,
        lock_token: str,
        cloudwatch_metrics_enabled: bool,
        cloudwatch_metric_name: str,
        default_action: str,
        rule_priority: int,
        rule_group_arn: Optional[str],
        rule_source_name: str,
        ip_set_arn: Optional[str],
        ip_set_action: Optional[str] = None,
    ) -> bool:
        """
        Updates the specified WebACL .
        A Web ACL defines a collection of rules to use to inspect and control web requests. Each rule has an action defined (allow, block, or count)
        for requests that match the statement of the rule. In the Web ACL, you assign a default action to take (allow, block) for any request
        that does not match any of the rules. The rules in a Web ACL can be a combination of the types Rule , RuleGroup , and managed rule group.
        You can associate a Web ACL with one or more AWS resources to protect. The resources can be Amazon CloudFront, an Amazon API Gateway REST API,
        an Application Load Balancer, or an AWS AppSync GraphQL API.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param name: {str} The name of the Web ACL. You cannot change the name of a Web ACL after you create it.
        :param id: {str} The unique identifier for the Web ACL. This ID is returned in the responses to create and list commands.
                         You provide it to operations like update and delete.
        :param rules: {[{dict}]} list of updated rules in rule group. Each rule is represented as json of type dictionary.
                           The Rule statements used to identify the web requests that you want to allow, block, or count.
                           Each rule includes one top-level statement that AWS WAF uses to identify matching web requests, and parameters
                           that govern how AWS WAF handles them.
        :param rule_source_name: {str} the name of the rule to add the created Web ACL.
        :param rule_group_arn: {str} A rule statement used to run the rules that are defined in a RuleGroup . To use this, create a rule group
                            with your rules, then provide the ARN of the rule group in this statement.
        :param ip_set_arn: {str} A rule statement used to detect web requests coming from particular IP addresses or address ranges. To use this, create an IPSet that specifies the addresses you want to detect, then use the ARN of that set in this statement. To create an IP set, see CreateIPSet .
                            Each IP set rule statement references an IP set. You create and maintain the set independent of your rules.
                            This allows you to use the single set in multiple rules. When you update the referenced set, AWS WAF automatically
                            updates all rules that reference it. The Amazon Resource Name (ARN) of the IPSet that this statement references.
        :param ip_set_action: {str} The action that AWS WAF should take on a web request when it matches the rule statement.
                            Settings at the web ACL level can override the rule action setting. Values can be 'Allow' 'Block' or 'Count'
        :param rule_priority: {int} If you define more than one Rule in a WebACL , AWS WAF evaluates each request against the Rules in order
                            based on the value of Priority . AWS WAF processes rules with lower priority first. The priorities don't need to
                            be consecutive, but they must all be different.
        :param sampled_requests_enabled: {bool} A boolean indicating whether AWS WAF should store a sampling of the web requests that match
                            the rules. You can view the sampled requests through the AWS WAF console.
        :param cloudwatch_metrics_enabled: {bool} A boolean indicating whether the associated resource sends metrics to CloudWatch.
                            For the list of available metrics, see: https://docs.aws.amazon.com/waf/latest/developerguide/monitoring-cloudwatch.html#waf-metrics
        :param cloudwatch_metric_name: {str} A name of the CloudWatch metric. The name can contain only the characters: A-Z, a-z, 0-9, -
                            (hyphen), and _ (underscore). The name can be from one to 128 characters long. It can't contain whitespace or
                            metric names reserved for AWS WAF, for example "All" and "Default_Action."
        :param default_action: {str} The action to perform if none of the Rules contained in the WebACL match.
        :param lock_token: {str} A token used for optimistic locking. AWS WAF returns a token to your get and list
                                 requests, to mark the state of the entity at the time of the request. To make changes
                                 to the entity associated with the token, you provide the token to operations like update
                                 and delete. AWS WAF uses the token to ensure that no changes have been made to the entity
                                 since you last retrieved it.
        :return: {bool} true if succeeded
                    raise AWSWAFStatusCodeException if failed to validate response status code
        """
        rule_json = {
            "Name": rule_source_name,
            "Priority": rule_priority,
            "Statement": {},
            "VisibilityConfig": {
                "SampledRequestsEnabled": True,
                "CloudWatchMetricsEnabled": True,
                "MetricName": rule_source_name,
            },
        }
        if rule_group_arn:
            rule_json["Statement"]["RuleGroupReferenceStatement"] = {
                "ARN": rule_group_arn,
                "ExcludedRules": [],
            }
            rule_json["OverrideAction"] = {"None": {}}

        elif ip_set_arn:
            rule_json["Statement"]["IPSetReferenceStatement"] = {"ARN": ip_set_arn}
            rule_json["Action"] = {ip_set_action: {}}

        try:
            response = self._get_client(scope).update_web_acl(
                Name=name,
                Scope=scope,
                Id=id,
                LockToken=lock_token,
                Rules=rules + [rule_json],
                DefaultAction={default_action: {}},
                VisibilityConfig={
                    "SampledRequestsEnabled": sampled_requests_enabled,
                    "CloudWatchMetricsEnabled": cloudwatch_metrics_enabled,
                    "MetricName": cloudwatch_metric_name,
                },
            )
        except botocore.exceptions.ClientError as error:
            self.validate_limitation(
                error.response,
                error_msg=f"{scope} Web ACL {name} exceeded resource limit in AWS WAF",
            )
            raise error

        self.validate_response(response, error_msg=f"Failed to update Web ACL {name}")
        return True

    def remove_web_acl(
        self,
        scope: str,
        name: str,
        id: str,
        rules: List[dict],
        default_action: str,
        sampled_requests_enabled: bool,
        cloudwatch_metrics_enabled: bool,
        cloudwatch_metric_name: str,
        lock_token: Optional[str] = None,
    ) -> bool:
        """
        Remove WebACL by updating the rule list without him.
        A Web ACL defines a collection of rules to use to inspect and control web requests. Each rule has an action defined (allow, block, or count)
        for requests that match the statement of the rule. In the Web ACL, you assign a default action to take (allow, block) for any request
        that does not match any of the rules. The rules in a Web ACL can be a combination of the types Rule , RuleGroup , and managed rule group.
        You can associate a Web ACL with one or more AWS resources to protect. The resources can be Amazon CloudFront, an Amazon API Gateway REST API,
        an Application Load Balancer, or an AWS AppSync GraphQL API.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param name: {str} The name of the Web ACL. You cannot change the name of a Web ACL after you create it.
        :param id: {str} The unique identifier for the Web ACL. This ID is returned in the responses to create and list commands.
                         You provide it to operations like update and delete.
        :param rules: {[{dict}]} list of updated rules in rule group. Each rule is represented as json of type dictionary.
                           The Rule statements used to identify the web requests that you want to allow, block, or count.
                           Each rule includes one top-level statement that AWS WAF uses to identify matching web requests, and parameters
                           that govern how AWS WAF handles them.
        :param default_action: {str} The action to perform if none of the Rules contained in the WebACL match.
        :param lock_token: {str} A token used for optimistic locking. AWS WAF returns a token to your get and list
                                 requests, to mark the state of the entity at the time of the request. To make changes
                                 to the entity associated with the token, you provide the token to operations like update
                                 and delete. AWS WAF uses the token to ensure that no changes have been made to the entity
                                 since you last retrieved it.
        :param cloudwatch_metrics_enabled: {bool} A boolean indicating whether the associated resource sends metrics to CloudWatch.
                            For the list of available metrics, see: https://docs.aws.amazon.com/waf/latest/developerguide/monitoring-cloudwatch.html#waf-metrics
        :param cloudwatch_metric_name: {str} A name of the CloudWatch metric. The name can contain only the characters: A-Z, a-z, 0-9, -
                            (hyphen), and _ (underscore). The name can be from one to 128 characters long. It can't contain whitespace or
                            metric names reserved for AWS WAF, for example "All" and "Default_Action."
        :param sampled_requests_enabled: {bool} A boolean indicating whether AWS WAF should store a sampling of the web requests that match
                            the rules. You can view the sampled requests through the AWS WAF console.
        :return: {bool} true if succeeded
                    raise AWSWAFStatusCodeException if failed to validate response status code
        """

        try:
            response = self._get_client(scope).update_web_acl(
                Name=name,
                Scope=scope,
                Id=id,
                LockToken=lock_token,
                Rules=rules,
                DefaultAction={default_action: {}},
                VisibilityConfig={
                    "SampledRequestsEnabled": sampled_requests_enabled,
                    "CloudWatchMetricsEnabled": cloudwatch_metrics_enabled,
                    "MetricName": cloudwatch_metric_name,
                },
            )
        except botocore.exceptions.ClientError as error:
            self.validate_limitation(
                error.response,
                error_msg=f"{scope} Web ACL {name} exceeded resource limit in AWS WAF",
            )
            raise error

        self.validate_response(response, error_msg=f"Failed to update Web ACL {name}")
        return True
