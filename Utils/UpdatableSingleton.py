"""utils.py"""

from dataclasses import fields, is_dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Protocol, TypeGuard, cast, runtime_checkable

from libs.api.airflow.helpers import log_and_raise


class UpdatableSingleton(type):
    """
    Метакласс Singleton с гибкой логикой:
    - Возможность выбора между обновляемым (updatable) и базовым (static) Singleton
    - У наследуемых классов нужно ввести параметр класса `_singleton_mode`:
        - updatable - UpdatableSingleton с методом _perform_update() по каждому вызову __call__()
            Экземпляр создается только один раз, последующие вызовы обновляют текущий инстанс
        - static: - Singleton c базовым функционалом создания общего на все вызовы класса
            Экземпляр создается только один раз, последующие вызовы игнорируют аргументы инита

    Ex: Класс-синглтон, наследующий DotDict:

        class MySingletonDict(DotDict, metaclass=UpdatableSingleton):
            _singleton_mode = "updatable"
            def __init__(self, data=None, _inherited=True, **kwargs):
                super().__init__(data, _inherited=_inherited, **kwargs)

            def _perform_update(self, url):
                pass
    """
    _instances = {}
    _lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            # Режим работы синглтона (по умолчанию updatable)
            mode = getattr(cls, "_singleton_mode", "updatable")

            if cls not in cls._instances:
                # Создаем новый экземпляр
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
            else:
                instance = cls._instances[cls]
                if mode == "updatable":
                    # Обновляем существующий экземпляр
                    instance._perform_update(*args, **kwargs)
                # В режиме static ничего не делаем

            return instance


@runtime_checkable
class DataclassInstance(Protocol):
    """Протокол для проверки экземпляров датаклассов"""
    __dataclass_fields__: dict


def is_dataclass_instance(obj: Any) -> TypeGuard[DataclassInstance]:
    """TypeGuard для проверки объектов датаклассов"""
    return is_dataclass(obj) and not isinstance(obj, type)


def convert_to_serializable(obj: Any) -> Any:
    """Рекурсивная конвертация объектов в JSON-сериализуемый формат"""
    if obj is None:
        return None

    # Базовые типы
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # Словари
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items() if v is not None}

    # Коллекции
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [convert_to_serializable(item) for item in obj]

    # Датаклассы
    if is_dataclass_instance(obj):
        return {
            field.name: convert_to_serializable(getattr(obj, field.name))
            for field in fields(cast(DataclassInstance, obj))  # type: ignore[arg-type]
            if getattr(obj, field.name) is not None
        }

    # Специальные типы
    if isinstance(obj, datetime):
        return obj.isoformat()

    if isinstance(obj, Path):
        return str(obj)

    # Обработка неизвестных типов
    log_and_raise(TypeError,
                  f"Тип {type(obj)} не поддерживается сериализацией",
                  logger_name="convert_to_serializable",
                  log_level="error",
                  )
