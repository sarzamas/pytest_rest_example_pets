""" Хуки вынесены из базового conftest.py в отдельный файл для разделения функций по уровням прикладных задач """

import logging
from os import path

import pytest
from _socket import gethostname

from Utils.RandomData import RandomData as Faker
from Config import LOG_PATH

@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """
    Хук для конфигурации тестового прогона:
     - задает имя и путь для локального лог-файла
     - определяет цвет отображения в консоли меток [INFO]
    :param config: служебная фикстура pytest
    """
    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")

    logfile_name = f"{gethostname()}--{Faker.timestamp()}.log"
    logfile_path = path.join(LOG_PATH, logfile_name)

    logging_plugin.set_log_path(logfile_path)
    logging_plugin.log_cli_handler.formatter.add_color_level(logging.INFO, 'cyan')
