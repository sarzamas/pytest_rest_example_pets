"""Хуки вынесены из базового conftest в отдельный файл в одной папке для разделения функций по уровням решаемых задач"""

import logging
from os import getenv, linesep, path

import pytest
from _socket import gethostname

from Config import LOG_PATH
from Utils.log import logger
from Utils.RandomData import RandomData as Faker


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config):
    """
    Хук для конфигурации тестового прогона:
     - задает имя и путь для локального лог-файла
     - распределяет лог-файлы между workers при запуске прогона с xdist
     - определяет цвет отображения меток `log_level`: [INFO] в консоли
    :param config: служебная фикстура pytest
    """
    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")

    worker_id = getenv('PYTEST_XDIST_WORKER')
    logfile_name = f"{gethostname()}--{Faker.timestamp()}"
    if worker_id:
        logfile_name = f"{logfile_name}--{worker_id}"
        config.option.color = 'no'
    logfile_path = path.join(LOG_PATH, f"{logfile_name}.log")
    logging_plugin.set_log_path(logfile_path)

    if config.option.color == 'yes':
        logging_plugin.log_cli_handler.formatter.add_color_level(logging.INFO, 'cyan')


@pytest.fixture(autouse=True)
def log_delimiter(request):
    """
    Фикстура: разделитель строк текста между тестами в лог-файле тестового прогона
    :param request: служебная фикстура pytest
    """
    test_name = request.function.__name__
    test_path = request.fspath.strpath
    logger.info(f"{linesep}{(' ' + test_name + ' '):-^79} {test_path}")
