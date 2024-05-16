""" Хуки вынесены из базового conftest.py в отдельный файл для разделения функций по уровням прикладных задач """

import logging
from os import linesep, path

import pytest
from _socket import gethostname

from Config import LOG_PATH
from Utils.log import logger
from Utils.RandomData import RandomData as Faker


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """
    Хук для конфигурации тестового прогона:
     - задает имя и путь для локального лог-файла
     - определяет цвет отображения меток `log_level`: [INFO] в консоли
    :param config: служебная фикстура pytest
    """
    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")

    logfile_name = f"{gethostname()}--{Faker.timestamp()}.log"
    logfile_path = path.join(LOG_PATH, logfile_name)

    logging_plugin.set_log_path(logfile_path)
    logging_plugin.log_cli_handler.formatter.add_color_level(logging.INFO, 'cyan')


@pytest.fixture(autouse=True)
def log_delimiter(request):
    """
    Разделитель строк текста между тестами в лог-файле тестового прогона
    """
    test_name = request.function.__name__
    test_path = request.fspath.strpath
    logger.info(f"{linesep}{test_name:-^79} from {test_path}")
