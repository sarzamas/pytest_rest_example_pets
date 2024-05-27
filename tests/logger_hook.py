"""Хуки и служебные фикстуры вынесены из базового conftest в отдельный файл для разделения по уровням решаемых задач"""

import logging
import warnings
from os import getenv, path

import pytest
from _socket import gethostname

from Config import DEBUG, LOG_PATH
from Utils.RandomData import RandomData as Faker

from Utils.functions import clear_empty_in_folder, make_text_ansi_bold, make_text_ansi_info, make_text_ansi_warning, make_text_wrapped


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

    caplog.set_level(logging.DEBUG) if DEBUG else caplog.set_level(logging.INFO)

    test_name, test_link, allure_decorator = get_allure_decorator

    decorator = make_text_wrapped(f"{allure_decorator or ''} {test_link}") if test_link else None
    test_name = make_text_wrapped(test_name)
    empty_line = make_text_wrapped('', space=0)
    newline = f"{'-' * 4} [{make_text_ansi_info('   INFO')}]"

    test_title = f"{newline}{empty_line}{decorator or ''}{test_name}{empty_line}"

    test_title = make_text_ansi_bold(test_title) if request.config.option.color == 'yes' else test_title

    logger.info(test_title)


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

    testcase, story, combo_report_mark = '@allure_testcase', '@allure_story', '@pytest.mark.allure_combo_report'
    newline = linesep + '-- '
    prefix = f"{newline}У теста `{test_name}` "

    postfix1 = (f"{newline}Вы действительно хотите объединить несколько тестовых функций под одним заголовком "
                f"в представлении `Behaviors` Allure отчета?{newline}"
                f"Если `ДА`, то добавьте декоратор `{combo_report_mark}` к тестовой функции `{test_name}` чтобы убрать "
                f"`Warning`{newline}Если `НЕТ`, то используйте декоратор `{testcase}`{newline}"
                f"P.S. Объединять декоратором `{combo_report_mark}` можно только тестовые функции, "
                f"которые либо не параметризованы вовсе, либо имеют всего одно значение параметризации, иначе Allure "
                f"отчет в представлении `Behaviors` выглядит некорректно")

    postfix2 = (f"{newline}P.S. В Allure отчете, для корректного группирования заголовков "
                f"теста с белее чем одним значением для параметризации в представлении `Behaviors`, "
                f"необходимо использовать декоратор `{story}`")

    decorator_type, parametrize_count, combo_report, test_link = [None] * 4
    allure_decorator = hasattr(test, '__allure_display_name__')

    if hasattr(test, 'pytestmark'):
        for Mark in test.pytestmark:  # noqa: N806
            match Mark.name:
                case 'allure_link':
                    test_link = Mark.args[0]
                    decorator_type = Mark.kwargs['link_type']
                case 'parametrize':
                    parametrize_count = len(Mark.args[1])
                case 'allure_combo_report':
                    combo_report = True

    match allure_decorator, decorator_type, parametrize_count, combo_report, test_link:
        case (a, 'link', p, True, t) if not a and not p and t:
            pass
        case (a, 'link', 1, True, t) if not a and t:
            pass
        case (a, 'test_case', p, _, t) if a and not p and t:
            pass
        case (a, 'test_case', 1, _, t) if a and t:
            pass
        case (a, 'link', p, None, t) if a and p and p > 1 and t:
            pass
        case (a, 'link', p, True, t) if a and not p and t:
            log_warning(f"{prefix}необходимо или установить флаг `parametrized_func = False`, или убрать декоратор "
                        f"`{combo_report_mark}`")
        case (a, 'link', p, None, t) if a and not p and t:
            log_warning(f"{prefix}необходимо или использовать декоратор `{testcase}` "
                        f"или установить флаг `parametrized_func = False`")
        case (a, 'link', 1, True, t) if a and t:
            log_warning(f"{prefix}необходимо или установить флаг `parametrized_func = False`, или убрать декоратор "
                        f"`{combo_report_mark}`")
        case (a, d, p, c, _) if not a and d and not p and not c:
            log_warning(f"{prefix}нет параметризации{postfix1}")
        case (a, d, 1, c, _) if not a and d and not c:
            log_warning(f"{prefix}отсутствует множественная параметризация{postfix1}")
        case (_, 'link', p, True, _) if p > 1:
            log_warning(f"{prefix}множественная параметризация - необходимо убрать декоратор `{combo_report_mark}`")
        case (a, d, p, _, _) if not a and d and p and p > 1:
            log_warning(f"{prefix}необходимо установить флаг `parametrized_func = True` в декораторе `{story}`")
        case (a, 'link', p, _, _) if a and not p:
            log_warning(f"{prefix}необходимо или использовать декоратор `{testcase}`, или установить флаг "
                        f"`parametrized_func = False` в декораторе `{story}`")
        case (a, 'link', p, _, _) if a and p and p == 1:
            log_warning(f"{prefix}необходимо или использовать декоратор `{testcase}`, или установить флаг "
                        f"`parametrized_func = False` в декораторе `{story}`")
        case (_, 'test_case', p, _, _) if p and p > 1:
            log_warning(f"{prefix}необходимо использовать  декоратор `{story}` вместо `{testcase}`{postfix2}")
        case (_, _, _, _, t) if not t:
            log_warning(f"{prefix}отсутствует ссылка на TMS TestCaseURL в декораторе `@allure_...`")
        case _:
            raise NotImplementedError

    allure_decorator = story if decorator_type == 'link' else allure_decorator
    allure_decorator = testcase if decorator_type == 'test_case' else allure_decorator

    log_warning(f"{prefix}отсутствует декоратор `{testcase}` или `{story}`") if not allure_decorator else None

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

    stdout = f"{'-' * 4} [{make_text_ansi_warning('WARNING')}]"
    stderr = f"{'-' * 4} [{make_text_ansi_warning('WARNING', is_tty=False)}]"

    logger.warning(stdout + message)
    warnings.warn(stderr + message)
