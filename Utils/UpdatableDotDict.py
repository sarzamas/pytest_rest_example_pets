"""UpdatableDotDict"""

from collections.abc import Iterable, Mapping
from datetime import datetime
from threading import Lock
from typing import Any, TypeAlias

from libs import get_log
from libs.api.airflow.helpers__ll import log_and_raise

LOG = get_log(__name__)

ScalarType: TypeAlias = int | float | str | bool | None
RecursiveType: TypeAlias = (
        dict[str, "RecursiveType | list[RecursiveType] | ScalarType"] |
        list["RecursiveType | ScalarType"] |
        tuple["RecursiveType | ScalarType", ...] |
        ScalarType
)

DotDictType: TypeAlias = (
        dict[str, "DotDictType | list[RecursiveType] | datetime"] |
        list["DotDictType | RecursiveType"] |
        tuple["DotDictType | list[RecursiveType]", datetime] |
        Mapping[str, "DotDictType | RecursiveType"] |
        Iterable[tuple[str, "DotDictType | RecursiveType"]]
)


class UpdatableSingleton(type):
    """
    Метакласс Singleton с гибкой логикой:
    - Возможность выбора между обновляемым (updatable) и базовым (static) Singleton
    - У наследуемых классов нужно ввести параметр класса `_singleton_mode`:
        - updatable - Singleton с методом _perform_update() по каждому вызову __call__()
        - static: - Singleton c базовым функционалом создания общего на все вызовы класса
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


class DotDict(dict):
    """
    Расширенный словарь с `dotted` доступом к ключам и рекурсивной конвертацией структур:
        - Автоматическая конвертация вложенных dict, list и комбинированных структур данных
        - Динамическое обновление атрибутов
        - Полная интеграция с dict API
        - Расширенная обработка ошибок
        - Конвертация в обычный dict (to_dict())
        Ex:
        json_data = json.dumps(data.to_dict())

        TODO: Добавить кэширование или мемоизацию
    """

    def __init__(self, data: DotDictType = None, _inherited: bool = False, **kwargs: Any):
        super().__init__()
        self._inherited = _inherited  # У классов наследников в __init__(): super().__init__(_inherited=True)

        if data is not None:
            # Явная обработка Mapping и Iterable
            if isinstance(data, Mapping):
                # Для словарей и подобных объектов
                for key, value in data.items():
                    self[key] = self._convert(value)
            elif isinstance(data, Iterable):
                # Для списков/кортежей пар (ключ, значение)
                for key, value in data:
                    self[key] = self._convert(value)
            else:
                log_and_raise(
                    TypeError,
                    f'Неподдерживаемый тип данных: {type(data)}',
                    logger_name=self.__class__.__name__,
                    log_level="error",
                )

        # Обработка kwargs
        for key, value in kwargs.items():
            self[key] = self._convert(value)

    def __getattr__(self, name: str) -> Any:
        """Получение атрибута по имени. Если атрибут не найден, генерирует исключение"""
        try:
            return self[name]
        except KeyError:
            log_and_raise(
                AttributeError,
                f'"{self.__class__.__name__}" не содержит атрибута "{name}"',
                available_attrs=list(self.keys()),
                logger_name=self.__class__.__name__,
                log_level="error",
            )

    def __setattr__(self, name: str, value: Any) -> None:
        """Установка атрибута по имени. Автоматически конвертирует значение, если оно является dict или list"""
        if name in dir(dict):
            log_and_raise(
                AttributeError,
                f'Ключ "{name}" конфликтует со встроенным атрибутом dict',
                logger_name=self.__class__.__name__,
                log_level="error",
            )
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self[name] = self._convert(value)

    def __delattr__(self, name: str) -> None:
        """Удаление атрибута по имени. Если атрибут не найден, генерирует исключение"""
        try:
            del self[name]
        except KeyError:
            log_and_raise(
                AttributeError,
                f'Атрибут "{name}" не существует',
                object_type=self.__class__.__name__,
                logger_name="DotDict",
                log_level="error",
            )

    def __getitem__(self, key: str) -> Any:
        """Получение значения по ключу. Автоматически конвертирует значение, если оно является dict или list"""
        value = super().__getitem__(key)
        return self._convert(value) if isinstance(value, (dict, list)) else value

    def __setitem__(self, key: str, value: Any) -> None:
        """Установка значения по ключу. Автоматически конвертирует значение, если оно является dict или list"""
        super().__setitem__(key, self._convert(value))

    def __repr__(self) -> str:
        """Строковое представление объекта. Отображает имя класса и содержимое словаря"""
        return f'{self.__class__.__name__}({super().__repr__()})'

    def _convert(self, data: Any) -> Any:
        """
        Рекурсивная конвертация элементов:
            - Конвертирует вложенные dict, list, tuple, а также комбинированные структуры данных
            - Флаг `_inherited=True` защищает от бесконечной рекурсии в `__init__()` у наследников
        """
        if isinstance(data, dict):
            if self._inherited:
                # У наследуемого класса при __init__() создается базовый DotDict() - предотвращение бесконечной рекурсии
                return DotDict(data, _inherited=True)
            else:
                # Для сохранения типа корневого объекта у вложенных объектов
                return self.__class__(data, _inherited=False)

        elif isinstance(data, (list, tuple)):
            return type(data)(self._convert(item) for item in data)

        return data

    def update(self, __m: Mapping | Iterable[tuple[any, any]] = None, **kwargs) -> None:
        """
        Обновление с автоматической конвертацией всех элементов:
            - Может принимать словарь или итерируемый объект с парами ключ-значение
        """
        if __m is not None:
            if isinstance(__m, Mapping):
                items = __m.items()
            else:
                items = __m
            for key, value in items:
                self[key] = self._convert(value)
        for key, value in kwargs.items():
            self[key] = self._convert(value)

    def to_dict(self) -> dict[str, RecursiveType]:
        """
        Конвертация обратно в обычный dict:
            - Рекурсивно конвертирует в dict все вложенные объекты DotDict, [DotDict], (DotDict,)
        :returns:
            Словарь, где значения могут быть:
                - Базовыми типами (int, str, bool, None и т.д.),
                - Вложенными словарями (Dict[str, Any]),
                - Списками (List[Any]),
                - Кортежами (Tuple[Any, ...]).
        """

        def convert(value: Any) -> RecursiveType:
            """Конвертер DotDict --> dict"""
            if isinstance(value, DotDict):
                return value.to_dict()
            elif isinstance(value, list):
                return [convert(item) for item in value]
            elif isinstance(value, tuple):
                return tuple(convert(item) for item in value)
            return value

        return {key: convert(value) for key, value in self.items()}


class Config(DotDict, metaclass=UpdatableSingleton):
    """
    Ключевые особенности:
    - Глубокое слияние словарей
    - Обновление вложенных структур без перезаписи всего раздела
    - Поддержка разных форматов данных:
        - Словари (Mapping)
        - Итерируемые объекты с парами ключ-значение
        - Ключевые аргументы
    - Валидация данных
        - Автоматическая проверка корректности после обновления
    - Наблюдатели (Observers)
        - Уведомление внешних компонентов об изменениях
    - Потокобезопасность
        - Использование блокировки для корректной работы в многопоточной среде
    """

    def _perform_update(self, *args, **kwargs):
        """
        Расширенный метод обновления с дополнительной функциональностью:
        - Автоматическим слиянием настроек
        - Валидацией значений
        - Механизмом оповещения
        - Поддержкой сложных структур данных
        """

        # 1. Слияние вложенных словарей (deep merge)
        def deep_update(source, overrides):
            for key, value in overrides.items():
                if isinstance(value, Mapping) and key in source:
                    deep_update(source[key], value)
                else:
                    source[key] = self._convert(value)
            return source

        # 2. Обработка разных типов данных
        for arg in args:
            if isinstance(arg, Mapping):
                deep_update(self, arg)
            elif isinstance(arg, Iterable):
                for k, v in arg:
                    self[k] = self._convert(v)
            else:
                raise TypeError("Неподдерживаемый тип данных для обновления")

        # 3. Обработка ключевых аргументов
        deep_update(self, kwargs)

        # 4. Валидация данных после обновления
        self._validate()

        # 5. Уведомление подписчиков
        self._notify_observers()

    def _validate(self):
        """Пример валидации конфигурации"""
        if 'timeout' in self and not (0 < self.timeout < 100):
            raise ValueError("Некорректное значение timeout")

    def _notify_observers(self):
        """Уведомление подписчиков об изменениях"""
        for callback in getattr(self, '_callbacks', []):
            try:
                callback(self)
            except Exception as e:
                LOG.error(f"Ошибка в callback: {e}")

    def add_callback(self, callback: callable):
        """Добавление callback-функции при изменениях"""
        if not hasattr(self, '_callbacks'):
            self._callbacks = []
        self._callbacks.append(callback)
