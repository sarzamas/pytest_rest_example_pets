"""conftest_airflow"""
# pylint: disable=unused-import, redefined-outer-name

from collections.abc import Iterator

import pytest
from libs.api.airflow.api_client import AirflowAPIClient
from libs.api.airflow.api_config import AirflowConfig
from simple_settings import settings as cfg

from libs import get_log
from .pytest_hook import *

LOG = get_log(__name__)


@pytest.fixture(scope="session")
def airflow_api_config() -> AirflowConfig:
    """
    Создаёт конфигурацию для создания клиента Airflow
        Позволяет добавить:
        - данные подключения к серверу AirFlow
        - заголовок `User-Agent` в запросах
        - кастомные заголовки в запросы
        - получение в логе версии API Backend Airflow
        - Default HTTP Request Timeouts (если None - будут взяты из common_config.py)
    """
    config = AirflowConfig(
        host=cfg.AIRFLOW_HOST,
        url=cfg.AIRFLOW_BASE_URL,
        username=cfg.AIRFLOW_USER,
        password=cfg.AIRFLOW_PASSWORD,
    )
    config.custom_user_agent = "OpenAPI-Generator/2.6.0/python"
    config.custom_headers = {}
    config.request_timeout = None
    config.log_server_api_version = True
    return config


@pytest.fixture(scope="session", name="api_client")
def airflow_api_session(airflow_api_config: AirflowConfig) -> Iterator[AirflowAPIClient]:
    """Фикстура для создания авторизованной сессии для AirflowAPIClient"""
    session = AirflowAPIClient(configuration=airflow_api_config)
    yield session
    session.close()


@pytest.fixture(scope="session")
def test_dag_id() -> str:
    """Тестовый DAG в Airflow"""
    return cfg.TEST_DAG_ID


@pytest.fixture(scope="class")
def test_dag_run(api_client, test_dag_id, data_collector) -> dict[str, any]:
    """Создаем DAG Run для тестов и фиксируем время"""
    dag_run = api_client.trigger_dag_run(test_dag_id)

    # Записываем метаданные в коллектор
    data_collector.data.update({
        'dag_run_id': dag_run['dag_run_id'],
        'execution_date': dag_run['execution_date']
    })

    return dag_run
