from collections import namedtuple
from uuid import UUID

import pytest


class DataCollector:
    """Класс для парсинга респонсов и хранения в себе информации фильтруя ее по атрибутам класса"""

    _data_dict = {}
    cookie = None
    auth_code = None
    code_verifier = None
    code_challenge = None
    access_token = None
    expires_in = None
    refresh_token = None
    workplaces_id: UUID = None

    def __init__(self, response_json: dict = None):
        """
        :param response_json: Тело ответа от сервера в формате json/dict
        """
        self.__dict__ = self._data_dict
        if isinstance(response_json, dict):
            for key, value in response_json.items():
                if key in DataCollector.__dict__:
                    self._data_dict[key] = value

    @classmethod
    def reset_atr(cls):
        """Сброс значений атрибутов класса"""
        for key, value in list(cls._data_dict.items()):
            del cls._data_dict[key]

    def __repr__(self):
        return "\n".join([f"{key}: {value}" for key, value in self.__dict__.items()])
