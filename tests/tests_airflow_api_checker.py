"""airflow_client_unit_tests"""

import pytest

from libs.api.airflow.checker import Checker


@pytest.mark.airflow
class TestDAGRun:

    def test_get_dags_list(self, api_client):
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
        resp = api_client.get(url=url)
        # Check
        dags = Checker.validate_response_json(
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
        assert "dags" in dags, "Ключ 'dags' отсутствует в ответе"
        assert isinstance(dags["dags"], list), "DAGs должны быть списком"
        assert "total_entries" in dags, "Нет информации о количестве DAG"

        print(Checker.get_value(resp.json(), key_path="total_entries"))
        print(Checker.get_value(resp.json(), key_path="dags.[0].is_paused", unique=True))
        print(Checker.get_value(resp.json(), key_path="dags.[*].is_paused", unique=True))
        print(Checker.get_value(resp.json(), key_path="dags.[0].owners.[*]", unique=True))
        print(Checker.get_value(resp.json(), key_path="dags.[*].owners.[0]", unique=True))
        print(Checker.get_value(resp.json(), key_path="dags.[*].owners.[*]"))
        print(Checker.get_value(resp.json(), key_path="dags.[*].owners.[*]", unique=True))
        print(Checker.get_value(resp.json(), key_path="dags.[*].tags.[*].name", unique=True))

    def test_get_dag_by_id(self, api_client, test_dag_id):
        """
        Получение данных о DAG по ID: GET /dags/{dag_id}
        Ex:
            curl -k --user 'api-user:api-user' -X GET \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags/person_hdfs_s3 \
            -H 'Content-Type: application/json'
        """
        # Arrange
        url = f'/////dags/////{test_dag_id}'  # проверка на нормализацию `/` в url - OK!
        # Act
        resp = api_client.get(url=url)
        # Check
        dag = Checker.validate_response_json(
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
        assert "dag_id" in dag, "Ключ 'dag_id' отсутствует в ответе"
        assert dag["dag_id"] == test_dag_id, "Значение ключа 'dag_id' не соответствует ожиданию"

        print(Checker.get_value(resp.json(), key_path="dag_id"))
        print(Checker.get_value(resp.json(), key_path="is_paused"))
        print(Checker.get_value(resp.json(), key_path="tags.[*].name", unique=True))
        # Проверка на несуществующий ключ - Path Error!
        print(Checker.get_value(resp.json(), key_path="total_entries"))  # ключа нет - None!
        print(Checker.get_value(resp.json(), key_path="dags.[0].is_paused", unique=True))  # ключа нет - None!

    @pytest.mark.parametrize("is_paused, expected_status",
                             [(True, "ОСТАНОВЛЕН"), (False, "ЗАПУЩЕН")], ids=["ОСТАНОВКА DAG", "ЗАПУСК DAG"])
    def test_dag_control(self, api_client, test_dag_id, is_paused, expected_status):
        """
        Остановка/Запуск DAG: PATCH /dags/{dag_id}
        Ex:
            curl -k --user 'api-user:api-user' -X PATCH \
            https://airflow-forge.apps.qa.kryptodev.ru/api/v1/dags/person_hdfs_s3?update_mask=is_paused \
            -H 'Content-Type: application/json' \
            -d '{
                "is_paused": true/false
            }'
        """
        # Arrange
        url = f'dags/{test_dag_id}'
        params = {"update_mask": "is_paused"}
        payload = {"is_paused": is_paused}
        # Act
        resp = api_client.patch_dag(url=url, params=params, data=payload)
        # Check
        dag = Checker.validate_response_json(
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
        assert "dag_id" in dag, "Ключ 'dag_id' отсутствует в ответе"
        assert dag["dag_id"] == test_dag_id, "Значение ключа 'dag_id' не соответствует ожиданию"
        assert "is_paused" in dag, "Ответ не содержит is_paused"
        assert dag["is_paused"] is is_paused, f'Ожидалось что DAG должен быть {expected_status}'

        print(Checker.get_value(resp.json(), key_path="dag_id"))
        print(Checker.get_value(resp.json(), key_path="is_paused"))
        print(Checker.get_value(resp.json(), key_path="is_paused.[*]"))
        print(Checker.get_value(resp.json(), key_path="dags.[0].is_paused", unique=True))
        print(Checker.get_value(resp.json(), key_path="is_paused.[*]", unique=True))
