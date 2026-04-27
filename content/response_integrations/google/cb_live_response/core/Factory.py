from __future__ import annotations
from .CarbonBlackLiveResponseManagerV6 import CarbonBlackLiveResponseManagerV6
from .CarbonBlackLiveResponseManager import CarbonBlackLiveResponseManager


class ManagerFactory:
    @staticmethod
    def create_manager(
        api_root,
        org_key,
        cb_cloud_api_id,
        cb_cloud_api_secret_key,
        lr_api_id=None,
        lr_api_secret_key=None,
        verify_ssl=False,
        force_check_connectivity=False,
        use_new_api_version=False,
    ):
        """
        Helper function for getting Manager Instance
        :param api_root: {str} api root
        :param org_key: {str} organization key
        :param cb_cloud_api_id: {str} CB cloud app id
        :param cb_cloud_api_secret_key: {str} CB cloud app secret
        :param lr_api_id: {str} CB cloud LiveResponse app id
        :param lr_api_secret_key: {str} CB cloud LiveResponse app secret
        :param verify_ssl: {bool} verify ssl
        :param force_check_connectivity: {bool} check connectivity param
        :param use_new_api_version: {bool} run action with v3 or v6
        :return: {CarbonBlackLiveResponseManager} or {CarbonBlackLiveResponseManagerV6} instance
        """
        if use_new_api_version:
            return CarbonBlackLiveResponseManagerV6(
                api_root=api_root,
                org_key=org_key,
                cb_cloud_api_id=cb_cloud_api_id,
                cb_cloud_api_secret_key=cb_cloud_api_secret_key,
                lr_api_id=lr_api_id,
                lr_api_secret_key=lr_api_secret_key,
                verify_ssl=verify_ssl,
                force_check_connectivity=force_check_connectivity,
            )

        return CarbonBlackLiveResponseManager(
            api_root=api_root,
            org_key=org_key,
            cb_cloud_api_id=cb_cloud_api_id,
            cb_cloud_api_secret_key=cb_cloud_api_secret_key,
            lr_api_id=lr_api_id,
            lr_api_secret_key=lr_api_secret_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=force_check_connectivity,
        )
