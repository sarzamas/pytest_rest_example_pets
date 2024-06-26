"""Хуки и служебные фикстуры вынесены из базового conftest в отдельный файл для разделения по уровням решаемых задач"""

import logging
import re
import warnings
from os import getenv, linesep, path

import pytest
from _socket import gethostname

from Config import DEBUG, LOG_PATH
from Utils.RandomData import RandomData as Faker

from Utils.functions import (  # isort:skip
    clear_empty_in_folder,  # isort:skip
    make_text_ansi_bold,  # isort:skip
    make_text_ansi_info,  # isort:skip
    make_text_ansi_warning,  # isort:skip
    make_text_wrapped,  # isort:skip
)  # isort:skip

logger = logging.getLogger('logger')
log_level = {10: 'DEBUG', 20: 'INFO', 30: 'WARNING', 40: 'ERROR', 50: 'CRITICAL'}
logger.setLevel(log_level[10])


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

    worker_id = getenv('PYTEST_XDIST_WORKER')
    logfile_name = f"{gethostname()}_{Faker.timestamp()}"

    if worker_id:
        logfile_name = f"{logfile_name}_{worker_id}"
    logfile_path = path.join(LOG_PATH, f"{logfile_name}.log")

    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")

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
       - со ссылкой на тест в TMS (данные берутся из декоратора `@allure_...`)
     - выделяет отбивку как `bold` только при наличии параметра `--color=yes`
     - scope: function
     - запускается из `pytest.ini` ключом `usefixtures`
    :param get_allure_decorator: фикстура получения данных о тесте из декоратора теста `@allure_...` (для отбивки)
    :param caplog: служебная фикстура pytest
    :param request: служебная фикстура pytest
    """

    color = request.config.option.color == 'yes'

    caplog.set_level(logging.DEBUG) if DEBUG else caplog.set_level(logging.INFO)

    test_name, test_link, decorator = get_allure_decorator

    if test_link and not re.findall("(?P<url>https?://\\S+)", test_link):
        test_link = '!!! данный тест не имеет валидной ссылки на TMS !!!'
        if color:
            test_link = make_text_ansi_warning(test_link, not color, bold_on_ending=True)

    decorator = make_text_wrapped(f"{decorator or ''} {test_link}") if test_link else None
    test_name = make_text_wrapped(test_name)
    empty_line = make_text_wrapped('', space=0)

    test_title = f"{empty_line}{decorator or ''}{test_name}{empty_line}"

    if color:
        log_level[20] = make_text_ansi_info(log_level[20], not color)
        test_title = make_text_ansi_bold(test_title, not color)

    logger.info(f"{'-' * 4} [{' ' * 3}{log_level[20]}]{test_title}")


@pytest.fixture()
def get_allure_decorator(request) -> tuple:
    """
    Фикстура получения данных о тесте из декоратора `@allure_...`:
    - логирует `Warning` в `stderr` и в логфайл, если у теста:
      - отсутствует декоратор `@allure_...`
      - отсутствует ссылка на TMS TestCaseURL в декораторе `@allure_...`
      - неправильно указан тип декоратора из списка: ['@allure_testcase', '@allure_story']
      - неправильно указан флаг `parametrized_func` в декораторе '@allure_story'
    - scope: function
    :param request: служебная фикстура pytest
    :return: tuple: test_name - имя функции текущего теста
                    test_link - ссылка на тесткейс в TMS
                    allure_decorator - название используемого в тесте декоратора `@allure_...`
    """

    test = request.function
    test_name = test.__name__

    testcase, story = '@allure_testcase', '@allure_story'
    newline = linesep + '-- '
    prefix = f"У теста `{test_name}` необходимо использовать декоратор "

    postfix = (
        f"{newline}P.S. В Allure отчете, для корректного группирования заголовков "
        f"теста с белее чем одним значением для параметризации в представлении `Behaviors`, "
        f"необходимо использовать декоратор `{story}` c `parametrized_func = True`",
    )

    rule_01 = f"OK! - RULE-#01 - Тест с `{testcase}` без параметризации"
    rule_02 = f"OK! - RULE-#02 - Тест с `{testcase}` и одним параметром параметризации"
    rule_03 = f"OK! - RULE-#03 - Тест с `{story}` и многими параметрами параметризации, `parametrized_func = True`"

    rule_11 = (
        f"{make_text_ansi_warning('NOK! RULE-#11', is_tty=False)}  - Тест с `{story}` без параметризации, "
        "`parametrized_func = True`"
    )
    rule_12 = (
        f"{make_text_ansi_warning('NOK! RULE-#12', is_tty=False)}  - Тест с `{story}` без параметризации, "
        "`parametrized_func = False`"
    )
    rule_21 = (
        f"{make_text_ansi_warning('NOK! RULE-#21', is_tty=False)}  - Тест с `{story}` "
        "и одним параметром параметризации, `parametrized_func = True`"
    )
    rule_22 = (
        f"{make_text_ansi_warning('NOK! RULE-#22', is_tty=False)}  - Тест с `{story}` "
        "и одним параметром параметризации, `parametrized_func = False`"
    )
    rule_31 = (
        f"{make_text_ansi_warning('NOK! RULE-#31', is_tty=False)}  - Тест с `{testcase}` "
        "и многими параметрами параметризации"
    )
    rule_32 = (
        f"{make_text_ansi_warning('NOK! RULE-#32', is_tty=False)}  - Тест с `{story}` "
        "и многими параметрами параметризации, `parametrized_func = False`"
    )
    rule_91 = f"{make_text_ansi_warning('NOK! RULE-#91', is_tty=False)}  - Тест без ссылки на TMS"

    decorator_type, parametrize_count, test_link = [None] * 3
    allure_decorator = hasattr(test, '__allure_display_name__')

    if hasattr(test, 'pytestmark'):
        for Mark in test.pytestmark:  # noqa: N806
            match Mark.name:
                case 'allure_link':
                    test_link = Mark.args[0]
                    decorator_type = Mark.kwargs['link_type']
                case 'parametrize':
                    parametrize_count = len(Mark.args[1])

    match allure_decorator, decorator_type, parametrize_count, test_link:
        case (True, 'test_case', None, t) if t:
            logger.debug(rule_01)

        case (True, 'test_case', 1, t) if t:
            logger.debug(rule_02)

        case (True, 'link', p, t) if p and p > 1 and t:
            logger.debug(rule_03)

        case (True, 'link', None, t) if t:
            logger.warning(rule_11)
            log_warning(f"{prefix}`{testcase}`")

        case (False, 'link', p, t) if not p and t:
            logger.warning(rule_12)
            log_warning(f"{prefix}`{testcase}`")

        case (True, 'link', 1, t) if t:
            logger.warning(rule_21)
            log_warning(f"{prefix}`{testcase}`")

        case (False, 'link', 1, t) if t:
            logger.warning(rule_22)
            log_warning(f"{prefix}`{testcase}`")

        case (True, 'test_case', p, t) if p and p > 1 and t:
            logger.warning(rule_31)
            log_warning(f"{prefix}`{story}` вместо `{testcase}`{postfix}")

        case (False, 'link', p, t) if p and p > 1 and t:
            logger.warning(rule_32)
            log_warning(f"{prefix}`{testcase}`")

        case (_, _, _, t) if not t:
            logger.warning(rule_91)
            log_warning(f"{prefix}`@allure_...` c ссылкой на TMS TestCaseURL")

        case _:
            raise NotImplementedError

    allure_decorator = story if decorator_type == 'link' else allure_decorator
    allure_decorator = testcase if decorator_type == 'test_case' else allure_decorator

    log_warning(f"{prefix}`{testcase}` или `{story}`") if not allure_decorator else None

    return test_name, test_link, allure_decorator


def log_warning(message, logger=None, logger_name=None):
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

    message = f"{'-' * 4} [{make_text_ansi_warning(log_level[30], is_tty=False)}]  - {message}"

    logger.warning(message)
    warnings.warn(message)
