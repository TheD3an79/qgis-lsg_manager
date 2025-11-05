from qgis.PyQt.QtWidgets import QMenu, QAction, QToolBar
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import pyqtSlot
import os


class LSGManagerPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.menu = None
        self.action = None
        self.toolbar = None
        self.menu_title = "LS&G Manager"  # Title for the top-level menu
        self.toolbar_title = "LSG Toolbar"  # Title for the toolbar

    def initGui(self):
        """Create the custom top-level menu and actions"""

        dir_path = os.path.dirname(os.path.realpath(__file__))
        icon = 'question.svg'
        icon_path = os.path.join(dir_path, icon)

        # 1. Create the action and connect it
        self.action = QAction(QIcon(icon_path), "Run My Plugin Function", self.iface.mainWindow())
        self.action.triggered.connect(self.run)

        # 2. Create the custom QMenu object
        self.menu = QMenu(self.menu_title, self.iface.mainWindow())
        self.menu.addAction(self.action)

        # 3. Add the menu to the main QGIS menu bar
        menu_bar = self.iface.mainWindow().menuBar()
        # Find the 'Help' menu action to insert our menu before it
        # If 'Help' isn't found, it might append to the end
        help_action = None
        for action in menu_bar.actions():
            if action.text() == "&Help":
                help_action = action
                break

        if help_action:
            menu_bar.insertMenu(help_action, self.menu)
        else:
            menu_bar.addMenu(self.menu)

        # 4. Create the custom toolbar and add the action as a button
        self.toolbar = QToolBar(self.toolbar_title)
        self.toolbar.addAction(self.action)
        # Add the toolbar to the main QGIS window
        self.iface.addToolBar(self.toolbar)

    @pyqtSlot()
    def unload(self):
        """Remove the menu and actions when the plugin is deactivated"""

        # 1. Remove the action from the menu
        if self.action and self.menu:
            self.menu.removeAction(self.action)
            # We don't delete self.action yet as it's also used by the toolbar

        # 2. Remove the menu from the main menu bar
        if self.menu:
            menu_bar = self.iface.mainWindow().menuBar()
            menu_bar.removeAction(self.menu.menuAction())
            self.menu.deleteLater()
            self.menu = None

        # 3. Remove the toolbar and its contents
        if self.toolbar:
            # Remove the action from the toolbar before removing the toolbar itself
            self.toolbar.removeAction(self.action)
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()  # Ensures proper destruction
            self.toolbar = None

        # 4. Finally, delete the action itself once it's removed from all UI elements
        if self.action:
            self.action.deleteLater()
            self.action = None

    def run(self):
        """The main function of your plugin"""
        self.iface.messageBar().pushMessage('Hello from Plugin')
