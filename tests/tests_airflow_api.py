"""airflow_client_unit_tests"""

import pytest


@pytest.mark.airflow
class TestDAGRun:

    def test_get_dags_list(self, airflow_client):
        """Получение списка DAGs: GET /dags"""

        # Act
        json = airflow_client.get_dags_list()

        # Check
        assert "dags" in json, "Ключ 'dags' отсутствует в ответе"
        assert isinstance(json["dags"], list), "DAGs должны быть списком"
        assert "total_entries" in json, "Нет информации о количестве DAG"

    def test_get_dag_by_id(self, airflow_client, test_dag_id):
        """Получение данных о DAG по ID: GET /dags/{dag_id}"""

        # Act
        json = airflow_client.get_dag_by_id(dag_id=f'/{test_dag_id}')

        # Check
        assert "dag_id" in json, "Ключ 'dag_id' отсутствует в ответе"
        assert json["dag_id"] == test_dag_id, "Значение ключа 'dag_id' не соответствует ожиданию"

    @pytest.mark.parametrize("is_paused, expected_status",
                             [(True, "ОСТАНОВЛЕН"), (False, "ЗАПУЩЕН")], ids=["paused", "unpaused"])
    def test_dag_control(self, airflow_client, test_dag_id, is_paused, expected_status):
        """Остановка/Запуск DAG: PATCH /dags/{dag_id} - "is_paused": true/false"""

        # Act
        json = airflow_client.dag_control(dag_id=test_dag_id, is_paused=is_paused)

        # Check
        assert "dag_id" in json, "Ключ 'dag_id' отсутствует в ответе"
        assert json["dag_id"] == test_dag_id, "Значение ключа 'dag_id' не соответствует ожиданию"
        assert "is_paused" in json, "Ответ не содержит is_paused"
        assert json["is_paused"] is is_paused, f"Ожидалось {expected_status}"
