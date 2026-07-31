from __future__ import annotations
import unittest
from unittest.mock import patch, MagicMock
from core import ActiveDirectoryManager as adm_module
from core.ActiveDirectoryManager import (
    ActiveDirectoryManager,
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_RECEIVE_TIMEOUT,
)

class TestActiveDirectoryManager(unittest.TestCase):
    @patch.object(adm_module, "Server")
    @patch.object(adm_module, "Connection")
    def test_manager_init_default_timeouts(self, mock_connection, mock_server):
        # Instantiate with default timeouts (None passed)
        ActiveDirectoryManager(
            server_ip="1.2.3.4",
            domain="example.local",
            username="user",
            password="password",
        )
        
        # Verify Server is called with default connect_timeout
        mock_server.assert_called_once_with(
            "1.2.3.4",
            use_ssl=False,
            tls=None,
            connect_timeout=DEFAULT_CONNECTION_TIMEOUT,
        )
        
        # Verify Connection is called with default receive_timeout
        mock_connection.assert_called_once_with(
            mock_server.return_value,
            "user",
            "password",
            auto_bind=True,
            auto_encode=True,
            receive_timeout=DEFAULT_RECEIVE_TIMEOUT,
        )

    @patch.object(adm_module, "Server")
    @patch.object(adm_module, "Connection")
    def test_manager_init_custom_timeouts(self, mock_connection, mock_server):
        # Instantiate with custom timeouts
        ActiveDirectoryManager(
            server_ip="1.2.3.4",
            domain="example.local",
            username="user",
            password="password",
            connection_timeout=25,
            receive_timeout=120,
        )
        
        # Verify Server is called with connect_timeout = 25
        mock_server.assert_called_once_with(
            "1.2.3.4",
            use_ssl=False,
            tls=None,
            connect_timeout=25,
        )
        
        # Verify Connection is called with receive_timeout = 120
        mock_connection.assert_called_once_with(
            mock_server.return_value,
            "user",
            "password",
            auto_bind=True,
            auto_encode=True,
            receive_timeout=120,
        )

    @patch.object(adm_module, "Server")
    @patch.object(adm_module, "Connection")
    def test_manager_init_none_timeouts(self, mock_connection, mock_server):
        # Instantiate with explicit None or invalid timeouts
        ActiveDirectoryManager(
            server_ip="1.2.3.4",
            domain="example.local",
            username="user",
            password="password",
            connection_timeout=None,
            receive_timeout="invalid",
        )

        mock_server.assert_called_once_with(
            "1.2.3.4",
            use_ssl=False,
            tls=None,
            connect_timeout=DEFAULT_CONNECTION_TIMEOUT,
        )

        mock_connection.assert_called_once_with(
            mock_server.return_value,
            "user",
            "password",
            auto_bind=True,
            auto_encode=True,
            receive_timeout=DEFAULT_RECEIVE_TIMEOUT,
        )


if __name__ == "__main__":
    unittest.main()
