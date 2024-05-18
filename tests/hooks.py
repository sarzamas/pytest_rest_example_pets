"""Хуки и служебные фикстуры вынесены из базового conftest в отдельный файл для разделения по уровням решаемых задач"""

import logging
from os import getenv, linesep, path

import pytest
from _socket import gethostname

from Config import DEBUG, LOG_PATH
from Utils.functions import clear_empty_in_folder
from Utils.RandomData import RandomData as Faker


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config):
    """
    Хук для конфигурации тестового прогона:
     - задает путь и уникальное имя для локальных лог-файлов
     - распределяет лог-файлы между workers при запуске прогона с опцией xdist
     - удаляет пустые лог-файлы от прошлых прогонов с опцией xdist
     - определяет цвет отображения меток `log_level`: [INFO] в
     - scope: session
    :param config: служебная фикстура pytest
    """
    clear_empty_in_folder(LOG_PATH) if path.isdir(LOG_PATH) else None

    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")

    worker_id = getenv('PYTEST_XDIST_WORKER')
    logfile_name = f"{gethostname()}--{Faker.timestamp()}"
    if worker_id:
        logfile_name = f"{logfile_name}--{worker_id}"
    logfile_path = path.join(LOG_PATH, f"{logfile_name}.log")
    logging_plugin.set_log_path(logfile_path)

    if config.option.color == 'yes':
        logging_plugin.log_cli_handler.formatter.add_color_level(logging.INFO, 'bold', 'cyan')


@pytest.fixture()
def log_dispatcher(caplog, request):
    """
    Фикстура диспетчеризации логирования:
     - устанавливает общий уровень логирования из ENV
       (для разделения уровней логирования между консолью и файлом использовать ключи в `pytest.ini`)
     - форматирует разделитель между блоками лога именем теста
     - scope: function
     - запускается из `pytest.ini` ключом `usefixtures`
    :param caplog: служебная фикстура pytest
    :param request: служебная фикстура pytest
    """
    caplog.set_level(logging.DEBUG) if DEBUG else caplog.set_level(logging.INFO)

    test_name = request.function.__name__
    test_title = f"{'':-^79}{linesep}{(' ' + test_name + ' '):-^79}{linesep}{'':-^79}"
    if request.config.option.color == 'yes':
        # выделение `bold`
        test_title = '\033[1m%s\033[0m' % test_title

    logging.getLogger('logger').info(f"{linesep}{test_title}")
