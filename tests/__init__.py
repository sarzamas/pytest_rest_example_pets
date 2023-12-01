# <editor-fold desc='CI/CD'>
"""
Список параметров для CI/CD, которые возможно изменять `на лету` из командной строки запуска тестов
    Пример использования проброса параметров при запуске тестов:
    $ python -m pytest <имя папки с тестами> --<параметр1>=<value1> --<параметр2>=<value2>
"""
PARAMS = (
    'username',
    'password',
)


def pytest_addoption(parser):
    """
    Функция проброса в тестовую сессию pytest параметров из строки команды запуска
    Пример использования:
        $ python -m pytest <имя папки с тестами> --<параметр1>=<value1> --<параметр2>=<value2>
    Help:
        Подсказку по доступным для проброса параметрам можно увидеть после первого запуска тестовой сессии pytest
            - формируется динамически из папки __pycache__
            - в списке доступных опций появится секция [Custom options]
                $ python -m pytest --help
    Зависимости:
        для работы метода необходимо определить:
         - кортеж пробрасываемых констант PARAMS ()
         - в фикстуре config(request) переназначить пробрасываемые параметры в цикле:
           value = request.config.getoption(f'--{param}')

    :param parser: экземпляр служебного класса Parser
    """

    for param in PARAMS:
        prefix = f'если не задан параметр `--{param}`, по умолчанию используется из Config файла проекта'
        parser.addoption(f'--{param}', action='store', default=None, help=f'{prefix}')


# </editor-fold desc='CI/CD'>


def change_handler(old_url, new_handler=''):
    """
    Функция замены/удаления последнего хендлера в url для реализации возможности смены HTTP методов в тесте
    Ex: по умолчанию производится удаление последнего хендлера со slash `/`
    :param old_url: 'https://petstore.swagger.io/v2/pet/findByStatus'
    :param new_handler: str: ''
    :return: new_url: str: new_url: 'https://petstore.swagger.io/v2/pet'
    """
    return '/'.join(old_url.split('/')[:-1]) + new_handler
