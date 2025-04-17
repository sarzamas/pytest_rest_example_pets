"""airflow_api_client"""
# pylint: disable=possibly-unused-variable


from datetime import datetime, UTC

from airflow_client.client import ApiClient
from airflow_client.client.api.dag_api import DAGApi
from airflow_client.client.api.dag_run_api import DAGRunApi
from airflow_client.client.api.task_instance_api import TaskInstanceApi
from airflow_client.client.model.dag import DAG
from airflow_client.client.model.dag_run import DAGRun
from airflow_client.client.model.task_instance_collection import TaskInstanceCollection
from airflow_client.client.model.task_instance_reference import TaskInstanceReference
from airflow_client.client.model.update_task_instance import UpdateTaskInstance

from libs.api.airflow.api_config import AirflowConfig
from libs.api.airflow.decorators import handle_api_errors, log_method_args
from libs.api.airflow.helpers import get_method_name, log_and_raise, make_text_ansi_name, process_kwargs_timeout
from libs.api.airflow.rest_client import CustomRESTClient
from libs.logging import get_log

LOG = get_log(__name__)


class AirflowAPIClient(ApiClient):
    """
    Бизнес-логика работы с API

    SWAGGER:
        https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html
        https://airflow-forge.apps.qa.kryptodev.ru/api/v1/ui/
    """
    DEFAULT_TASK_STATE = "success"
    ALLOWED_TASK_STATES = {
        "success",
        "failed",
        "running",
        "up_for_retry",
        "up_for_reschedule",
        "queued",
        "skipped",
        "scheduled",
    }

    # (Airflow v2.4+)
    DEFAULT_ORDER_BY = "logical_date"
    ALLOWED_ORDER_BY_FIELDS = {
        "dag_id",
        "data_interval_start",
        "data_interval_end",
        "logical_date",
        "start_date",
        "end_date",
        "state",
        "run_id",
        "external_trigger",
        "conf",
    }

    # (Airflow API < v2.4)
    DEFAULT_ORDER_BY = "execution_date"
    ALLOWED_ORDER_BY_FIELDS = {
        "execution_date",
        "start_date",
        "end_date",
        "state",
        "dag_id",
        "run_id",
    }

    def __init__(self, configuration: AirflowConfig = None, **kwargs):
        super().__init__(configuration=configuration, **kwargs)
        self.dag_api = DAGApi(self)
        self.dag_run_api = DAGRunApi(self)
        self.task_instance_api = TaskInstanceApi(self)

        self._retries = self.configuration.retries
        self._debug = self.configuration.debug
        # Кастомные свойства API
        self.rest_client = CustomRESTClient(configuration)
        self._request_timeout = configuration.request_timeout
        self.user_agent = configuration.custom_user_agent or None
        _ = configuration.log_server_api_version and self.rest_client.log_server_api_version()
        if self._debug:
            instance = self.__class__.__name__
            LOG.debug(f'Инициализирован экземпляр: "{make_text_ansi_name(self.__class__.__name__)}" (ID: {id(self)})')
            LOG.debug(f'Timeouts: "{instance}._request_timeout::Default": {self._request_timeout}')
            LOG.debug(f'Retries: "{instance}._retries::Default": {self._retries}')
            LOG.debug(f'Кастомные заголовки экземпляра: "{instance}.headers::Custom": {self.default_headers}')
            LOG.debug(f'Кастомные заголовки конфигурации: "{instance}.Configuration.custom_headers": '
                      f'{configuration.default_headers}')
            LOG.debug(f'Конфигурация: "{instance}.Configuration": {self.configuration.__dict__}')

    @property
    def debug(self) -> bool:
        """Доступ к флагу отладки"""
        return self._debug

    @property
    def request_timeout(self) -> tuple[int, int]:
        """Доступ к таймерам запросов к API"""
        return self._request_timeout

    # ------------------------- DAG Methods -------------------------
    @log_method_args()
    @handle_api_errors
    def get_dags(
            self,
            limit: int | None = 1000,
            offset: int | None = 0,
            order_by: str | None = "dag_id",
            **kwargs: dict[str, str] | tuple[int, int] | bool | None
    ) -> dict[str, any] | None:
        """
        Получить список DAGs с пагинацией упорядоченных по DAG ID

        :param limit: Максимальное количество DAG для получения
        :param offset: Смещение для пагинации
        :param order_by: Поле для сортировки
        :param kwargs: Словарь с дополнительными параметрами (см. Документацию базового метода)
        :return: Словарь с информацией о DAGs
        """
        kwargs = process_kwargs_timeout(getattr(self, get_method_name(self)), locals())

        response = self.dag_api.get_dags(**kwargs)

        return response.to_dict()

    @log_method_args()
    @handle_api_errors
    def get_dag_by_id(
            self,
            dag_id: str,
            **kwargs: dict[str, str] | tuple[int, int] | None
    ) -> dict[str, any] | None:
        """
        Получить DAG по его ID

        :param dag_id: Идентификатор DAG
        :param kwargs: Словарь с дополнительными параметрами (см. Документацию базового метода)
        :return: Словарь с информацией о DAG
        """
        kwargs = process_kwargs_timeout(getattr(self, get_method_name(self)), locals())

        response = self.dag_api.get_dag(**kwargs)

        return response.to_dict()

    @log_method_args()
    @handle_api_errors
    def patch_dag(
            self,
            dag_id: str,
            is_paused: bool,
            **kwargs: dict[str, str] | tuple[int, int] | bool | None
    ) -> dict | None:
        """
        Приостанавливает или возобновляет DAG (`is_paused`)

        :param dag_id: Идентификатор DAG
        :param is_paused: Флаг приостановки (Ex: True - приостановить, False - возобновить).
        :param kwargs: Словарь с дополнительными параметрами (см. Документацию базового метода)
        :return: Обновленный DAG в виде словаря
        """
        # Подготавливаем маску полей для целевого метода
        dag = DAG(is_paused=is_paused)
        update_mask = ["is_paused"]

        kwargs = process_kwargs_timeout(getattr(self, get_method_name(self)), locals())

        # Извлекаем избыточные для целевого метода аргументы
        kwargs.pop("is_paused")

        response = self.dag_api.patch_dag(**kwargs)

        return response.to_dict()

    # -------------------------- DAG Runs ---------------------------
    @log_method_args()
    @handle_api_errors
    def get_dag_runs(
            self,
            dag_id: str,
            limit: int | None = 1000,
            offset: int | None = 0,
            order_by: str | None = DEFAULT_ORDER_BY,
            **kwargs: dict[str, str] | tuple[int, int] | bool | None
    ) -> dict | None:
        """
        Получает список запусков DAG (DAG runs) для указанного DAG

        :param dag_id: Идентификатор DAG
        :param limit: Максимальное количество запусков для получения
        :param offset: Смещение для пагинации
        :param order_by: Поле для сортировки
        :param kwargs: Дополнительные параметры (см. Документацию базового метода)
        :return: Словарь с информацией о запусках DAG Runs
        """
        if order_by not in self.ALLOWED_ORDER_BY_FIELDS:
            log_and_raise(
                ValueError,
                f'Invalid "order_by": "{order_by}". Allowed values: "{self.ALLOWED_ORDER_BY_FIELDS}"',
                logger_name=self.__class__.__name__,
                log_level="error",
            )

        kwargs = process_kwargs_timeout(getattr(self, get_method_name(self)), locals())

        response = self.dag_run_api.get_dag_runs(**kwargs)

        return response.to_dict()

    @log_method_args()
    @handle_api_errors
    def trigger_dag_run(
            self,
            dag_id: str,
            conf: dict | None = None,
            execution_date: str | None = None,
            **kwargs: dict[str, str] | tuple[int, int] | bool | None
    ) -> dict[str, any] | None:
        """
        Запуск DAG Run

        :param dag_id: Идентификатор DAG
        :param conf: Дополнительные параметры конфигурации
        :param execution_date: Дата выполнения
        :param kwargs: Словарь с дополнительными параметрами (см. Документацию базового метода)
        :return: Словарь с информацией о DAG Run
        """
        dag_run_obj = DAGRun(
            dag_run_id=f'autotest__{datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S")}',
            conf=conf,
            execution_date=execution_date,
        )

        response = self.dag_run_api.post_dag_run(
            dag_id=dag_id,
            dag_run=dag_run_obj,
            **kwargs
        )

        return response.to_dict()

    # ------------------------ Task Methods -------------------------
    @log_method_args()
    @handle_api_errors
    def get_tasks_in_dag_run(
            self,
            dag_id: str,
            dag_run_id: str,
            **kwargs: dict[str, str] | tuple[int, int] | bool | None
    ) -> dict[str, any] | None:
        """
        Получить список задач в DAG Run (Airflow v2.10+)

        :param dag_id: Идентификатор DAG
        :param dag_run_id: Идентификатор DAG Run
        :param kwargs: Словарь с дополнительными параметрами (см. Документацию базового метода)
        :return: Словарь с информацией о DAG Run Tasks
        """
        response: TaskInstanceCollection = self.task_instance_api.get_task_instances(
            dag_id=dag_id,
            dag_run_id=dag_run_id,
            **kwargs
        )

        return response.to_dict()

    @log_method_args()
    @handle_api_errors
    def set_task_state(
            self,
            dag_id: str,
            task_id: str,
            execution_date: str,
            new_state: str = DEFAULT_TASK_STATE
    ) -> dict[str, any] | None:
        """Изменить состояние задачи (Airflow v2.10+)

        :param dag_id: Идентификатор DAG
        :param task_id: Идентификатор задачи
        :param execution_date: Дата выполнения задачи
        :param new_state: Новое состояние задачи
        :return: Словарь с информацией о DAG Run Task
        """
        if new_state not in self.ALLOWED_TASK_STATES:
            log_and_raise(
                ValueError,
                f'Invalid "new_state": "{new_state}". Allowed states: {self.ALLOWED_TASK_STATES}',
                logger_name=self.__class__.__name__,
                log_level="error",
            )

        update_body = UpdateTaskInstance(new_state=new_state, dry_run=False)

        response: TaskInstanceReference = self.task_instance_api.patch_task_instance(
            dag_id=dag_id,
            dag_run_id=execution_date,  # TODO Verify: execution_date is used as dag_run_id
            task_id=task_id,
            update_task_instance=update_body,
        )

        return response.to_dict()
