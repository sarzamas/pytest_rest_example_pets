"""airflow_api_client_config"""

import re
from os import getenv
from urllib.parse import urlparse

from airflow_client.client import Configuration
from simple_settings import settings as cfg
from str2bool import str2bool

from libs import get_log
from libs.api.airflow.utils import log_and_raise

LOG = get_log(__name__)


class AirflowConfig(Configuration):
    """Кастомная Конфигурация клиента API Airflow"""

    def __init__(
            self,
            host: str = None,
            url: str = "api/v1",
            custom_headers: dict[str, any] | None = None,
            log_server_api_version: bool = False,
            **kwargs
    ):
        self.request_timeout: tuple[int, int] = (
                kwargs.pop("request_timeout", None) or (cfg.REQUEST_TIMEOUT_CONN, cfg.REQUEST_TIMEOUT_READ,) or None
        )
        super().__init__(host=self._process_host_url(host, url), **kwargs)
        self.debug: bool = str2bool(getenv("DEBUG", "False"))
        self.verify_ssl: bool = cfg.SSL_VERIFY
        self.assert_hostname: str = cfg.AIRFLOW_HOST
        self.retries: int = cfg.REQUEST_RETRY_COUNT
        self.default_headers: dict = {"Accept": "application/json", "Cache-Control": "no-cache"}
        self.custom_headers = custom_headers if custom_headers is not None else {}
        self.custom_user_agent: str | None = None
        self.log_server_api_version: bool = log_server_api_version
        # переопределяем логирование по умолчанию для библиотеки на кастомное
        get_log("urllib3")

    @property
    def request_timeout(self) -> tuple[int, int]:
        """
        Таймауты для HTTP-запросов.
        :return: Кортеж (connect_timeout, read_timeout) в секундах.
        """
        return self._request_timeout

    @request_timeout.setter
    def request_timeout(self, value: tuple[int, int]):
        if not value:
            return  # Будет назначено в common_config.py
        elif isinstance(value, tuple) and len(value) == 2:
            if all(not elem for elem in value):
                self._request_timeout = None  # Будет назначено в CustomRESTClient
                return
            elif all(isinstance(num, int) and num > 0 for num in value):
                self._request_timeout = value
                return

        log_and_raise(
            error_type=ValueError,
            message="`request_timeout` must be a tuple of two positive integers: (connect_timeout, read_timeout)",
            invalid_value=value,
            allowed_format="(int > 0, int > 0)",
            logger_name=self.__class__.__name__,
            log_level="error",
        )

    @staticmethod
    def _process_host_url(host_name: str, url: str) -> str:
        """
        Валидация и нормализация параметров запросов: `schema`, `host` и `url`
            - используется доменная адресация
        Варианты подстановки `AIRFLOW_HOST`:
            - [schema] domain
        Варианты подстановки `AIRFLOW_BASE_URL`:
            - path (only)
            - schema domain path (full url)
        :param host_name: `AIRFLOW_HOST`
        :param url: `AIRFLOW_BASE_URL`
        :returns: schema: (https only) + domain: host + path: (url partial)
        """
        host = host_name.strip() if isinstance(host_name, str) else ""
        url = url.strip() if isinstance(url, str) else ""
        if not host and not url:
            log_and_raise(
                ValueError,
                "Не задано ни `AIRFLOW_HOST`, ни `AIRFLOW_BASE_URL` :",
                logger_name=__class__.__name__,
                log_level="error",
            )

        if not host.startswith(("http",)):
            host = "https://" + host

        modified_host = host.replace("http:", "https:")
        if modified_host != host:
            LOG.debug(f'Замена протокола: http→https | "{host}" → "{modified_host}"')

        schema, domain, path, *_ = urlparse(modified_host)
        schema_, domain_, path_, *_ = urlparse(url)
        if schema_ and domain_ != domain:
            log_and_raise(
                ValueError,
                f'Несовпадение доменов в записи `HOST` и `URL`: "{domain}" != "{domain_}" :',
                logger_name=__class__.__name__,
                log_level="error",
            )

        if path_.split("/")[0] == domain:
            path_ = "/".join(path_.split("/")[1:])

        if domain and path not in ("", "/"):
            log_and_raise(
                ValueError,
                f'`AIRFLOW_HOST` содержит путь после имени домена: "{host_name}" :',
                logger_name=__class__.__name__,
                log_level="error",
            )

        if not schema or not re.match(r"^([a-z0-9-]+\.)*[a-z0-9-]+\.[a-z]{2,}$", domain.lower()):
            log_and_raise(
                ValueError,
                f'`AIRFLOW_HOST` содержит недопустимый домен: "{host_name}" :',
                logger_name=__class__.__name__,
                log_level="error",
            )

        return f'{schema}://{domain.rstrip("/")}/{path_.strip("/")}'
