"""Хуки и служебные фикстуры вынесены из базового conftest в отдельный файл для разделения по уровням решаемых задач"""

import logging
import warnings
from os import getenv, path
from typing import Optional

import pytest
from _socket import gethostname

from Config import DEBUG, LOG_PATH
from Utils.RandomData import RandomData as Faker

from Utils.functions import clear_empty_in_folder, make_text_ansi_bold, make_text_wrapped  # isort:skip

logger = logging.getLogger('logger')


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config):
    """
    Хук для конфигурации тестового прогона:
     - задает путь и уникальное имя для локальных лог-файлов
     - распределяет лог-файлы между workers при запуске прогона с опцией xdist
     - удаляет пустые лог-файлы от прошлых прогонов (возможно с опцией xdist)
     - определяет цвет отображения меток `log_level`: [INFO] в консоли
     - scope: session
    :param config: служебная фикстура pytest
    """

    clear_empty_in_folder(LOG_PATH) if path.isdir(LOG_PATH) else None

    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")

    worker_id = getenv('PYTEST_XDIST_WORKER')
    logfile_name = f"{gethostname()}_{Faker.timestamp()}"

    if worker_id:
        logfile_name = f"{logfile_name}_{worker_id}"
    logfile_path = path.join(LOG_PATH, f"{logfile_name}.log")

    logging_plugin.set_log_path(logfile_path)

    if config.option.color == 'yes':
        add_color = logging_plugin.log_cli_handler.formatter.add_color_level
        add_color(logging.INFO, 'bold', 'cyan')
        add_color(logging.WARNING, 'bold', 'black', 'Yellow')
        add_color(logging.ERROR, 'invert', 'red', 'Black')


@pytest.fixture()
def log_dispatcher(caplog, get_allure_decorator, request):
    """
    Фикстура диспетчеризации логирования:
     - устанавливает общий уровень логирования для лога консоли и файла из env.DEBUG
       (для разделения уровней логирования между консолью и файлом использовать ключи в `pytest.ini`)
     - форматирует и вставляет в лог визуальную отбивку между блоками тестовой сессии:
       - с именем текущего теста
       - со ссылкой на тест в TMS (данные берутся из декоратора `@allure_testcase`)
     - выделяет отбивку как `bold` только при наличии параметра `--color=yes`
     - scope: function
     - запускается из `pytest.ini` ключом `usefixtures`
    :param get_allure_decorator: фикстура получения данных о тесте из декоратора теста `@allure_testcase` (для отбивки)
    :param caplog: служебная фикстура pytest
    :param request: служебная фикстура pytest
    """

    caplog.set_level(logging.DEBUG) if DEBUG else caplog.set_level(logging.INFO)

    test_name, test_link = (make_text_wrapped(_) if _ else None for _ in get_allure_decorator)
    empty_line = make_text_wrapped('', space=0)

    test_title = f"{empty_line}{test_name}{test_link or ''}{empty_line}"

    test_title = make_text_ansi_bold(test_title) if request.config.option.color == 'yes' else test_title

    logger.info(test_title)


@pytest.fixture()
def get_allure_decorator(request) -> tuple:
    """
    Фикстура получения данных о тесте из декоратора `@allure_testcase`:
       - логирует `warning` если у теста отсутствует декоратор `@allure_testcase`
       - логирует `warning` если у теста отсутствует ссылка на TMS TestCaseURL в декораторе `@allure_testcase`
    :param request: служебная фикстура pytest
    :return: tuple:  test_name, test_link - имя текущего теста и ссылка на тесткейс в TMS
    """

    test = request.function
    test_name = test.__name__
    test_link = None
    prefix = f"У теста `{test_name}` отсутствует"

    log_warning(f"{prefix} декоратор `@allure_testcase`") if not hasattr(test, '__allure_display_name__') else None

    if hasattr(test, 'pytestmark'):
        for Mark in test.pytestmark:  # noqa: N806
            if Mark.name == 'allure_link':
                test_link = Mark.args[0]
                break

    if not test_link:
        log_warning(f"{prefix} ссылка на TMS TestCaseURL в декораторе `@allure_testcase`")

    return test_name, test_link


def log_warning(message: str, logger: logging.Logger = None, logger_name: str = None):
    """
    Функция для репортинга сообщения уровня `Warning` одновременно в лог и stderr
     - для репортинга необязательно передавать имеющийся экземпляр `logger`
     - можно задать только желаемое `logger_name` для отображения имени в логе (косвенная ссылка на источник)
     - по умолчанию `logger` будет иметь имя `warning`
    :param message: текст сообщения
    :param logger: экземпляр уже имеющегося logger (опционально)
    :param logger_name: имя в логе для ссылки на источник сообщения (опционально)
    """

    name = logger_name if logger_name else 'warning'
    logger = logging.getLogger(name) if not logger else logger

    logger.warning(message)
    warnings.warn(message)
