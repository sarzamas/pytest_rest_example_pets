"""airflow_steps"""
# pylint: disable=broad-exception-caught

import time
from abc import ABC, abstractmethod
from os import linesep

from requests import HTTPError

from libs import get_log
from libs.api.airflow.client import AirflowApiClient

LOG = get_log(__name__)


class StepsAirflow(ABC):
    """Класс выполнения шагов с API Airflow"""

    def __init__(self, client: AirflowApiClient, dag_id: str = None):
        self.client = client
        self.dag_id = dag_id
        self.wait_timeout: int = 300  # 5 минут
        self.check_interval: int = 10  # секунд

    @abstractmethod
    def execute_dagrun_pipeline(self, start_now: bool | None = False, logical_date: str | None = None):
        """
        Абстрактный метод для запуска DAG pipeline
        - Осуществляет полный цикл выполнения сценария с DAG:
            - Запуск DAG
            - Запуск DAG Run
            - Ожидание выполнения DAG Run (только для опции `start_now`)
            - ...
        - Обеспечивает гибкую логику запуска сценария

        :param start_now: Флаг немедленного запуска
        :param logical_date: Кастомное время для периода выполнения по расписанию
        """
        pass

    def wait_for_task_success(self, run_id: str, task_id: str, timeout: int = None) -> str:
        """
        Ожидание успешного выполнения задачи в DAG Run

        :param run_id: Идентификатор запуска DAG Run
        :param task_id: Идентификатор задачи
        :param timeout: Таймер ожидания выполнения задачи (секунды)
        :return: str состояние задачи после истечения таймера
        """
        state = "N/A"
        context = f'Task: "{task_id}" для DAG: "{self.dag_id}" '
        LOG.info(f'Ожидание завершения выполнения {context}')

        timeout = timeout if timeout else self.wait_timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time
            state = self.client.get_task_instance(self.dag_id, run_id, task_id)["state"]
            state = state.upper() if state else "N/A"
            LOG.info(f'Текущее состояние Task: "{state}" | Время ожидания: {elapsed:.0f} s | {context}')

            if state == "SUCCESS":
                LOG.debug(f'Выполнение Task успешно завершено за {elapsed:.1f} s | {context}')
                return state
            time.sleep(self.check_interval)

        LOG.debug(
            f'Текущее состояние Task: "{state}" | '
            f'{context}не завершилась успешно за отведенное время: {timeout} секунд'
        )
        return state

    def set_task_state_with_validation(self, run_id: str, task_id: str, state: str = "success") -> None:
        """
        Изменение состояния задачи с валидацией:
        - Получение enum возможных состояний задачи из SWAGGER (актуально для версии сервера Airflow 2.5+)
        - Получение списка всех задач в DAG Run
        - Проверка существования `task_id` целевой задачи в списке доступных в DAG Run
        - Изменение состояния для целевой задачи
        - Проверка успешности операции

        :param run_id: Идентификатор запуска DAG Run
        :param task_id: Идентификатор задачи
        :param state: Целевое состояние задачи
        :raises HTTPError: При ошибках связи с API
        :raises JSONDecodeError: При проблемах с JSON
        :raises ValueError: Если не найдена задача, неверно указано целевое состояние или состояние не установлено
        """
        # Получаем из кеша enum возможных состояний задач
        swagger_spec = self.client.get_swagger_spec()
        task_state_schema = swagger_spec.get("components", {}).get("schemas", {}).get("TaskState", {})
        allowed_states = task_state_schema.get("enum", [])

        if not allowed_states:
            raise ValueError(
                "Не удалось извлечь допустимые состояния задач из SWAGGER схемы | "
                f'Полученные данные:: {task_state_schema}'
            )
        # Валидируем аргумент при вызове метода
        if state not in allowed_states:
            raise ValueError(
                f'Недопустимое значение аргумента для состояния задачи "state": {state} '
                f'Допустимые значения: {", ".join(allowed_states)}'
            )
        # Получаем список всех задач в DAG Run
        tasks = self.client.get_dag_run_tasks(self.dag_id, run_id)
        available_tasks = [task["task_id"] for task in tasks]
        # Валидация имени задачи при вызове метода
        if task_id not in available_tasks:
            raise ValueError(
                f'Задача "{task_id}" не найдена в списке задач для DAG: "{self.dag_id}"{linesep}'
                f'Доступные задачи: {", ".join(available_tasks)}'
            )
        # Установка состояния задачи
        try:
            self.client.set_task_instance_state(
                dag_id=self.dag_id,
                run_id=run_id,
                task_id=task_id,
                state=state
            )
        except Exception as e:
            raise RuntimeError(
                f'Ошибка установки состояния "{state}" для задачи "{task_id}" в DAG: "{self.dag_id}"| {str(e)}'
            ) from e
        # Проверяем результат
        task_info = self.client.get_task_instance(
            dag_id=self.dag_id,
            run_id=run_id,
            task_id=task_id
        )

        if task_info.get("state") != state:
            raise ValueError(
                f'Состояние задачи "{task_id}" не изменилось на требуемое: "{state}" '
                f'Текущее состояние задачи в DAG "{self.dag_id}": {task_info.get("state")}'
            )

    def wait_for_dag_run_completion(self, run_id: str, timeout: int = None) -> None:
        """
        Ожидание завершения DAG Run с проверкой состояния и логированием времени выполнения

        :param run_id: Идентификатор запуска DAG Run
        :param timeout: Таймер ожидания выполнения DAG Run (секунды)
        """
        context = f'DAG Run: "{run_id}" для DAG: "{self.dag_id}" '
        LOG.info(f'Ожидание завершения выполнения {context}')

        timeout = timeout if timeout else self.wait_timeout
        start_time = time.time()
        while time.time() - start_time < timeout:
            elapsed = time.time() - start_time
            state = self.client.get_dag_run_state(self.dag_id, run_id)
            state = state.upper() if state else "N/A"
            LOG.info(f'Текущее состояние DAG Run: "{state}" | Время ожидания: {elapsed:.0f} s | {context}')

            if state == "SUCCESS":
                LOG.debug(f'Выполнение DAG Run успешно завершено за {elapsed:.1f} s | {context}')
                return
            elif state in {None, "FAILED", "UPSTREAM_FAILED"}:
                tasks = self.client.get_dag_run_tasks(self.dag_id, run_id)
                failed_tasks = [task for task in tasks if task["state"] in {None, "FAILED".lower()}]
                raise RuntimeError(
                    f'{context}завершился с ошибкой. Состояние выполнения: "{state}"{linesep}'
                    f'Проваленные задачи: {failed_tasks}'
                )

            time.sleep(self.check_interval)

        raise TimeoutError(f'{context}не завершился за отведенное время: {timeout} секунд')

    def safe_delete_dag_run(self, run_id: str, force: bool = False) -> dict:
        """
        Безопасное удаление DAG Run с проверкой состояния и обработкой ошибок

        :param run_id: Идентификатор запуска DAG Run
        :param force: Попытка принудительного удаления (в состоянии `running`)
        :return: dict: Результат операции
        """
        context = f'DAG Run: "{run_id}" для DAG: "{self.dag_id}" '
        log_prefix = "Результат попытки удаления DAG Run: "

        result = {
            "status": "pending".upper(),
            "deleted": False,
            "message": "",
        }
        LOG.info(f'Попытка удаления {context}')

        try:
            # Получаем состояние DAG Run
            current_state = self.client.get_dag_run_state(self.dag_id, run_id)

            # Проверка опасных состояний
            if current_state.lower() == "running" and not force:
                result.update({
                    "status": "warning".upper(),
                    "message": (
                        f'{context}в состоянии {current_state.upper()} '
                        "Удаление запрещено (используйте `force=True` для принудительного удаления)"
                    )
                })
                LOG.warning(f'{log_prefix}{result} ')
                return result

            # Выполняем удаление
            delete_success = self.client.delete_dag_run(self.dag_id, run_id)

            # Формируем результат
            if delete_success:
                result.update({
                    "status": "success".upper(),
                    "message": f'{context}успешно удален',
                    "deleted": True
                })
                LOG.debug(f'{log_prefix}{result} ')
            else:
                result.update({
                    "status": "error".upper(),
                    "message": f'Не удалось удалить {context}(неизвестная ошибка)'
                })
                LOG.error(f'{log_prefix}{result} ')

        except HTTPError as error_message:
            if "dagrun not found" in str(error_message).lower():
                result.update({
                    "status": "warning".upper(),
                    "message": f'{context}не существует'
                })
                LOG.warning(f'{log_prefix}{result} ')
            else:
                result.update({
                    "status": "error".upper(),
                    "message": f"Ошибка API сервера Airflow: {error_message}"
                })
                LOG.error(f'{log_prefix}{result} ')

        except Exception as e:
            result.update({
                "status": "error".upper(),
                "message": f'Непредвиденная ошибка: {str(e)}'
            })
            LOG.error(f'{log_prefix}{result} ')

        return result
