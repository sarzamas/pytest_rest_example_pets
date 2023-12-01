from typing import Callable

import pytest

from tests import change_handler

swagger_missing_info = {  # TODO #1 - добавить в Swagger.json эти параметры для HANDLER: /pet METHOD: POST
    'parameters': [{
        'name': 'status',
        'items': {
            'default': 'available',
            'enum': ['available', 'pending', 'sold'],
            'type': 'string',
        },
    }],
}


@pytest.fixture(scope='class', name='pet_data')
def class_test_data(test_data, faker) -> Callable:
    """
    Фикстура подготовки общих данных для выполнения класса тестов
    TEARDOWN_IDS_POOl: количество используемых этим классом тестов слотов для параметра 'test_ids'
    Все тестовые сущности созданные в тестах как POST с `id` из 'test_ids'
    будут автоматически очищены из базы при teardown
    :param test_data: базовая фикстура подготовки данных для выполнения всех тестовых классов
    :param faker: фикстура подготовки случайных данных
    """

    def _class_test_data(pool, handler, method, context='max') -> Callable:
        class_test_data = test_data(pool, handler, method)

        _url = class_test_data['query_data']['url']
        class_test_data['query_data']['url'] = change_handler(_url) if '/{' in handler else _url

        if 'items' in class_test_data['meta']['parameters'][0].keys():
            swagger_var_params = class_test_data['meta']['parameters']
        elif handler == '/pet' and method == 'POST':  # TODO #1 убрать после решения
            swagger_var_params = swagger_missing_info['parameters']
        else:
            swagger_var_params = []

        var_params = {}
        if swagger_var_params:
            for param in swagger_var_params:
                var_params[param['name']] = param['items']

            count = len([enum for param in var_params for enum in var_params[param]['enum']])
            assert pool >= count, (
                f'Необходимо установить число выделяемых слотов (сейчас это {pool}) '
                f'для идентификаторов создаваемых тестом сущностей не меньшим числа возможных вариантов: {count} '
                f'значений параметра(ов) {var_params.keys()} в текущей версии SWAGGER'
            )

        class_test_data['variables'] = var_params if var_params else None

        context_min = {
            'name': faker.fwords(),
            'photoUrls': [
                f'https://img.freepik.com/free-photo/{_}.jpg'
                for _ in faker.fwords(lang='en', capitalize=False, nb=faker.int(length=1)).split()
            ],
        }

        context_max = {
            'category': {
                'id': faker.int(length=4),
                'name': faker.fwords(nb=1),
            },
            'tags': [{
                'id': faker.int(length=3),
                'name': f'#{_}',
            }
                for _ in faker.fwords(nb=faker.int(length=1)).split()
            ],
        }

        if context == 'min':
            class_test_data['payload'] = context_min
        if context == 'max':
            class_test_data['payload'] = context_min | context_max

        return class_test_data

    return _class_test_data
