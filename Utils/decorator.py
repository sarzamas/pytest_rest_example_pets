import allure
import pytest


def allure_testcase(title: str, url: str = None, name: str = "Ссылка на тест кейс в Jira"):
    """
    Декоратор тестовой функции, модифицирующий одноименный стандартный декоратор:
    - заменяет собой стандартные декораторы `@allure.title`, `@allure.testcase`
    ```
    @allure_testcase("Название", "https://ссылка.на.тесткейс/PROJ-1234")
    эквивалентно:
    @allure.title("PROJ-1234 Название")
    @allure.testcase("https://ссылка.на.тесткейс/PROJ-1234", "Ссылка на тест кейс в Jira")
    ```
    :param title: (str): Имя, отражаемое в Allure-отчете. Аналогично @allure.title
    :param url: (str, optional): Ссылка, отражаемая в Allure-отчете. Аналогично @allure.testcase
    :param name: (str, optional): Имя ссылки, отражаемое в Allure-отчете. Аналогично @allure.testcase
    """

    def wrapper(function):
        new_title = title
        if url:
            function = allure.testcase(url, name)(function)
            if (testcase_num := url.split('/')[-1]).startswith("PROJ-"):
                new_title = f"{testcase_num} {title}"
        return allure.title(new_title)(function)

    return wrapper


def allure_story(title: str, url: str = None, name: str = "Ссылка на сторю в Jira", parametrized_func: bool = True):
    """
    Декоратор тестовой функции, модифицирующий одноименный стандартный декоратор:
    - заменяет собой стандартные декораторы `@allure.story`, `@allure.link`
    - при использовании модифицированного декоратора отсутствует необходимость в декораторе `@allure_testcase`
    ```
    @allure_testcase("Название", "https://ссылка.на.сторю/PROJ-1234")
    эквивалентно:
    @allure.story("PROJ-1234 Название")
    @allure.link("https://ссылка.на.сторю/PROJ-1234", name="Ссылка на сторю в Jira")
    ```
    Применяется для объединения в Allure отчете, в представлении `Behaviors`, нескольких тестов под одним заголовком:
       - для одного параметризованного теста - `parametrized_func = True`
    - ! объединять параметризованный тест с другими тестами без установки флага parametrized_func !
     или
       - для нескольких тестов (в т.ч. содержащихся в разных классах) - `parametrized_func = False`
    ---
    :param title: (str): Имя, отражаемое в Allure-отчете. Аналогично @allure.story
    :param url: (str, optional): Ссылка, отражаемая в Allure-отчете. Аналогично @allure.link
    :param name: (str, optional): Имя ссылки, отражаемое в Allure-отчете. Аналогично @allure.link
    :param parametrized_func: (bool, optional): Признак для отображения в отчете раскрывающегося списка:
        -   True:  список с дублированием заголовка в имени каждого теста (параметризованный тест)
        -   False: список имен тестовых функций, объединенных под одним заголовком (несколько тестов в одной стори)
    """



    def wrapper(function):
        new_title = title
        if url:
            function = allure.link(url, name=name)(function)
            if (story_num := url.split('/')[-1]).startswith("PROJ-"):
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
