"""airflow_api_client"""

from datetime import datetime, timezone
from functools import lru_cache
from os import linesep
from typing import Any
from urllib.parse import urljoin

import requests
from requests import HTTPError, JSONDecodeError, Response
from simple_settings import settings as cfg

from libs import get_log

LOG = get_log(__name__)


class AirflowApiClient:
    """airflow_api_client"""

    def __init__(self):
        self.base_url = cfg.AIRFLOW_BASE_URL.rstrip("/") + "/"
        self.session = requests.Session()
        self.session.auth = cfg.AIRFLOW_AUTH_CREDENTIALS
        self.session.verify = cfg.SSL_VERIFY
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        }
        self.session.headers.update(headers)

    def _request(
            self,
            method: str,
            endpoint: str,
            params: dict[str, Any] | None = None,
            json: dict | list | None = None,
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
        LOG.debug(f'Send Request | {log_info} ')

        return self.session.request(
            method=method,
            url=url,
            params=params,
            json=json,
        )

    def close(self) -> None:
        """Закрытие сессии (очистка соединений)"""
        self.session.close()

    # --------------------------- Response checker ----------------------------

    @staticmethod
    def retrieve_response_json(response: Response) -> dict | list:
        """
        Выполняет базовые проверки ответа API:
            - Проверяет соответствие статус-кода ответа значению из диапазона 200-399
            - Парсит ответ в JSON (или возвращает пустой словарь для HTTP 204 "NO CONTENT")
            - Гарантирует, что JSON не пустой (кроме HTTP 204)
        Возвращает JSON-объект или исключение с детализацией ошибки

        :param response: Объект HTTP-ответа
        :return: JSON-объект
        :raises HTTPError: При ошибках статус-кода ответа
        :raises JSONDecodeError: При ошибках парсинга JSON
        :raises ValueError: При пустом или невалидном JSON (кроме HTTP 204)
        """
        # Проверка статус-кода
        if not response.ok:
            raise HTTPError(
                f'Получен неуспешный код ответа HTTP {response.status_code} | '
                f'URL: {response.url}{linesep}Response: {response.text}'
            )

        # Обработка случая HTTP 204
        if response.reason.upper() == "NO CONTENT":
            return {}

        # Парсинг JSON
        try:
            json_data = response.json()
        except JSONDecodeError as e:
            raise JSONDecodeError(f'Не удалось распарсить JSON: {e}{linesep}Response: {response.text}') from e

        # Проверка непустого содержимого JSON
        if not (isinstance(json_data, (dict, list)) and json_data):
            raise ValueError(
                f'Недопустимый формат ответа: ожидался непустой словарь (dict) или список (list) | '
                f'Получен тип: {type(json_data).__name__}, содержимое: {json_data}'
            )

        return json_data

    # ------------------------- SWAGGER scheme cache --------------------------

    @lru_cache(maxsize=1)
    def get_swagger_spec(self) -> dict:
        """
        Получение SWAGGER схемы API Airflow
        - SWAGGER доступен по эндпоинту сервера `/api/v1/openapi.json`
        - SWAGGER схема кэшируется на время жизни клиента

        :return: Полная схема OpenAPI
        :raises Exception: Пробрасывает исключения из `retrieve_response_json()`
        """
        response = self._request("GET", "openapi.json")
        return self.retrieve_response_json(response)

    # ------------------------- Методы примитивы API --------------------------

    def get_dags_list(self) -> dict:
        """
        Получение списка DAGs: GET /dags

        Документация:
            https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/get_dags

        Ex:
            curl -k --user 'api-user:api-user' -X GET \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags \
            -H 'Content-Type: application/json'

        :return: dict - JSON-объект из Response
        """
        # Arrange
        endpoint = "dags"
        # Act
        LOG.info(f'Получение списка DAGs | endpoint: {endpoint}')
        response = self._request("GET", endpoint)
        # Check
        return self.retrieve_response_json(response)

    def get_dag_by_id(self, dag_id: str) -> dict:
        """
        Получение данных о DAG по ID: GET /dags/{dag_id}

        Документация:
            https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/get_dag

        Ex:
            curl -k --user 'api-user:api-user' -X GET \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags/person_hdfs_s3 \
            -H 'Content-Type: application/json'

        :param dag_id: Имя DAG
        :return: dict - JSON-объект из Response
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

        Документация:
            https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/patch_dags

        Ex:
            curl -k --user 'api-user:api-user' -X PATCH \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags/person_hdfs_s3?update_mask=is_paused \
            -H 'Content-Type: application/json' \
            -d '{"is_paused": true}'

        :param dag_id: Имя DAG
        :param is_paused: Флаг приостановки / запуска работы DAG
            Ex:
                is_paused=True работа DAG приостановлена
                is_paused=False работа DAG возобновлена
        :return: dict - JSON-объект из Response
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

    def trigger_dag_run(self, dag_id: str, logical_date: str) -> dict:
        """
        Запуск DAG Run: POST /dags/{dag_id}/dagRuns
            - с автоматической генерацией DAG RunID с `timestamp.now` в формате Airflow UI

        Документация:
            https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/post_dag_run

        :param dag_id: Имя DAG
        :param logical_date: Временной период для обработки данных DAG Run (в формате ISO 8601)
            Требования:
            - Формат: "YYYY-MM-DDTHH:MM:SS.mmmZ"
            - Часовой пояс: UTC (обозначается суффиксом 'Z')
            - Другие часовые пояса кроме UTC не принимаются сервером

        :return: dict - JSON-объект из Response
        """
        # Arrange
        endpoint = f'dags/{dag_id}/dagRuns'
        run_id = f'autotest__{datetime.now(timezone.utc).isoformat(timespec="microseconds")}'
        payload = {
            "dag_run_id": run_id,
            "logical_date": logical_date,
            "conf": {}
        }
        # Act
        LOG.info(f'Запуск DAG Run для DAG ID с DAG RunID: "{run_id}" | endpoint: {endpoint}')
        response = self._request("POST", endpoint, json=payload)
        # Check
        return self.retrieve_response_json(response)

    def get_dag_run_state(self, dag_id: str, run_id: str) -> str:
        """
        Получение статуса DAG Run: GET /dags/{dag_id}/dagRuns/{dag_run_id}

        Документация:
            https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/get_dag_run

        :param dag_id: Имя DAG
        :param run_id: Идентификатор запуска DAG Run
        :return: str - текущее состояние DAG Run
        """
        # Arrange
        endpoint = f'dags/{dag_id}/dagRuns/{run_id}'
        # Act
        LOG.debug(f'Проверка состояния DAG Run для DAG ID по DAG RunID | endpoint: {endpoint}')
        response = self._request("GET", endpoint)
        # Check
        return self.retrieve_response_json(response)["state"]

    def delete_dag_run(self, dag_id: str, run_id: str) -> bool:
        """
        Удаление DAG Run: POST /dags/{dag_id}/dagRuns/{dag_run_id}

        Документация:
            https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/delete_dag_run

        :param dag_id: Имя DAG
        :param run_id: Идентификатор запуска DAG Run
        :return: bool - при (не)успешном  удалении (HTTP 204 `NO CONTENT`)
        :raises HTTPError: при ошибках API
        """
        # Arrange
        endpoint = f'dags/{dag_id}/dagRuns/{run_id}'
        # Act
        LOG.info(f'Удаление DAG Run для DAG ID по DAG RunID | endpoint: {endpoint} ')
        response = self._request("DELETE", endpoint)
        # Check
        return True if not self.retrieve_response_json(response) else False

    def get_dag_tasks(self, dag_id: str) -> list[str]:
        """
        Получение списка ИМЕН задач DAG: GET /dags/{dag_id}/tasks
         - Без привязки к DAG Run
         - Возвращает плоский список идентификаторов задач в формате:
            ["task_1", "task_2", ...]

        Документация:
            https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/get_tasks

        :param dag_id: Имя DAG
        :return: list - Список `task_id` из DAG
        """
        # Arrange
        endpoint = f"dags/{dag_id}/tasks"
        # Act
        LOG.debug(f'Получение списка задач для DAG по DAG ID | endpoint: {endpoint}')
        response = self._request("GET", endpoint)
        # Check
        response_data = self.retrieve_response_json(response)
        # Извлекаем только task_id из каждой задачи
        return [task["task_id"] for task in response_data.get("tasks", [])]

    def get_dag_run_tasks(self, dag_id: str, run_id: str) -> list[dict]:
        """
        Получение списка задач DAG Run: GET /dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances
         - Для конкретного DAG Run

        Документация:
            https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/get_task_instances

        :param dag_id: Имя DAG
        :param run_id: Идентификатор запуска DAG Run
        :return: list - JSON-объект из Response
        """
        # Arrange
        endpoint = f'dags/{dag_id}/dagRuns/{run_id}/taskInstances'
        # Act
        LOG.info(f'Получение списка задач DAG Run для DAG ID по DAG RunID | endpoint: {endpoint}')
        response = self._request("GET", endpoint)
        # Check
        return self.retrieve_response_json(response).get("task_instances", [])

    def get_task_instance(self, dag_id: str, run_id: str, task_id: str) -> dict:
        """
        Получение информации о задаче в DAG Run: GET /dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}

        Документация:
            https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/get_task_instance

        :param dag_id: Имя DAG
        :param run_id: Идентификатор запуска DAG Run
        :param task_id: Идентификатор таски
        :return: dict - JSON-объект из Response
        """
        # Arrange
        endpoint = f"dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}"
        # Act
        LOG.debug(f'Получение состояния задачи "{task_id}" в DAG Run для DAG ID | endpoint: {endpoint}')
        response = self._request("GET", endpoint)
        # Check
        return self.retrieve_response_json(response)

    def set_task_instance_state(self, dag_id: str, run_id: str, task_id: str, state: str = "success") -> dict:
        """
        Изменение состояния задачи в DAG Run: PATCH /dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}

        Документация:
            https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html#operation/patch_task_instance

        :param dag_id: Имя DAG
        :param run_id: Идентификатор запуска DAG Run
        :param task_id: Идентификатор таски
        :param state: Новый статус (по умолчанию "success")
        :return: dict - JSON-объект из Response
        """
        # Arrange
        endpoint = f"dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}"
        payload = {"new_state": state}
        # Act
        LOG.info(f'Изменение состояния задачи "{task_id}" на {state} в DAG Run для DAG ID | endpoint: {endpoint}')
        response = self._request("PATCH", endpoint, json=payload)
        # Check
        return self.retrieve_response_json(response)
