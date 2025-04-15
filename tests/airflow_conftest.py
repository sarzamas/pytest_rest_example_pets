"""airflow_client_conftest"""

from collections.abc import Iterator

import pytest
from simple_settings import settings as cfg

from libs.api.airflow.client import AirflowApiClient


@pytest.fixture(scope="session", name="airflow_client")
def airflow_api_session() -> Iterator[AirflowApiClient]:
    """Сессия REST-клиента airflow"""
    session = AirflowApiClient()

    yield session

    session.close()


@pytest.fixture(scope="session")
def test_dag_id() -> str:
    """Тестовый DAG в Airflow"""
    return cfg.TEST_DAG_ID
