"""decorators.py"""

import inspect
import json
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from airflow_client.client import ApiException
from urllib3.exceptions import ConnectTimeoutError, MaxRetryError

from libs import get_log
from libs.api.airflow.exeptions import ServiceUnavailableError
from libs.api.airflow.helpers import get_error_source, handle_api_exception, log_and_raise, make_text_ansi_name

# Обобщённая типизации
T = TypeVar("T")
P = ParamSpec("P")

LOG = get_log(__name__)


def log_method_args(
        exclude_keys: list | None = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    @Decorator: для логирования вызова метода класса в `stdout`
        - Активен при наличии в переменных окружения флага `DEBUG=True`
        - Логирует все параметры вызова метода (без `self`)
        - Обрабатывает позиционные параметры и `**kwargs`
        - Фильтрует `******` конфиденциальные данные через добавление `exclude_keys`
    ВАЖНО:
        - Обязательно наличие декоратора @wraps() для сохранения исходного имени метода
        - У класса исходного метода необходимо наличие @property `self.debug`
        - Декоратор параметризованный - необходимо использовать со скобками!
            Example:`@log_method_args()`

    :param exclude_keys: Список маскируемых параметров
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(self, *args: P.args, **kwargs: P.kwargs) -> T:
            # Проверяем флаг debug из экземпляра класса
            if not getattr(self, "debug", False):
                return func(self, *args, **kwargs)

            # Получаем информацию о сигнатуре метода
            sig = inspect.signature(func)

            # Полное связывание аргументов с обработкой исключений
            try:
                # Связываем аргументы с учетом self
                bound_args = sig.bind(self, *args, **kwargs)
            except TypeError:
                # Для методов с **kwargs используем частичное связывание
                bound_args = sig.bind_partial(self, *args, **kwargs)

            bound_args.apply_defaults()

            # Маскирование конфиденциальных данных в выводе логгера
            exclude = exclude_keys or []
            filtered_args = {
                k: "******" if k in exclude else v
                for k, v in bound_args.arguments.items()
                if k != "self" and not k.startswith("_") and v is not None
            }
            # Создаем логгер с именем класса вызываемого метода
            method = f'{self.__class__.__name__}.{func.__name__}'
            logger = get_log(method)
            logger.debug(f'Вызов метода из теста: {make_text_ansi_name(method)} с параметрами: {filtered_args}')

            # Передаем оригинальные аргументы без изменений
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def handle_api_errors(func: Callable) -> Callable:
    """
    @Decorator: для обработки ошибок методов Airflow API:
            - `ApiException`: Ошибки API Airflow
            - `JSONDecodeError`: Некорректные JSON-ответы
            - Общие исключения: Резервная обработка непредвиденных ошибок
        Определяет метод вызвавший исключение
        С минимальным логированием:
            - Для Airflow: ErrorType + Status + Краткий reason + Обрезанный body
            - Для остальных: ErrorType: Message
        Сохраняет полный трейсбэк в stderr PEP 3134 (атрибут `__cause__`)
        Использует хелперы:
            - `handle_api_exception` для специфичной обработки API-ошибок
            - `log_and_raise` для унифицированного логирования и выброса исключений
    ВАЖНО:  Порядок применения декоратора к методу:
        Ex:
        @log_method_args()       1. Логирование аргументов
        @auto_handle_errors      2. Обработка ошибок (должен быть ВТОРЫМ!)
        def any_method(...)

    :param func: Обертываемая функция метода API
    :return: Обернутая функция с обработкой ошибок
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)

        except ApiException as e:
            source = get_error_source(self)
            handle_api_exception(e, method_name=source)

        except json.JSONDecodeError as e:
            log_and_raise(
                type(e),
                f'Invalid JSON response: {str(e)}',
                from_exception=e,
                logger_name=self.__class__.__name__,
                log_level="error",
            )

        except ValueError as e:
            log_and_raise(type(e), str(e), from_exception=e, logger_name=self.__class__.__name__, log_level="error")

        except (MaxRetryError, ConnectTimeoutError) as e:
            # Извлекаем детали из оригинального исключения
            url = getattr(e, "url", "Unknown URL")
            reason = getattr(e, "reason", "No reason provided")
            # Формируем сообщение с контекстом
            error_msg = (
                f"[Network Failure] URL: {url} | "
                f"Reason: {reason} | "
                f"Retries: {self.configuration.retries}"
            )
            # Логируем и пробрасываем кастомное исключение
            log_and_raise(
                error_type=ServiceUnavailableError,
                message=error_msg,
                from_exception=e,
                logger_name=self.__class__.__name__,
                log_level="error",
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            error_msg = f'{repr(type(e))} : {str(e)}'
            log_and_raise(
                RuntimeError,
                error_msg,
                from_exception=e,
                logger_name=self.__class__.__name__,
                log_level="error",
            )

    return wrapper
