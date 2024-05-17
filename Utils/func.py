from os import listdir, path, remove

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
                if path.getsize(entity_path) == 0:
                    remove(entity_path)
            except PermissionError:
                continue
        if path.isdir(entity_path):
            clear_empty_in_folder(entity_path)
