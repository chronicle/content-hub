from __future__ import annotations
import requests
from urllib.parse import urljoin
from .exceptions import (
    AnomaliThreatStreamNotFoundException,
    AnomaliThreatStreamInvalidCredentialsException,
    AnomaliThreatStreamBadRequestException,
    AnomaliManagerException,
)
from .constants import (
    INTEGRATION_NAME,
    API_NOT_FOUND_ERROR,
    API_UNAUTHORIZED_ERROR,
    API_BAD_REQUEST,
    OR,
    PARSER_MAPPER,
    MAX_STATICSTICS_TO_FETCH_DEFAULT,
    MAX_STATISTICS_FOR_TTP_TYPE_DEFAULT,
)
from .AnomaliThreatStreamParser import ThreatStreamParser
from .utils import datetime_to_string
import datetime
import json

HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}
THREAT_INFO_RESOURCE = "intelligence"

API_ENDPOINTS = {
    "ping": f"/api/v2/{THREAT_INFO_RESOURCE}/",
    "get-indicators": f"/api/v2/{THREAT_INFO_RESOURCE}/",
    "get-analysis-links": "api/v1/inteldetails/references/{value}/",
    "get-intel-details": "api/v1/inteldetails/automatic/",
    "tag-for-indicator": "api/v2/intelligence/{indicator_id}/tag/",
    "remove-tag": "api/v2/intelligence/{indicator_id}/tag/{tag_id}/",
    "report-false-positive": "/api/v1/falsepositive/report/",
    "submit-observable": "/api/v2/intelligence/import/",
    "get-job-details": "/api/v1/importsession/{job_id}/",
    "related-indicator-associations": "/api/v1/{association_type}/"
                                      "associated_with_intelligence/",
    "get_association_details": "/api/v1/{association_type}/{association_id}/",
    "association-type-indicators": "/api/v1/{association_type}/{association_id}/"
                                   "intelligence/",
    "get-association-by-name": "/api/v1/threat_model_search/",
}


class AnomaliManager:
    def __init__(
        self,
        web_root,
        api_root,
        username,
        api_key,
        verify_ssl=False,
        force_check_connectivity=False,
        logger=None,
    ):
        self.web_root = self._get_adjusted_root_url(web_root)
        self.api_root = self._get_adjusted_root_url(api_root)
        self.email_address = username
        self.api_key = api_key
        self.session = requests.Session()
        self.logger = logger
        self.session.verify = verify_ssl
        self.session.headers = HEADERS
        self.session.headers.update(
            {"Authorization": f"apikey {self.email_address}:{self.api_key}"}
        )
        self.parser = ThreatStreamParser()
        if force_check_connectivity:
            self.test_connectivity()

    @staticmethod
    def _get_adjusted_root_url(api_root):
        """
        Get adjusted url
        :param api_root: {str} Provided api root
        :return: {str} The adjusted url
        """
        return api_root if api_root[-1] == r"/" else f"{api_root}/"

    def _get_full_url(self, url_key, **kwargs):
        """
        Get full url from url key.
        :param url_key: {str} The key of url
        :param kwargs: {dict} Variables passed for string formatting
        :return: {str} The full url
        """
        return urljoin(self.api_root, API_ENDPOINTS[url_key].format(**kwargs))

    @classmethod
    def get_api_error_message(cls, exception):
        """
        Get API error message
        :param exception: {Exception} The api error
        :return: {str} error message
        """
        try:
            if not exception.response.json().get("error"):
                return exception.response.json().get("message")

            return exception.response.json().get("error")
        except:
            return exception.response.content.decode()

    @classmethod
    def validate_response(cls, response, error_msg="An error occurred"):
        """
        Validate Threat Fuse response
        :param response:
        :param error_msg: {str} error message to display
        :return: {bool} True if successfully validated response
            raise ThreatFuseStatusCode exceptions if failed to validate response's status code
        """
        try:
            if response.status_code == API_NOT_FOUND_ERROR:
                raise AnomaliThreatStreamNotFoundException(
                    f"Not Found in {INTEGRATION_NAME}"
                )
            if response.status_code == API_UNAUTHORIZED_ERROR:
                raise AnomaliThreatStreamInvalidCredentialsException(
                    "Invalid credentials were provided"
                )
            if response.status_code == API_BAD_REQUEST:
                raise AnomaliThreatStreamBadRequestException(
                    response.json().get("message")
                )
            response.raise_for_status()
        except requests.HTTPError as error:
            try:
                response.json()
            except:
                # Not a JSON - return content
                raise AnomaliManagerException(
                    f"{error_msg}: {error} - {error.response.text}"
                )

            raise AnomaliManagerException(
                f"{error_msg}: "
                f"{response.json().get('message') or response.json().get('error')} "
                f"status code: {response.status_code}"
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
        ):  # check if more pagination are possible
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

    def test_connectivity(self):
        """
        Test connection with Siemplify ThreatFuse server
        :return: {bool} true if successfully connected to ThreatFuse
            raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        response = self.session.get(self._get_full_url("ping"), params={"limit": 1})
        self.validate_response(response)

    def get_indicators(self, entities, limit=None):
        """
        Get list of Indicators for entities
        :param entities: {[{str}]} list of entities. Each value is a string, can be IP Address, domain, hash...
        :param limit: {int} max number of related associations to return. Default is 20.
        :return: {[datamodels.Indicator]} list of Indicator datamodels
            raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        request_url = self._get_full_url("get-indicators")
        params = {"q": f" {OR} ".join([f"value={entity}" for entity in entities])}

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

    def get_analysis_links(self, value):
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

    def get_intel_details(self, value, type):
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

    def add_tags_to_entity(self, indicator_id, tags):
        """
        Add tags to entity
        :param indicator_id: {str} Indicator id for entity
        :param tags: {list} list of adding tags
        :return: {bool} I tag added or not
        """
        payload = {"tags": [{"name": tag, "tlp": "red"} for tag in tags]}
        response = self.session.post(
            self._get_full_url("tag-for-indicator", indicator_id=indicator_id),
            json=payload,
        )
        self.validate_response(
            response,
            error_msg=f"Failed to add tag to the following indicator {indicator_id}",
        )

        return True

    def remove_tag_from_entity(self, indicator_id, tag_id):
        """
        Remove tag from entity
        :param indicator_id: {str} Indicator id for entity
        :param tag_id: {tag_id} tag_id
        :return: {bool} I tag added or not
        """
        response = self.session.delete(
            self._get_full_url(
                "remove-tag",
                indicator_id=indicator_id,
                tag_id=tag_id
            )
        )
        self.validate_response(
            response,
            error_msg=(
                f"Failed to remove tag from the following indicator {indicator_id}"
            ),
        )

        return True

    def report_as_false_positive(self, indicator_id, reason, comment):
        """
        Add tags to entity
        :param indicator_id: {str} Indicator id for entity
        :param reason: {str} reason of setting false positive
        :param comment: {str} comment
        :return: {bool} If is false positive or not
        """
        payload = {"intelligence": indicator_id, "reason": reason, "comment": comment}
        response = self.session.post(
            self._get_full_url("report-false-positive"), json=payload
        )
        self.validate_response(
            response,
            error_msg=f"Reported as false positive for indicator {indicator_id}",
        )

        return True

    def submit_observable(
        self,
        entity_identifier,
        classification,
        threat_type,
        intelligence_source,
        trusted_circle_ids,
        can_override_confidence,
        confidence=None,
        is_anonymous=False,
        expiration_ts=None,
        tlp=None,
        tags=None,
    ):
        """
        Submit an observable
        :param entity_identifier: {str} entity to
        :param classification: {str} specify the classification of the observable. Valid values are 'private' or 'public'
        :param threat_type: {str} specify the threat type for the observables. Can be 'apt', 'bot', 'brute', 'ddos'..
        :param confidence: {int} specify what should be the confidence for the observable. Note: this parameter will
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
            "expiration_ts": expiration_ts if expiration_ts else "null",
            "tlp": tlp,
            "trustedcircles": (
                ",".join(trusted_circle_ids) if trusted_circle_ids else None
            ),
        }

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

        payload = {k: v for k, v in payload.items() if v is not None}

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

    def get_job_details(self, job_id):
        """
        Get Job details
        :param job_id: {str} the id of the job to get details from
        :return: {datamodels.JobDetails} JobDetails datamodel
                raise ThreatFuseStatusCode exception if failed to validate response status code
        """
        response = self.session.get(
            self._get_full_url("get-job-details", job_id=job_id)
        )
        self.validate_response(
            response, error_msg=f"Failed to get job details for job id {job_id}"
        )

        return self.parser.build_job_details_obj(response.json())

    def get_related_indicator_associations(
        self, association_type, ids, sort_by_key=None, asc=False, limit=None
    ):
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
        params = {"ids": ",".join([str(id) for id in ids])}

        results = self._paginate_results(
            method="GET",
            url=self._get_full_url(
                "related-indicator-associations",
                association_type=association_type
            ),
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

    def get_association_details(self, association_type, association_id, limit=None):
        """
        Get Association details
        :param association_type: {str} api endpoint part
        :param association_id: {str} Association ID
        :return: {list} list of {Association} models
        """
        params = {"skip_associations": True, "skip_intelligence": True}
        if limit:
            params["limit"] = limit

        request_url = self._get_full_url(
            "get_association_details",
            association_type=association_type,
            association_id=association_id,
        )
        response = self.session.get(request_url, params=params)
        self.validate_response(response)

        parser_function_name = PARSER_MAPPER.get(association_type)
        self.logger.info("==================================")
        self.logger.info(parser_function_name)
        self.logger.info("==================================")
        return getattr(self.parser, parser_function_name)(
            response.json(), self.web_root
        )

    def get_association_type_indicators_stats(
        self, association_type, association_id, limit=None
    ):

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
                MAX_STATICSTICS_TO_FETCH_DEFAULT
                if association_type != "ttp"
                else MAX_STATISTICS_FOR_TTP_TYPE_DEFAULT
            ),
            error_msg=(
                f"Failed to get indicators for association {association_type} with id "
                f"{association_id}"
            ),
            return_meta=True,
        )

        return self.parser.build_attribute_statistics_obj(
            raw_data=results, limit=limit, meta_total_count=meta_total_count
        )

    def get_association_type_indicators(
        self,
        association_type,
        association_id,
        indicator_type,
        confidence_threshold=None,
        limit=None,
    ):
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
        params = {"type": indicator_type, "confidence__gte": confidence_threshold}
        params = {k: v for k, v in params.items() if v is not None}

        results = self._paginate_results(
            method="GET",
            url=self._get_full_url(
                "association-type-indicators",
                association_type=association_type,
                association_id=association_id,
            ),
            params=params,
            limit=limit,
            error_msg=(
                f"Failed to get indicators for association {association_type} with id "
                f"{association_id}"
            ),
        )

        return [
            self.parser.build_indicator_obj(object_data, self.web_root)
            for object_data in results
        ]

    def get_related_associations_by_name(self, association_type, value):
        """Get related associations for given associated type and name.

        Args:
            association_type (str): Association type. Can be actor or vulnerability.
            value (str): Entity identifier.

        Returns:
            ([datamodels.Association]): List of Association objects.

        Raises:
            exceptions.AnomaliManagerException: exception if failed to validate response status code
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
