"""pytest_hooks.py"""

__all__ = [
    "data_collector",
    "pytest_configure",
    "pytest_report_header",
    "pytest_report_teststatus",
    "pytest_runtest_logreport",
    "pytest_runtest_protocol",
    "pytest_sessionfinish",
    # "pytest_sessionstart", TODO: уточнить
    # "pytest_unconfigure" TODO: устранить ошибки
]

from collections.abc import Iterator
from os import linesep, path
from sys import stdin, stdout

import pytest
from _pytest.reports import TestReport
from _pytest.runner import runtestprotocol
from libs.api.airflow.data_collector import SessionDataCollector
from libs.api.airflow.helpers import (
    get_debug_flag,
    get_local_time,
    make_text_ansi_name,
    make_text_ansi_error,
    make_text_ansi_warning,
)
from simple_settings import settings as cfg

from libs import get_log

LOG = get_log("pytest_hook", cr_mark_after="-#-")
debug = get_debug_flag()


@pytest.fixture(scope="session", autouse=True)
def data_collector() -> Iterator[SessionDataCollector]:
    """
    Фикстура для сбора данных тестовой сессии:
        - Сохраняет собранные данные в JSON-файл после завершения сессии

    Ex: Задание имени JSON-файла:
        session_file = sdc.stop_session(filename=path.join(PROJECT_ROOT_DIR, "Path"))

    Ex: Использование в фикстуре:
        @pytest.fixture(scope="function")
        def data_collector(request) -> LocalDataCollector:
            collector = LocalDataCollector()
            collector.mark_test_start(request.node.nodeid)
            yield collector
            collector.mark_test_stop(request.node.nodeid, "passed")

    Ex: Использование в тесте:
        def test_example(data_collector: LocalDataCollector, request):
        nodeid = request.node.nodeid                    # Уникальный ID теста (например, "test_file.py::test_example")
        data_collector.mark_test_start(nodeid)          # Старт теста
        ...                                             # Логика теста
        data_collector.mark_test_stop(nodeid, "passed") # Фиксация результата
    """
    sdc = SessionDataCollector()
    sdc.start_session()

    yield sdc

    sdc.stop_session()


def pytest_configure(config):
    """Позволяет изменять параметры конфигурации тестовой сессии"""
    session_vars = vars(config.option)
    pytest_debug = session_vars.get('debug', False)

    if pytest_debug:
        # pytest_debug = config.option.debug
        # if pytest_debug:
        # config.option.debug = config.option.debug if config.option.debug else False
        config.option.verbose = 0
        config.option.showlocals = True
        config.option.setupshow = True
        config.option.showfixtures = True
        config.option.show_fixtures_per_test = True

        if pytest_debug:
            min_duration = config.option.durations_min
            # percentile = config.option.durations_percentile   # TODO: устранить

            config.option.durations = 3 if not config.option.durations else config.option.durations
            config.option.durations_min = 0.1 if min_duration <= 0.1 or min_duration is None else min_duration
            # config.option.durations_percentile = 90 if percentile <= 0 or percentile is None else percentile

    LOG.info(f'Конфигурация pytest: {session_vars}')
    LOG.debug(f'Режим отладки pytest: {pytest_debug}')


def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None) -> bool:
    """
    Хук для кастомного протокола выполнения тестов со сбором метрик:
    - Производит измерения времени выполнения тестов
        - Перед запуском теста фиксируется время старта
        - Стандартный протокол pytest выполняется через runtestprotocol
        - После выполнения теста рассчитывается длительность и сохраняется в коллектор данных

    :param item: - Текущий объект теста
    :param nextitem: - Объект для передачи в `runtestprotocol`
    :return: True - Сообщаем pytest об кастомном управлении выполнением теста
    :return: None/False - Позволяем pytest продолжить стандартное выполнение
    """

    data_collector = None

    try:
        # Получаем коллектор данных из фикстур теста
        data_collector = item.funcargs.get("data_collector") if hasattr(item, "funcargs") else None
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    # Фиксируем время начала теста
    if data_collector:
        data_collector.mark_test_start(item.nodeid)

    # Выполняем стандартный протокол теста (setup, call, teardown) и получаем отчеты
    reports: list[TestReport] = runtestprotocol(item, nextitem=nextitem)

    # Фиксируем окончание и статус теста
    if data_collector:
        # Ищем отчет о непосредственном выполнении теста (call)
        call_report = next((r for r in reports if r.when == "call"), None)
        status = "failed"
        if call_report:
            if call_report.passed:
                status = "passed"
            elif call_report.skipped:
                status = "skipped"
            elif call_report.outcome == "xfailed":
                status = "xfailed"
            elif call_report.outcome == "xpassed":
                status = "xpassed"
        # Фиксируем время окончания и сохраняем длительность в коллектор
        data_collector.mark_test_stop(item.nodeid, status)
    # Указываем pytest, что протокол обработан
    return True


def pytest_runtest_logreport(report):
    """
    Хук добавляет данные каждого теста в SessionDataCollector
        - Старт теста фиксируется по условию успешного окончания фазы `setup` для теста
        - Окончание теста фиксируется по условию любого окончания фазы `call` для теста
    :param report: pytest log report
    """
    sdc = SessionDataCollector()

    if report.when == "setup" and report.passed:
        sdc.mark_test_start(report.nodeid)

    if report.when == "call":
        status = report.outcome
        if status == "xfailed":
            status = make_text_ansi_warning("expected_failure")
        elif status == "xpassed":
            status = make_text_ansi_warning("unexpected_success")
        else:
            status = report.outcome
        sdc.mark_test_stop(report.nodeid, status)


def pytest_report_header(config):
    """
    :param config: pytest config
    :return: Добавляет заголовок к тестовой сессии
    """
    logo = [
        make_text_ansi_error("©️2025 Kryptonite.ru®️ ") +
        make_text_ansi_name("AirflowAPIClient: apache-airflow-client v.2.10.0  ") +
        make_text_ansi_warning("by sarzamas™️"),
        f'verbose option: {config.option.verbose}',
    ]
    return logo if debug else None


def pytest_report_teststatus(report):
    """
    Хук добавляет перенос строки и отбивку в логе после каждого теста (для визуального разделения тестов)
        - в режиме отладки DEBUG
        - только в интерактивном терминале (не в IDE)
    """
    if report.when == "teardown":
        # Проверяем, что IO идет из/в TTY (`Interactive Terminal`), а не в IDE (из окна CODE в окно RUN)
        if stdin.isatty() and stdout.isatty() and debug:
            stdout.write(linesep * 2 + cfg.LINE_SEPARATOR + linesep)
            stdout.flush()


def pytest_sessionstart(session):  # TODO: разобраться
    """
    Хук управления началом тестовой сессии
    :param session: pytest session
    """
    session.data_collector = SessionDataCollector()
    session.data_collector.start_session()
    start_time = session.data_collector.session.start.strftime("%Y-%m-%d %H:%M:%S")
    LOG.debug(f'Сессия началась в: {start_time}{linesep * 2}{cfg.LINE_SET_UP}{linesep}')


def pytest_sessionfinish(session, exitstatus):
    """Хук для завершения всей сессии тестов"""
    if stdin.isatty() and stdout.isatty() and debug:
        stdout.write(cfg.LINE_TEAR_DOWN + linesep + cfg.LINE_SEPARATOR + linesep)
        stdout.flush()
    sdc = SessionDataCollector()
    sdc.save_session_data(path.join(session.path, "log", "test_results.json"))


def pytest_unconfigure(config):  # TODO: разобраться
    """Управляет действиями после завершения тестовой сессии"""
    print("[!] Все тесты завершены. Освобождаю ресурсы...")
    print(f'[!] Всего тестов: {config._numcollected}')
    print(f'[!] Пройдено: {config._numcollected - len(config._collected_failed)}')
    print(f'[!] Провалено: {len(config._collected_failed)}')
    print(f'[!] Пропущено: {len(config._collected_skipped)}')
    print(f'[!] Время выполнения: {get_local_time() - config._starttime}')
    print(f'[!] Конфигурация: {config._startpath}')
