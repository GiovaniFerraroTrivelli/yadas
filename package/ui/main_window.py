import asyncio

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtWidgets import QWidget, QMessageBox, QTableWidgetItem

from package.models.gameserver import GameServer
from package.models.servermanager import ServerManager
from package.ui.main_window_ui import Ui_MainWindow
from package.ui.server_table_model import ServerTableModel
from package.utils.utils import float_to_hhmmss


class MainWindow(QWidget, Ui_MainWindow):
    """
    Main window class for the YADAS application.
    """

    def __init__(self):
        super().__init__()

        # Load the UI file
        self.setupUi(self)

        # Create a server manager instance
        self.server_manager = ServerManager().load()

        # Create the server table model
        server_table_model = ServerTableModel(self.server_manager.get_servers())
        self.serverTable.setModel(server_table_model)
        self.serverTable.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.serverTable.customContextMenuRequested.connect(self.on_server_table_context_menu)
        self.serverTable.show()

        # Set latency graph properties
        self.latencyGraph.hide()
        self.latencyGraph.setXRange(0, 60, padding=0.075)
        self.latencyGraph.setYRange(0, 100, padding=0.075)
        self.latencyGraph.hideAxis("bottom")
        self.latencyGraph.setBackground((255, 255, 255, 0))
        self.latencyGraph.hideButtons()
        self.latencyGraph.setMouseEnabled(False, False)
        self.latencyGraph.setMenuEnabled(False)

        # Trigger click row event from table
        self.serverTable.selectionModel().currentRowChanged.connect(self.on_server_table_row_changed)

        # Observe the server manager for changes
        self.server_manager.on_update(self.on_server_list_change)

    def keyPressEvent(self, event):
        """
        Handle the key press event for the main window.
        :param event: QKeyEvent
        :return:
        """
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            text = self.serverAdd.text()

            if not GameServer.is_valid_address(text):
                # Create popup to show that the server address is invalid
                QMessageBox.information(self, "YADAS", "Server address must be in the format ip:port.")
                return

            server = GameServer(text)

            if self.server_manager.get_server_by_ip_port(server.ip, server.port):
                # Create popup to show that the server already exists
                QMessageBox.information(self, "YADAS", "Server has already been added to the server list.")
                return

            if server.is_valid():
                asyncio.run(server.refresh())
                self.server_manager.add_server(server)

        super().keyPressEvent(event)

    def closeEvent(self, a0):
        """
        Handle the close event of the main window.
        :param a0:  QCloseEvent
        :return:
        """
        self.server_manager.remove_listener(self.on_server_list_change)
        self.server_manager.save()

        # Cancel all async tasks
        asyncio.get_event_loop().close()
        super().closeEvent(a0)

    def on_server_table_context_menu(self, pos) -> None:
        """
        Display the context menu for the server table.
        :param pos: QPoint
        :return:
        """
        # Get all selected indexes
        selected = self.serverTable.selectedIndexes()

        if not selected:
            return

        # Create menu
        menu = QtWidgets.QMenu()
        delete_item = menu.addAction('Delete selected servers...')
        delete_item.triggered.connect(lambda: self.remove_server(selected))

        # Display menu
        menu.exec(self.serverTable.viewport().mapToGlobal(pos))

    def remove_server(self, selected) -> None:
        """
        Remove the selected servers from the server list.
        :param selected:  List of QModelIndex
        :return:
        """
        # Get all selected addresses
        addresses = set([index.data(Qt.ItemDataRole.UserRole) for index in selected])

        # Display dialog
        reply = QMessageBox.question(self, 'Delete Server',
                                     'Are you sure you want to delete the following servers? ' + ", ".join(addresses),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        # If user confirms, delete the servers
        if reply == QMessageBox.StandardButton.Yes:
            for address in addresses:
                self.server_manager.remove_server(address)

    def on_server_table_row_changed(self, index: QModelIndex) -> None:
        """
        Handle the event when the selected row in the server table changes.
        :param index: QModelIndex
        :return:
        """
        if index is None:
            return

        # Get address from selected row
        address = index.data(Qt.ItemDataRole.UserRole)
        self.server_manager.set_selected(address)

        # Display server info
        self.display_server_info(address)

    def on_server_list_change(self, servers, event, address) -> None:
        """
        Handle the event when the server list changes.
        :param servers: list of GameServer
        :param event: str "ADD", "UPDATE", "DELETE"
        :param address: str address
        :return:
        """
        # Refresh the server table
        self.serverTable.model().update_all_data(self.server_manager.get_servers())

        if address == self.server_manager.selected:
            if event == "DELETE":
                # Clear the server info if the selected server is deleted and unselect it
                self.server_manager.set_selected(None)
                self.clear_server_info()
            else:
                # Display the server info if the selected server is updated or added
                self.display_server_info(address)

    def display_server_info(self, address) -> None:
        """
        Display the server information in the server info panel.
        :param address:  str address
        :return:
        """
        server = self.server_manager.get_server_by_address(address)

        if server:
            self.serverName.setText(server.name)
            self.playersLabelVal.setText(f"{server.player_count} / {server.max_players}")
            self.mapLabelVal.setText(server.map_name)
            self.pingLabelVal.setText(server.display_ping_in_ms())
            self.passwordLabelVal.setText("Password Protected" if server.password else "No Password")
            self.vacLabelVal.setText("Secure" if server.vac else "Not Secure")
            self.addressLabelVal.setText(f"<a href='steam://connect/{str(server)}'>{str(server)}</a>")

            self.fill_players_table(server.players)

            # Add a graphical representation of the server latency, using plot widget
            # Generate the plot and set it to the graphics view
            self.generate_latency_plot(server.get_latency_history())
        else:
            self.clear_server_info()

    def clear_server_info(self) -> None:
        """
        Clear the server information in the server info panel.
        :return:
        """
        self.serverName.setText("")
        self.playersLabelVal.setText("")
        self.mapLabelVal.setText("")
        self.pingLabelVal.setText("")
        self.passwordLabelVal.setText("")
        self.vacLabelVal.setText("")
        self.addressLabelVal.setText("")
        self.serverPlayers.setRowCount(0)
        self.latencyGraph.hide()

    def generate_latency_plot(self, data):
        """
        Generate a plot of the server latency history.
        :param data: list of int latency values
        :return:
        """
        x = list(range(len(data)))
        self.latencyGraph.show()
        self.latencyGraph.plot(x, data, clear=True)

    def fill_players_table(self, players):
        if players is None:
            return

        table = self.serverPlayers

        table.setRowCount(len(players))
        total_width = table.viewport().width()

        for i, player in enumerate(players):
            # Player name item
            player_item = QTableWidgetItem()
            player_item.setData(Qt.ItemDataRole.DisplayRole, player.name)

            # Player score item (value is an integer).
            score_item = QTableWidgetItem()
            score_item.setData(Qt.ItemDataRole.DisplayRole, player.score)

            # Player duration item (value is a float). Display as hh:mm:ss.
            duration_item = QTableWidgetItem()
            duration_item.setData(Qt.ItemDataRole.DisplayRole, float_to_hhmmss(player.duration))

            table.setItem(i, 0, player_item)
            table.setItem(i, 1, score_item)
            table.setItem(i, 2, duration_item)

        # TODO: Fix the column width calculation
        # print("Table width:", total_width)

        # table.setColumnWidth(0, int(total_width * 0.70))
        # table.setColumnWidth(1, int(total_width * 0.15))
        # table.setColumnWidth(2, int(total_width * 0.15))

        # print("Each column width:", int(total_width * 0.70), int(total_width * 0.15), int(total_width * 0.15))
