# pylint: disable=E0601, disable=wildcard-import, unused-wildcard-import

from common_config import *

ENV = "qa"

SSL_VERIFY = False

# airflow
AIRFLOW_HOST = AIRFLOW_HOST.format(env=ENV)
TEST_DAG_ID = "person_hdfs_s3"
