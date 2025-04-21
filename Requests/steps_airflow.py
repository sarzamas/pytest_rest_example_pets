"""airflow_steps"""

import logging
import time
from datetime import datetime, timedelta, timezone
from os import linesep
from zoneinfo import ZoneInfo

from requests import HTTPError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from libs.api.airflow.client import AirflowApiClient
from libs.api.airflow.helpers import create_retry_logger


class DAGNotActiveError(Exception):
    """Исключение при неудачной активации DAG"""


class StepsAirflow:
    """Класс выполнения шагов с API Airflow"""

    def __init__(self, client: AirflowApiClient):
        self._activation_attempted = None
        self.client = client
        self.wait_timeout = 300  # 5 минут
        self.check_interval = 10  # секунд

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(1),
        retry=retry_if_exception_type((DAGNotActiveError, HTTPError, TimeoutError)),
        # retry=retry_if_exception(
        #    lambda e: isinstance(e, (DAGNotActiveError, HTTPError)) or "connection lost" in str(e)
        # ),
        before_sleep=create_retry_logger(logging.WARNING),  # использование кастомного логгера для retry в helpers.py
        # before_sleep=before_sleep_log(logger, logging.DEBUG, exc_info=True),  # Добавит полный traceback в логи
        reraise=True
    )
    def ensure_dag_enabled(self, dag_id: str) -> None:
        """
        Гарантирует, что указанный DAG запущен
            - корректно информирует о причине ошибки

        :param dag_id: Идентификатор DAG
        :raises DAGNotActiveError: Если запуск DAG не удался
        """
        try:
            # Идемпотентный вызов активации (is_paused=False)
            dag_status = self.client.dag_control(dag_id)
            if dag_status.get("is_paused", True):
                raise DAGNotActiveError(f'Ошибка API сервера Airflow: DAG "{dag_id}" не активирован')

        except Exception as e:
            raise DAGNotActiveError(
                f'Ошибка конфигурации при активации DAG: "{dag_id}" | '
                f'Тип: {type(e).__name__} | '
                f'Детали: {e}'
            ) from e

    def trigger_dag_with_future_date(self, dag_id: str) -> str:
        """
        Запуск DAG Run с завтрашней датой в ISO формате с timezone UTC

        :param dag_id: Идентификатор DAG
        :return: Идентификатор запущенного DAG Run
        """
        # Получаем текущее время в Москве
        local_time = datetime.now(ZoneInfo("Europe/Moscow"))
        # Конвертируем в UTC
        utc_time = local_time.astimezone(timezone.utc)
        # Добавляем 1 день и форматируем
        logical_date = (utc_time + timedelta(days=1)).isoformat(timespec='milliseconds')

        response = self.client.trigger_dag_run(dag_id, logical_date)
        return response["dag_run_id"]

    def wait_for_dag_run_completion(self, dag_id: str, dag_run_id: str) -> None:
        """
        Ожидание завершения DAG Run с проверкой статуса

        :param dag_id: Идентификатор DAG
        :param dag_run_id: Идентификатор запуска DAG Run
        """
        start_time = time.time()

        while time.time() - start_time < self.wait_timeout:
            status = self.client.get_dag_run_status(dag_id, dag_run_id)

            if status == "success":
                return
            elif status in ("failed", "upstream_failed"):
                tasks = self.client.get_dag_run_tasks(dag_id, dag_run_id)
                failed_tasks = [task for task in tasks if task["state"] == "failed"]
                raise RuntimeError(
                    f'DAG: {dag_id} | DAG Run "{dag_run_id}" завершился с ошибкой. Статус: "{status}"{linesep}'
                    f"Проваленные задачи: {failed_tasks}"
                )

            time.sleep(self.check_interval)

        raise TimeoutError(
            f'DAG: {dag_id} | DAG Run "{dag_run_id}" не завершился за отведенное время: {self.wait_timeout} секунд'
        )

    def execute_dagrun_pipeline(self, dag_id: str) -> None:
        """
        Полный цикл выполнения DAG

        :param dag_id: Идентификатор DAG для выполнения
        """
        self.ensure_dag_enabled(dag_id)
        dag_run_id = self.trigger_dag_with_future_date(dag_id)
        self.wait_for_dag_run_completion(dag_id, dag_run_id)
