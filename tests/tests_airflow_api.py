"""airflow_client_unit_tests"""

import pytest

from libs.api.airflow.checker import Checker


@pytest.mark.airflow
class TestDAGRun:

    def test_get_dags_list(self, airflow_client):
        """
        Получение списка DAGs: GET /dags
        Ex:
            curl -k --user 'api-user:api-user' -X GET \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags \
            -H 'Content-Type: application/json'
        """
        # Arrange
        url = "dags"
        # Act
        resp = airflow_client.get(url=url)
        # Check
        Checker.validate_response_json(
            resp,
            required_keys=[
                "dags.[*].dag_id",
                "dags.[*].tags.[*].name",
                "dags.[*].schedule_interval.value",
                "dags.[*].is_paused",
                "dags.[*].owners.[*]",
                "total_entries",
            ],
            key_types={
                "dags.[*].dag_id": str,
                "dags.[*].tags.[*].name": str,
                "dags.[*].schedule_interval.value": str,
                "dags.[*].is_paused": bool,
                "total_entries": int,
                "dags.[*].owners": list,
                "dags.[0].owners": list,
                "dags.[*].owners.[0]": str,
                "dags.[*].owners.[*]": str,
                "dags.[0].owners.[0]": str,
                "dags.[0].owners.[*]": str,
                # Проверка на неправильный тип данных - Type Error!
                # "dags.[*].owners[0]": str,  # неверный синтаксис - OK!
                # "dags.[*].owners.[:]": str,  # неверный синтаксис - OK!
            },
        )
        print(Checker.get_value(resp.json(), key_path="total_entries"))
        print(Checker.get_value(resp.json(), key_path="dags.[0].is_paused", unique=True))
        print(Checker.get_value(resp.json(), key_path="dags.[*].is_paused", unique=True))
        print(Checker.get_value(resp.json(), key_path="dags.[0].owners.[*]", unique=True))
        print(Checker.get_value(resp.json(), key_path="dags.[*].owners.[0]", unique=True))
        print(Checker.get_value(resp.json(), key_path="dags.[*].owners.[*]"))
        print(Checker.get_value(resp.json(), key_path="dags.[*].owners.[*]", unique=True))
        print(Checker.get_value(resp.json(), key_path="dags.[*].tags.[*].name", unique=True))

    def test_get_dag_by_id(self, airflow_client):
        """
        Получение данных о DAG по ID: GET /dags/{dag_id}
        Ex:
            curl -k --user 'api-user:api-user' -X GET \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags/person_hdfs_s3 \
            -H 'Content-Type: application/json'
        """
        # Arrange
        url = "/////dags/////person_hdfs_s3"  # проверка на нормализацию `/` в url - OK!
        # Act
        resp = airflow_client.get(url=url)
        # Check
        Checker.validate_response_json(
            resp,
            required_keys=[
                "dag_id",
                "tags.[*].name",
                "schedule_interval.value",
                "is_paused",
                "owners.[*]",
                # Проверка на несуществующий ключ - Path Error!
                # "total_entries",  # ключа нет - OK!
            ],
            key_types={
                "dag_id": str,
                "tags.[*].name": str,
                "schedule_interval.value": str,
                "is_paused": bool,
                "owners": list,
                "owners.[0]": str,
                # Проверка на несуществующий тип в несуществующем ключе - Path Error!
                # "total_entries": int,  # ключа нет - OK!

            },
        )
        print(Checker.get_value(resp.json(), key_path="dag_id"))
        print(Checker.get_value(resp.json(), key_path="is_paused"))
        print(Checker.get_value(resp.json(), key_path="tags.[*].name", unique=True))
        # Проверка на несуществующий ключ - Path Error!
        print(Checker.get_value(resp.json(), key_path="total_entries"))  # ключа нет - None!
        print(Checker.get_value(resp.json(), key_path="dags.[0].is_paused", unique=True))  # ключа нет - None!

    def test_patch_dag_paused(self, airflow_client):
        """
        Остановка DAG: PATCH /dags/{dag_id}
        Ex:
            curl -k --user 'api-user:api-user' -X PATCH \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags/person_hdfs_s3?update_mask=is_paused \
            -H 'Content-Type: application/json' \
            -d '{
                "is_paused": true
            }'
        """
        # Arrange
        url = "dags/person_hdfs_s3"
        params = {"update_mask": "is_paused"}
        payload = {"is_paused": True}
        # Act
        resp = airflow_client.patch(url=url, params=params, data=payload)
        # Check
        Checker.validate_response_json(
            resp,
            required_keys=[
                "dag_id",
                "is_paused",
            ],
            key_types={
                "dag_id": str,
                "is_paused": bool,
            },
        )
        print(Checker.get_value(resp.json(), key_path="dag_id"))
        print(Checker.get_value(resp.json(), key_path="is_paused"))
        print(Checker.get_value(resp.json(), key_path="dags.[0].is_paused", unique=True))

    def test_patch_dag_un_paused(self, airflow_client):
        """
        Запуск DAG: PATCH /dags/{dag_id}
        Ex:
            curl -k --user 'api-user:api-user' -X PATCH \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags/person_hdfs_s3?update_mask=is_paused \
            -H 'Content-Type: application/json' \
            -d '{
                "is_paused": false
            }'
        """
        # Arrange
        url = "dags/person_hdfs_s3"
        params = {"update_mask": "is_paused"}
        payload = {"is_paused": False}
        # Act
        resp = airflow_client.patch(url=url, params=params, data=payload)
        # Check
        Checker.validate_response_json(
            resp,
            required_keys=[
                "dag_id",
                "is_paused",
            ],
            key_types={
                "dag_id": str,
                "is_paused": bool,
            },
        )
        print(Checker.get_value(resp.json(), key_path="dag_id"))
        print(Checker.get_value(resp.json(), key_path="is_paused"))
        print(Checker.get_value(resp.json(), key_path="is_paused.[*]"))
        print(Checker.get_value(resp.json(), key_path="is_paused.[*]", unique=True))
