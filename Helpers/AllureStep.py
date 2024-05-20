import inspect
import logging
from functools import wraps
from typing import Any

from allure_commons._allure import StepContext  # noqa: PLC2701
from allure_commons.utils import func_parameters, represent


class StepNestingLevel:
    """Класс для отслеживания уровня вложенности шагов у отчёта"""

    def __init__(self):
        self.level = 0

    def __enter__(self):
        """Прибавляет один уровень вложенности"""
        self.level += 1
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Отнимает один уровень вложенности"""
        self.level -= 1


stn = StepNestingLevel()


def get_callers_local_vars() -> type({}.items):
    """Вспомогательная функция для получения локальных переменных на 2 фрейма назад"""
    return inspect.currentframe().f_back.f_back.f_locals.items()


def retrieve_varname(callers_local_vars: type({}.items), var: Any) -> str:
    """Вспомогательная функция для получения оригинального имени переменной

    :param callers_local_vars: Локальные переменные фрейма
    :param var: Значение переменной, имя которой необходимо получить
    :return: Имя переменной
    """
    return next(var_name for var_name, var_val in callers_local_vars if var_val is var)


def allure_step(title: str, *params: Any, show_local_vars: bool = False):
    """Вспомогательная функция для использования функции и как контекстный менеджер, и как декоратор

    :param title: Имя шага
    :param params: (В случае использования в качестве контекстного менеджера) Переменные, которые необходимо вывести
    :param show_local_vars: (В случае использования в качестве контекстного менеджера) Выводить ли все локальные
    переменные, defaults to False
    """

    if callable(title):
        return CustomStep(title.__name__, {})(title)
    callers_local_vars = get_callers_local_vars()
    return CustomStep(
        title,
        (
            {name: represent(value) for name, value in callers_local_vars}
            if show_local_vars
            else {retrieve_varname(callers_local_vars, param): represent(param) for param in params}
        ),
    )


class CustomStep(StepContext):
    """Класс кастомного шага для Allure отчётов. Наследуется от класса StepContext - класс шага аллюр из библиотеки"""

    def __init__(self, title, params):
        """Помимо стандартной инициализации используется экземпляр класса отслеживания уровня вложенности"""
        self.stn = stn
        super().__init__(title, params)

    def __enter__(self):
        """Дополненный метод из класса StepContext c увеличением уровня вложенности и логированием"""
        self.stn.__enter__()
        if self.stn.level < 2:
            logging.getLogger('allure').log(20, self.title, stacklevel=2)
        super().__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Дополненный метод из класса StepContext c уменьшением уровня вложенности"""
        super().__exit__(exc_type, exc_val, exc_tb)
        self.stn.__exit__(exc_type, exc_val, exc_tb)

    def __call__(self, func):
        """
        Дополненный метод из класса StepContext для использования в качестве декоратора с пробрасыванием параметров
        """

        @wraps(func)
        def impl(*a, **kw):
            __tracebackhide__ = True
            params = func_parameters(func, *a, **kw)
            args = [represent(x) for x in a]
            with CustomStep(self.title.format(*args, **params), params):
                return func(*a, **kw)

        return impl
