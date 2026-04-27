from __future__ import annotations
from typing import Optional
from . import consts


class IPSet:
    """
    AWS WAF IP Set datamodel.
    """

    def __init__(
        self,
        raw_data=None,
        name=None,
        ipset_id=None,
        description=None,
        lock_token=None,
        arn=None,
        ip_version=None,
        addresses=None,
        scope=None,
        entity_addresses=None,
        **kwargs,
    ):
        """

        :param raw_data: raw json response
        :param name: {str} the name of the ip set
        :param ipset_id: {str} A unique identifier for the set. This ID is returned in the responses to create and list
                               commands. You provide it to operations like update and delete.
        :param description: {str} A description of the IP set that helps with identification.
                               You cannot change the description of an IP set after you create it.
        :param lock_token: {str} A token used for optimistic locking. AWS WAF returns a token to your get and list requests,
                               to mark the state of the entity at the time of the request. To make changes to the entity
                               associated with the token, you provide the token to operations like update and delete. AWS WAF uses the token to ensure that no changes have been made to the entity since you last retrieved it.
        :param arn: {str} The Amazon Resource Name (ARN) of the entity.
        :param ip_version: {str} Specify IPV4 or IPV6.
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param addresses: {list} Contains an array of strings that specify one or more IP addresses or blocks of IP addresses
                                in Classless Inter-Domain Routing (CIDR) notation. AWS WAF supports all address ranges for
                                IP versions IPv4 and IPv6.
        :param entity_addresses: {list} of IP addresses correlated to the matching entity.identifier.
        """
        self.raw_data = raw_data
        self.name = name
        self.ipset_id = ipset_id
        self.description = description
        self.lock_token = lock_token
        self.arn = arn
        self.ip_version = ip_version
        self.addresses = addresses or []  # masked IP addresses
        self.entity_addresses = (
            entity_addresses or []
        )  # masked/unmasked IP addresses correlated to entity.identifier
        self.scope = scope

    @property
    def unmapped_scope(self):
        if self.scope:
            return self.scope.lower().title()

    @property
    def unmapped_ipversion(self):
        if self.ip_version:
            return consts.UNMAPPED_IPV.get(self.ip_version)

    @property
    def scoped_name(self):
        """
        IP Set unique name, consist of IP Set name combined and belonging scope. For example, if the IP Set is named "My_SET" the scoped
        name will be "My_SET_CLOUDFRONT" or "My_SET_REGIONAL".
        :return: {str} IP Set scoped name
        """
        return f"{self.name}_{self.scope}"

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return {
            "Name": self.name,
            "ID": self.ipset_id,
            "Description": self.description,
            "Lock Token": self.lock_token,
            "ARN": self.arn,
        }


class RegexSet:
    """
    AWS WAF Regex Pattern Set datamodel.
    """

    def __init__(
        self,
        raw_data=None,
        name=None,
        regex_id=None,
        description=None,
        lock_token=None,
        arn=None,
        regex_list: Optional[list] = None,
        entity_list: Optional[list] = None,
        scope=None,
        **kwargs,
    ):
        """

        :param raw_data: raw json response
        :param name: {str} The name of the set. You cannot change the name after you create the set.
        :param regex_id: {str} A unique identifier for the set. This ID is returned in the responses to create and list commands.
                            You provide it to operations like update and delete.
        :param description: {str}  A description of the set that helps with identification. You cannot change the
                            description of a set after you create it.
        :param lock_token: {str} A token used for optimistic locking. AWS WAF returns a token to your get and list
                            requests, to mark the state of the entity at the time of the request. To make changes to the
                            entity associated with the token, you provide the token to operations like update and delete.
                            AWS WAF uses the token to ensure that no changes have been made to the entity since you last retrieved it.
        :param arn: {str} The Amazon Resource Name (ARN) of the entity.
        :param regex_list: {list} of regular expressions.
        :param entity_list: {list} of entities correlated to the regex expressions in the regex_list
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        """
        self.raw_data = raw_data
        self.name = name
        self.regex_id = regex_id
        self.description = description
        self.lock_token = lock_token
        self.arn = arn
        self.regex_list = regex_list or []
        self.entity_list = entity_list or []
        self.scope = scope

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return {
            "Name": self.name,
            "ID": self.regex_id,
            "Description": self.description,
            "Lock Token": self.lock_token,
            "ARN": self.arn,
        }

    @property
    def unmapped_scope(self):
        if self.scope:
            return self.scope.lower().title()

    @property
    def scoped_name(self):
        return self.name + self.scope


class RuleGroup:
    """
    AWS WAF Rule Group data model.
    """

    def __init__(
        self,
        raw_data=None,
        name=None,
        scope=None,
        capacity: Optional[int] = None,
        description=None,
        sampled_requests_enabled: Optional[bool] = None,
        cloudwatch_metrics_enabled: Optional[bool] = None,
        rules=None,
        cloudwatch_metric_name: Optional[str] = None,
        arn: str = None,
        rule_group_id: Optional[str] = None,
        lock_token: Optional[str] = None,
        **kwargs,
    ):
        """

        :param raw_data: raw json response
        :param name: {str} name of the rule group
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param capacity: {int} The web ACL capacity units (WCUs) required for this rule group.
                               When you create your own rule group, you define this, and you cannot change it after creation. When you add
                               or modify the rules in a rule group, AWS WAF enforces this limit. You can check the capacity for a set of rules
                               using CheckCapacity. AWS WAF uses WCUs to calculate and control the operating resources that are used to run
                               your rules, rule groups, and web ACLs. AWS WAF calculates capacity differently for each rule type, to reflect
                               the relative cost of each rule. Simple rules that cost little to run use fewer WCUs than more complex rules
                               that use more processing power. Rule group capacity is fixed at creation, which helps users plan their web ACL
                               WCU usage when they use a rule group. The WCU limit for web ACLs is 1,500.
        :param description: {str} A description of the rule group that helps with identification. You cannot change the description of a rule group after you create it.
        :param sampled_requests_enabled: {bool} A boolean indicating whether AWS WAF should store a sampling of the web requests that match the rules.
                                                You can view the sampled requests through the AWS WAF console.
        :param cloudwatch_metrics_enabled: {bool} A boolean indicating whether the associated resource sends metrics to CloudWatch.
                                                  For the list of available metrics, see AWS WAF Metrics - https://docs.aws.amazon.com/waf/latest/developerguide/monitoring-cloudwatch.html#waf-metrics
        :param cloudwatch_metric_name: {str} A name of the CloudWatch metric. The name can contain only the characters: A-Z, a-z, 0-9, - (hyphen), and _ (underscore).
                                             The name can be from one to 128 characters long. It can't contain whitespace or metric names
                                             reserved for AWS WAF, for example "All" and "Default_Action."
        :param arn: {str} The Amazon Resource Name (ARN) of the entity.
        :param rules: [{datamodels.Rule}] list of Rule data models
        :param rule_group_id: {str} A unique identifier for the rule group. This ID is returned in the responses to create and list commands.
                                    You provide it to operations like update and delete.
        :param lock_token: {str} A token used for optimistic locking.
        """
        self.raw_data = raw_data
        self.name = name
        self.scope = scope
        self.capacity = capacity
        self.description = description
        self.sampled_requests_enabled = sampled_requests_enabled
        self.cloudwatch_metrics_enabled = cloudwatch_metrics_enabled
        self.cloudwatch_metric_name = cloudwatch_metric_name
        self.arn = arn
        self.rule_group_id = rule_group_id
        self.lock_token = lock_token
        self.rules = rules

    def as_json(self):
        return {
            "Name": self.name,
            "Id": self.rule_group_id,
            "Description": self.description,
            "LockToken": self.lock_token,
            "ARN": self.arn,
        }

    def as_csv(self):
        return {
            "Name": self.name,
            "ID": self.rule_group_id,
            "Description": self.description,
            "Lock Token": self.lock_token,
            "ARN": self.arn,
        }

    @property
    def unmapped_scope(self):
        if self.scope:
            return self.scope.lower().title()

    @property
    def scoped_name(self):
        return self.name + self.scope


class Rule:
    """
    AWS WAF Rule data model.
    """

    def __init__(self, raw_data=None, name=None, priority=None, **kwargs):
        """

        :param raw_data: raw json response
        :param Name: {str} The name of the rule group. You cannot change the name of a rule group after you create it.
        :param Priority: {str} If you define more than one Rule in a WebACL , AWS WAF evaluates each request against the Rules in order based on the value of Priority . AWS WAF processes rules with lower priority first. The priorities don't need to be consecutive, but they must all be different.
        :param kwargs:
        """
        self.raw_data = raw_data
        self.name = name
        self.priority = priority

    def as_dict(self):
        return self.raw_data


class WebACL:
    """
    AWS WAF Web ACL data model.
    """

    def __init__(
        self,
        raw_data=None,
        name=None,
        scope=None,
        description=None,
        default_action=None,
        sampled_requests_enabled: Optional[bool] = None,
        cloudwatch_metrics_enabled: Optional[bool] = None,
        rules=Optional[Rule],
        cloudwatch_metric_name: Optional[str] = None,
        arn: str = None,
        web_acl_id: Optional[str] = None,
        lock_token: Optional[str] = None,
        **kwargs,
    ):
        """

        :param raw_data: raw json response
        :param name: {str} name of the Web ACL
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :param capacity: {int} The web ACL capacity units (WCUs) required for this rule group.
                               When you create your own rule group, you define this, and you cannot change it after creation. When you add
                               or modify the rules in a rule group, AWS WAF enforces this limit. You can check the capacity for a set of rules
                               using CheckCapacity. AWS WAF uses WCUs to calculate and control the operating resources that are used to run
                               your rules, rule groups, and web ACLs. AWS WAF calculates capacity differently for each rule type, to reflect
                               the relative cost of each rule. Simple rules that cost little to run use fewer WCUs than more complex rules
                               that use more processing power. Rule group capacity is fixed at creation, which helps users plan their web ACL
                               WCU usage when they use a rule group. The WCU limit for web ACLs is 1,500.
        :param description: {str} A description of the Web ACL that helps with identification. You cannot change the description of a Web ACL after you create it.
        :param sampled_requests_enabled: {bool} A boolean indicating whether AWS WAF should store a sampling of the web requests that match the rules.
                                                You can view the sampled requests through the AWS WAF console.
        :param cloudwatch_metrics_enabled: {bool} A boolean indicating whether the associated resource sends metrics to CloudWatch.
                                                  For the list of available metrics, see AWS WAF Metrics - https://docs.aws.amazon.com/waf/latest/developerguide/monitoring-cloudwatch.html#waf-metrics
        :param cloudwatch_metric_name: {str} A name of the CloudWatch metric. The name can contain only the characters: A-Z, a-z, 0-9, - (hyphen), and _ (underscore).
                                             The name can be from one to 128 characters long. It can't contain whitespace or metric names
                                             reserved for AWS WAF, for example "All" and "Default_Action."
        :param arn: {str} The Amazon Resource Name (ARN) of the entity.
        :param rules: [{datamodels.Rule}] list of Rule data models
        :param default_action: {str} The action to perform if none of the Rules contained in the WebACL match. Values can be 'Allow' or 'Block'
        :param rule_group_id: {str} A unique identifier for the rule group. This ID is returned in the responses to create and list commands.
                                    You provide it to operations like update and delete.
        """
        self.raw_data = raw_data
        self.name = name
        self.scope = scope
        self.description = description
        self.sampled_requests_enabled = sampled_requests_enabled
        self.cloudwatch_metrics_enabled = cloudwatch_metrics_enabled
        self.cloudwatch_metric_name = cloudwatch_metric_name
        self.arn = arn
        self.web_acl_id = web_acl_id
        self.default_action = default_action
        self.rules = rules
        self.lock_token = lock_token

    @property
    def unmapped_scope(self):
        if self.scope:
            return self.scope.lower().title()

    @property
    def scoped_name(self):
        return self.name + self.scope

    def as_dict(self):
        return self.raw_data

    def as_json(self):
        return {
            "Name": self.name,
            "Id": self.web_acl_id,
            "Description": self.description,
            "LockToken": self.lock_token,
            "ARN": self.arn,
        }

    def as_csv(self):
        return {
            "Name": self.name,
            "ID": self.web_acl_id,
            "Description": self.description,
            "Lock Token": self.lock_token,
            "ARN": self.arn,
        }
