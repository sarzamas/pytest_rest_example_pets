from typing import Any, Optional

from requests.structures import CaseInsensitiveDict


class CommonChecker:
    """
    Класс с базовыми чекерами для HTTP запросов
    """

    default_message = "Некорректный статус код"

    @staticmethod
    def check_status_code(r: Any, status_code: int, assertion_message: str = default_message):
        assert r.status_code == status_code, f"{assertion_message}: {r.status_code}"

    @staticmethod
    def check_status_code_ok(r: Any, assertion_message: str = default_message):
        assert r.status_code == 200, f"{assertion_message}: {r.status_code}, {r.text}"

    @staticmethod
    def check_status_code_204(r: Any, assertion_message: str = default_message):
        assert r.status_code == 204, f"{assertion_message}: {r.status_code}, {r.text}"

    @staticmethod
    def check_status_code_302(r: Any, assertion_message: str = default_message):
        assert r.status_code == 302, f"{assertion_message}: {r.status_code}"

    @staticmethod
    def check_status_code_400(r: Any, assertion_message: str = default_message):
        assert r.status_code == 400, f"{assertion_message}: {r.status_code},  {r.text}"

    @staticmethod
    def check_status_code_401(r: Any, assertion_message: str = default_message):
        assert r.status_code == 401, f"{assertion_message}: {r.status_code}"

    @staticmethod
    def check_status_code_415(r: Any, assertion_message: str = default_message):
        assert r.status_code == 415, f"{assertion_message}: {r.status_code}, {r.text}"

    @staticmethod
    def check_status_code_500(r: Any, assertion_message: str = default_message):
        assert r.status_code == 500, f"{assertion_message}: {r.status_code}"

    @staticmethod
    def check_key_in_collection(
        key: str, collection: CaseInsensitiveDict[str] | str, assertion_message: Optional[str] = None
    ):
        if not assertion_message:
            assertion_message = f"Ключ '{key}' отсутствует в коллекции {collection}"
        assert key in collection, assertion_message

    @staticmethod
    def check_key_not_in_collection(
        key: str, collection: CaseInsensitiveDict[str] | dict, assertion_message: Optional[str] = None
    ):
        if not assertion_message:
            assertion_message = f"Неожиданный Ключ '{key}' присутствует в коллекции {collection}"
        assert key not in collection, assertion_message

    @staticmethod
    def check_field_equals(field: Any, expected_value: Any, assertion_message: Optional[str] = None):
        if not assertion_message:
            assertion_message = f"Некорректное значение поля '{field}', ожидалось значение '{expected_value}'"
        assert field == expected_value, assertion_message

    @staticmethod
    def check_field_not_equals(field: str, expected_value: str | int, assertion_message: Optional[str] = None):
        if not assertion_message:
            assertion_message = f"Ожидалось, что значение поля '{field}' отлично от '{expected_value}'"
        assert field != expected_value, assertion_message

    @staticmethod
    def check_field_consist(field: Any, expected_value: Any, assertion_message: Optional[str] = None):
        """Проверка вхождения ожидаемого значения в состав значения полученного поля как его части"""
        if not assertion_message:
            assertion_message = (
                f"Некорректное значение поля '{field}', ожидалось что в нем содержится значение '{expected_value}'"
            )
        assert expected_value in field, assertion_message
