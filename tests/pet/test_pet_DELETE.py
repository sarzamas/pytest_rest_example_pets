import pytest
import requests as r


@pytest.mark.pet
@pytest.mark.DELETE
class TestCheckPetDELETE:
    """
    Тестовый класс группы хендлеров /pet
    """

    HANDLER = '/pet/{petId}'
    METHOD = 'DELETE'
    TEARDOWN_IDS_POOl = 2

    @pytest.fixture(scope='class', name='data')
    def current_test_data(self, pet_data):
        """
        Фикстура подготовки общих данных для выполнения этого класса тестов
        TEARDOWN_IDS_POOl: количество используемых этим классом тестов слотов для параметра `test_ids`
        Все тестовые сущности созданные в тестах как POST с `id` из `test_ids`
        будут автоматически очищены из базы при teardown
        :param pet_data: фикстура подготовки данных для выполнения тестовых классов группы хендлеров: /pet
        """
        return pet_data(self.TEARDOWN_IDS_POOl, self.HANDLER, self.METHOD, context="min")

    @pytest.mark.positive
    def test_pet_delete_positive1(self, data):
        """
        Тест проверки удаления записи для группы хендлеров /pet:
            DELETE /<HANDLER>
            - удаление записи (Swagger.json)
            - параметры ответа (HTTP 200, JSON)
            - проверка идемпотентности DELETE
            - параметры ответа (HTTP 404)
            - проверка переиспользования `id` для создания после удаления
            - параметры ответа (HTTP 200, JSON)
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        """
        query_data = data['query_data'].copy()
        post_query = query_data.copy()
        post_query['json'] = data['payload'].copy()

        post_query['json']['id'] = data['test_ids'][0]

        new_pet = r.post(**post_query)

        query_data['url'] += f"/{new_pet.json()['id']}"
        res = r.delete(**query_data)
        assert res.status_code == 200
        result = res.json()
        assert len(result) == 3
        assert result['code'] == 200
        assert result['type'] == 'unknown'
        assert result['message'] == str(new_pet.json()['id'])

        twice_del = r.delete(**query_data)
        assert twice_del.status_code == 404
        assert twice_del.reason == 'Not Found'
        assert not twice_del.text

        twice_new_pet = r.post(**post_query)
        assert twice_new_pet.status_code == 200

    @pytest.mark.negative
    def test_pet_delete_null_negative1(self, data):
        """
        Тест проверки валидации данных при удалении записи для группы хендлеров /pet:
            DELETE /<HANDLER>
            - отсутствие обязательных параметров (Swagger.json)
            - параметры ответа (HTTP 405)
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        """
        query_data = data['query_data'].copy()

        res = r.delete(**query_data)
        assert res.status_code == 405
        result = res.json()
        assert len(result) == 2
        assert result['code'] == 405
        assert result['type'] == 'unknown'

    @pytest.mark.xfail
    @pytest.mark.negative
    def test_pet_delete_validate_negative2(self, data, faker):
        """
        Тест проверки валидации данных при запросе записей для группы хендлеров /pet:
            DELETE /<HANDLER>
            - валидация параметра `api_key`: string
            - параметры ответа (HTTP 403)
        :param data: фикстура подготовки тестовых данных для этого класса тестов
        :param faker: фикстура подготовки случайных данных
        """
        query_data = data['query_data'].copy()
        post_query = query_data.copy()
        post_query['json'] = data['payload'].copy()

        post_query['json']['id'] = data['test_ids'][1]

        new_pet = r.post(**post_query)

        query_data['url'] += f"/{new_pet.json()['id']}"

        query_data['headers']['api_key'] = faker.fwords(nb=1, lang='en', uuid=True)
        res = r.delete(**query_data)
        assert res.status_code == 403  # 403 # TODO #5 ожидается error code 403
