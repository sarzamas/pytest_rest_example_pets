from os import linesep, listdir, path, remove
from sys import stdin


def clear_empty_in_folder(folder: str):
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
     - False - запуск производился из окна IDE -> подразумевается вывод в окно IDE - с метками ANSI color
    :return: str: ANSI bold text
    """
    return '\033[1m%s\033[0m' % text if not is_tty else text


def make_text_ansi_plain(text) -> str:
    """
    Функция убирает все метки ANSI escape sequence color options из текста для логирования его в файл в виде plain/text
     - сигнатуры меток добавлены по факту их обнаружения в логфайле
    :param text: исходный текст
    :return: str: текст, очищенный от меток ANSI color
    """
    return (
        text.replace('\033[34;1m', '')
        .replace('\033[32;1m', '')
        .replace('\033[31;1m', '')
        .replace('\033[1;1m', '')
        .replace('\033[0m', '')
    )


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
