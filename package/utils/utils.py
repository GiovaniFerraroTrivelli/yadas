from typing import Any

from platformdirs import user_config_dir


def float_to_hhmmss(seconds):
    """
    Convert a float seconds value to a string in the format hh:mm:ss
    :param seconds:  float seconds
    :return:
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def get_config_folder():
    """
    Get the configuration folder for the application.
    :return:  str path to the configuration folder
    """
    return user_config_dir("yadas", appauthor=False)


def get_db_file_path() -> str:
    """
    Get the path to the database file.
    :return:  str path to the database file
    """
    return user_config_dir("yadas", appauthor=False) + "/pysw.data"


def get_db_file() -> Any:
    """
    Get the database file.
    :return:  Any data
    """
    import pickle
    import os

    file_path = get_db_file_path()
    return pickle.load(open(file_path, "rb")) if os.path.exists(file_path) else None


def save_to_db_file(data) -> None:
    """
    Save data to the database file.
    :param data: Any data
    :return:
    """
    import pickle
    import os

    file_path = get_db_file_path()

    if not os.path.exists(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))

    pickle.dump(data, open(file_path, "wb"))
