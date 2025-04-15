"""checker.py"""

import re
from os import linesep
from typing import Any, get_args

from requests import Response

from libs import get_log

LOG = get_log(__name__)


class Checker:
    """Класс методов проверки и валидации HTTP ответов"""

    @staticmethod
    def validate_response_json(
            response: Response,
            expected_code: int = 200,
            required_keys: str | list[str] | None = None,
            key_types: dict[str, type | tuple[type, ...]] | None = None,
            check_non_empty: bool = False
    ) -> dict:
        """
        Выполняет последовательные проверки ответа API:
        - Проверяет статус-код HTTP-ответа
        - Проверяет валидность JSON-объекта:
            - Проверяет наличие в JSON объекте обязательных ключей (если указан `required_keys`)
             с расширенной проверкой путей в dotted.notation:
                - Вложенных ключей через точку: required_keys = "key.subkey.value"
                - Элементов списков через индекс: required_keys = "key.[0].subkey.[123]"
                - Всех элементов списка: required_keys = "key.[*].subkey.[*].value"
                - параметр `required_keys` может содержать несколько проверок в виде списка:
                    Ex: required_keys = ["key1.subkey", "key2.[0].subkey.[*].value"]
            - Проверяет типы значений (если указан словарь `key_types` и значения есть в ответе):
                - Вложенных ключей через точку: key_types = {"key.subkey.value": list}
                - Элементов списков через индекс: key_types = {"key.[0].subkey.[123]": str}
                - Всех элементов списка: key_types = {"key.[*].subkey.[*].value": bool}
                - Словарь `key_types` может содержать несколько проверок в виде словаря:
                    Ex: key_types = {"key": list, "key.[*].subkey.value": dict}
                - Позволяет делать проверки типов с разрешением `null`:
                    Ex: key_types = {"key.[*].subkey.value": (dict, type(None)}
            - Опционально проверяет, что JSON не пустой
            - Возвращает распарсенный JSON для дополнительных проверок

        :param response: requests.Response object
        :param expected_code: Ожидаемый HTTP-код (по умолчанию 200)
        :param required_keys: Ключи или пути, которые должны существовать
        :param key_types: Dict {key: expected_type or tuple_of_types} для проверки типов
                  Ex: {"key": (str, type(None))}
        :param check_non_empty: Проверять, что JSON не пустой
        :return: dict - JSON-объект целиком

        Usage:
        >>> Checker.validate_response_json(response, required_keys="dags.[*].schedule_interval.value")
        >>> Checker.validate_response_json(response, required_keys=["dags.[*].dag_id", "total_entries"])
        >>> Checker.validate_response_json(response, key_types={"dags": list, "dags.[*].schedule_interval.value": str})
        >>> Checker.validate_response_json(response, required_keys="dag.[*].dag_id", key_types={"dag.[*].dag_id": str})
        >>> Checker.validate_response_json(response, key_types={"dags.[*].schedule_interval.value": (str, type(None))
        """
        # region Подготовка
        postfix = f'{linesep}Response: {Checker.truncate(response.text)}'
        # endregion

        # region Проверка статус-кода
        assert response.status_code == expected_code, (
            f'Expected HTTP {expected_code}, got {response.status_code} | URL: {response.url}{postfix}'
        )
        # endregion

        # region Парсинг JSON
        try:
            json_data = response.json()
        except Exception as e:
            raise AssertionError(f'Invalid JSON: {e}{postfix}') from e

        postfix = f'{linesep}Response: {Checker.truncate(str(json_data))}'
        # endregion

        # region Проверка на пустоту
        if check_non_empty:
            assert (isinstance(json_data, (dict, list)) and json_data), f'JSON is empty{postfix}'
        # endregion

        # region Проверка обязательных ключей (required_keys)
        if required_keys:
            # Проверка синтаксиса для всех путей
            for key_path in required_keys:
                Checker._validate_path_syntax(key_path)

            required_keys = [required_keys] if isinstance(required_keys, str) else required_keys

            for key_path in required_keys:
                try:
                    # Валидация синтаксиса пути
                    if any(part.startswith("[") and not re.match(r"\[\*?\d*]", part)
                           for part in key_path.split(".")):
                        raise ValueError(f"Invalid path syntax: '{key_path}'")

                    values = Checker.get_value(json_data, key_path)
                    if values is None:
                        raise AssertionError(f'Путь "{key_path}" не найден')

                    # Если результат — список, проверяем, что все элементы не None
                    if isinstance(values, list):
                        for idx, item in enumerate(values):
                            if item is None:
                                raise AssertionError(
                                    f'Элемент #{idx} в пути "{key_path}" содержит None '
                                    f'или отсутствует{postfix}'
                                )
                    # Для скаляров проверяем существование
                    else:
                        assert values is not None, f'Значение для пути "{key_path}" равно None{postfix}'

                except Exception as e:
                    raise AssertionError(f'Ошибка проверки обязательных ключей: {e}{postfix}') from e
        # endregion

        # region Проверка типов данных (key_types)
        if key_types:
            for key_path, expected_type in key_types.items():
                try:
                    # Проверяем синтаксис пути перед обработкой
                    Checker._validate_path_syntax(key_path)
                    # Получаем значение по заданному пути
                    values = Checker.get_value(json_data, key_path)

                    allowed_types = get_args(expected_type) or (expected_type,)
                    has_wildcard = "[*]" in key_path

                    if has_wildcard:
                        # Для wildcard-путей проверяем элементы списка на соответствие типу
                        if not isinstance(values, list):
                            raise AssertionError(
                                f'Ожидался список для пути "{key_path}", получен: {type(values).__name__}'
                            )

                        # Перебираем элементы с выводом индекса
                        for idx, item in enumerate(values, start=1):  # <--- start=1 для удобства нумерации элементов
                            try:
                                assert isinstance(item, allowed_types), (
                                    f'Ошибка Типа данных в элементе #{idx} | Путь: {key_path} | '
                                    f'Ожидаемый тип: {allowed_types} | '
                                    f'Фактический тип: {type(item).__name__} | '
                                    f'Значение: {Checker.truncate(str(item))}'
                                )
                            except AssertionError as e:
                                # Вывод отладочной информации
                                LOG.debug(
                                    f'Проблемный элемент с несоответствием типа для пути {key_path}: '
                                    f'{key_path.split(".")[0]}[{idx - 1}] | {e}{linesep}'
                                    f'Response JSON: {Checker.truncate(str(json_data))}'
                                )
                                raise

                    else:
                        # Для обычных путей проверяем тип самого значения
                        if not isinstance(values, allowed_types):
                            raise AssertionError(
                                f'Ошибка Типа данных | Путь: "{key_path}") | '
                                f'Ожидаемый тип: {allowed_types} | '
                                f'Фактический тип: {type(values).__name__} | '
                                f'Значение: {Checker.truncate(str(values))}'
                            )

                except Exception as e:
                    raise AssertionError(f'Ошибка проверки типа для пути "{key_path}": {e}') from e
        # endregion

        return json_data

    @staticmethod
    def assert_json_value(
            response: Response,
            key_path: str | tuple[str, ...],
            expected_value: Any | tuple[Any, ...],
            expected_code: int = 200
    ) -> None:
        """
        Проверяет, что значение ключа (или ключей в виде кортежа) в JSON-ответе равно ожидаемому:
            - Автоматическая проверка HTTP status_code и наличия ключа в JSON объекте
            - Поддержка вложенных ключей через синтаксис dotted.notation
            - Проверка всех типов данных (скалярных и списочных), но только в виде сравнения:
                - одного элемента пути: key_path = "key.subkey.value"
                - кортежа путей: key_path = ("key1.subkey.value", "key2.[0].subkey.value")
        ВАЖНО:
            - Запрещено использование [*] в `key_path`
            - Для списков используйте конкретные индексы: [0], [123] и т.д.

        :param response: requests.Response object
        :param key_path: Путь(и) до ключа в схеме JSON объекта:
                          - Для вложенных ключей использовать dotted.notation
                          - Может быть строкой или кортежем строк
                          - Кортеж используется для проверки нескольких путей одновременно
        :param expected_value: Ожидаемое значение:
                                - Если key_path - кортеж, expected_value должно быть кортежем той же длины
        :param expected_code: Expected HTTP status_code (20<0/1/...>)

        Usage:
        >>> assert_json_value(response, key_path="key.subkey", expected_value=...) - OK!
        >>> assert_json_value(response, key_path="key.[0].subkey", expected_value=...) - OK!
        >>> assert_json_value(response, key_path=("key.[0].subkey", "key.[1].subkey") expected_value=...) - OK!
        >>> assert_json_value(response, key_path="key.[*].subkey", expected_value=...) - Error!
        """

        # region Проверка на запрещенный паттерн [*] в key_path
        def _check_wildcard(key: str) -> None:
            """Внутренняя проверка синтаксиса пути"""
            if "[*]" in key:
                raise AssertionError(
                    f'Использование [*] запрещено в key_path: "{key}" | '
                    f'Используйте конкретные индексы, например [0], [123]'
                )

        if isinstance(key_path, tuple):
            for path in key_path:
                _check_wildcard(path)
        else:
            _check_wildcard(key_path)
        # endregion

        # region Подготовка данных
        json_data = Checker.validate_response_json(response, expected_code=expected_code)
        key_paths = key_path if isinstance(key_path, tuple) else (key_path,)
        expected_values = expected_value if isinstance(expected_value, tuple) else (expected_value,)

        if len(key_paths) != len(expected_values):
            raise ValueError("Количество путей и ожидаемых значений должно совпадать")

        postfix = f'{linesep}Response: {Checker.truncate(str(json_data))}'
        # endregion

        # region Получение и проверка значений
        try:
            for path, expected in zip(key_paths, expected_values):
                actual = Checker.get_value(json_data, path)
                assert actual == expected, (
                    f'Несоответствие значения для пути "{path}" | '
                    f'Ожидалось: {expected} ({type(expected.__name__)}) | '
                    f'Фактически: {actual} ({type(actual.__name__)}){postfix}'
                )
        except (KeyError, IndexError) as e:
            raise AssertionError(f'Ошибка пути key_path: "{key_path}" | {e}{postfix}') from e
        # endregion

    @staticmethod
    def get_value(data: dict | list, key_path: str, unique: bool = False) -> Any:
        """
        Возвращает значение по сложному пути в JSON-структуре, заданному в dotted.notation:
            - Для вложенного ключа с указанием через точку: key_path = "key.subkey.value"
            - Для элемента списка через индекс: key_path = "key.[123].subkey.[0].value"
            - Для списка значений ключей всех элементов списка: key_path = "key.[*].subkey.[*]"
                Ex: key_path = dags.[*].tags.[0].name → список значений `name` из первого элемента `tags` каждого DAG
            - Для wildcard [*] может возвращать уникальные значения (unique=True) или все по порядку (unique=False)
            - Если на пути встречается null или [] - возвращает None
            - Если unique=True, None будут исключены из результатов, даже если они разрешены в key_types.

        :param data: JSON-объект (объект может содержать вложенные структуры такие как  dict или list)
        :param key_path: Путь к ключу в формате dotted.notation (вида `key.subkey` или `key.[n]/[*].subkey`)
        :param unique: Для wildcard-путей возвращает set вместо list (без None)
        :return: value/list - значение ключа по указанному пути или список значений всех ключей (при [*])
        """

        def traverse(current: Any, parts: list[str]) -> Any:
            """
            Рекурсивно обходит структуру данных по указанному пути

            :param current: Текущий элемент для обработки (dict, list или None)
            :param parts: Оставшиеся части пути для обработки
            :return: Результат обхода. Может быть:
                    - Списком значений для wildcard-путей
                    - Конкретным значением для точных путей
                    - None если путь не найден
            """
            if not parts:
                return [current] if current is not None else []

            part = parts[0]
            remaining = parts[1:]

            # Обработка списков и wildcard
            if part.startswith("[") and part.endswith("]"):
                results = []
                if part == "[*]":
                    if isinstance(current, list):
                        for item in current:
                            results.extend(traverse(item, remaining))
                else:
                    idx = int(part[1:-1])
                    if isinstance(current, list) and idx < len(current):
                        results.extend(traverse(current[idx], remaining))
                return results

            # Обработка словарей
            if isinstance(current, dict):
                return traverse(current.get(part), remaining)
            return []

        # Определяем, содержит ли путь wildcard
        has_wildcard = "[*]" in key_path
        all_values = traverse(data, key_path.split("."))

        # Для обычных путей возвращаем единственное значение
        if not has_wildcard:
            return all_values[0] if all_values else None

        # Обработка уникальности
        if unique:
            unique_values = []
            seen = set()
            for value in all_values:
                if value not in seen:
                    seen.add(value)
                    unique_values.append(value)
            return unique_values

        return all_values

    @staticmethod
    def truncate(text: str, max_len: int = 1000) -> str:
        """
        Ограничивает длину выводимого текста до указанной для вывода в ошибках
        :param text: исходный текст
        :param max_len: ограничение длины вывода текста
        :return: укороченная до `max_len` символов строка
        """
        return text[:max_len] + "..." if len(text) > max_len else text

    @staticmethod
    def _validate_path_syntax(key_path: str):
        """Проверяет корректность синтаксиса пути в формате dotted.notation"""
        _INDEX_PATTERN = re.compile(r"^\[\d+]$")
        _WILDCARD_PATTERN = re.compile(r"^\[\*]$")

        parts = key_path.split(".")
        for part in parts:
            if part.startswith("["):
                # Проверяем корректность индекса списка: [*], [0], [123]
                if not (_WILDCARD_PATTERN.match(part) or _INDEX_PATTERN.match(part)):
                    raise ValueError(
                        f'Некорректный формат индекса списка: "{part}" | '
                        'Используйте `[*]` для всех элементов или `[число]` для конкретного индекса'
                    )
            else:
                # Запрещаем квадратные скобки в обычных ключах
                if "[" in part or "]" in part:
                    raise ValueError(
                        f'Недопустимые символы в key_path: "{part}"{linesep}'
                        'Ключи не должны содержать "[", "]" | '
                        'Для списков используйте синтаксис с точкой: `key.[*].subkey` или `key.[0].subkey`'
                    )
        # Проверяем отсутствие пустых сегментов (например, "dags..[*]")
        if "" in parts:
            raise ValueError(f'Путь содержит пустые сегменты dotted.notation: "{key_path}"')
