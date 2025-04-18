"""airflow_api_client"""

import time
from os import linesep
from typing import Any
from urllib.parse import urljoin

import requests
from requests import HTTPError, JSONDecodeError, Response
from requests.adapters import HTTPAdapter
from simple_settings import settings as cfg
from urllib3 import Retry

from libs import get_log

LOG = get_log(__name__)


def with_validation(expected_status=200, validate_json=True):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            response = func(self, *args, **kwargs)
            json = self.check_response_json(
                response,
                status_code=expected_status,
                validate_json=validate_json,
            )
            return json if validate_json else response

        return wrapper

    return decorator


class AirflowApiClient:
    """airflow_api_client"""

    def __init__(self, default_headers: dict = None, **kwargs):
        self.base_url = cfg.AIRFLOW_BASE_URL.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.auth = cfg.AIRFLOW_AUTH_CREDENTIALS
        self.session.verify = cfg.SSL_VERIFY
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }
        if default_headers:
            headers.update(default_headers)
        self.session.headers.update(headers)
        self.timeout = (
            getattr(cfg, "REQUEST_TIMEOUT_CONN", 10),
            getattr(cfg, "REQUEST_TIMEOUT_READ", 20),
        )
        self.retry = Retry(total=getattr(cfg, "REQUEST_RETRY_COUNT", 2))
        # Сессия с адаптерами переиспользует соединения, что ускоряет запросы при Retry
        adapter = HTTPAdapter(max_retries=self.retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _request(
            self,
            method: str,
            endpoint: str,
            params: dict[str, Any] | None = None,
            data: dict | str | bytes | None = None,
            json: dict | list | None = None,
            **kwargs: Any
    ) -> Response:
        """Базовый запрос с логированием"""
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        log_info = {
            "method": method,
            "url": url,
        }
        if params is not None:
            log_info["params"] = params
        if json is not None:
            log_info["json"] = json
        if data is not None:
            log_info["data"] = "<binary data>" if isinstance(data, (bytes, bytearray)) else data
        LOG.debug(f'Send Request | {log_info}')

        start_time = time.monotonic()
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            data=data,
            json=json,
            timeout=self.timeout,
            **kwargs
        )
        duration = time.monotonic() - start_time

        LOG.debug(f'Response Status: HTTP{response.status_code} | Duration: {duration:.2f}s')
        return response

    def close(self) -> None:
        """Закрытие сессии (очистка соединений)"""
        self.session.close()

    # --------------------------- Response checker ----------------------------

    @staticmethod
    def retrieve_response_json(response: Response) -> dict | list:
        """
        Выполняет базовые проверки ответа API:
            - Проверяет соответствие статус-кода ответа значению из диапазона 200-399
            - Парсит ответ в JSON
            - Гарантирует, что JSON не пустой (dict/list с элементами)
        Возвращает JSON-объект или исключение с детализацией ошибки

        :param response: Объект HTTP-ответа
        :return: JSON-объект
        :raises HTTPError: При ошибках статус-кода ответа
        :raises JSONDecodeError: При ошибках парсинга JSON
        :raises ValueError: При пустом или невалидном JSON
        """
        # Проверка статус-кода
        if not response.ok:
            raise HTTPError(
                f'Получен неуспешный код ответа HTTP{response.status_code} | '
                f'URL: {response.url}{linesep}Response: {response.text}'
            )
        # Парсинг JSON
        try:
            json_data = response.json()
        except JSONDecodeError as e:
            raise JSONDecodeError(f'Не удалось распарсить JSON: {e}') from e

        # Проверка непустого содержимого JSON
        if not (isinstance(json_data, (dict, list)) and json_data):
            raise ValueError(
                f'Недопустимый формат ответа: ожидался непустой словарь (dict) или список (list) | '
                f'Получен тип: {type(json_data).__name__}, содержимое: {json_data}'
            )

        return json_data

    # ---------------------------- Методы обертки -----------------------------

    def get_dags_list(self) -> dict:
        """
        Получение списка DAGs: GET /dags
        Ex:
            curl -k --user 'api-user:api-user' -X GET \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags \
            -H 'Content-Type: application/json'

        :return:  dict - JSON-объект из Response
        """
        # Arrange
        endpoint = "dags"
        # Act
        LOG.info(f'Получение списка DAGs  | endpoint: {endpoint}')
        response = self._request("GET", endpoint)
        # Check
        return self.retrieve_response_json(response)

    def get_dag_by_id(self, dag_id: str) -> dict:
        """
        Получение данных о DAG по ID: GET /dags/{dag_id}
        Ex:
            curl -k --user 'api-user:api-user' -X GET \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags/person_hdfs_s3 \
            -H 'Content-Type: application/json'

        :param dag_id: имя DAG
        :return:  dict - JSON-объект из Response
        """
        # Arrange
        endpoint = f'dags/{dag_id}'
        # Act
        LOG.info(f'Получение данных о DAG по ID | endpoint: {endpoint}')
        response = self._request("GET", endpoint)
        # Check
        return self.retrieve_response_json(response)

    def dag_control(self, dag_id: str, is_paused: bool = False) -> dict:
        """
        Остановка/Запуск DAG по ID: PATCH /dags/{dag_id}
        Ex:
            curl -k --user 'api-user:api-user' -X PATCH \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags/person_hdfs_s3?update_mask=is_paused \
            -H 'Content-Type: application/json' \
            -d '{"is_paused": true}'

        :param dag_id: имя DAG
        :param is_paused: флаг приостановки / запуска работы DAG
            Ex:
                is_paused=True работа DAG приостановлена
                is_paused=False работа DAG возобновлена
        :return:  dict - JSON-объект из Response
        """
        # Arrange
        endpoint = f'dags/{dag_id}'
        params = {"update_mask": "is_paused"}
        payload = {"is_paused": is_paused}
        prefix = "Остановка" if is_paused else "Запуск"
        # Act
        LOG.info(f'{prefix} DAG по ID | endpoint: {endpoint}')
        response = self._request("PATCH", endpoint, params=params, json=payload)
        # Check
        return self.retrieve_response_json(response)
