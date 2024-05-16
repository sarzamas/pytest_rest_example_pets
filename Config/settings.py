from os import getenv, path

DEBUG = getenv('DEBUG', 'false').lower() not in ('false', '0')  # булевый флаг
