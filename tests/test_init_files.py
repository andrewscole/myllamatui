import os

import pytest

from unittest.mock import patch, mock_open, Mock, MagicMock

from src.myllamatui.init_files import set_database_path


@patch("os.path.exists")
def test_set_database_path(os_path):
    home_dir = os.path.expanduser("~")
    db_path = home_dir + "/.config/myllamatui"
    db_name = "myllamatui.db"

    os_path.return_value = True
    MYLLAMACLI_DB = set_database_path()
    assert MYLLAMACLI_DB == f"{db_path}/{db_name}"
