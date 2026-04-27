from __future__ import annotations
from .AlienVaultAnywhereManagerV1 import AlienVaultAnywhereManagerV1
from .AlienVaultAnywhereManagerV2 import (
    AlienVaultAnywhereOauthAdapter,
    AlienVaultAnywhereManagerV2,
)
from enum import Enum


from TIPCommon.oauth import AuthorizedOauthClient, CredStorage, OauthManager


class ManagerVersionNotFound(Exception):
    pass


class ManagerVersionsEnum(Enum):
    V1 = 1
    V2 = 2


class AlienVaultManagerLoader:
    @staticmethod
    def load_manager(version, api_root, username, password, use_ssl, chronicle_soar):
        """
        Load the relevant manager based on integration parameter
        :param version: {string} V1/V2
        :return: {manager instance) the relevant manager instance
        """
        if version == ManagerVersionsEnum.V1.name:
            return AlienVaultAnywhereManagerV1(
                api_root=api_root,
                username=username,
                password=password,
                use_ssl=use_ssl,
                siemplify=chronicle_soar,
            )

        elif version == ManagerVersionsEnum.V2.name:
            oauth_manager = OauthManager(
                oauth_adapter=AlienVaultAnywhereOauthAdapter(
                    api_root=api_root,
                    username=username,
                    password=password,
                    use_ssl=use_ssl,
                ),
                cred_storage=CredStorage(password, chronicle_soar),
            )
            authorized_client = AuthorizedOauthClient(
                oauth_manager=oauth_manager, verify=use_ssl
            )
            return AlienVaultAnywhereManagerV2(
                api_root=api_root,
                auth_client=authorized_client,
                siemplify=chronicle_soar,
            )

        raise ManagerVersionNotFound(
            f"Manager version {version} was not found. Aborting."
        )
