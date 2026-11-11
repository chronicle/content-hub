import pytest

from TIPCommon.validation import ParameterValidationError

from google_big_query.core.GoogleBigQueryUtils import (
    validate_wi_and_sa,
    ExtractConfigurationParameters,
)
from google_big_query.core.GoogleBigQueryUtils import data_models
from google_big_query.tests.conftest import Mockplify


class TestExtractConfigurationParameters:

    def test_get_service_account_fields(
        self,
        conf_param_extractor: ExtractConfigurationParameters,
    ) -> None:
        sa: data_models.GoogleServiceAccount = (
            conf_param_extractor.get_service_account_fields()
        )

        assert isinstance(sa, data_models.GoogleServiceAccount)

    def test_get_workload_identity_configuration_parameters(
        self,
        conf_param_extractor: ExtractConfigurationParameters,
    ) -> None:
        wi: data_models.WorkloadIdentityConfiguration = (
            conf_param_extractor.get_workload_identity_configuration_parameters()
        )

        assert isinstance(wi, data_models.WorkloadIdentityConfiguration)


class TestValidateWiAndAa:

    def test_none_values_return_none(self, mockplify: Mockplify) -> None:
        email: None = None
        json_str: None = None

        wi, sa = validate_wi_and_sa(email, json_str, mockplify)

        assert wi is None and sa is None

    def test_wi_is_str_and_sa_is_parsed_to_json(self, mockplify: Mockplify) -> None:
        email: str = "a@a.com"
        json_str: str = '{"key": "value"}'

        wi, sa = validate_wi_and_sa(email, json_str, mockplify)

        assert isinstance(wi, str) and isinstance(sa, dict) and sa["key"] == "value"

    def test_invalid_email_raises_parameter_validation_error(
        self,
        mockplify: Mockplify,
    ) -> None:
        email: str = "blah"
        json_str: None = None

        with pytest.raises(ParameterValidationError):
            _ = validate_wi_and_sa(email, json_str, mockplify)

    def test_invalid_json_raises_parameter_validation_error(
        self,
        mockplify: Mockplify,
    ) -> None:
        email: None = None
        json_str: str = '{"Key": value"}'

        with pytest.raises(ParameterValidationError):
            _ = validate_wi_and_sa(email, json_str, mockplify)
