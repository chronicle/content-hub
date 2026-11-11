from __future__ import annotations
import re
from abc import ABC

from TIPCommon.base.action import Action
from TIPCommon.base.interfaces import ApiClient
from TIPCommon.extraction import extract_configuration_param
from TIPCommon.types import Contains
from vertex_ai.core.VertexAIApiManager import ApiManager
from vertex_ai.core.VertexAIAuthManager import AuthManager, build_auth_manager_params
from vertex_ai.core.VertexAIConstants import API_ROOT_REGEX, DEFAULT_LOCATION, INTEGRATION_IDENTIFIER
from vertex_ai.core.VertexAIExceptions import VertexAIValidationException


class BaseAction(Action, ABC):
    def _init_api_clients(self) -> Contains[ApiClient]:
        auth_params = build_auth_manager_params(self.soar_action)
        auth_manager = AuthManager(auth_params)
        return ApiManager(
            api_root=self.params.api_root,
            session=auth_manager.prepare_session(),
            location_id=self.params.location_id,
            project_id=auth_manager.project_id,
            logger=self.logger,
        )

    def _validate_api_root(self) -> re.Match[str]:
        api_root_match = re.fullmatch(API_ROOT_REGEX, self.params.api_root)
        if api_root_match is None:
            raise VertexAIValidationException(
                "the API root that you provided doesn’t match the following expected "
                f'pattern: "{API_ROOT_REGEX}". Check the spelling.',
            )
        return api_root_match

    def __get_fallback_location(self) -> str:
        api_root_match = self._validate_api_root()
        return next((g for g in api_root_match.groups() if g), DEFAULT_LOCATION)

    def _extract_action_parameters(self) -> None:
        self.params.api_root = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="API Root",
            print_value=True,
        )
        self.params.location_id = (
            extract_configuration_param(
                self.soar_action,
                provider_name=INTEGRATION_IDENTIFIER,
                param_name="Location ID",
                print_value=True,
            )
            or self.__get_fallback_location()
        )
        self.params.default_model = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Default Model",
            is_mandatory=True,
            print_value=True,
        )
        self.params.default_publisher_name = extract_configuration_param(
            self.soar_action,
            provider_name=INTEGRATION_IDENTIFIER,
            param_name="Publisher Name",
            is_mandatory=True,
            print_value=True,
        )
        self._extract_parameters()

    def _extract_parameters(self) -> None:
        """Extract action specific parameters."""
