from typing import Any
from unittest.mock import MagicMock

import mysql.connector.cursor



class MySQLSession(MagicMock):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.cursor = MagicMock(spec=mysql.connector.cursor.MySQLCursor)
        self.cursor_mock = self.cursor.return_value
