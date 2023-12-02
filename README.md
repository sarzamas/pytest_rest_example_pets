| CI/CD TEST |                                                                                                                                                                                                           Status |
|:-----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
| :octocat:  | [![CI/CD TEST](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/CI.yaml/badge.svg?branch=main&event=push)](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/CI.yaml) |

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

Запуск автотестов
============================
#### 1. GitHub CI Actions
- Запуск Manual TestRun по кнопке Manual TestRun -> `Run Workflow`

[![Manual TestRun](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/manual.yaml/badge.svg?event=workflow_dispatch)](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/manual.yaml)

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
> fixtures are shown according to specified file_or_dir or current dir if not specified;

> fixtures with leading '_' are only shown with the '-v' option)

#### 5. Отчеты
- На данном этапе реализации предусмотрен отчет по копке:
- - чтобы просмотреть отчет о запуске автотестов на этапе CI pipeline:
- - нажать на кнопку [![CI/CD TEST](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/CI.yaml/badge.svg?branch=main&event=push)](https://github.com/sarzamas/pytest_rest_example_pets/actions/workflows/CI.yaml)
- - выбрать `<Commit name>` -> Workflow: `CI.yaml` -> Matrix: `test` -> Job: `test(3.12)` -> Step: `Run Test`

Документация
============================
#### Описание тестового покрытия
- Ссылка на требования: в папке проекта [\DOC](https://github.com/sarzamas/pytest_rest_example_pets/tree/main/DOC)
- [SWAGGER](https://petstore.swagger.io/)
