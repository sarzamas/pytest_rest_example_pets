import inspect
from os import curdir, path, linesep


def lookup_report() -> str:
    """
    Функция сбора метрик вызываемого и вызывающего методов с помощью inspect
    Ex: frame, filename, line_number, function_name, lines, index = inspect.stack()[<stack_frame_depth>]
    :return: str: данные о методе, из которого был вызван текущий метод
    """
    stack_frame_depth = (
        2
        if (
            inspect.stack()[1][3] == 'alert'
            or 'lookup_report()' in inspect.stack()[1][4][0]
            or 'raise' in inspect.stack()[1][4][0]
        )
        else 1
    )
    trace_source = {
        'called': inspect.stack()[stack_frame_depth],
        'caller': inspect.stack()[stack_frame_depth + 1],
        'caller-1': inspect.stack()[stack_frame_depth + 2],
        'caller-2': inspect.stack()[stack_frame_depth + 3],
    }
    lookup = {}
    for item, source in trace_source.items():
        lookup[item + '_name'] = source[3]
        lookup[item + '_file_path'] = path.relpath(source[1], start=curdir)
        lookup[item + '_line_nbr'] = source[2]
        lookup[item + '_line_text'] = source[4][0]

    report = (
        f"{linesep}{' ! ДАННЫЕ ОБ ОШИБКЕ ! ':*^145}{linesep}"
        f"* Вызываемый (Current Method):{'\t' * 3}`{lookup['called_name']}`\tв\t{lookup['called_file_path']}:"
        f"{lookup['called_line_nbr']}{linesep}*\tСтрока с ошибкой:\t{lookup['called_line_nbr']}"
        f"{lookup['called_line_text']}{'*' * 145}{linesep}"
        f"* Вызывающий (Caller Method):{'\t' * 3}`{lookup['caller_name']}`\tиз\t{lookup['caller_file_path']}:"
        f"{lookup['caller_line_nbr']}{linesep}*\t Строка вызова:{'\t' * 2}{lookup['caller_line_nbr']}"
        f"{lookup['caller_line_text']}{'*' * 145}{linesep}"
        f"* Вызывающий-1 (Predecessor Method):\t`{lookup['caller-1_name']}`\tиз\t{lookup['caller-1_file_path']}:"
        f"{lookup['caller-1_line_nbr']}{linesep}*\t Строка вызова:{'\t' * 2}{lookup['caller-1_line_nbr']}"
        f"{lookup['caller-1_line_text']}{'*' * 145}{linesep}"
        f"* Вызывающий-2 (Forerunner Method):\t\t`{lookup['caller-2_name']}`\tиз\t{lookup['caller-2_file_path']}:"
        f"{lookup['caller-2_line_nbr']}{linesep}*\t Строка вызова:{'\t' * 2}{lookup['caller-2_line_nbr']}"
        f"{lookup['caller-2_line_text']}{'*' * 145}{linesep}"
    )

    print(report, end='')
    return report
