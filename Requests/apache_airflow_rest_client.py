"""airflow_rest_client"""

import json
from os import linesep

from airflow_client.client.rest import RESTClientObject, RESTResponse

from libs import get_log
from libs.api.airflow.api_config import AirflowConfig
from libs.api.airflow.decorators import handle_api_errors
from libs.api.airflow.helpers import make_text_ansi_name

LOG = get_log(__name__)


class CustomRESTClient(RESTClientObject):
    """
    Кастомный REST-клиент для работы с Airflow API

    Расширяет стандартный RESTClientObject из airflow-client, добавляя:
    - Кастомные таймауты запроса
    - Объединение системных и пользовательских заголовков
    - Логирование параметров запроса

    Args:
        configuration: Конфигурация клиента из airflow-client

    Attributes:
        _request_timeout: Таймауты запроса в формате (connect timeout, read timeout)
        default: Дефолтные заголовки запроса
    """

    def __init__(self, configuration: AirflowConfig):
        super().__init__(configuration)
        self.configuration: AirflowConfig = configuration
        self.debug: bool = configuration.debug
        self.base_url: str = configuration.host + "/"
        self._request_timeout: tuple[int, int] = configuration.request_timeout or (30, 60)
        self.default: dict = {
            "_preload_content": False,
        }

    def request(self, method: str, url: str, headers: dict | None = None, **kwargs) -> RESTResponse:
        merged_headers = {**self.configuration.default_headers, **(headers or {})}
        kwargs["_request_timeout"] = kwargs.pop("_request_timeout", None) or self._request_timeout

        LOG.debug(
            f'Timeouts|Retries - Default: {self._request_timeout}; Used: {kwargs["_request_timeout"]}; '
            f'(retries): {self.configuration.retries}'
        )
        LOG.debug(f'Отправляемые заголовки: {merged_headers}')

        return super().request(method, url, headers=merged_headers, **kwargs)

    @handle_api_errors
    def log_server_api_version(self) -> None:
        """Получает и логирует метаданные о версии сервера Airflow."""
        health = self.GET(self.base_url + "health", **self.default)
        version = self.GET(self.base_url + "version", **self.default)
        version_data = json.loads(version.data)

        LOG.debug(
            f'Airflow BackEnd: {{"API version": "{make_text_ansi_name(version_data["version"])}", '
            f'"GIT version": "{make_text_ansi_name(version_data["git_version"])}"}}')
        LOG.debug(f'Health: {json.loads(health.data)}{linesep if not self.debug else None}')
