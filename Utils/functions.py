from os import linesep, listdir, path, remove
from sys import stdin
from typing import Union


def clear_empty_in_folder(folder: Union[path, str]):
    """
    Рекурсивное удаление всех пустых сущностей в текущей директории
     - игнорирование ошибки: в случае, если удаление невозможно - продолжаем двигаться дальше без удаления
    :param folder: папка от которой включительно и вниз начинается поиск
    """
    dir_list = listdir(folder)
    for entity in dir_list:
        entity_path = path.join(folder, entity)
        if path.isfile(entity_path):
            if not path.getsize(entity_path):
                try:
                    remove(entity_path)
                except PermissionError:
                    continue
        elif path.isdir(entity_path):
            clear_empty_in_folder(entity_path)


def make_text_ansi_bold(text: str, is_tty: bool = stdin.isatty()) -> str:
    """
    Функция для выделения текста жирным с помощью меток ANSI escape sequence color options:
     - для дифференциации форматирования теста в зависимости от места назначения вывода (в окно IDE или в логфайл)
     - может сочетаться с другими метками ANSI-color
    :param text: исходный текст
    :param is_tty: stdin.isatty() - признак процесса, инициировавшего запуск тестовой сессии:
     - True - инициатор запуска - консоль терминала (как в CI) -> подразумевается вывод в логфайл - без меток ANSI color
     - False - запуск производился из окна IDE (Run/Debug Configuration) -> вывод в окно IDE - с метками ANSI color
    :return: str: ANSI bold text
    """
    return '\033[1m%s\033[0m' % text if not is_tty else text


def make_text_ansi_plain(text: str, is_tty: bool = stdin.isatty()) -> str:
    """
    Функция убирает метки ANSI escape sequence color options из текста для логирования его в файл allure как plain/text
     - для дифференциации форматирования теста в зависимости от места назначения вывода (в окно IDE или в логфайл)
     - сигнатуры всех меток  - pytest.TerminalWriter._esctable:
     -  Capitalized colors indicates background color
     Ex: `'green', 'Yellow', 'bold'` will give bold green text on yellow background
        bold=1,
        light=2,
        blink=5,
        invert=7,
        black=30,
        red=31,
        green=32,
        yellow=33,
        blue=34,
        purple=35,
        cyan=36,
        white=37,
        Black=40,
        Red=41,
        Green=42,
        Yellow=43,
        Blue=44,
        Purple=45,
        Cyan=46,
        White=47,
    :param text: исходный текст
    :param is_tty: stdin.isatty() - признак процесса, инициировавшего запуск тестовой сессии:
     - True - инициатор запуска - консоль терминала (как в CI) -> подразумевается вывод в логфайл - без меток ANSI color
     - False - запуск производился из окна IDE (Run/Debug Configuration) -> вывод в окно IDE - с метками ANSI color
    :return: str: текст, очищенный от меток ANSI escape sequence color options
    """
    if not is_tty:
        (
            text.replace('\033[0m', '')  # any-end
            .replace('\033[1m', '')  # bold-start
            .replace('\033[32m', '')  # green-start
            .replace('\033[33m', '')  # yellow-start
        )
    return text


def make_text_wrapped(text: str, wrap_symbol: str = '-', width: int = 79, space: int = 1, new_line: bool = True) -> str:
    """
    Функция для форматирования текста в строку с дополнением одинаковыми символами до нужной ширины (Centered)
     - Example: `---------- example ----------`
    :param text: исходный текст
    :param width: итоговая ширина форматированного текста с обёрткой его символами
    :param wrap_symbol: символ для обертки текста
    :param space: количество пробелов между текстом и `wrap_symbol`
    :param new_line: ключ для выдачи результата с новой строки
    :return: str: wrapped text
    """
    ls = linesep if new_line else None
    text = ' ' * space + text + ' ' * space
    return f"{ls or ''}{text:{wrap_symbol}^{width}}"
