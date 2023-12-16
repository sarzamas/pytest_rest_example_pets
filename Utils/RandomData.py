import random
import string
from uuid import uuid4

from faker import Faker

from Utils.Singleton import Singleton


class RandomData(metaclass=Singleton):
    """
    Провайдер случайных данных
    """

    def __init__(self):
        self.__faker_ru = Faker('ru_RU')
        self.__faker_en = Faker('en')

    def __getattr__(self, item):
        return getattr(self.__faker, item)

    def fwords(self, lang='ru', nb=2, capitalize=True, uuid=False):
        """
        Генератор фраз из случайных слов
        :param lang: str: язык локали для букв в словах
        :param nb: int: количество слов
        :param capitalize: признак, устанавливающий CapsLock на каждое слово
        :param uuid:  признак, добавляющий uuid к результату
        :return: str: случайная фраза
        """
        if lang == 'ru':
            rand = ' '.join([_.capitalize() if capitalize else _ for _ in self.__faker_ru.words(nb=nb)])
        elif lang == 'en':
            rand = ' '.join([_.capitalize() if capitalize else _ for _ in self.__faker_en.words(nb=nb)])
        else:
            raise ValueError(f"запрашиваемый язык: `{lang}` для генерации случайных фраз не реализован")

        rand += f' {str(uuid4())}' if uuid else ''
        return rand

    @staticmethod
    def text(length_word=10, count_words=1) -> str:
        """
        Статический метод генерации случайного текста
        :param length_word: int: количество символов в слове
        :param count_words: int: количество слов
        :return: str: случайный текст из ascii символов
        """
        result_str = ''
        for i in range(count_words):
            letters = string.ascii_letters
            result_str += ''.join(random.choice(letters) for i in range(length_word))
            if i + 1 < count_words:
                result_str += ' '
        return result_str

    @staticmethod
    def int(length=16) -> int:
        """
        Статический метод генерации случайного числа
        :param length: int: количество цифр в числе
        :return: int: случайное число
        """
        return random.randint(10 ** (length - 1), 10**length - 1)
