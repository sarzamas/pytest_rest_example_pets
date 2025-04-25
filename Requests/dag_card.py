"""pipeline_person_inc_s3"""

from libs import get_log
from libs.api.airflow import resolve_logical_date
from libs.api.airflow.client import AirflowApiClient
from libs.api.airflow.steps_airflow import StepsAirflow

LOG = get_log(__name__)


class DagCard(StepsAirflow):
    """Класс исполнения pipeline для DAG_ID"""

    DAG_ID: str = "dag_1"

    def __init__(self, client: AirflowApiClient):
        super().__init__(client, self.DAG_ID)
        self.tasks = self.client.get_dag_tasks(self.dag_id)
        LOG.info(f'Список задач для DAG: "{self.dag_id}" | {self.tasks}')

    def execute_dagrun_pipeline(self, start_now: bool | None = False, logical_date: str | None = None) -> None:
        """Полный цикл выполнения pipeline для DAG_ID"""
        self.client.dag_control(self.dag_id)
        logical_date = resolve_logical_date(start_now, logical_date)
        run_id = self.client.trigger_dag_run(self.dag_id, logical_date)["dag_run_id"]
        if start_now:
            self.set_task_state_with_validation(run_id, self.tasks.pop(0))
            while self.tasks:  # Пока список не пуст
                current_task = self.tasks.pop(0)  # Удаляем задачу из начала списка
                self.wait_for_task_success(run_id, current_task)
            self.wait_for_dag_run_completion(run_id)
            # self.safe_delete_dag_run(run_id)
