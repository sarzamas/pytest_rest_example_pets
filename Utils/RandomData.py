import random
import string
from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from allure_commons.utils import now
from faker import Faker

from Utils.Singleton import Singleton

Locale = Literal['en', 'ru']


class RandomData(metaclass=Singleton):
    """
    Провайдер случайных данных
    """

    def __init__(self):
        self.__faker_ru = Faker('ru_RU')
        self.__faker_en = Faker('en')

    def __getattr__(self, item):
        return getattr(self.__faker, item)

    def words(
        self,
        lang: Locale = 'ru',
        nb: int = 2,
        capitalize: bool = True,
        prefix: Optional[str] = None,
        uuid: bool = False,
    ):
        """
        Генератор фраз из случайных слов
        :param lang: Locale: язык локали для букв в словах
        :param nb: int: количество слов
        :param capitalize: bool: признак, устанавливающий CapsLock на каждое слово
        :param uuid: bool: признак, добавляющий uuid к результату (в конец фразы)
        :param prefix: str: префикс, добавляемый к результату (в начало фразы)
        :return: str: случайная фраза
        """
        if lang == 'ru':
            rand = ' '.join([_.capitalize() if capitalize else _ for _ in self.__faker_ru.words(nb=nb)])
        elif lang == 'en':
            rand = ' '.join([_.capitalize() if capitalize else _ for _ in self.__faker_en.words(nb=nb)])
        else:
            raise NotImplementedError(f"запрашиваемый язык: `{lang}` для генерации случайных фраз не реализован")

        rand = f'{prefix} {rand}' if prefix else rand
        rand += f' {str(uuid4())}' if uuid else ''
        return rand

    @staticmethod
    def texts(length_word: int = 10, count_words: int = 1, prefix: Optional[str] = None) -> str:
        """
        Статический метод генерации случайного текста
        :param length_word: int: количество символов в слове
        :param count_words: int: количество слов
        :param prefix: str: префикс, добавляемый к результату (в начало фразы)
        :return: str: случайный текст из ascii символов
        """
        result_str = ''
        for i in range(count_words):
            letters = string.ascii_letters
            result_str += ''.join(random.choice(letters) for i in range(length_word))
            if i + 1 < count_words:
                result_str += ' '
        return f'{prefix} {result_str}' if prefix else result_str

    @staticmethod
    def ints(length: int = 16) -> int:
        """
        Статический метод генерации случайного целого числа c заданной разрядностью
        :param length: int: количество цифр в числе (разрядность)
        :return: int: случайное число заданной разрядности
        """
        return random.randint(10 ** (length - 1), 10**length - 1)

    @staticmethod
    def uuid() -> str:
        """
        Статический метод генерации уникального ID
        :return: UUID: str: уникальный ID версии uuid4
        """
        return str(uuid4())

    @staticmethod
    def timestamp() -> str:
        """
        Статический метод, возвращающий время в виде строки
        :return: строка вида "2024-06-29_11-54-25"
        """
        current_time = datetime.now()
        return current_time.strftime('%Y-%m-%d_%H-%M-%S')

    @staticmethod
    def datetime_now() -> str:
        """
        Статический метод, возвращающий дату в виде строки
        :return: строка вида "2024-06-29"
        """
        epoch = now()
        unix_timestamp_seconds = epoch / 1000
        dt_object = datetime.fromtimestamp(unix_timestamp_seconds)
        return dt_object.strftime('%Y-%m-%d')


class Counter(metaclass=Singleton):
    """
    Провайдер последовательности натуральных чисел (счетчик)
    """

    _instance = None
    _state = 1  # Initial state of the generator

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Counter, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self.count = self._get_count()

    def _get_count(self):
        while True:
            yield self._state
            self._state += 1

    def get_next(self):
        """
        Следующий элемент последовательности
        """
        return next(self.count)
