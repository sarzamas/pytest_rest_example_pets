"""
Color logger for consumer (logs will be emitted when poll() is called)
Smart linebreak handler for Pytest log record
Decorator for class method invocation logging
"""
import re
from logging import DEBUG, Filter, Formatter, getLogger, Handler, INFO, Logger, LogRecord
from os import getenv, linesep
from sys import stdout

import colorama
from colorama import Back, Fore, Style
from str2bool import str2bool

colorama.init(autoreset=True)


class ColoredFormatter(Formatter):
    """Цветной форматтер для выделения полей в `log record`"""

    def __init__(self, fmt: str, *args, **kwargs):
        # Явно сохраняем формат в атрибуте экземпляра
        self.fmt = fmt
        super().__init__(fmt, *args, **kwargs)

    def format(self, record: LogRecord) -> str:
        """
        Применение цвета к полям записи лога без изменения длины поля от добавления ASCII символов цвета
            - Форматируем запись родительским классом (без цвета - для сохранения длины поля)
            - Получаем цвет для уровня записи
            - Устанавливаем цветовое значение для поля
            - Заменяем поле в записи на цветное значение
              возвращаем форматированное сообщение с цветным полем (но с длинной как у записи без цвета)
        Важно:
            - сохраняем длину цветного поля как у нецветного, несмотря на наличие в поле ASCII символов цвета
        Example:
            - необходимо для корректного выравнивания цветного поля `[%(levelname)-8s]` в параметрах при инициализации
              `-8s` - значение для выравнивания слева символа `]` по самому длинному из возможных значений - `CRITICAL`
        """
        colors = {
            "DEBUG": Style.BRIGHT + Fore.MAGENTA,
            "INFO": Style.BRIGHT + Fore.GREEN,
            "WARNING": Style.BRIGHT + Fore.YELLOW,
            "ERROR": Style.BRIGHT + Fore.RED,
            "CRITICAL": Style.BRIGHT + Fore.WHITE + Back.RED,
            "NAME": Style.NORMAL + Fore.CYAN,
            "BOLD": Style.BRIGHT + Fore.WHITE,
        }

        formatted_message = super().format(record)

        fields = {
            record.levelname: colors.get(record.levelname, Style.RESET_ALL),
            record.name: colors.get("NAME", Style.RESET_ALL),
        }

        for string, color in fields.items():
            colored_string = color + string + Style.RESET_ALL
            formatted_message = formatted_message.replace(string, colored_string)

        return formatted_message


class SmartLineBreakHandler(Handler):
    """
    Обработчик с управлением переносами строк в `log record`:
        - Устраняет артефакты вывода лога первой строки каждой тестовой сессии Pytest
        - Позволяет добавлять переносы строк До и После записи в лог избирательно:
            - По имени логгера обрабатывает атрибуты `new_line_before` и `new_line_after` у `log record`
            - По наличию в записи кастомного маркера отмены переноса каретки `cr_marker_after` не добавляет перенос
             EX: маркер `cr_marker_after="-#"` устанавливается непосредственно в сообщении для логирования:
                LOG.debug(f'{make_text_ansi_warning(message)}-#')
                 - переноса строки после записи не будет
                 - сам маркер "-#" тоже будет удален из записи
    Ex:
    Pytest самостоятельно модерирует переносы строк в зависимости от модификаторов вывода:
        - Pytest не устанавливает `terminator` (возврат каретки) в записи `log record` о начале/результате теста
        - Pytest ожидает добавить результат теста в эту же строку лога после окончания теста
        - Pytest может писать только результаты тестов в одну строчку при минималистическом выводе
    Кастомный логгер в режиме `DEBUG` генерирует `log record` в промежутке между событиями Pytest
        - артефактом кастомного логгера является запись `log record` в одну строчку с `log record` от Pytest
    SmartLineBreakHandler - устраняет такие артефакты кастомного логгера
    """

    def __init__(self, cr_mark_after: str = "-#"):
        if not isinstance(cr_mark_after, str) or len(cr_mark_after) == 0:
            raise ValueError("Маркер должен быть непустой строкой")
        super().__init__()
        self.cr_mark_after = cr_mark_after

    def emit(self, record: LogRecord):
        """
        Управляет переносом строк у записи в лог в зависимости от флагов, выставленных в TruncateNameFilter:
            - атрибуты записи в лог `linesep_before` и linesep_after` зависят от имени логгера
            - `linesep_before=True` - добавляется перенос строки в начале `log record`
            - `linesep_after=True` - добавляется перенос строки в конце `log record`
            - добавляется перенос строки в начале `log record`, если оба флага не установлены

        :param record: запись подлежащая форматированию и эмитированию в `stdout`
        """
        # Используем флаг из записи или значение по умолчанию
        linesep_before = getattr(record, "linesep_before", False)
        linesep_after = getattr(record, "linesep_after", False)
        cancel_return_after = None
        if (
                not linesep_before
                and not linesep_after
        ):
            linesep_before = True  # условие по умолчанию

        msg = self.format(record)
        # Проверяем, заканчивается ли сообщение на маркер
        if msg.endswith(self.cr_mark_after):
            msg = msg[:-len(self.cr_mark_after)]  # Удаляем маркер
            cancel_return_after = True

        output_msg = (
                (linesep if linesep_before else "") +
                msg +
                (linesep if linesep_after and not cancel_return_after else "")
        )
        stdout.write(output_msg)
        # Вывод в лог мгновенно (без буфера обмена)
        stdout.flush()


class TruncateNameFilter(Filter):
    """
    Фильтр для усечения имени логгера до максимальной длины поля `name`, указанной в форматтере

    Правила обрезки:
        - Если длина имени <= `max_len` поля `name` в форматтере - оставить имя как есть
        - Если (длина имени - `max_len`) > 10 - оставить имя как есть
        - Иначе обрезать имя до длины `max_len`, добавив эллипсис слева

    Фильтр выставляет флаги переноса строк (зависит от имени логгера в поле `name`):
        - `names_linesep_before` для записей требующих переноса строки в начале
        - `names_linesep_after` для записей требующих переноса строки в конце
        Ex:
            - для логгера `urllib3.connectionpool` следующая запись всегда по умолчанию пишется в ту же строку

    Атрибуты:
        max_len (int): Максимальная допустимая длина имени из форматтера
        ellipsis (str): Символы эллипсиса (по умолчанию "..")
        names_linesep_before (bool): Флаг необходимости добавить перенос строки в начале записи
        names_linesep_after (bool): Флаг необходимости добавить перенос строки в конце записи
    """

    def __init__(
            self,
            formatter: ColoredFormatter,
            names_linesep_before: set[str] = None,
            names_linesep_after: set[str] = None,
    ):
        super().__init__()
        self.max_len: int = self._parse_max_len(formatter)
        self.ellipsis: str = ".."
        self.names_linesep_before: set = names_linesep_before or set()
        self.names_linesep_after: set = names_linesep_after or set()

    @staticmethod
    def _parse_max_len(formatter: ColoredFormatter) -> int:
        """
        Парсит строку формата форматтера для определения максимальной длины поля `name`

        :param formatter: Экземпляр форматтера
        :return: int: Максимальная длина имени логгера (0 если не задано)
        """
        fmt = formatter.fmt if hasattr(formatter, "fmt") else getattr(formatter._style, "_fmt", "")

        match = re.search(r"%\(name\)-(\d+)s", fmt)
        return int(match.group(1)) if match else 0

    def filter(self, record: LogRecord) -> bool:
        """
        Применяет фильтрацию к записи лога для форматирования длины поля `name`
            - для сокращения общей длины поля сокращает имя в виде левого `ellipsis`
            - если надо сократить более чем 12 символов - сокращение имени не применяется!
       Пробрасывает флаги переноса строк До и После записи в лог

        :param record: Запись лога для обработки
        :return: bool: Всегда возвращает True (запись не отбрасывается)
        """
        name = record.name

        # Проверяем, нужно ли добавить перенос строки для этого логгера
        record.linesep_before = name in self.names_linesep_before
        record.linesep_after = name in self.names_linesep_after

        # Логика усечения имени логгера
        if (
                0 < self.max_len < len(name)  # имя длиннее чем длина поля в форматере
                and (len(name) - self.max_len) <= 12  # превышение меньше 10 символов
        ):
            # Вычисляем длину части имени для сохранения
            keep_chars = self.max_len - len(self.ellipsis)
            # Формируем новое имя
            record.name = f"{self.ellipsis}{name[-keep_chars:]}" if keep_chars > 0 else self.ellipsis[:self.max_len]

        return True


def get_log(name: str, cr_mark_after: str = "-#") -> Logger:
    """
    Настройка кастомного логирования с использованием
        - ColoredFormatter
        - SmartLineBreakHandler
        - TruncateNameFilter
    Уровень логирования зависит от переменной окружения DEBUG
    ВАЖНО:
        - уровень обработчика должен совпадать с уровнем логгера
        - список `names` содержит имена логгеров, не имеющих доступа для настройки переноса строки после записи в лог
        - маркер `cr_mark_after` устанавливается непосредственно в конце сообщения для логирования
                            и будет удален при форматировании записи (нужен в особых случаях для модерации переносов)
                            Ex: LOG.debug(f'{make_text_ansi_warning(message)}-#')

    :param name: имя логгера Ex: LOG = get_log(__name__)
    :param cr_mark_after: маркер запрета устанавливать перенос строки после записи
    :return: Logger:
    """

    log = getLogger(name)

    # Список имен логгеров с добавлением переноса строки До
    names_linesep_before = {"pytest_hook", "urllib3.util.retry"}
    # Список имен логгеров с добавлением переноса строки После
    names_linesep_after = {"pytest_hook", "urllib3.util.retry", "urllib3.connectionpool"}
    if log.name in {"urllib3",
                    "requests",
                    'socks',
                    "requests.packages",
                    "requests.packages.urllib3",
                    "requests.packages.urllib3.connectionpool",
                    "requests.packages.urllib3.util",
                    "requests.packages.urllib3.util.retry",
                    'urllib3.connection',
                    'urllib3.response',
                    'urllib3.poolmanager',
                    "urllib3.connectionpool",
                    "urllib3.exceptions",
                    "urllib3.util",
                    "urllib3.util.retry",
                    "requests.packages.urllib3.exceptions"
                    }:
        # удалив все обработчики избегаем задвоения строк
        log.handlers = []

    # Не передавать сообщения родительским логгерам
    log.propagate = False
    # Добавляем обработчик ТОЛЬКО если его нет у логгера с этим именем
    if not log.handlers:
        debug_mode = str2bool(getenv("DEBUG", "False"))
        log_level = DEBUG if debug_mode else INFO
        log.setLevel(log_level)
        handler = SmartLineBreakHandler(cr_mark_after=cr_mark_after)
        handler.setLevel(log_level)
        formatter = ColoredFormatter(
            "%(asctime)s [%(levelname)-8s] [%(name)-21s] %(message)s",
            datefmt="%Y-%d-%m %H:%M:%S"
        )
        handler.setFormatter(formatter)
        handler.addFilter(TruncateNameFilter(formatter, names_linesep_before, names_linesep_after))
        log.addHandler(handler)

    return log
