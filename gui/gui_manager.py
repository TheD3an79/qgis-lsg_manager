from qgis.PyQt.QtWidgets import QMenu, QAction, QToolBar
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import pyqtSlot
import os
from qgis.core import QgsSettings  # only here while testing settings functions
from ..functions.export_data import ExportData
from ..functions.lsg_settings import LSGSettings
from . forms.Export_Dialog import ExportDialog


class GuiManager:
    def __init__(self, iface):
        self.iface = iface
        self.menu = None
        self.actions_list: list[QAction] = []
        self.toolbar = None
        self.menu_title = "LS&G Manager"  # Title for the top-level menu
        self.toolbar_title = "LSG Toolbar"  # Title for the toolbar
        self.icon_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "icons")
        # initialise all the forms
        # self.export_dialog = ExportDialog()

    # called in initgui to initialise the elements of the gui
    def initialiseGui(self):
        """Create the custom top-level menu, toolbar and actions"""

        # Create the custom QMenu object
        self.menu = QMenu(self.menu_title, self.iface.mainWindow())
        # Create the custom toolbar
        self.toolbar = QToolBar(self.toolbar_title)

        # run functon to create actions and add to menu and toolbar
        self.prepare_gui()

        # Add the menu to the main QGIS menu bar
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

        # Add the toolbar to the QGIS interface
        self.iface.addToolBar(self.toolbar)

    # called from unload() to remove the elements of the gui
    def unloadGui(self):
        """Remove the menu and actions when the plugin is deactivated"""

        # Remove the actions from the menu
        if self.menu:
            # Get a copy of all actions currently in the menu
            actions_to_remove = list(self.menu.actions())
            # Iterate through the actions and remove/delete them
            for action in actions_to_remove:
                # Remove the action from the menu itself
                self.menu.removeAction(action)

        # Remove the menu from the main menu bar
        if self.menu:
            menu_bar = self.iface.mainWindow().menuBar()
            menu_bar.removeAction(self.menu.menuAction())
            self.menu.deleteLater()
            self.menu = None

        # Remove the toolbar and its contents
        if self.toolbar:
            # Get all actions from the toolbar
            all_actions = self.toolbar.actions()
            # Iterate over the actions and remove them from the toolbar
            for action in all_actions:
                self.toolbar.removeAction(action)
            # Removes the toolbar from the window
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()  # Ensures proper destruction
            self.toolbar = None

        # Delete the actions themselves, once they are removed from all UI elements
        for action in self.actions_list:
            if action:
                action.deleteLater()
        self.actions_list = []

    def prepare_gui(self):
        """function that holds all the information on the actions and calls their creation
         and addition to the menu and tollbar"""
        # action_name - string for the name of the action
        # action_icon - name of the icon to be used. will be joined to the filepath for icons folder
        # action_function - name of the function to be triggered
        # is_menu - bool representing if needing to be added to the menu
        # is_toolbar - bool representing if needing to be added to the toolbar

        # add functionality to export the data in CSV format for GeoGateway or Alloy
        # rules for this are set in the DTF document provided by Geoplace
        self.populate_gui("Export Data",
                     os.path.join(self.icon_path, 'question.svg'),
                     ExportData,
                     True,
                     True)

        # allows for configuring, and saving, the map layers used in the plugin
        self.populate_gui("Layer settings",
                          os.path.join(self.icon_path, 'question.svg'),
                          LSGSettings,
                          True,
                          True)

    def populate_gui(self, action_name, action_icon, action_function,
                     is_menu, is_toolbar):
        """Creates and action and adds to the actions list along with menu and
        toolbar if necessary"""

        new_action = QAction(QIcon(action_icon), action_name, self.iface.mainWindow())
        # lambda: allows parameters to be passed at the time of being triggered
        new_action.triggered.connect(lambda: action_function(self.iface))
        self.actions_list.append(new_action)

        # if it should go into the menu then add it
        if is_menu:
            self.menu.addAction(new_action)

        # if it should go onto the toolbar then add it
        if is_toolbar:
            self.toolbar.addAction(new_action)
