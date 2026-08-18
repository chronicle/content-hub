from __future__ import annotations

import dataclasses

import pytest

from ...core.constants import (
    GET_INDICATOR_INTEL_LOOKUP_RESULT_ACTION_IDENTIFIER,
    GET_SOC_INSIGHTS_INDICATORS_ACTION_IDENTIFIER,
    INDICATOR_THREAT_LOOKUP_WITH_TIDE_ACTION_IDENTIFIER,
    INITIATE_INDICATOR_INTEL_LOOKUP_WITH_DOSSIER_ACTION_IDENTIFIER,
    PING_ACTION_IDENTIFIER,
    UNDO_RECOMMENDATION_ACTION_ACTION_IDENTIFIER,
)
from ...core.InfobloxExceptions import (
    InfobloxException,
    InternalSeverError,
    ItemNotFoundException,
)
from ...core.utils import HandleExceptions


@dataclasses.dataclass
class FakeResponse:
    status_code: int
    _json: dict | None = None
    content: bytes = b""

    def json(self) -> dict:
        if self._json is None:
            raise ValueError("No JSON body")
        return self._json


@dataclasses.dataclass
class FakeHTTPError:
    response: FakeResponse


class TestInternalServerError:
    def test_5xx_always_raises_internal_server_error(self) -> None:
        response = FakeResponse(status_code=503)
        error = FakeHTTPError(response=response)
        with pytest.raises(InternalSeverError, match="503"):
            HandleExceptions("unknown_identifier", error, response).do_process()


class TestCommonException:
    def test_unknown_identifier_400_extracts_api_error_message(self) -> None:
        response = FakeResponse(status_code=400, _json={"error": [{"message": "Bad filter syntax"}]})
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="Bad filter syntax"):
            HandleExceptions("unknown_identifier", error, response).do_process()

    def test_unknown_identifier_404_without_error_key_falls_back_to_general(self) -> None:
        response = FakeResponse(status_code=404, _json={"detail": "not found"})
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException):
            HandleExceptions("unknown_identifier", error, response, error_msg="Oops").do_process()

    def test_unknown_identifier_non_4xx_uses_general_error(self) -> None:
        response = FakeResponse(status_code=403)
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="Oops"):
            HandleExceptions("unknown_identifier", error, response, error_msg="Oops").do_process()


class TestPingHandler:
    def test_ping_uses_general_error_handler(self) -> None:
        response = FakeResponse(status_code=401)
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="An error occurred"):
            HandleExceptions(PING_ACTION_IDENTIFIER, error, response).do_process()


class TestInfobloxIQForThreatDefenseErrorHandler:
    def test_404_reports_insight_not_found(self) -> None:
        response = FakeResponse(status_code=404)
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="Insight doesn't exist."):
            HandleExceptions(GET_SOC_INSIGHTS_INDICATORS_ACTION_IDENTIFIER, error, response).do_process()

    def test_400_with_message_uses_api_message(self) -> None:
        response = FakeResponse(status_code=400, _json={"message": "Bad status filter"})
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="Bad status filter"):
            HandleExceptions(GET_SOC_INSIGHTS_INDICATORS_ACTION_IDENTIFIER, error, response).do_process()

    def test_other_status_falls_back_to_common_exception(self) -> None:
        response = FakeResponse(status_code=403)
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException):
            HandleExceptions(GET_SOC_INSIGHTS_INDICATORS_ACTION_IDENTIFIER, error, response, error_msg="X").do_process()


class TestIndicatorIntelLookupResultHandler:
    def test_404_raises_item_not_found_exception(self) -> None:
        response = FakeResponse(status_code=404, _json={"error": "no such job"})
        error = FakeHTTPError(response=response)
        with pytest.raises(ItemNotFoundException, match="Job ID does not exist"):
            HandleExceptions(GET_INDICATOR_INTEL_LOOKUP_RESULT_ACTION_IDENTIFIER, error, response).do_process()

    def test_non_404_falls_back_to_common_exception(self) -> None:
        response = FakeResponse(status_code=400, _json={"error": [{"message": "bad job id"}]})
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="bad job id"):
            HandleExceptions(GET_INDICATOR_INTEL_LOOKUP_RESULT_ACTION_IDENTIFIER, error, response).do_process()


class TestTideLookupHandler:
    def test_400_uses_message_field(self) -> None:
        response = FakeResponse(status_code=400, _json={"message": "Invalid indicator type"})
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="Invalid indicator type"):
            HandleExceptions(INDICATOR_THREAT_LOOKUP_WITH_TIDE_ACTION_IDENTIFIER, error, response).do_process()


class TestDossierLookupHandler:
    def test_400_uses_error_field(self) -> None:
        response = FakeResponse(status_code=400, _json={"error": "unsupported source"})
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="unsupported source"):
            HandleExceptions(
                INITIATE_INDICATOR_INTEL_LOOKUP_WITH_DOSSIER_ACTION_IDENTIFIER, error, response
            ).do_process()


class TestUndoRecommendationActionHandler:
    def test_404_reports_audit_entry_not_found(self) -> None:
        response = FakeResponse(status_code=404)
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="Audit entry doesn't exist."):
            HandleExceptions(UNDO_RECOMMENDATION_ACTION_ACTION_IDENTIFIER, error, response).do_process()

    def test_400_with_message_uses_it(self) -> None:
        response = FakeResponse(status_code=400, _json={"message": "Already undone"})
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="Already undone"):
            HandleExceptions(UNDO_RECOMMENDATION_ACTION_ACTION_IDENTIFIER, error, response).do_process()

    def test_400_without_message_or_error_uses_default(self) -> None:
        response = FakeResponse(status_code=400, _json={})
        error = FakeHTTPError(response=response)
        with pytest.raises(InfobloxException, match="The action cannot be undone."):
            HandleExceptions(UNDO_RECOMMENDATION_ACTION_ACTION_IDENTIFIER, error, response).do_process()
