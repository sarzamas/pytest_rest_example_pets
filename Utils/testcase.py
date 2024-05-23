import allure
import pytest


def allure_testcase(title: str, url: str = None, name: str = "Ссылка на тест кейс в Jira"):
    """
    Декоратор. Заменяет собой @allure.title, @allure.testcase

    ```
    @allure_testcase("Название", "https://ссылка.на.тесткейс/SED-1234")
    равносильно
    @allure.title("SED-1234 Название")
    @allure.testcase("https://ссылка.на.тесткейс/SED-1234", "Ссылка на тест кейс в Jira")
    ```

    ---

    :param title: (str): Имя, отражаемое в Allure-отчете. Аналогично @allure.title
    :param url: (str, optional): Ссылка, отражаемая в Allure-отчете. Аналогично @allure.testcase
    :param name: (str, optional): Имя ссылки, отражаемое в Allure-отчете. Аналогично @allure.testcase

    ---

    Изменения по https://ihelp.rt.ru/browse/SED-33795:
    - В начало allure.title добавляется № ТК из Jira
    """
    def wrapper(function):
        new_title = title
        if url:
            function = allure.testcase(url, name)(function)
            if (testcase_num := url.split('/')[-1]).startswith("SED-"):
                new_title = f"{testcase_num} {title}"
        return allure.title(new_title)(function)
    return wrapper


def allure_story(title: str, url: str = None, name: str = "Ссылка на сторю в Jira", parametrized_func=False):
    """
    Декоратор. Заменяет собой @allure.story, @allure.link

    ```
    @allure_testcase("Название", "https://ссылка.на.сторю/SED-1234")
    равносильно
    @allure.story("SED-1234 Название")
    @allure.link("https://ссылка.на.сторю/SED-1234", name="Ссылка на сторю в Jira")
    ```

    Применяется, когда необходимо объединить несколько тестов (в т.ч. содержащихся в классе) в одну сторю внутри
    представления Behaviors.
    Если применяется к функции - необходимо выставить флаг parametrized_case, тогда каждый размноженный тест с
    параметром получит имя стори (т.к. по сути это один и тот же тест) и отпадет необходимость ставить декоратор
    @allure_testcase

    ---

    :param title: (str): Имя, отражаемое в Allure-отчете. Аналогично @allure.story
    :param url: (str, optional): Ссылка, отражаемая в Allure-отчете. Аналогично @allure.link
    :param name: (str, optional): Имя ссылки, отражаемое в Allure-отчете. Аналогично @allure.link
    :param parametrized_func: (bool, optional): Флаг, который необходимо ставить, если декоратор вешается на одну
                                               параметризованную функцию
    """

    def wrapper(function):
        new_title = title
        if url:
            function = allure.link(url, name=name)(function)
            if (story_num := url.split('/')[-1]).startswith("SED-"):
                new_title = f"{story_num} {title}"
        function = allure.story(new_title)(function)
        return allure.title(new_title)(function) if parametrized_func else function
    return wrapper


def pytest_marks(*marks: str):
    """
    Декоратор. Позволяет назначить несколько pytest.mark в одну строку.
    ```
    @pytest_marks("A", "B", "C")
    ```
    :param marks: (str): маркеры, которые необходимо поместить. В формате строки
    """
    def wrapper(function):
        for mark in marks:
            function = getattr(pytest.mark, mark)(function)
        return function
    return wrapper
