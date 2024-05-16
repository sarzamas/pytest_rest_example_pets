from os import getenv

DEBUG = getenv('DEBUG', 'false').lower() not in ('false', '0')  # булевый флаг
