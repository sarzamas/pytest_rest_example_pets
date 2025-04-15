""" Common Configuration """

# Usage: export SIMPLE_SETTINGS=config_qa

import pathlib
from os import environ

from str2bool import str2bool

from libs.api.airflow.helpers import make_text_ansi_bold, make_text_wrapped

# special settings that change how simple-settings will load settings
SIMPLE_SETTINGS = {"OVERRIDE_BY_ENV": True}

SSL_VERIFY = bool(str2bool(environ.get("SSL_VERIFY", "False")))

LINE_SEPARATOR = make_text_ansi_bold("-" * 80)
LINE_SET_UP = make_text_ansi_bold(make_text_wrapped("SETUP IS DONE! STARTING TEST SESSION..."))
LINE_TEAR_DOWN = make_text_ansi_bold(make_text_wrapped("TEST SESSION IS DONE! STARTING TEARDOWN..."))

REQUEST_TIMEOUT_CONN = 3
REQUEST_TIMEOUT_READ = 3
REQUEST_RETRY_COUNT = 1

# airflow
AIRFLOW_HOST = "airflow-forge.apps.{env}.kryptodev.ru"
AIRFLOW_BASE_URL = "api/v1"
AIRFLOW_USER = "api-user"
AIRFLOW_PASSWORD = "api-user"
