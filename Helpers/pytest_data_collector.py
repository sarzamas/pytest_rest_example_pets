"""local_data_collector"""

import json
from os import linesep
from pathlib import Path
from typing import TextIO

from libs import get_log
from libs.api.airflow.exeptions import DataSerializationError, FileSaveError
from libs.api.airflow.helpers import log_and_raise, make_text_ansi_bold, make_text_ansi_name, make_text_ansi_warning
from libs.api.airflow.session_data import SessionData, TestData
from libs.api.airflow.utils import UpdatableSingleton, convert_to_serializable

LOG = get_log(__name__)


class SessionDataCollector(metaclass=UpdatableSingleton):
    """
    Менеджер методов работы с контейнером данных тестовой сессии
        - Глобальный доступ к общим данным через Singleton-паттерн
        - Консистентное хранение данных в структурированном виде
        - Расширяемый кеш данных любого назначения
        - Сохранение данных сессии в JSON файл

    Attributes: @dataclass
        - data (SessionData): Корневой контейнер данных тестовой сессии

    Доступ к данным в контейнере:
        - Все данные хранятся в виде структуры вложенных датаклассов внутри объекта `data`

    Примеры корректного использования:
        - Инициализация в любом месте получает единый общий экземпляр данных сессии:
            collector = SessionDataCollector()
        - Вызовы методов сессии:
            collector.start_session()
            collector.stop_session(filename)
        - Доступ к данным сессии (dotted.notation):
            LOG.debug(collector.data.timing.duration)
        - Работа с тестами (dict-доступ):
            test_data = collector.mark_test_start(nodeid)
            collector.mark_test_stop(nodeid, "PASSED")
    """
    _singleton_mode = "static"

    def __init__(self):
        self._data = SessionData()

    @property
    def data(self) -> SessionData:
        """Основной интерфейс доступа к данным сессии"""
        return self._data

    def start_session(self, debug: bool = None) -> None:
        """Инициализация новой тестовой сессии"""
        self._data.debug = debug
        self._data.session.start()
        LOG.debug(
            f"Начало тестовой сессии | "
            f'Время старта: {make_text_ansi_name(self._data.session.start_time)} | '
            f'PytestDebug mode: {make_text_ansi_name(debug)}'
        )

    def mark_test_start(self, nodeid: str) -> TestData:
        """Регистрация старта теста"""
        test_data = self._data.add_test(nodeid)
        test_data.timing.start()
        if self._data.debug:
            LOG.debug(
                f'Старт теста: {test_data.test_name} | '
                f'Модуль: {test_data.module} | '
                f'Класс: {test_data.class_name or "N/A"} | '
                f'Время старта: {test_data.timing.start_time}'
            )
        return test_data

    def mark_test_stop(self, nodeid: str, status: str) -> None:
        """Фиксация результатов завершенного теста"""
        if nodeid not in self._data.tests:
            LOG.warning(f'Попытка завершить несуществующий тест: {nodeid}')
            return

        test = self._data.tests[nodeid]
        test.timing.stop()
        test.status = status
        if self._data.debug:
            LOG.debug(
                f'Завершение теста: {make_text_ansi_bold(test.test_name)} | '
                f'Модуль: {test.module} | '
                f'Класс: {test.class_name or "N/A"} | '
                f'Длительность: {make_text_ansi_bold(test.timing.duration)} сек | '
                f'Статус: {make_text_ansi_bold(status.upper())}{linesep}'
            )

    def stop_session(self) -> None:
        """Завершение сессии"""
        self._data.session.stop()
        LOG.debug(
            f'Завершение тестовой сессии | '
            f'Время окончания: {make_text_ansi_name(self._data.session.end_time)} | '
            f'Общая длительность: {make_text_ansi_name(self._data.session.duration)} (с) | '
            f'Количество тестов: {make_text_ansi_name(len(self._data.tests))}'
        )

    def save_session_data(self, filename: str | Path | None) -> bool | None:
        """
        Сохранение данных в JSON-файл с обработкой ошибок
        :param filename: Полный путь к файлу для сохранения (str, Path или None)
        :return: Статус операции
        """
        if filename is not None and not isinstance(filename, (str, Path)):
            log_and_raise(TypeError,
                          f'Некорректное имя/путь к файлу: {type(filename)} '
                          "Ожидается `str`, `Path` или `None`",
                          logger_name=self.__class__.__name__,
                          log_level="error",
                          )
        if isinstance(filename, str):
            filename = Path(filename)

        if not filename:
            LOG.warning(
                "Тестовая сессия завершилась без создания JSON-файла сессии на диске | "
                f'{make_text_ansi_warning("Путь к JSON-файлу не задан")} |'
            )
            return False

        try:
            file_path = Path(filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            serialized = convert_to_serializable(self._data)

            with file_path.open("w", encoding="utf-8") as file:  # type: TextIO
                json.dump(
                    serialized,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            LOG.debug(
                f'Данные сессии сохранены | '
                f'Путь: {make_text_ansi_name(file_path)} | '
                f'Размер: {make_text_ansi_name(file_path.stat().st_size)} байт'
            )
            return True

        except (TypeError, ValueError) as e:
            log_and_raise(
                error_type=DataSerializationError,
                message="Ошибка сериализации данных в JSON",
                from_exception=e,
                logger_name=self.__class__.__name__,
                log_level="error",
            )
        except OSError as e:
            log_and_raise(
                error_type=FileSaveError,
                message="Ошибка записи в файл",
                from_exception=e,
                filename=filename,
                logger_name=self.__class__.__name__,
                log_level="error",
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            log_and_raise(
                error_type=DataSerializationError,
                message=f"Неизвестная ошибка сериализации",
                from_exception=e,
                filename=filename,
                logger_name=self.__class__.__name__,
                log_level="error",
            )
