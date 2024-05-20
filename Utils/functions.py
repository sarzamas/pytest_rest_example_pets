from os import listdir, path, remove


def report_warning(message, logger=None, logger_name=None):
    """
    Функция для репортинга сообщения уровня `Warning` одновременно в лог и stderr
     - для репортинга необязательно передавать имеющийся экземпляр `logger`
     - можно задать только желаемое `logger_name` для отображения имени в логе (косвенная ссылка на источник)
     - по умолчанию `logger` будет иметь имя `warning`
    :param message: текст сообщения
    :param logger: экземпляр уже имеющегося logger (опционально)
    :param logger_name: имя в логе для ссылки на источник сообщения (опционально)
    """

    name = logger_name if logger_name else 'warning'
    logger = logging.getLogger(name) if not logger else logger

    logger.warning(message)
    warnings.warn(message)


def clear_empty_in_folder(folder: str):
    """
    Рекурсивное удаление всех пустых сущностей в текущей директории
    :param folder: папка от которой включительно и вниз начинается поиск
    """
    dir_list = listdir(folder)
    for entity in dir_list:
        entity_path = path.join(folder, entity)
        if path.isfile(entity_path):
            try:
                if not path.getsize(entity_path):
                    remove(entity_path)
            except PermissionError:
                continue
        elif path.isdir(entity_path):
            clear_empty_in_folder(entity_path)


def make_text_bold(text: str) -> str:
    """
    Функция для выделения текста жирным с помощью меток ANSI-color
     - для форматирования строк лога
     - может сочетаться с другими метками ANSI-color
    :param text: исходный текст
    :return str: bold text
    """
    return '\033[1m%s\033[0m' % text


def make_text_wrapped(text: str, wrap_symbol: str = '-', width: int = 79, space: int = 1, new_line: bool = True) -> str:
    """
    Функция для форматирования текста в строку с дополнением одинаковыми символами до нужной ширины (Centered)
    :param text: исходный текст
    :param width: итоговая ширина форматированного текста с обёрткой его символами
    :param wrap_symbol: символ для обертки текста
    :param space: количество пробелов между текстом и `wrap_symbol`
    :param new_line: ключ для выдачи результата с новой строки
    :return str: bold text
    """
    ls = linesep if new_line else None
    text = ' ' * space + text + ' ' * space
    return f"{ls or ''}{text:{wrap_symbol}^{width}}"
    
