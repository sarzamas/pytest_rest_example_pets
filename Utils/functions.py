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


def make_text_ansi_bold(text: str, is_tty: bool = stdin.isatty(), reuse_on_ending: bool = None) -> str:
    """
    Функция для выделения текста жирным с помощью меток ANSI escape sequence color options:
     - для дифференциации форматирования теста в зависимости от места назначения вывода (в окно IDE или в логфайл)
     - может сочетаться с другими метками ANSI-color
    :param text: исходный текст
    :param is_tty: stdin.isatty() - признак процесса, инициировавшего запуск тестовой сессии:
     - True - инициатор запуска - консоль терминала (как в CI) -> подразумевается вывод в логфайл - без меток ANSI color
     - False - запуск производился из окна IDE (Run/Debug Configuration) -> вывод в окно IDE - с метками ANSI color
    :param reuse_on_ending: признак сброса цвета и переустановки bold символа на конце текста
    :return: str: ANSI bold text
    """
    if not is_tty:
        text = '\033[1m%s\033[0m' % text
        if reuse_on_ending:
            text = '%s\033[1m' % text
    return text


def make_text_ansi_warning(text: str, is_tty: bool = stdin.isatty(), bold_on_ending: bool = None) -> str:
    """Функция для выделения текста цветом для сообщения типа `Warning`
    :param text: исходный текст
    :param is_tty: stdin.isatty() - признак процесса, инициировавшего запуск тестовой сессии (см. make_text_ansi_bold)
    :param bold_on_ending: признак сброса цвета и переустановки `bold` символа на конце текста
    :return: str: ANSI Warning-colored text: {background: Yellow, foreground: black, style: bold}
    """
    if not is_tty:
        text = make_text_ansi_bold('\033[30m\033[43m%s' % text, is_tty=is_tty, reuse_on_ending=bold_on_ending)
    return text


def make_text_ansi_info(text: str, is_tty: bool = stdin.isatty()) -> str:
    """Функция для выделения текста цветом для сообщения типа `Info`
    :param text: исходный текст
    :param is_tty: stdin.isatty() - признак процесса, инициировавшего запуск тестовой сессии (см. make_text_ansi_bold)
    :return: str: ANSI Warning-colored text: {foreground: cyan, style: bold}
    """
    return make_text_ansi_bold('\033[36m%s' % text, is_tty=is_tty) if not is_tty else text


def make_text_wrapped(
    text: str,
    wrap_symbol: str = '-',
    width: int = 79,
    space: int = 1,
    align: str = '<',
    align_nbr: int = 2,
    new_line: bool = True,
) -> str:
    """
    Функция для форматирования текста в строку с дополнением одинаковыми символами до нужной ширины
     - Example: `---------- example ----------` (Centered)
                `-- example ------------------` (Left aligned)
                `------------------ example --` (Right aligned)
    :param text: исходный текст
    :param width: итоговая ширина форматированного текста с обёрткой его символами
    :param wrap_symbol: символ для обертки текста
    :param space: количество пробелов между текстом и `wrap_symbol`
    :param align: ключ для выбора стратегии выравнивания текста в строке
    :param align_nbr: количество отступов от края для бокового выравнивания
    :param new_line: ключ для выдачи результата с новой строки
    :return: str: wrapped text
    """
    align_options = ('<', '^', '>')
    if align not in align_options:
        message = f"Для выравнивая текста использовать значение `align` из списка возможных: {align_options}"
        raise ValueError(message)

    ls = linesep if new_line else None
    edge = wrap_symbol * align_nbr if align != '^' else ''

    text = ' ' * space + text + ' ' * space
    escape_len = len(repr(text)) - len(text) + 5
    width = width + escape_len if escape_len > 7 else width

    return (
        f"{ls or ''}"
        f"{(edge if align == '<' else '') + text + (edge if align == '>' else ''):{wrap_symbol}{align}{width}}"
    )
