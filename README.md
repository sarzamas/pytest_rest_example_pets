| CI/CD TEST                                                                                                                                                                                                                                     |                                                                                                      Status                                                                                                      |                                                                                                              Code Quality |
|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|--------------------------------------------------------------------------------------------------------------------------:|
| :octocat: [![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) | [![CI/CD TEST](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/CI.yaml/badge.svg?branch=main&event=push)](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/CI.yaml) | [![code: qodana](https://avatars.githubusercontent.com/u/92853461?s=200&v=4)](https://github.com/JetBrains/qodana-action) |

Проверка REST на базе Pytest
============================

Table of Contents
-----------------

* [Запуск автотестов](#запуск-автотестов)
  * [1. GitHub CI Actions](#1-github-ci-actions)
  * [2. Remote Clone Project](#2-remote-clone-project)
  * [3. Варианты конфигурации](#3-варианты-конфигурации)
  * [4. Запуск скрипта автотестов](#4-запуск-скрипта-автотестов)
  * [5. Отчеты](#5-отчеты)
* [Документация](#Документация)
  * [Описание тестового покрытия](#описание-тестового-покрытия)
* [Логирование](#логирование)
  * [Создание локального логфайла](#создание-локального-логфайла)
  * [Доступные настройки логирования](#доступные-настройки-логирования)
  * [Создание отчета Allure](#создание-отчета-allure)
* [Known issues](#known-issues)

Запуск автотестов
============================
#### 1. GitHub CI Actions
- Запуск по кнопке `Manual TestRun` -> `Run Workflow`
> [![Manual TestRun](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/manual.yaml/badge.svg?event=workflow_dispatch)](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/manual.yaml)

#### 2. Remote Clone Project
- Предполагается что уже установлена версия Python 3.12 и настроен venv
- Выполнить для установки зависимых пакетов:
```
(venv)$ cd <директория проекта>
(venv)$ pip install -r requirements.txt
```
#### 3. Варианты конфигурации
Конфигурация запуска реализована по приоритетам:
- Приоритет №1: параметризация из командной строки (для CI/CD pipeline)
- Приоритет №2: параметризация из локального файла `config.local.json` (не коммитится в Git)
- Приоритет №3: параметризация из общего файла `config.json` (коммитится в Git)
#### 4. Запуск скрипта автотестов
Пример использования проброса параметров конфигурации при запуске тестов:
```
 $ python -m pytest <путь к папке tests>
```
Пример запуска тестов с фильтром по маркерам, установленным в файле `pytest.ini`:
```
 $ python -m pytest <marker1> ... <markerN>
```
- Для просмотра всех маркеров: ```$ pytest --markers```
- Для просмотра всех доступных fixtures: ```$ pytest --fixtures```
> fixtures are shown according to specified file_or_dir or current dir if not specified

> fixtures with leading '_' are only shown with the '-v' option

#### 5. Отчеты
- На данном этапе реализации предусмотрен отчет по копке
> чтобы просмотреть отчет о запуске автотестов на этапе CI pipeline on: `push`
> - нажать на кнопку [![CI/CD TEST](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/CI.yaml/badge.svg?branch=main&event=push)](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/CI.yaml)
> - Workflow: `CI/CD TestRun` -> выбрать верхний workflow run: `<Commit name>` -> Matrix: `test` -> Job: `test (3.12)` 
-> Step: `Run Test with pytest`

Документация
============================
#### Описание тестового покрытия
- Ссылка на требования: в папке проекта [\DOC](https://github.com/sarzamas/pytest_rest_example_pets/tree/main/DOC)
- [SWAGGER](https://petstore.swagger.io/)

Логирование
============================
#### Создание локального логфайла

- логфайлы копятся в папке `.log` (папка создается автоматически)
- для каждого тестового прогона создается отдельный уникальный логфайл с `hostname` и `timestamp` в имени
-
  - при запуске прогона с xdist создается несколько логфайлов по числу воркеров с `worker_id` в имени
-
  - если воркеров больше чем тестов, то при следующем запуске удаляются пустые логфайлы, созданные xdist в предыдущей
    сессии

#### Доступные настройки логирования

- настройки логирования находятся в `pytest.ini`

- логирование в консоль сообщений о выполнении Allure steps из кода тестов настраивается параметром:

```
log_cli = true
```

-
  - для отключения сообщений с Allure steps в консоль -> `log_cli = false`
-
  - при запуске с xdist Allure steps в консоли всегда отсутствуют
-
  - для переопределения существующих в `pytest.ini` ключей в команде запуска: `pytest -o log_cli=<new_value>`
-
  - отключение сообщений с Allure steps в логфайл - не предусмотрено (всегда присутствуют)

- детализация сообщений в файле и в консоли зависит от ENV.DEBUG flag:
-
  - по умолчанию в консоли установлен:

```
log_cli_level = INFO
```

-
  - при выставлении переменной окружения `DEBUG = True`:
  -
    - -> уровень сообщений в консоль остается бех изменения: `log_level = INFO`
  -
    - -> уровень сообщений в логфайл понижается до `log_level = DEBUG`

#### Создание отчета Allure

- отчет с результатами запуска каждого тестового прогона формируется в папке `allure-results`
-
  - папка создается автоматически
-
  - содержимое папки очищается от файлов прошлого прогона автоматически
- настройка папки осуществляется в `pytest.ini`

```
addopts = --alluredir allure-results --clean-alluredir
```

---

Known issues
============================
- у цветных строк лога имеются артефакты в отчете Allure: https://github.com/allure-framework/allure-python/issues/806
- для того чтобы папка `allure_results` создавалась в корне проекта при запуске тестовой сессии из окна IDE (PyCharm)
  необходимо настроить в IDE (PyCharm) Run/Debug Configurations

```
Search -> Run/Debug Configurations -> Edit configuration templates... -> Python tests -> Autodetect
```

-
  - заполнить в окне `Autodetect` поле `Working directory:` актуальным значением `<PROJECT_ROOT>`
-
  - запомнить Template
-
  - удалить все существующие Run/Debug Configurations сделанные до обновления Template

---
