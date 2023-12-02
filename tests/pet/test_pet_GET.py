from os import linesep

import pytest
import requests as r

from tests import change_handler


@pytest.mark.pet
@pytest.mark.GET
class TestCheckPetGET:
    """
    Тестовый класс группы хендлеров /pet
    """

    HANDLER = '/pet/findByStatus'
    METHOD = 'GET'
    TEARDOWN_IDS_POOl = 3

    @pytest.fixture(scope='class', name='data')
    def current_test_data(self, pet_data, faker):
        """
        Фикстура подготовки общих данных для выполнения этого класса тестов
        TEARDOWN_IDS_POOl: количество используемых этим классом тестов слотов для параметра `test_ids`
        Все тестовые сущности созданные в тестах как POST с `id` из `test_ids`
        будут автоматически очищены из базы при teardown
        :param pet_data: фикстура подготовки данных для выполнения тестовых классов группы хендлеров: /pet
        :param faker: фикстура подготовки случайных данных
        """
        return pet_data(self.TEARDOWN_IDS_POOl, self.HANDLER, self.METHOD, context='min')

    @pytest.mark.positive
    def test_pet_get_positive1(self, data):
        """
        Тест проверки запроса записей для группы хендлеров /pet:
            GET /<HANDLER>
            - запрос записей со всеми вариантами списочных параметров (Swagger.json)
            - параметры ответа (HTTP 200, JSON)
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        """
        match = {}
        query_data = data['query_data'].copy()
        post_query = query_data.copy()
        post_query['json'] = data['payload'].copy()

        for var_param in data['variables']:
            for test_id, var_value in enumerate(data['variables'][var_param]['enum']):
                query_data['params'] = f"{var_param}={var_value}"
                post_query['json']['id'] = data['test_ids'][test_id]
                post_query['json'][var_param] = var_value
                post_query['url'] = change_handler(query_data['url'])

                new_pet = r.post(**post_query)
                assert new_pet.status_code == 200

                res = r.get(**query_data)
                assert res.status_code == 200
                records = res.json()
                assert isinstance(records, list)
                assert len(records) >= 1

                for record in records:
                    if record['id'] == post_query['json']['id']:
                        match = record
                        break
                assert match, (
                    f"{linesep}В выдаче по критерию `{var_param}`: `{var_value}` "
                    f"не найдена созданная запись с `id`: {post_query['json']['id']}"
                )
                assert set(match) == set(new_pet.json())
                assert match[var_param] == var_value

    @pytest.mark.xfail
    @pytest.mark.negative
    def test_pet_get_null_negative1(self, data):
        """
        Тест проверки валидации данных при запросе записей для группы хендлеров /pet:
            GET /<HANDLER>
            - отсутствие обязательных параметров (Swagger.json)
            - параметры ответа (HTTP 400)
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        """
        query_data = data['query_data'].copy()

        res = r.get(**query_data)
        assert res.status_code == 400  # 400 # TODO #4 ожидается error code 400
        assert res.text == '[]'  # TODO #4 ожидается error message

    @pytest.mark.negative
    def test_pet_get_validate_negative2(self, data, faker):
        """
        Тест проверки валидации данных при запросе записей для группы хендлеров /pet:
            GET /<HANDLER>
            - валидация параметра `status`: array[string]
            - параметры ответа (HTTP 405)
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        :param faker: фикстура подготовки случайных данных
        """
        query_data = data['query_data'].copy()

        for var_param in data['variables']:
            for val in [faker.int(20), faker.fwords(nb=1, lang='en')]:
                query_data['params'] = f"{var_param}={val}"

                res = r.post(**query_data)
                assert res.status_code == 405
                result = res.json()
                assert len(result) == 2
                assert result['code'] == 405
                assert result['type'] == 'unknown'
