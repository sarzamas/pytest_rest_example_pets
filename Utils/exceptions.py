"""exceptions"""

from libs import get_log

LOG = get_log(__name__)


class DataSerializationError(Exception):
    """Базовое исключение для ошибок сериализации данных"""

    def __init__(self, message: str, **kwargs):
        self.details = kwargs
        super().__init__(message)

    def __str__(self):
        details = ", ".join(f'{k}={v}' for k, v in self.details.items())
        return f'{self.args[0]} ({details})'


class FileSaveError(DataSerializationError):
    """Ошибка записи данных в файл"""

    def __init__(self, message: str, filename: str, **kwargs):
        super().__init__(message, filename=filename, **kwargs)
        self.filename = filename


class ServiceUnavailableError(Exception):
    """Исключение для ошибок подключения к API"""

    def __init__(self, message: str, url: str = "Unknown", reason: str = "No details"):
        self.url = url
        self.reason = reason
        super().__init__(message)

    def __str__(self):
        return f"{self.args[0]} | URL: {self.url} | Reason: {self.reason}"
