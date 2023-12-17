from datetime import datetime
from os import linesep
from typing import Callable

import pytest
import requests as r
from validators import hostname as valid_hostname
from validators import url as valid_url

from Config import Config
from Helpers.RequestsHelper import TestTimeout
from tests import change_handler
from Utils.RandomData import RandomData


@pytest.fixture(scope='session', name='test_data')
def preconditions_teardown(config: Config, faker: RandomData) -> Callable:
    """
    Фикстура выполняет следующие действия:
    preconditions:
        - Создает тестовые данные/объекты
        - Возвращает текущие тестовые данные/объекты тестовому классу
    teardown:
        - Очищает созданные тестами сущности
    :param config: Config: фикстура инициализации config
    :param faker: RandomData: фикстура подготовки случайных данных
    :return: Callable: параметризованную функцию, которая может быть вызвана в теле теста или другой фикстуры
    """
    teardown_params = []
    query_data = {}

    def _preconditions_teardown(pool, handler, method) -> dict:
        api_key = config.api_key
        host = config.host

        base_url = f"{host.schema}://{host.name}:{_}" if (_ := host.port) else f"{host.schema}://{host.name}"
        resource = f"v{_}/swagger.json" if (_ := host.version) else '/swagger.json'

        headers = {
            'Content-type': 'application/json; charset=utf-8',
            'Accept': 'application/json',
            'api_key': _ if (_ := api_key) else None,
        }
        query_data['url'] = f'{base_url}/{resource}'
        query_data['headers'] = headers
        query_data['timeout'] = TestTimeout()

        now = datetime.now().strftime('%H:%M:%S')
        prefix = f"URL неверен: проверьте данные в config{linesep}Time: {now}"

        swagger = r.get(**query_data) if valid_hostname(host.name) and valid_url(query_data['url']) else None

        if not swagger or swagger.status_code != 200:
            raise ConnectionError(
                f"SWAGGER_{prefix}{linesep}{swagger.text}{linesep}{swagger.request.method} "
                f"{swagger.status_code} {swagger.url}{linesep}{query_data}{linesep}{swagger.request.headers}"
                if swagger
                else f"{prefix}{linesep}{query_data}"
            )
        print(f"{linesep}Time: {now}{linesep}Swagger version: {swagger.json()['swagger']} - OK!")
        meta = swagger.json()['paths'][handler][method.lower()]
        query_data['url'] = change_handler(query_data['url'], handler)

        test_ids = []
        for _ in range(pool):
            test_ids.append(faker.int())

        teardown_params.append(test_ids)

        return {
            'meta': meta,
            'query_data': query_data,
            'test_ids': test_ids,
        }

    yield _preconditions_teardown

    teardown_params = [_ for __ in teardown_params for _ in __]

    print(
        f"{linesep}Список идентификаторов тестовых сущностей `test_ids`, подлежащих удалению при `teardown`:{linesep}"
        if teardown_params
        else linesep
    )

    for param in teardown_params:
        print(f"\t`{param}`")
        query_data['url'] += f"/{param}"

        res = r.delete(**query_data)
        assert any([res.status_code == 200, res.status_code == 404])
        res = r.get(**query_data)
        assert res.status_code == 404
        assert res.json()['message'] == 'Pet not found' or 'null for uri' in res.json()['message']


@pytest.fixture(scope='session')
def config() -> Config:
    """
    Фикстура инициализации Config с возможностью пробросить параметры из строки команды запуска pytest
    :return: экземпляр (Singleton) DotDict словаря с конфигурационными данными
    """
    return Config()


@pytest.fixture(scope='session')
def faker() -> RandomData:
    """
    Фикстура инициализации генератора случайных данных
    :return: экземпляр RandomData (Singleton)
    """
    return RandomData()

def pytest_emoji_passed(config):
    return "✅ ", "PASSED 🍪 "


def pytest_emoji_failed(config):
    return "❌ ", "FAILED 😿 "


def pytest_emoji_skipped(config):
    return "✂️ ", "SKIPPED 🙈 "


def pytest_emoji_error(config):
    return "⁉️ ", "ERROR 💩 "


def pytest_emoji_xfailed(config):
    return "⚠️ ", "XFAIL 🤓 "


def pytest_emoji_xpassed(config):
    return "❎ ", "XPASS 😜 "
