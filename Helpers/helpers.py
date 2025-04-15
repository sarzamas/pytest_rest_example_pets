"""helpers.py"""

import inspect
from datetime import datetime
from os import linesep
from pathlib import Path
from types import FrameType, MethodType
from typing import Any
from zoneinfo import ZoneInfo

from airflow_client.client import ApiException

from libs import get_log

LOG = get_log(__name__)


def get_local_time() -> datetime:
    """:return: local time: datetime(timezone)"""
    return datetime.now(ZoneInfo("Europe/Moscow"))


def parse_pytest_nodeid(nodeid: str) -> tuple[str, str, str] | tuple[str, None, str] | None:
    """Разбирает pytest nodeid на компоненты"""
    parts = nodeid.split("::")
    module_path = parts[0]
    # Получаем имя модуля без .py
    module = Path(module_path).stem

    if len(parts) == 2:
        # Формат: tests/test_file.py::test_function
        return module, None, parts[1]

    elif len(parts) >= 3:
        # Формат: tests/test_file.py::TestClass::test_method
        # Игнорируем возможные вложенные классы (parts[2:] при необходимости)
        return module, parts[1], parts[2]

    else:
        log_and_raise(
            ValueError,
            f'Неверный формат nodeid: {nodeid}',
            logger_name=__name__,
            log_level="error",
        )


def get_method_name(instance: object, max_depth: int = 5) -> str | None:
    """
    Функция: определяет имя оригинального метода, учитывая декораторы

    :param instance: Экземпляр класса (self)
    :param max_depth: Максимальная глубина поиска в стеке вызовов
    """
    frame: FrameType = inspect.currentframe()
    class_methods = [m for m in dir(instance) if callable(getattr(instance, m)) and not m.startswith("__")]

    try:
        for _ in range(max_depth):
            frame = frame.f_back  # type: ignore
            if not frame:
                break

            # Проверяем, есть ли имя функции в списке методов класса
            method_name = frame.f_code.co_name
            if method_name in class_methods:
                return method_name

    finally:
        # Очищаем ссылки на фреймы для избежания утечек памяти
        del frame

    log_and_raise(
        RuntimeError,
        "Original method name not found in call stack",
        logger_name=__name__,
        log_level="error",
    )


def process_kwargs_timeout(method: MethodType, local_vars: dict[str, Any]) -> dict[str, Any]:
    """
    Функция: обрабатывает аргументы метода класса, подставляя значения по умолчанию из экземпляра
        - Конвертирует позиционные и именованные аргументы в плоский словарь `kwargs`
        - Явно переданные аргументы имеют приоритет над значениями по умолчанию из экземпляра
        - Добавляет `_request_timeout` из экземпляра класса, если он не задан в аргументах метода
    ВАЖНО:
        - В `excluded_keys` должны быть указаны служебные переменные (Ex: `self`),
          которые не являются аргументами целевого метода и могут вызвать ошибки

    :param method: Метод класса (должен быть привязан к экземпляру, Ex: `self.method`)
    :param local_vars: Локальные переменные метода, включая аргументы полученные через `locals()`
    :return: Плоский словарь `kwargs` с обработанными аргументами
    :raises ValueError: Если `method` не является `bound method` (не привязан к экземпляру класса)
    """
    if not inspect.ismethod(method):
        log_and_raise(
            ValueError,
            "Метод должен быть связан с экземпляром класса",
            logger_name=__name__,
            log_level="error",
        )

    instance = method.__self__
    logger = get_log(f'{method.__self__.__class__.__name__}.{method.__name__}')
    # Очищаем kwargs от служебных переменных
    excluded_keys = {"self", "local_vars"}
    raw_kwargs = {key: value for key, value in local_vars.items() if key not in excluded_keys}
    # Извлекаем вложенный kwargs
    nested_kwargs = raw_kwargs.pop("kwargs", {})
    # Собираем плоский словарь kwargs
    kwargs = {**raw_kwargs, **nested_kwargs}
    # Получаем значения из экземпляра
    instance_timeout = getattr(instance, "_request_timeout", None) or getattr(instance, "request_timeout", None)
    # Обогащаем kwargs при отсутствии значения при вызове
    kwargs["_request_timeout"] = kwargs.pop("_request_timeout", instance_timeout)
    logger.debug(f'Параметры запроса в API: {{"kwargs": {kwargs}}}')
    return kwargs


def get_error_source(instance: object) -> str:
    """
    Функция: определяет источник ошибки с приоритетом:
    1. Фикстуры pytest (по имени)
    2. Методы класса
    3. Внешние вызовы

    :param instance: Экземпляр класса (self)
    :return: str: имя источника ошибки
    """
    try:
        frames = inspect.getouterframes(inspect.currentframe().f_back.f_back.f_back)
        class_methods = [m for m in dir(instance) if callable(getattr(instance, m)) and not m.startswith("__")]

        # 1. Поиск фикстур pytest
        for frame_info in frames:
            if "fixture" in frame_info.function.lower() and "pytest" not in frame_info.filename:
                return frame_info.function.split()[0]  # Возвращаем имя фикстуры из декоратора

        # 2. Поиск методов класса
        for frame_info in frames:
            if frame_info.function in class_methods:
                return f"{instance.__class__.__name__}.{frame_info.function}"

        # 3. Первый не-pytest фрейм
        for frame_info in frames:
            if "pytest/" not in frame_info.filename and not frame_info.function.startswith("_"):
                return frame_info.function

    except Exception as e:  # pylint: disable=broad-exception-caught
        LOG.error(f'Error source detection failed: {str(e)}')

    return "unknown_source"


def log_and_raise(error_type: type[Exception], message: str, from_exception: Exception | None = None, **kwargs):
    """
    Универсальный хелпер для логирования и вызова исключений

    :param error_type: Тип исключения для проброса
    :param message: Краткое сообщение для логирования
    :param from_exception: Оригинальное исключение сохраняется в цепочке (PEP 3134: атрибут `__cause__`)
    :param kwargs: Аргументы для конструктора исключения (например, filename, obj_type)
    """
    msg = f'{message} | Details: {kwargs}'
    LOG.error(make_text_ansi_error(f'{error_type.__name__}: ') + msg + linesep)
    raise error_type(msg) from from_exception


def handle_api_exception(exception: ApiException, method_name: str = "unknown") -> None:
    """
    Обработка ошибок API с кастомным сообщением
        - с опциональным указанием метода вызвавшего исключение
    :param exception:
    :param method_name:
    :raises RuntimeError:
    """
    # Формируем краткое сообщение (первое предложение из reason)
    reason = exception.reason.split(".")[0].strip() if exception.reason else "Unknown API Error"
    msg = f'[{method_name}] Airflow API Error {exception.status}: {reason}{linesep}'
    # Дополняем деталями из body при наличии
    if exception.body:
        # Обрезаем длинные сообщения
        msg += f'Response details: {exception.body[:300]} ...'

    log_and_raise(
        RuntimeError,
        msg,
        from_exception=exception,
        logger_name=__name__,
        log_level="error",
    )


def make_text_ansi_bold(text: str, reuse_bold_on_ending: bool = None) -> str:
    """
    Функция: для выделения текста жирным с помощью меток ANSI escape sequence color options:
     - для дифференциации форматирования теста в зависимости от места назначения вывода (в окно IDE или в логфайл)
     - может сочетаться с другими метками ANSI-color
    :param text: исходный текст
    :param reuse_bold_on_ending: признак сброса цвета и переустановки `bold` символа на конце текста
    :return: str: ANSI bold text
    """
    text = f'\033[1m{text}\033[0m'
    if reuse_bold_on_ending:
        text = f'{text}\033[1m'
    return text


def make_text_ansi_name(text: Any, reuse_bold_on_ending: bool = None) -> str:
    """
    Функция: для выделения текста сообщения цветом как у поля `name` в логе

    :param text: исходный текст
    :param reuse_bold_on_ending: признак сброса цвета и переустановки `bold` символа на конце текста
    :return: str: ANSI DEBUG-colored text: {foreground: cyan, style: bold}
    """
    return make_text_ansi_bold('\033[36m%s' % text, reuse_bold_on_ending=reuse_bold_on_ending)


def make_text_ansi_warning(text: str, reuse_bold_on_ending: bool = None) -> str:
    """
    Функция: для выделения текста цветом для сообщения типа `warning`

    :param text: исходный текст
    :param reuse_bold_on_ending: признак сброса цвета и переустановки `bold` символа на конце текста
    :return: str: ANSI DEBUG-colored text: {foreground: white, background: yellow, style: bold}
    """
    return make_text_ansi_bold('\033[43m%s' % text, reuse_bold_on_ending=reuse_bold_on_ending)


def make_text_ansi_error(text: str, reuse_bold_on_ending: bool = True) -> str:
    """
    Функция: для выделения текста цветом для сообщения типа `error`

    :param text: исходный текст
    :param reuse_bold_on_ending: признак сброса цвета и переустановки `bold` символа на конце текста
    :return: str: ANSI DEBUG-colored text: {foreground: red, style: bold}
    """
    return make_text_ansi_bold('\033[31m%s' % text, reuse_bold_on_ending=reuse_bold_on_ending)


def make_text_wrapped(
        text: str,
        wrap_symbol: str = "-",
        width: int = 80,
        space: int = 1,
        align: str = "^",
        align_nbr: int = 2,
        new_line: bool = None,
) -> str:
    """
    Функция: для форматирования текста в строку с дополнением одинаковыми символами до нужной ширины
     - Example: `---------- example ----------` (Centered)
                `-- example ------------------` (Left aligned)
                `------------------ example --` (Right aligned)
    :param text: исходный текст
    :param wrap_symbol: символ для обертки текста
    :param width: итоговая ширина форматированного текста с обёрткой его символами
    :param space: количество пробелов между текстом и `wrap_symbol`
    :param align: ключ для выбора стратегии выравнивания текста в строке
    :param align_nbr: количество отступов от края для бокового выравнивания
    :param new_line: ключ для выдачи результата с новой строки
    :return: str: wrapped text
    """
    align_options = ("<", "^", ">")
    if align not in align_options:
        message = f'Для выравнивая текста использовать значение `align` из списка возможных: {align_options}'
        log_and_raise(
            ValueError,
            message,
            logger_name=__name__,
            log_level="error",
        )

    ls = linesep if new_line else None
    edge = wrap_symbol * align_nbr if align != "^" else ""

    text = " " * space + text + " " * space
    escape_len = len(repr(text)) - len(text) + 5
    width = width + escape_len if escape_len > 7 else width

    return (
        f'{ls or ""}'
        f'{(edge if align == "<" else "") + text + (edge if align == ">" else ""):{wrap_symbol}{align}{width}}'
    )
