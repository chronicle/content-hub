# ============================================================================#
# title           :ThreatFuseManager.py
# description     :This Module contain all Threat Fuse operations functionality
# author          :gabriel.munits@siemplify.co
# date            :09-11-2020
# python_version  :3.7
# product_version :1.0
# ============================================================================#

# ============================= IMPORTS ===================================== #

from __future__ import annotations
import datetime
import json
from typing import Optional, List
from urllib.parse import urljoin

import requests
from . import consts
from . import datamodels
from .ThreatFuseParser import ThreatFuseParser
from .exceptions import (
    ThreatFuseStatusCodeException,
    ThreatFuseNotFoundException,
    ThreatFuseInvalidCredentialsException,
    ThreatFuseBadRequestException,
)
from .utils import datetime_to_string


ENDPOINTS = {  # must begin with '/'
    "ping": "/api/v2/intelligence/",
    "get-indicators": "/api/v2/intelligence/",
    "get-observables-indicators": "/api/v2/intelligence/associated_with_intelligence/",
    "related-indicator-associations": "/api/v1/{association_type}/associated_with_intelligence/",
    "association-type-indicators": "/api/v1/{association_type}/{association_id}/intelligence/",
    "get-association-by-name": "/api/v1/threat_model_search/",
    "report-as-falsepositive": "/api/v1/falsepositive/report/",
    "submit-observable": "/api/v1/intelligence/import/",
    "get-job-details": "/api/v1/importsession/{job_id}/",
    "get-actor-ids": "/api/v1/threat_model_search/",
    "get-actor-details": "/api/v1/actor/{actor_id}/",
    "get-vulnerability-ids": "/api/v1/threat_model_search/",
    "get-vulnerability-details": "/api/v1/vulnerability/{vulnerability_id}/",
    "get-campaign-ids": "/api/v1/threat_model_search/",
    "get-campaign-details": "/api/v1/campaign/{campaign_id}/",
    "get-signature-ids": "/api/v1/threat_model_search/",
    "get-signature-details": "/api/v1/signature/{signature_id}/",
    "get-analysis-links": "api/v1/inteldetails/references/{value}/",
    "get-intel-details": "api/v1/inteldetails/automatic/",
    "get-attackpattern-details": "/api/v1/attackpattern/{attackpattern_id}/",
    "get-infrastructure-details": "/api/v1/infrastructure/{infrastructure_id}/",
    "get-intrusionset-details": "/api/v1/intrusionset/{intrusionset_id}/",
    "get-tipreport-details": "/api/v1/tipreport/{tipreport_id}/",
    "get-courseofaction-details": "/api/v1/courseofaction/{courseofaction_id}/",
    "get-identity-details": "/api/v1/identity/{identity_id}/",
    "get-incident-details": "/api/v1/incident/{incident_id}/",
    "get-malware-details": "/api/v1/malware/{malware_id}/",
    "get-tool-details": "/api/v1/tool/{tool_id}/",
    "get-ttp-details": "/api/v1/ttp/{ttp_id}/",
}

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


class ThreatFuseManager:

    def __init__(
        self,
        api_root,
        api_key,
        email_address,
        verify_ssl=False,
        web_root="",
        siemplify_logger=None,
    ):
        """
        The method is used to init an object of Manager class
        :param api_root: API Root of the ThreatFuse instance.
        :param web_root: Web root of the ThreatFuse instance.
        :param verify_ssl: If enabled, verify the SSL certificate for the connection to the ThreatFuse server is valid.
        :param siemplify_logger: Siemplify logger.
        """
        self.api_root = api_root[:-1] if api_root.endswith("/") else api_root
        self.web_root = (
            web_root[:-1] if web_root and web_root.endswith("/") else web_root
        )
        self.api_token = api_key
        self.email_address = email_address

        self.siemplify_logger = siemplify_logger
        self.parser = ThreatFuseParser()
        self.session = requests.session()
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.headers.update(
            {"Authorization": f"apikey {self.email_address}:{self.api_token}"}
        )

    @staticmethod
    def validate_response(response, error_msg="An error occurred"):
        """
        Validate Threat Fuse response
        :param response:
        :param error_msg: {str} error message to display
        :return: {bool} True if successfully validated response
            raise ThreatFuseStatusCode exceptions if failed to validate response's status code
        """
        try:
            if response.status_code == consts.API_NOT_FOUND_ERROR:
                raise ThreatFuseNotFoundException(
                    f"Not Found in {consts.INTEGRATION_NAME}"
                )
            if response.status_code == consts.API_UNAUTHORIZED_ERROR:
                raise ThreatFuseInvalidCredentialsException(
                    "Invalid credentials were provided"
                )
            if response.status_code == consts.API_BAD_REQUEST:
                raise ThreatFuseBadRequestException(response.json().get("message"))
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise ThreatFuseStatusCodeException(
                    f"{error_msg}: {error} - {error.response.text}"
                )

            raise ThreatFuseStatusCodeException(
                f"{error_msg}: {response.json().get('message') or response.json().get('error')} status code: {response.status_code}"
            )

    def _get_full_url(self, url_key, **kwargs) -> str:
        """
        Get full url from url key.
        :param url_id: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, ENDPOINTS[url_key].format(**kwargs))

    def test_connectivity(self):
        """
        Test connection with Siemplify ThreatFuse server
        :return: {bool} true if successfully connected to ThreatFuse
            raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url("ping")
        params = {"limit": 1}
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to connect to {consts.INTEGRATION_NAME}"
        )

    def get_indicators(self, entities: list, limit=None) -> [datamodels.Indicator]:
        """
        Get list of Indicators for entities
        :param entities: {[{str}]} list of entities. Each value is a string, can be IP Address, domain, hash...
        :param limit: {int} max number of related associations to return. Default is 20.
        :return: {[datamodels.Indicator]} list of Indicator datamodels
            raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url("get-indicators")
        params = {
            "q": f" {consts.OR} ".join([f"value={entity}" for entity in entities])
        }

        results = self._paginate_results(
            method="GET",
            url=request_url,
            params=params,
            limit=limit,
            error_msg=f"Failed to get indicator IDs for entities {entities}",
        )
        return [
            self.parser.build_indicator_obj(object_data, self.web_root)
            for object_data in results
        ]

    def get_filtered_indicators(
        self,
        confidence: int,
        severities: list,
        last_timestamp: str,
        observable_statuses: Optional[list] = None,
        observable_types: Optional[list] = None,
        feed_ids: Optional[list] = None,
        threat_types: Optional[list] = None,
        trusted_circle_ids: Optional[list] = None,
        tags: Optional[list] = None,
        limit=None,
    ) -> [datamodels.Indicator]:
        """
        Get list of Indicators by filters
        :param confidence: {int} lowest confidence that will be used to fetch observables
        :param severities: {list} list of severities. Values can be 'low', 'medium', 'high' or 'very-high'
        :param feed_ids: {list} list of integers. Each integer is source filter id
        :param observable_types: {list} list of observable types. Values can be url, domain, email, hash, ip, ipv6
        :param observable_statuses: {list} list of observable statuses. Values can be active, inactive, falsepos
        :param threat_types: {list} list of threat types. Values can be adware, anomalous, anonymization, apt, bot, brute,
               c2, compromised, crypto, data_leakage, ddos, dyn_dns, exfil, exploit, fraud, hack_tool, i2p, informational,
               malware, p2p, parked, phish, scan, sinkhole, spam, suppress, suspicious, tor, vps
        :param tags: {[str]} list of tags
        :param page_size: {int} max observables to return in page
        :param last_timestamp: {str} last timestamp of  format 2020-01-30T05:53:27.683. Indicators will be older than
               last timestamp.
        :param trusted_circle_ids: {list} list of integers. Each integer represents Trusted Circle ID
        :return: {[datamodels.Indicator]} list of Indicator datamodels
            raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        # Check if pagination should be continued or this is the first request
        request_url = self._get_full_url("get-indicators")

        query = "(confidence>={confidence}) AND ({severities}) AND (modified_ts>={modified_ts})".format(
            confidence=confidence,
            severities=f" {consts.OR} ".join(
                [f'severity="{severity}"' for severity in severities]
            ),
            modified_ts=last_timestamp,
        )

        if feed_ids:
            sub_query = f" {consts.OR} ".join(
                [f"feed_id={feed_id}" for feed_id in feed_ids]
            )
            query += f" {consts.AND} ({sub_query})"

        if observable_types:
            sub_query = f" {consts.OR} ".join(
                [f'type="{observable_type}"' for observable_type in observable_types]
            )
            query += f" {consts.AND} ({sub_query})"

        if observable_statuses:
            sub_query = f" {consts.OR} ".join(
                [f'status="{status}"' for status in observable_statuses]
            )
            query += f" {consts.AND} ({sub_query})"

        if threat_types:
            sub_query = f" {consts.OR} ".join(
                [f'threat_type="{threat_type}"' for threat_type in threat_types]
            )
            query += f" {consts.AND} ({sub_query})"

        if trusted_circle_ids:
            sub_query = f" {consts.OR} ".join(
                [
                    f"trusted_circle_ids={trusted_id}"
                    for trusted_id in trusted_circle_ids
                ]
            )
            query += f" {consts.AND} ({sub_query})"

        if tags:
            sub_query = f" {consts.OR} ".join([f'tag.name="{tag}"' for tag in tags])
            query += f" {consts.AND} ({sub_query})"

        params = {"order_by": "modified_ts"}  # get latest results

        results = self._paginate_results(
            method="GET",
            url=request_url + "?q=" + query,
            params=params,
            limit=limit,
            error_msg=f"Failed to get filtered indicators",
        )
        return [
            self.parser.build_indicator_obj(object_data, self.web_root)
            for object_data in results
        ]

    def report_as_false_positive(self, indicator_id, reason, comment):
        """
        Report as false positive for an indicator id
        :param indicator_id: {str} id of the indicator
        :param reason: {str} the reason of the repost of false positive
        :param comment: {str} the comment of the report of false positive
        :return: {bool} True if succeeded, otherwise return false
                raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url("report-as-falsepositive")
        response = self.session.post(
            url=request_url,
            json={"intelligence": indicator_id, "reason": reason, "comment": comment},
        )
        self.validate_response(
            response,
            error_msg=f"Failed to report false positive for indicator id {indicator_id}",
        )
        return response.json().get("success")

    def get_observables_indicators(
        self, ids: list, indicator_type, limit=None
    ) -> [datamodels.Indicator]:
        """
        Get observables indicators.
        :param ids: {[list]} list of ids. Each id represented as int
        :param limit: {int} max number of related associations to return. Default is 20.
        :param indicator_type: {str} indicator types to return. Can be md5, url, domain, email, ip
        :return: {[datamodels.Indicator]} list of Indicator datamodels.
                raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url("get-observables-indicators")

        params = {"ids": ",".join([str(id) for id in ids])}

        results = []
        # paginate through results to find results with matching indicator type
        while request_url:
            if limit and len(results) >= limit:
                results = results[:limit]  # trim exceeding results
                break

            request_url, results_page = self._results_page(
                method="GET",
                url_root=self.api_root,
                url=request_url,
                params=params,
                # we perform search so page_size should be max (not specified)
                error_msg=f"Failed to get observables indicators for ids: {ids}",
            )
            # search for results with matching indicator type
            results.extend(
                [page for page in results_page if page.type == indicator_type]
            )

        return [
            self.parser.build_indicator_obj(object_data, self.web_root)
            for object_data in results
        ]

    def get_related_indicator_associations(
        self, association_type: str, ids: list, sort_by_key=None, asc=False, limit=None
    ) -> [datamodels.Association]:
        """
        Get related associations for given associated type and ids. Sort results by sort_by_key in an ascending or
        descending order and limit returned results, default is ascending order.
        :param association_type: {str} association type. Can be actor, campaign, tool, malware, signature...
            Note: 'Observables' association type is not supported here. Use get_observables_indicators method instead
        :param ids: {[list]} list of ids. Each id represented as int
        :param sort_by_key: {str} attribute of Association data model to sort by
        :param asc: {bool} if True sorted results will be in an ascending order, otherwise they will be sorted in descending order
        :param limit: {int} max number of related associations to return. Default is 20.
        :return: {[datamodels.Association]} list of Association datamodels.
                raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url(
            "related-indicator-associations", association_type=association_type
        )

        params = {"ids": ",".join([str(id) for id in ids])}

        results = self._paginate_results(
            method="GET",
            url=request_url,
            params=params,
            error_msg=f"Failed to get related associations for ids: {ids}",
        )
        association_objs = [
            self.parser.build_association_obj(object_data, self.web_root)
            for object_data in results
        ]

        if sort_by_key:  # sort related association by sort_by key and in asc/desc order
            sorted_association_objs = sorted(
                association_objs,
                key=lambda association: getattr(association, sort_by_key),
                reverse=not asc,
            )
            return (
                sorted_association_objs[:limit]
                if limit is not None
                else sorted_association_objs
            )

        return association_objs[:limit] if limit is not None else association_objs

    def get_related_associations_by_name(
        self, association_type: str, value: str
    ) -> List[datamodels.Association]:
        """Get related associations for given associated type and name.

        Args:
            association_type (str): Association type. Can be actor or vulnerability.
            value (str): Entity identifier.

        Returns:
            ([datamodels.Association]): List of Association objects.

        Raises:
            exceptions.ThreatFuseStatusCode: exception if failed to validate response status code
        """
        request_url = self._get_full_url("get-association-by-name")

        params = {
            "limit": 50,
            "model_type": association_type,
            "offset": 0,
            "order_by": "-modified_ts",
            "value": [value],
        }

        response = self.session.get(request_url, params=params)
        self.validate_response(response, "Unable to get results")
        results = response.json().get("objects")
        return [
            self.parser.build_association_obj(object_data, self.web_root)
            for object_data in results
        ]

    def get_association_type_indicators(
        self,
        association_type,
        association_id,
        indicator_type,
        confidence_threshold=None,
        limit=None,
    ) -> [datamodels.Indicator]:
        """
        Get association type indicators
        :param association_type: {str} association type. Can be actor, campaign, tool, malware, signature...
        :param association_id: {str} id of the association
        :param indicator_type: {str} indicator types to return. Can be md5, url, domain, email, ip
        :param confidence_threshold: {int} confidence threshold. Only indicators with higher confidence will be returned.
            Ranges from 0 to 100.
        :param limit: {int} max number of related associations to return. Default is 20.
        :return: {[datamodels.Indicator]} list of Indicator datamodels.
            raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url(
            "association-type-indicators",
            association_type=association_type,
            association_id=association_id,
        )

        params = {"type": indicator_type}

        if confidence_threshold:
            params["confidence__gte"] = confidence_threshold

        results = self._paginate_results(
            method="GET",
            url=request_url,
            params=params,
            limit=limit,
            error_msg=f"Failed to get indicators for association {association_type} with id {association_id}",
        )

        return [
            self.parser.build_indicator_obj(object_data, self.web_root)
            for object_data in results
        ]

    def get_association_type_indicators_stats(
        self, association_type, association_id, limit=None
    ) -> [datamodels.Indicator]:

        request_url = self._get_full_url(
            "association-type-indicators",
            association_type=association_type,
            association_id=association_id,
        )

        results, meta_total_count = self._paginate_results(
            method="GET",
            params={},
            url=request_url,
            # Later this condition should be removed and instead of MAX_STATISTICS_FOR_TTP_TYPE_DEFAULT should be used
            # MAX_STATICSTICS_TO_FETCH_DEFAULT as a regular pagination limit. For now Anomali doesn't support statistics
            # results more than 75 for TTP type.
            limit=(
                consts.MAX_STATICSTICS_TO_FETCH_DEFAULT
                if association_type != "ttp"
                else consts.MAX_STATISTICS_FOR_TTP_TYPE_DEFAULT
            ),
            error_msg=f"Failed to get indicators for association {association_type} with id {association_id}",
            return_meta=True,
        )

        return self.parser.build_attribute_statistics_obj(
            raw_data=results, limit=limit, meta_total_count=meta_total_count
        )

    def _paginate_results(
        self,
        method,
        url,
        params=None,
        body=None,
        limit=None,
        error_msg="Unable to get results",
        return_meta=False,
    ):
        """
        Paginate objects results. If limit is not specified, all results will be returned
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param limit: {int} The limit of the results to fetch
        :param error_msg: {str} The message to display on error
        :param return_meta: {bool} True if the function should return stats from meta section of the response
        :return: {[list]} List of results
                raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        if limit is not None:
            params.update({"limit": limit})

        response = self.session.request(method, url, params=params, json=body)
        self.validate_response(response, error_msg)
        results = response.json().get("objects")

        while (
            response.json().get("meta", {}).get("next")
        ):  # check if more paginations are possible
            if limit and len(results) >= limit:  # check if limit reached
                break
            request_url = urljoin(
                self.api_root, response.json().get("meta", {}).get("next")
            )
            response = self.session.request(
                method, request_url, params=params, json=body
            )
            self.validate_response(response, error_msg)
            results.extend(response.json().get("objects"))

        if return_meta:
            meta_total_count = response.json().get("meta", {}).get("total_count")
            return results[:limit] if limit is not None else results, meta_total_count

        return results[:limit] if limit is not None else results

    def _results_page(
        self,
        method,
        url,
        url_root,
        params=None,
        body=None,
        page_size=None,
        error_msg="Unable to get results",
    ) -> (str, list):
        """
        Returns results page
        :param method: {str} The method of the request (GET, POST, PUT, DELETE, PATCH)
        :param url: {str} The url to send request to
        :param url_root: {str} root url to send request to
        :param params: {dict} The params of the request
        :param body: {dict} The json payload of the request
        :param page_size: {int} The page size of the results to return. Max is 1000
        :param error_msg: {str} The message to display on error
        :return: {(str, list)} Tuple of next url to query for next pagination (if this is last pagination returned None)
            and list of results
                raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        if page_size is not None:
            params.update({"limit": page_size})

        response = self.session.request(method, url, params=params, json=body)
        self.validate_response(response, error_msg)
        results = response.json().get("objects")
        next_url = response.json().get("meta", {}).get("next")

        return urljoin(url_root, next_url) if next_url else None, (
            results[:page_size] if page_size is not None else results
        )

    def get_vulnerability_ids(self, cve, limit=None):
        """
        Returns CVE datamodel
        :param cve: {str} cve identifier
        :param limit: {int} The limit of the results to fetch
        :return: {[datamodels.CVE]} CVE datamodel.
        """
        params = {
            "model_type": "vulnerability",
            "order_by": "-modified_ts",
            "offset": "0",
            "value": f"{cve}",
        }
        if limit:
            params["limit"] = limit

        request_url = self._get_full_url("get-vulnerability-ids")
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to get vulnerability ID of CVE {cve}"
        )

        last_modified = (
            response.json().get("objects")[0]
            if response.json().get("objects")
            else None
        )

        return last_modified.get("id") if last_modified else None

    def get_actor_ids(self, actor_identifier, limit=None):
        """
        Retrieve actor from Siemplify ThreatFuse.
        :param actor_identifier: {str} actor identifier
        :param limit: {int} The limit of the results to fetch
        :return: {dict} Last modified actor
        """
        params = {
            "model_type": "actor",
            "offset": "0",
            "order_by": "-modified_ts",
            "value": f"{actor_identifier}",
        }
        if limit:
            params["limit"] = limit

        request_url = self._get_full_url("get-actor-ids")
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get ID of actor identifier: {actor_identifier}",
        )

        last_modified = (
            response.json().get("objects")[0]
            if response.json().get("objects")
            else None
        )

        return last_modified.get("id") if last_modified else None

    def get_actor_details(self, actor_id):
        """
        Retrieve actor details from Siemplify ThreatFuse.
        :param actor_id: {str} The id of the actor to retrieve
        :return: {datamodels.ActorDetails} ActorDetails object
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url("get-actor-details", actor_id=actor_id)
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to get details of actor with id: {actor_id}"
        )
        return self.parser.build_actor_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_vulnerability_details(self, vulnerability_id, limit=None):
        """
        Returns Vulnerability datamodel
        :param vulnerability_id: {str} cve identifier
        :param limit: {int} The limit of the results to fetch
        :return: {[datamodels.Vulnerability]} Vulnerability datamodel.
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}
        if limit:
            params["limit"] = limit

        request_url = self._get_full_url(
            "get-vulnerability-details", vulnerability_id=vulnerability_id
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get vulnerability details of vulnerability id: {vulnerability_id}",
        )
        return self.parser.build_vulnerability_obj(
            response.json(), web_root=self.web_root
        )

    def submit_observable(
        self,
        entity_identifier: str,
        classification: str,
        threat_type: str,
        intelligence_source: str,
        trusted_circle_ids: list,
        can_override_confidence: bool,
        confidence: Optional[int] = None,
        is_anonymous: Optional[bool] = False,
        expiration_ts: Optional[str] = None,
        tlp: Optional[str] = None,
        tags: Optional[list] = None,
    ) -> datamodels.JobStatus:
        """
        Submit an observable
        :param entity_identifier: {str} entity to
        :param classification: {str} specify the classification of the observable. Valid values are 'private' or 'public'
        :param threat_type: {str} specify the threat type for the observables. Can be 'apt', 'bot', 'brute', 'ddos'..
        :param confidence: {int} specify what shuld be the confidence for the observable. Note: this parameter will
                only work, if you create observables in your organization and requires 'can_override_confidence' to be True.
        :param intelligence_source:
        :param expiration_ts: {str} specify the expiration date for the observable. If expiration date is not specified
                the observable will never expire. Time format is 2020-11-08T12:34:00.00321
        :param trusted_circle_ids: {list} list of trusted circles ids which the submitted observables will be shared with
        :param tlp: {str} specify the TLP of the observable.
        :param is_anonymous: {bool} If enabled, action will make an anonymous submission.
        :param tags: {[str]} list of tags. Tags applied to the imported observables.
        :param can_override_confidence: {bool} if true, created observables will have the confidence specified in
                'confidence' parameter.
        :return: {datamodels.JobStatus} job status of submitted observable
                raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url("submit-observable")
        current_time = datetime_to_string(datetime.datetime.utcnow())
        payload = {
            "source_created": current_time,
            "source_modified": current_time,
            "datatext": entity_identifier,
            "threat_type": threat_type,
            "classification": classification,
            "intelligence_source": intelligence_source,
            "is_anonymous": is_anonymous,
            "default_state": "active",
        }

        if expiration_ts:
            payload.update({"expiration_ts": expiration_ts})
        else:  # if expiration timestamp is not set, observable will never expire
            payload.update({"expiration_ts": "null"})

        if tlp:
            payload.update({"tlp": tlp})

        if trusted_circle_ids:
            payload.update({"trustedcircles": ",".join(trusted_circle_ids)})

        if tags:
            payload.update(
                {"tags": json.dumps([{"name": tag, "tlp": "white"} for tag in tags])}
            )

        if (
            can_override_confidence and confidence is not None
        ):  # check if confidence should be overrided
            payload.update({"can_override_confidence": "True"})
            payload.update({"confidence": confidence})
            payload.update({"source_confidence_weight": 100})
        else:  # ignore source confidence
            payload.update({"can_override_confidence": "False"})
            payload.update({"confidence": 0})
            payload.update({"source_confidence_weight": 0})

        self.session.headers.update(
            {"Content-Type": "application/x-www-form-urlencoded"}
        )
        response = self.session.post(url=request_url, data=payload)
        self.session.headers.update({"Content-Type": "application/json"})
        self.validate_response(
            response,
            error_msg=f"Failed to submit observable for entity {entity_identifier}",
        )
        return self.parser.build_job_status_obj(response.json())

    def get_job_details(self, job_id: str) -> datamodels.JobDetails:
        """
        Get Job details
        :param job_id: {str} the id of the job to get details from
        :return: {datamodels.JobDetails} JobDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url("get-job-details", job_id=job_id)
        response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=f"Failed to get job details for job id {job_id}"
        )
        return self.parser.build_job_details_obj(response.json())

    def get_campaign_ids(self, campaign_identifier, limit=None):
        """
        Retrieve campaign id from Siemplify ThreatFuse.
        :param campaign_identifier: {str} campaign identifier
        :param limit: {int} The limit of the results to fetch
        :return: {dict} Last modified actor
        """
        params = {
            "model_type": "campaign",
            "offset": "0",
            "order_by": "-modified_ts",
            "value": f"{campaign_identifier}",
        }
        if limit:
            params["limit"] = limit

        request_url = self._get_full_url("get-campaign-ids")
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get ID of campaign identifier: {campaign_identifier}",
        )

        last_modified = (
            response.json().get("objects")[0]
            if response.json().get("objects")
            else None
        )

        return last_modified.get("id") if last_modified else None

    def get_campaign_details(self, campaign_id):
        """
        Retrieve campaign details from Siemplify ThreatFuse.
        :param campaign_id: {str} The id of the campaign to retrieve
        :return: {datamodels.CampaignDetails} CampaignDetails object
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url(
            "get-campaign-details", campaign_id=campaign_id
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get details of campaign with id: {campaign_id}",
        )
        return self.parser.build_campaign_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_signature_ids(self, signature_identifier, limit=None):
        """
        Retrieve signature id from Siemplify ThreatFuse.
        :param signature_identifier: {str} signature identifier
        :param limit: {int} The limit of the results to fetch
        :return: {dict} Last modified signature
        """
        params = {
            "model_type": "signature",
            "offset": "0",
            "order_by": "-modified_ts",
            "value": f"{signature_identifier}",
        }
        if limit:
            params["limit"] = limit

        request_url = self._get_full_url("get-signature-ids")
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get ID of campaign identifier: {signature_identifier}",
        )

        last_modified = (
            response.json().get("objects")[0]
            if response.json().get("objects")
            else None
        )

        return last_modified.get("id") if last_modified else None

    def get_signature_details(self, signature_id):
        """
        Retrieve signature details from Siemplify ThreatFuse.
        :param signature_id: {str} The id of the signature to retrieve
        :return: {datamodels.SignatureDetails} SignatureDetails object
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url(
            "get-signature-details", signature_id=signature_id
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get details of signature with id: {signature_id}",
        )
        return self.parser.build_signature_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_analysis_links(self, value: str) -> List[datamodels.AnalysisLink]:
        """
        Get analysis links for a value (ip/hash/url/etc)
        :param value: {str} The value to get the analysis links for
        :return: {[datamodels.AnalysisLink]} List of AnalysisLink datamodel objects
                raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url("get-analysis-links", value=value)
        response = self.session.get(request_url)
        self.validate_response(
            response, error_msg=f"Failed to get analysis links for {value}"
        )
        return self.parser.build_analysis_link_objects(response.json())

    def get_intel_details(self, value: str, type: str) -> datamodels.IntelDetails:
        """
        Get intel details for an value and type (ip/hash/url/etc)
        :param value: {str} the value to get the intel details for
        :param type: {str} the type of the value (ip/url/domain/hash/etc)
        :return: {datamodels.IntelDetails} IntelDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url("get-intel-details")
        response = self.session.get(request_url, params={"type": type, "value": value})
        self.validate_response(
            response,
            error_msg=f"Failed to get intel details for {value} (type: {type})",
        )
        return self.parser.build_intel_details_objects(response.json())

    def get_attackpattern_details(self, attackpattern_id):
        """
        Get attack pattern details
        :param attackpattern_id: {str} The id of the attack pattern to retrieve
        :return: {datamodels.AttackPatternDetails} AttackPatternDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
                raise ThreatFuseNotFoundException exception if attack pattern wasn't found
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url(
            "get-attackpattern-details", attackpattern_id=attackpattern_id
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get details of attack pattern id {attackpattern_id}",
        )
        return self.parser.build_attackpattern_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_courseofaction_details(self, courseofaction_id):
        """
        Get course of action details
        :param courseofaction_id: {str} The id of course of action to retrieve
        :return: {datamodels.CourseOfActionDetails} CourseOfActionDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
                raise ThreatFuseNotFoundException exception if course of action wasn't found
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url(
            "get-courseofaction-details", courseofaction_id=courseofaction_id
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get details of course of action id {courseofaction_id}",
        )
        return self.parser.build_course_of_action_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_identity_details(self, identity_id):
        """
        Get identity details
        :param identity_id: {str} The id of the identity to retrieve
        :return: {datamodels.IdentityDetails} IdentityDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
                raise ThreatFuseNotFoundException exception if identity was not found
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url(
            "get-identity-details", identity_id=identity_id
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to get details of identity id {identity_id}"
        )
        return self.parser.build_identity_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_incident_details(self, incident_id):
        """
        Get incident details
        :param incident_id: {str} The id of the incident to retrieve
        :return: {datamodels.IncidentDetails} IncidentDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
                raise ThreatFuseNotFoundException exception if incident was not found
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url(
            "get-incident-details", incident_id=incident_id
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to get details of incident id {incident_id}"
        )
        return self.parser.build_incident_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_infrastructure_details(self, infrastructure_id):
        """
        Get infrastructure details
        :param infrastructure_id: {str} The id of the infrastructure to retrieve
        :return: {datamodels.InfrastructureDetails} InfrastructureDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
                raise ThreatFuseNotFoundException exception if infrastructure was not found
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url(
            "get-infrastructure-details", infrastructure_id=infrastructure_id
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get details of infrastructure id {infrastructure_id}",
        )
        return self.parser.build_infrastructure_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_intrusionset_details(self, intrusionset_id):
        """
        Get intrusion set details
        :param intrusionset_id: {str} The id of the intrusion set to retrieve
        :return: {datamodels.IntrusionSetDetails} IntrusionSetDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
                raise ThreatFuseNotFoundException exception if intrusion set was not found
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url(
            "get-intrusionset-details", intrusionset_id=intrusionset_id
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get details of intrusion set id {intrusionset_id}",
        )
        return self.parser.build_intrusionset_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_malware_details(self, malware_id):
        """
        Get malware details
        :param malware_id: {str} The id of the malware to retrieve
        :return: {datamodels.MalwareDetails} MalwareDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
                raise ThreatFuseNotFoundException exception if malware was not found
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url("get-malware-details", malware_id=malware_id)
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to get details of malware id {malware_id}"
        )
        return self.parser.build_malware_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_tool_details(self, tool_id):
        """
        Get tool details
        :param tool_id: {str} The id of the tool to retrieve
        :return: {datamodels.ToolDetails} ToolDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
                raise ThreatFuseNotFoundException exception if tool was not found
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url("get-tool-details", tool_id=tool_id)
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to get details of tool id {tool_id}"
        )
        return self.parser.build_tool_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_ttp_details(self, ttp_id):
        """
        Get ttp details
        :param ttp_id: {str} The id of the ttp to retrieve
        :return: {datamodels.TTPDetails} TTPDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
                raise ThreatFuseNotFoundException exception if ttp was not found
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url("get-ttp-details", ttp_id=ttp_id)
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response, error_msg=f"Failed to get details of ttp id {ttp_id}"
        )
        return self.parser.build_ttp_details_obj(
            response.json(), web_root=self.web_root
        )

    def get_tipreport_details(self, tipreport_id):
        """
        Get Threat Bulletins details
        :param tipreport_id: {str} The id of the tipreport to retrieve
        :return: {datamodels.ThreatBulletinsDetails} ThreatBulletinsDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
                raise ThreatFuseNotFoundException exception if tipreport was not found
        """
        params = {"skip_associations": "true", "skip_intelligence": "true"}

        request_url = self._get_full_url(
            "get-tipreport-details", tipreport_id=tipreport_id
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(
            response,
            error_msg=f"Failed to get details of Threat Bulletins (tipreport) id {tipreport_id}",
        )
        return self.parser.build_threat_bulletins_details_obj(
            response.json(), web_root=self.web_root
        )
