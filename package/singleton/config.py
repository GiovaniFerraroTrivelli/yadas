from typing import Any

from package.singleton.singleton import Singleton


class Config(metaclass=Singleton):
    def __init__(self):
        self.config: dict[str, Any] = {
            'server_list_columns_width': [500, 300, 100, 100, 300, 100],
            'is_maximized': False,
        }

    def load(self, data: dict[str, Any]) -> None:
        if not data:
            return
        # Merge the data with the existing config
        self.config = {**self.config, **data}

    def get(self, key):
        return self.config[key]

    def set(self, key, value):
        self.config[key] = value

    def save(self):
        from package.utils.utils import save_config_file
        save_config_file(self.config)
