import asyncio

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QModelIndex
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QWidget, QMessageBox, QTableWidgetItem

from package.consts.consts import APP_NAME
from package.enums.latencyenum import LatencyEnum
from package.models.gameserver import GameServer
from package.models.servermanager import ServerManager
from package.singleton.config import Config
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

        # Create menu bar
        self.create_menu_bar()

        # Show as maximized if it was maximized before
        if Config().get("is_maximized"):
            self.showMaximized()

        # Create a server manager instance
        self.server_manager = ServerManager.load()

        # Create the server table model
        server_table_model = ServerTableModel(self.server_manager.get_servers())
        self.serverTable.setModel(server_table_model)
        self.serverTable.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.serverTable.customContextMenuRequested.connect(self.on_server_table_context_menu)
        self.serverTable.show()
        self.set_server_table_column_widths()

        # Set default visible columns width for the players table
        header = self.serverPlayers.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.serverPlayers.setColumnWidth(1, 100)
        self.serverPlayers.setColumnWidth(2, 150)

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
                QMessageBox.information(self, APP_NAME, "Server address must be in the format ip:port.")
                return

            server = GameServer(text)

            if self.server_manager.get_server_by_ip_port(server.ip, server.port):
                # Create popup to show that the server already exists
                QMessageBox.information(self, APP_NAME, "Server has already been added to the server list.")
                return

            if server.is_valid():
                server.refresh()
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
        self.save_config()

    def set_server_table_column_widths(self) -> None:
        """
        Set the column widths for the server table.
        :return:
        """
        column_widths = Config().get("server_list_columns_width")
        for i, width in enumerate(column_widths):
            self.serverTable.setColumnWidth(i, width)

    def save_config(self) -> None:
        """
        Save the configuration to the config file.
        :return:
        """
        Config().set("server_list_columns_width",
                     [self.serverTable.columnWidth(i) for i in range(self.serverTable.model().columnCount())])
        Config().set("is_maximized", self.isMaximized())

        Config().save()

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

        # Get all selected addresses
        addresses = set([index.data(Qt.ItemDataRole.UserRole) for index in selected])

        # Create menu
        menu = QtWidgets.QMenu()

        if len(addresses) == 1:
            properties_item = menu.addAction('Properties...')
            properties_item.triggered.connect(lambda: self.server_properties(addresses.pop()))
        delete_item = menu.addAction(f'Delete {len(addresses)} selected server(s)...')
        delete_item.triggered.connect(lambda: self.remove_server(addresses))

        # Display menu
        menu.exec(self.serverTable.viewport().mapToGlobal(pos))

    def remove_server(self, addresses) -> None:
        """
        Remove the selected servers from the server list.
        :param addresses:  set of str addresses
        :return:
        """
        # Display dialog
        reply = QMessageBox.question(self, 'Delete Server',
                                     'Are you sure you want to delete the following servers? ' + ", ".join(addresses),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        # If user confirms, delete the servers
        if reply == QMessageBox.StandardButton.Yes:
            for address in addresses:
                self.server_manager.remove_server(address)

    def server_properties(self, address) -> None:
        """
        Display the server properties dialog for the selected server.
        :param address: str address
        :return:
        """
        server = self.server_manager.get_server_by_address(address)

        if server:
            # Create dialog
            dialog = QtWidgets.QDialog()
            dialog.setWindowTitle("Modifying properties for server " + str(server))
            dialog.setGeometry(100, 100, 400, 200)
            dialog.setFixedSize(dialog.size())

            # Create layout
            # Add two rows with an input field and a label. After that, add a button to close the dialog.
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(QtWidgets.QLabel("Reserved slots:"))
            reserved_slots = QtWidgets.QLineEdit(str(server.reserved_slots))
            layout.addWidget(reserved_slots)
            save_button = QtWidgets.QPushButton("Save")
            save_button.clicked.connect(lambda: self.save_server_properties(dialog, server, reserved_slots.text()))
            layout.addWidget(save_button)
            button = QtWidgets.QPushButton("Cancel")
            button.clicked.connect(dialog.close)
            layout.addWidget(button)

            # Set layout
            dialog.setLayout(layout)
            dialog.exec()

    def save_server_properties(self, dialog, server, reserved_slots) -> None:
        """
        Save the server properties from the dialog.
        :param dialog: QDialog dialog
        :param server: GameServer server
        :param reserved_slots: str reserved slots
        :return:
        """
        server = self.server_manager.get_server_by_address(str(server))
        server.reserved_slots = int(reserved_slots)
        self.server_manager.update_server(server)
        dialog.close()

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

    def generate_latency_plot(self, latency_history) -> None:
        """
        Generate a plot of the server latency history.
        :param latency_history: list of int latency values
        :return:
        """
        # Let's copy to avoid concurrency issues
        data = latency_history.copy()

        x = list(range(len(data)))
        self.latencyGraph.show()
        self.latencyGraph.plot(x, data, clear=True)

        # Plot vertical red lines for timeout values
        for i, value in enumerate(data):
            if value == LatencyEnum.TIMEOUT:
                self.latencyGraph.addLine(x=i, pen='r')

    def fill_players_table(self, players) -> None:
        """
        Fill the players table with all the players in the server.
        :param players: list of Player
        :return:
        """
        if players is None:
            return

        table = self.serverPlayers
        table.setSortingEnabled(False)
        table.setRowCount(len(players))

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

        table.setSortingEnabled(True)

    def create_menu_bar(self) -> None:
        """
        Create the menu bar for the main window.
        :return:
        """
        # Create menu bar
        menu_bar = QtWidgets.QMenuBar(self)

        # File menu
        file_menu = menu_bar.addMenu("File")

        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Set the menu bar
        self.layout().setMenuBar(menu_bar)
