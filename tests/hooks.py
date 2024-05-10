from datetime import datetime

import pytest
from _socket import gethostname
from allure_commons.utils import now


def datetime_now() -> str:
    """Форматирование даты для имени лог файла"""
    epoch = now()
    unix_timestamp_seconds = epoch / 1000
    dt_object = datetime.fromtimestamp(unix_timestamp_seconds)
    return dt_object.strftime('%Y-%m-%d--%H-%M')


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")
    logging_plugin.set_log_path(f"{gethostname()}--{datetime_now()}.log")
