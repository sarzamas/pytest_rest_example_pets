import functools
from json import JSONDecodeError
from typing import Any, Callable, MutableMapping

import allure
from requests import Response

from helpers.data_collector import DataCollector


def get_flatten_dict(d: MutableMapping, parent_key: str = '', sep: str = '_') -> dict:
    """
    Реформатирование словаря из вложенной структуры в плоскую.
    :param d: Словарь для переборки
    :param parent_key: Имя родительского ключа
    :param sep: Разделитель имени
    :return: Одноуровневый словарь
    """
    items = []
    for key, value in d.items():
        new_key = f'{parent_key}{sep}{key}' if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(get_flatten_dict(value, new_key, sep=sep).items())
        elif isinstance(value, list):
            for i, item in enumerate(value):
                items.extend(get_flatten_dict({f'{key}_{i}': item}, parent_key, sep=sep).items())
        else:
            items.append((new_key, value))
    return dict(items)


def reformat_longest_str_in_response(entity: Response):
    """
    Обрезка середины у длинных значений респонса
    :param entity: сущность объекта Response
    """
    try:
        if entity.text:
            response = get_flatten_dict(entity.json())
            for key, value in response.items():
                if len(str(value)) > 50:
                    response[key] = f"{value[:20]}.....{value[25:50]}"
            return response
    except JSONDecodeError:
        return entity.text


def allure_attachment_request_data(entity: Response) -> None:
    """
    Формирование отображения данных запроса в отчете
    :param entity: сущность объекта Response
    """
    endpoint = entity.url
    request_body = entity.request.body
    status_code = str(entity.status_code)
    response = reformat_longest_str_in_response(entity)
    attachment = (
        """
            <p><strong>Endpoint:</strong> {}</p>
            <p><strong>Payload:</strong> {}</p>
            <p><strong>Status_code:</strong>&nbsp;{}</p>
            <p><strong>Response:</strong> {}</p>
        """
    ).format(endpoint, request_body, status_code, response)
    allure.attach(attachment, "Request data", allure.attachment_type.HTML)
    attachment_data_parsed = "\n".join(
        [f"<p><strong>{data.split(':')[0]}:</strong>{data.split(':')[1]}</p>"
         for data in str(DataCollector()).split("\n")],
    )
    allure.attach(attachment_data_parsed, "Parsed data", allure.attachment_type.HTML)


def allure_attach_response(method: Callable) -> Callable:
    """Декоратор для парсинга запроса и добавления данных к отчету"""

    @functools.wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        response: Response = method(self, *args, **kwargs)
        allure_attachment_request_data(response)
        return response

    return wrapper
