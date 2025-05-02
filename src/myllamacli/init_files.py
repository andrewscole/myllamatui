import logging
import os

from pathlib import Path


def set_database_path() -> str:
    home_dir = os.path.expanduser("~")
    db_path = home_dir + "/.config/myllamacli"
    db_name = "myllamacli.db"

    MYLLAMACLI_DB = db_path + "/" + db_name

    if not os.path.exists(db_path):
        os.mkdir(db_path)

    return MYLLAMACLI_DB
