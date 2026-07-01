from abc import ABC

from TIPCommon.base.action import Action
from TIPCommon.types import Contains

from .api_clients import APIBaseClient, CloudInfraApiClient, SmartAPIClient
from .auth import build_auth_params


class BaseAction(Action, ABC):

    def _init_api_clients(self) -> Contains[APIBaseClient]:
        auth_params = build_auth_params(self.soar_action)
        _APIClient = CloudInfraApiClient if auth_params.is_infinity else SmartAPIClient
        
        return _APIClient(
            host=auth_params.host,
            client_id=auth_params.client_id,
            client_secret=auth_params.client_secret,
            verify_ssl=auth_params.verify_ssl
        )



    @property
    def result_value(self) -> bool:
        return self._result_value

    @result_value.setter
    def result_value(self, value: bool) -> None:
        self._result_value = value
