from typing import Callable

import pytest

from Utils import lookup_report
from tests import change_handler

swagger_missing_info = {  # TODO #1 - добавить в Swagger.json эти параметры для HANDLER: /pet METHOD: POST
    "parameters": [
        {
            "name": "status",
            "items": {
                "default": "available",
                "enum": ["available", "pending", "sold"],
                "type": "string",
            },
        }
    ]
}


@pytest.fixture(scope='class', name='pet_data')
def swagger_data(test_data, faker) -> Callable:
    """
    Фикстура подготовки общих данных для выполнения класса тестов
    Тестовые сущности, созданные в тестах с использованием слотов из `test_ids` будут автоматически удалены при Teardown
        teardown_pool: количество слотов, необходимых вызывающему классу тестов для параметра `test_ids`
    :param test_data: базовая фикстура подготовки данных для выполнения всех тестовых классов
    :param faker: фикстура подготовки случайных данных
    """

    def _swagger_data(teardown_pool, handler, method, context='max') -> Callable:
        swagger_data = test_data(teardown_pool, handler, method)

        _url = swagger_data['query_data']['url']
        swagger_data['query_data']['url'] = change_handler(_url) if '/{' in handler else _url

        if 'items' in swagger_data['meta']['parameters'][0].keys():
            swagger_var_params = swagger_data['meta']['parameters']
        elif handler == '/pet' and method == 'POST':  # TODO #1 убрать после решения
            swagger_var_params = swagger_missing_info['parameters']
        else:
            swagger_var_params = []

        var_params = {}
        if swagger_var_params:
            for param in swagger_var_params:
                var_params[param['name']] = param['items']

            count = len([enum for param in var_params for enum in var_params[param]['enum']])
            assert teardown_pool >= count, (
                f"Необходимо установить число выделяемых слотов (сейчас это {teardown_pool}) "
                f"для идентификаторов создаваемых тестом сущностей не меньшим числа возможных вариантов: {count} "
                f"значений параметра(ов) {var_params.keys()} в текущей версии SWAGGER{lookup_report()}"
            )

        swagger_data['variables'] = _ if (_ := var_params) else None

        context_min = {
            'name': faker.fwords(),
            'photoUrls': [
                f"https://img.freepik.com/free-photo/{_}.jpg"
                for _ in faker.fwords(lang='en', capitalize=False, nb=faker.int(length=1)).split()
            ],
        }

        context_max = {
            'category': {
                'id': faker.int(length=4),
                'name': faker.fwords(nb=1),
            },
            'tags': [
                {
                    'id': faker.int(length=3),
                    'name': f'#{_}',
                }
                for _ in faker.fwords(nb=faker.int(length=1)).split()
            ],
        }

        if context == 'min':
            swagger_data['payload'] = context_min
        if context == 'max':
            swagger_data['payload'] = context_min | context_max

        return swagger_data

    return _swagger_data
