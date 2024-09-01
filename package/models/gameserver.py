import time

import a2s
from a2s.defaults import DEFAULT_ENCODING

from package.enums.latencyenum import LatencyEnum


class GameServer:
    """
    GameServer class to store the server information.
    """

    def __init__(self, address):
        ip, port = address.split(":")
        port = int(port)

        self.ip = ip
        self.port = port
        self.game = None
        self.name = None
        self.map_name = None
        self.player_count = 0
        self.max_players = 0
        self.ping = LatencyEnum.NOT_MEASURED
        self.timeout_count = 0
        self.password = False
        self.vac = False
        self.players = []
        self.rules = {}
        self.last_refresh = None
        self.latency_history = []
        self.reserved_slots = 0

    def __str__(self) -> str:
        """
        Return the server address as a string, in the format ip:port
        :return:  str
        """
        return f"{self.ip}:{self.port}"

    def __repr__(self) -> str:
        """
        Return the server information as a string
        :return: str
        """
        return f"{self.ip}:{self.port}, {self.name}, {self.game}, {self.map_name}, {self.player_count}, {self.max_players}, {self.ping}, {self.password}, {self.vac}"

    def refresh(self) -> tuple:
        """
        Refresh the server information using a2s library. This is an async function.
        :return:
        """
        val = None
        players = None
        rules = None

        # Get the server information
        try:
            val = a2s.info((self.ip, self.port), timeout=1.0, encoding=DEFAULT_ENCODING)
            self.name = val.server_name
        except Exception as e:
            self.ping = LatencyEnum.TIMEOUT
            self.add_latency(self.ping)
            print(f"Error requesting server info for {self}:", e)
            return val, None, None

        # Get the player list
        try:
            players = a2s.players((self.ip, self.port), timeout=1.0, encoding=DEFAULT_ENCODING)
        except Exception as e:
            print(f"Error requesting player list for {self}:", e)

        # TODO: Get the server rules
        # try:
        #     rules = await a2s.arules((self.ip, self.port), timeout=1.0, encoding=DEFAULT_ENCODING)
        #     print("Rules:", rules)
        # except Exception as e:
        #     print("Error:", e)

        self.fill_data(val, players, rules)
        return val, players, rules

    def is_valid(self) -> bool:
        """
        Check if the server is valid by trying to get the server information synchronously.
        :return: bool
        """
        try:
            val = a2s.info((self.ip, self.port), timeout=1.0, encoding=DEFAULT_ENCODING)
            self.name = val.server_name
            return True
        except Exception as e:
            print("Error checking if server is valid:", e)
            return False

    def fill_data(self, info, players, rules) -> None:
        """
        Fill the server data with the information provided
        :param info: Info object from a2s library
        :param players:  List of players from a2s library
        :param rules:  Dict of rules from a2s library
        :return:
        """
        if info:
            self.name = info.server_name
            self.game = info.folder
            self.map_name = info.map_name
            self.player_count = info.player_count
            self.max_players = info.max_players
            self.ping = int(info.ping * 1000)
            self.password = info.password_protected
            self.vac = info.vac_enabled
            self.last_refresh = time.time()
            self.add_latency(self.ping)

        if players:
            self.players = []
            self.players = players

        if rules:
            self.rules = rules

    def add_latency(self, ping) -> None:
        if ping == LatencyEnum.TIMEOUT:
            self.timeout_count += 1
        else:
            self.timeout_count = 0

        if self.latency_history:
            self.latency_history.append(ping if ping >= 0 else LatencyEnum.TIMEOUT)
        else:
            self.latency_history = [ping if ping >= 0 else LatencyEnum.TIMEOUT]
        self.latency_history = self.latency_history[-60:]

    def display_ping_in_ms(self) -> str:
        """
        Display the ping in milliseconds with 0 decimals and ms at the end
        :return: str "ping ms"
        """
        if self.ping == LatencyEnum.TIMEOUT:
            return f"Timeout ({self.timeout_count})"

        if self.ping == LatencyEnum.NOT_MEASURED:
            return "N/A"

        return f"{self.ping} ms"

    def get_latency_history(self) -> list[int]:
        """
        Get the latency history of the server
        :return: list of int
        """
        if not self.latency_history:
            self.latency_history = [0]
        return self.latency_history

    @staticmethod
    def is_valid_address(address) -> bool:
        """
        Check if the address is a valid ip:port address
        :param address: str
        :return: bool
        """
        try:
            ip, port = address.split(":")
            port = int(port)
            return True
        except Exception as e:
            return False
