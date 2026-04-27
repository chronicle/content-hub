from __future__ import annotations
from . import consts
from .datamodels import IPSet, RegexSet, RuleGroup, Rule, WebACL


class AWSWAFParser:
    """
    AWS WAF Transformation Layer.
    """

    @staticmethod
    def build_ip_set(raw_data: dict, scope=None) -> IPSet:
        """
        Returns IPSet data model.
        :param raw_data: {dict} raw json data response
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: {datamodels.RegexSet} IP Set data model
        """
        mapped_ipv = consts.MAPPED_IPV.get(raw_data.get("IPAddressVersion"))
        return IPSet(
            raw_data,
            name=raw_data.get("Name"),
            ipset_id=raw_data.get("Id"),
            description=raw_data.get("Description"),
            lock_token=raw_data.get("LockToken"),
            arn=raw_data.get("ARN"),
            ip_version=mapped_ipv,
            addresses=raw_data.get("Addresses"),
            scope=scope,
        )

    @staticmethod
    def build_ip_set_list(raw_data: dict, scope=None) -> [IPSet]:
        """
        Returns list of IPSet data models.
        :param raw_data: {dict} raw json data response
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: [datamodels.IPSet]
        """
        return [
            AWSWAFParser.build_ip_set(raw_data=ip_set, scope=scope)
            for ip_set in raw_data.get("IPSets", [])
        ]

    @staticmethod
    def build_regex_set(raw_data: dict, scope=None) -> RegexSet:
        """
        Returns RegexSet data model.
        :param raw_data: {dict} raw json data response
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: {datamodels.RegexSet} Regex Set data model
        """
        regex_list = raw_data.get("RegularExpressionList", [])

        return RegexSet(
            raw_data,
            name=raw_data.get("Name"),
            regex_id=raw_data.get("Id"),
            description=raw_data.get("Description"),
            lock_token=raw_data.get("LockToken"),
            arn=raw_data.get("ARN"),
            scope=scope,
            regex_list=[regex.get("RegexString") for regex in regex_list],
        )

    @staticmethod
    def build_regex_set_list(raw_data: dict, scope=None) -> [RegexSet]:
        """
        Returns list of RegexSet datamodels.
        :param raw_data:  {dict} raw json data response
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: {[datamodels.RegexSet]} List of Regex Set data models.
        """
        return [
            AWSWAFParser.build_regex_set(raw_data=regex_set, scope=scope)
            for regex_set in raw_data.get("RegexPatternSets", [])
        ]

    @staticmethod
    def build_rule_group(raw_data: dict, scope=None) -> RuleGroup:
        """
        Returns RuleGroup data model.
        :param raw_data: {dict} raw json data response
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: {datamodels.RuleGroup} RuleGroup data model
        """
        rules = raw_data.get("Rules", [])
        visibility_config = raw_data.get("VisibilityConfig", {})
        return RuleGroup(
            raw_data=raw_data,
            name=raw_data.get("Name"),
            lock_token=raw_data.get("LockToken"),
            rule_group_id=raw_data.get("Id"),
            description=raw_data.get("Description"),
            rules=[AWSWAFParser.build_rule(rule, scope=scope) for rule in rules],
            scope=scope,
            sampled_requests_enabled=visibility_config.get("SampledRequestsEnabled"),
            cloudwatch_metrics_enabled=visibility_config.get(
                "CloudWatchMetricsEnabled"
            ),
            cloudwatch_metric_name=visibility_config.get("MetricName"),
            arn=raw_data.get("ARN"),
        )

    @staticmethod
    def build_rule(raw_data: dict, scope=None) -> Rule:
        """
        Return Rule Data model
        :param raw_data: {dict} raw json rule response
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: {datamodels.Rule} Rule data model
        """
        return Rule(
            raw_data=raw_data,
            name=raw_data.get("Name"),
            priority=raw_data.get("Priority"),
        )

    @staticmethod
    def build_wec_acl(raw_data: dict, scope=None) -> WebACL:
        """
        Return WebACL data model
        :param raw_data: {dict} raw json web acl response
        :param scope: {str} Specifies whether this is for an AWS CloudFront distribution or for a regional application.
                            A regional application can be an Application Load Balancer (ALB), an API Gateway REST API,
                            or an AppSync GraphQL API. Values can be 'REGIONAL' or 'CLOUDFRONT'
        :return: {datamodels.WebACL} WebACL data model
        """
        rules = raw_data.get("Rules", [])
        default_action = raw_data.get("DefaultAction", {})
        if "Allow" in default_action:
            default_action = "Allow"
        elif "Block" in default_action:
            default_action = "Block"
        else:
            default_action = None

        return WebACL(
            raw_data=raw_data,
            name=raw_data.get("Name"),
            web_acl_id=raw_data.get("Id"),
            rules=[AWSWAFParser.build_rule(rule, scope=scope) for rule in rules],
            description=raw_data.get("Description"),
            lock_token=raw_data.get("LockToken"),
            arn=raw_data.get("ARN"),
            scope=scope,
            default_action=default_action,
            sampled_requests_enabled=raw_data.get("VisibilityConfig", {}).get(
                "SampledRequestsEnabled"
            ),
            cloudwatch_metrics_enabled=raw_data.get("VisibilityConfig", {}).get(
                "CloudWatchMetricsEnabled"
            ),
            cloudwatch_metric_name=raw_data.get("VisibilityConfig", {}).get(
                "MetricName"
            ),
        )
