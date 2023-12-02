import pytest
import requests as r

from tests import change_handler


@pytest.mark.pet
@pytest.mark.POST
class TestCheckPetPOST:
    """
    Тестовый класс группы хендлеров /pet
    """

    HANDLER = '/pet'
    METHOD = 'POST'
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
        return pet_data(self.TEARDOWN_IDS_POOl, self.HANDLER, self.METHOD)

    @pytest.mark.positive
    def test_pet_post_max_positive1(self, data):
        """
        Тест проверки создания новой записи для группы хендлеров /pet:
            POST /<HANDLER>
            - создание записи с полным перечнем параметров
            - создание записи со всеми вариантами списочных параметров (Swagger.json)
            - параметры ответа (HTTP 200, JSON)
            - проверка идемпотентности
            - постпроверка параметров записи методом GET
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        """
        query_data = data['query_data'].copy()
        get_query = data['query_data'].copy()
        query_data['json'] = data['payload'].copy()

        for var_param in data['variables']:
            for test_id, var_value in enumerate(data['variables'][var_param]['enum']):
                query_data['json'][var_param] = var_value
                query_data['json']['id'] = data['test_ids'][test_id]
                get_query['url'] += f"/{query_data['json']['id']}"

                new_pet = r.post(**query_data)
                assert new_pet.status_code == 200
                assert new_pet.json() == query_data['json']

                twice_new_pet = r.post(**query_data)
                assert twice_new_pet.status_code == 200  # 400 TODO #2 - !!!нет идемпотентности у POST!!!

                check_result = r.get(**get_query)
                assert check_result.status_code == 200
                assert check_result.json() == query_data['json']

                get_query['url'] = change_handler(get_query['url'])

    @pytest.mark.positive
    def test_pet_post_min_positive2(self, data):
        """
        Тест проверки создания новой записи для группы хендлеров /pet:
            POST /<HANDLER>
            - создание записи с минимальным перечнем параметров (Swagger.json)
            - параметры ответа (HTTP 200, JSON)
            - постпроверка параметров записи методом DELETE
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        """
        query_data = data['query_data'].copy()
        query_data['json'] = {
            'name': data['payload']['name'],
            'photoUrls': data['payload']['photoUrls'],
        }

        new_pet = r.post(**query_data)
        assert new_pet.status_code == 200
        assert set(new_pet.json()) - set(query_data['json']) == {'id', 'tags'}

        query_data['url'] += f"/{new_pet.json()['id']}"
        query_data['json']['id'] = new_pet.json()['id']

        del_pet = r.delete(**query_data)
        assert del_pet.status_code == 200

    @pytest.mark.xfail
    @pytest.mark.negative
    def test_pet_post_null_negative1(self, data, faker):
        """
        Тест проверки валидации данных при создании новой записи для группы хендлеров /pet:
            POST /<HANDLER>
            - отсутствие обязательных параметров (Swagger.json)
            - параметры ответа (HTTP 400)
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        :param faker: фикстура подготовки случайных данных
        """
        query_data = data['query_data'].copy()
        query_data['json'] = []

        new_pet = r.post(**query_data)
        assert new_pet.status_code == 400  # 400 # TODO #3 !!! 500 !!!

    @pytest.mark.xfail
    @pytest.mark.negative
    def test_pet_post_validate_negative2(self, data, faker):
        """
        Тест проверки валидации данных при создании новой записи для группы хендлеров /pet:
            POST /<HANDLER>
            - валидация параметра `id`:	integer($int64)
            - параметры ответа (HTTP 400)
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        :param faker: фикстура подготовки случайных данных
        """
        query_data = data['query_data'].copy()
        query_data['json'] = data['payload'].copy()

        for _ in [faker.int(20), faker.fwords()]:
            query_data['json']['id'] = _

            new_pet = r.post(**query_data)
            assert new_pet.status_code == 400  # 400 # TODO #3 !!! 500 !!!

    @pytest.mark.negative
    def test_pet_post_url_negative3(self, data, faker):
        """
        Тест проверки валидации url при создании новой записи для группы хендлеров /pet:
            POST /<HANDLER>
            - валидация url
            - параметры ответа (HTTP 404, 415)
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        :param faker: фикстура подготовки случайных данных
        """
        query_data = data['query_data'].copy()
        query_data['json'] = data['payload'].copy()

        for _ in ['{@}', faker.int(20), faker.fwords(nb=1, lang='en')]:
            query_data['url'] += f"/{_}"

            res = r.post(**query_data)
            result = res.json()
            assert any([res.status_code == 404, res.status_code == 415])
            assert len(result) == 3 if res.status_code == 404 else len(result) == 2
            assert any([result['code'] == 404, result['code'] == 415])
            assert result['type'] == 'unknown'
