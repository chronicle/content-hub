from __future__ import annotations

from typing import Iterator

import google.auth.credentials
import google.cloud.bigquery
import google.cloud.exceptions

import TIPCommon.rest.gcp
from google_big_query.core import data_models
from TIPCommon.types import SingleJson
from google_big_query.core import GoogleBigQueryExceptions
from google_big_query.core import GoogleBigQueryUtils
from google_big_query.core import authentication as auth


LIST_RESULT_LIMIT = 50


class GoogleBigQueryApiManager:

    def __init__(
        self, project_id: str, api_client: google.cloud.bigquery.Client
    ) -> None:
        self.project_id: str = project_id
        self.api_client: google.cloud.bigquery.Client = api_client

    @classmethod
    def from_config_params(
        cls, conf_param_extractor: GoogleBigQueryUtils.ExtractConfigurationParameters
    ) -> GoogleBigQueryApiManager:
        """Second constructor using the integration's configuration parameters"""
        wi_conf = conf_param_extractor.get_workload_identity_configuration_parameters()
        credentials = auth.get_auth_credentials_or_raise_error(wi_conf)
        project_id = _get_project_id(credentials, wi_conf)
        api_client = auth.create_session(
            wi_conf.api_root,
            credentials,
            project_id,
            wi_conf.verify_ssl
        )
        return cls(project_id, api_client)

    def test_connectivity(self) -> None:
        """Test connectivity to Google Big Query"""
        try:
            _ = list(self.list_datasets(max_results=1))
        except google.cloud.exceptions.GoogleCloudError as e:
            raise GoogleBigQueryExceptions.GoogleBigQueryManagerError(
                "Unable to connect to Google BigQuery. "
                f"Please validate your credentials. {e}"
            ) from e

    def list_datasets(
        self, max_results: int = LIST_RESULT_LIMIT
    ) -> Iterator[google.cloud.bigquery.dataset.DatasetListItem]:
        return self.api_client.list_datasets(max_results=max_results)

    def run_query(
        self, query: str, limit: int | None, dataset_name: str | None = None
    ) -> list[SingleJson]:
        """Run a query and get the results

        Args:
            dataset_name: Specify the name of the dataset, which will be used,
                when executing queries.
            query: Specify the SQL query that needs to be executed.
            limit: Max amount of results to fetch. Optional.

        Returns:
            The results of the query
        """
        job_config_params = {
            "default_dataset": (
                f"{self.project_id}.{dataset_name}" if dataset_name else None
            )
        }
        job_config = google.cloud.bigquery.QueryJobConfig(
            **{k: v for k, v in job_config_params.items() if v is not None}
        )
        query_job = self.api_client.query(query, job_config=job_config)
        rows = query_job.result(max_results=limit)
        results = rows.to_dataframe()
        return results.to_dict("records")


def _get_project_id(
    credentials: google.auth.credentials.Credentials,
    wi_conf: data_models.WorkloadIdentityConfiguration,
) -> str:
    """Fetch the project ID from the credentials if it exists. If not, extract"""
    project_id = getattr(credentials, "project_id", None)
    if project_id is not None:
        return project_id

    if wi_conf.service_account_fields.project_id:
        return wi_conf.service_account_fields.project_id

    if wi_conf.workload_identity_email:
        return TIPCommon.rest.gcp.retrieve_project_id(
            service_account_email=wi_conf.workload_identity_email,
            user_service_account=None,
        )

    if wi_conf.service_account_fields.project_id:
        return wi_conf.service_account_fields.project_id

    raise GoogleBigQueryExceptions.GoogleBigQueryManagerError(
        "Cannot determine the project ID"
    )
