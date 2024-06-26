import json
from os import getenv, path

from Utils.DotDict import DotDict
from Utils.Singleton import Singleton

PROJECT_PATH = path.split(path.dirname(__file__))[0]
CONFIG_PATH = path.dirname(path.abspath(__file__))
LOG_PATH = path.join(PROJECT_PATH, '.log')

DEBUG = getenv('DEBUG', 'false').lower() not in ('false', '0')  # булевый флаг


class Config(DotDict, metaclass=Singleton):
    """
    Класс экземпляра конфигурации (Singleton)
    """

    def __init__(self):
        config_path = path.join(CONFIG_PATH, 'config.json')
        local_config_path = path.join(CONFIG_PATH, 'config.local.json')
        self.config_path = _ if path.exists(_ := local_config_path) else config_path
        config_data = self.read_config(self.config_path)
        super().__init__(DotDict(config_data))

        self._host = self.rest_config.host
        self._api_key = self.rest_config.api_key
        self._username = self.rest_config.user.username
        self._password = self.rest_config.user.password

    @property
    def host(self) -> DotDict:
        """
        Свойство возвращает элемент словаря с данными удаленного хоста
        :return: DotDict
        """
        return self._host

    @property
    def api_key(self) -> str:
        """
        Свойство возвращает элемент словаря с данными api_key
        :return: str
        """
        return self._api_key

    @property
    def username(self) -> DotDict:
        """
        Свойство возвращает элемент словаря с именем учетной записи пользователя на удаленном хосте
        :return: DotDict
        """
        return self._username

    @username.setter
    def username(self, value: str):
        self._username = value

    @property
    def password(self) -> DotDict:
        """
        Свойство возвращает элемент словаря с паролем к имени учетной записи пользователя на удаленном хосте
        :return: DotDict
        """
        return self._password

    @password.setter
    def password(self, value: str):
        self._password = value

    @staticmethod
    def read_config(config_path: str) -> dict:
        """
        Метод чтения файла конфигурации
        :param config_path: - путь до файла конфигурации
        :return: - json
        """
        with open(config_path, encoding="utf-8") as file:
            config_data = json.load(file)
        return config_data

    def rewrite_config(self):
        """
        Перезаписывает содержимое текущего экземпляра Config в json файл, определяющий Config
        """
        with open(self.config_path, 'w', encoding="utf-8") as file:
            file.write(json.dumps(self))
