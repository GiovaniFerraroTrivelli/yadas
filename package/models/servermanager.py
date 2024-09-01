import asyncio
import threading
import time
from typing import List

from package.models.gameserver import GameServer
from package.utils.utils import get_db_file, save_to_db_file


class ServerManager:
    """
    ServerManager class to manage the servers in the server list.
    """
    servers = dict[str, GameServer]()
    selected = None

    def __init__(self):
        # Set autorefresh interval in a new thread every 5 seconds
        self.auto_refresh_interval = 1  # Interval in seconds
        self.auto_refresh_thread = threading.Thread(target=self._auto_refresh, daemon=True)
        self.auto_refresh_thread.start()

        self._listeners = []

    def add_server(self, server) -> None:
        """
        Add a server to the server list
        :param server:  GameServer object
        :return:
        """
        self.servers[str(server)] = server
        self._notify_listeners("ADD", str(server))

    def update_server(self, server) -> None:
        """
        Update the server in the server list
        :param server:  GameServer object
        :return:
        """
        self.servers.update({str(server): server})
        self._notify_listeners("UPDATE", str(server))

    def remove_server(self, server) -> None:
        """
        Remove a server from the server list
        :param server:  GameServer object
        :return:
        """
        if server in self.servers:
            del self.servers[str(server)]
            self._notify_listeners("DELETE", str(server))

    def get_server_by_address(self, address) -> GameServer:
        """
        Get a server by its address
        :param address:  str address
        :return:  GameServer object
        """
        return self.servers.get(address)

    def get_server_by_ip_port(self, ip, port) -> GameServer:
        """
        Get a server by its ip and port
        :param ip:  str ip
        :param port:  int port
        :return:  GameServer object
        """
        return self.servers.get(f"{ip}:{port}")

    def get_servers(self) -> List[GameServer]:
        """
        Get all servers
        :return:  List of GameServer objects
        """
        return list(self.servers.values())

    def refresh_all(self) -> None:
        """
        Refresh all servers
        :return:
        """
        for server in self.servers.copy().values():
            threading.Thread(target=server.refresh).start()
            self._notify_listeners("UPDATE", str(server))

    def on_update(self, callback) -> None:
        """
        Add a listener to the server list
        :param callback: function
        :return:
        """
        self._listeners.append(callback)

    def remove_listener(self, callback) -> None:
        """
        Remove a listener from the server list
        :param callback:  function
        :return:
        """
        if callback in self._listeners:
            self._listeners.remove(callback)

    def set_selected(self, address) -> None:
        """
        Set a server as selected, so it can be auto refreshed every second
        :param address:  str address
        :return:
        """
        self.selected = address

    def save(self) -> None:
        """
        Save the server list to a file
        :return:
        """
        data = self.servers.copy()
        # Remove attributes that are not needed
        for server in data.values():
            server.__dict__.pop("ping")
            server.__dict__.pop("rules")
            server.__dict__.pop("last_refresh")
            server.__dict__.pop("players")
            server.__dict__.pop("latency_history")
            server.__dict__.pop("timeout_count")

        save_to_db_file(data)

    def _auto_refresh(self) -> None:
        """
        Auto refresh servers in a separate thread
        :return:
        """
        while True:
            # Refresh all only every 5 seconds. For selected server, refresh every second
            timestamp = int(time.time())
            if timestamp % 5 == 0:
                self.refresh_all()
            elif self.selected is not None:
                server = self.servers.get(self.selected)
                if server:
                    threading.Thread(target=server.refresh).start()
                    self._notify_listeners("UPDATE", str(server))
            time.sleep(self.auto_refresh_interval)

    def _notify_listeners(self, event, address) -> None:
        """
        Notify all listeners of a change in the server list
        :param event:  str event
        :param address:  str address
        :return:
        """
        for listener in self._listeners:
            listener(self, event, address)

    @staticmethod
    def load() -> "ServerManager":
        try:
            manager = ServerManager()
            if data := get_db_file():
                temp = GameServer("0.0.0.0:0")
                # Merge dict from file with the current dict
                for server in data.values():
                    server.__dict__ = {**temp.__dict__, **server.__dict__}
                manager.servers = data
            return manager
        except FileNotFoundError:
            return ServerManager()
