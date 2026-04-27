from qgis.PyQt.QtWidgets import QMenu, QAction, QToolBar
from qgis.PyQt.QtGui import QIcon
import os

from ..functions.export_data import ExportData
from ..functions.lsg_settings import LSGSettings
from ..functions.new_site import NewSite
from ..functions.align_section import AlignSection



class GuiManager:
    """Manages the lifecycle and visibility of the LS&G Plugin's graphical interface.

    This class handles the creation, placement, and removal of custom menus, 
    toolbars, and dockable panels within the QGIS main window.

    Attributes:
        iface: Reference to the QGIS Interface (QgIface).
        menu: The top-level QMenu object in the QGIS menu bar.
        actions_list: A collection of QAction objects to prevent garbage collection.
        toolbar: The QToolBar object containing shortcut icons.
        panels: A list of active dock widgets to track for cleanup.
    """
    def __init__(self, iface):
        """Initialises the manager with QGIS interface references."""
        self.iface = iface
        self.menu = None
        self.actions_list: list[QAction] = []
        self.toolbar = None
        self.menu_title = "LS&G Manager"
        self.toolbar_title = "LSG Toolbar"
        
        # Build paths relative to this file so icons load regardless of install directory
        self.icon_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "icons")
        self.panels = [] 

    # called in initgui to initialise the elements of the gui
    def initialiseGui(self):
        """Builds and displays the menu, toolbar, and panels in QGIS.

        This is typically called by the main plugin's initGui() method.
        """

         # 1. Create the containers
        self.menu = QMenu(self.menu_title, self.iface.mainWindow())
        self.toolbar = QToolBar(self.toolbar_title)

        # 2. Define what goes inside them (Actions)
        self.prepare_gui()

        # 3. Inject the menu into the QGIS Menu Bar
        menu_bar = self.iface.mainWindow().menuBar()
        
        # We try to find the 'Help' menu so our plugin appears in a logical 
        # position (usually at the end, but before Help).
        help_action = None
        for action in menu_bar.actions():
            if action.text() == "&Help":
                help_action = action
                break

        if help_action:
            menu_bar.insertMenu(help_action, self.menu)
        else:
            menu_bar.addMenu(self.menu)

        # 4. Add the toolbar and panels to the UI
        self.iface.addToolBar(self.toolbar)
        self.prepare_panels()


    # called from unload() to remove the elements of the gui
    def unloadGui(self):
        """Safely removes all UI elements and clears memory.

        This must be called when the plugin is disabled or uninstalled 
        to prevent 'ghost' buttons or menu items remaining in QGIS.
        """

        # Remove actions from the menu first
        if self.menu:
            actions_to_remove = list(self.menu.actions())
            for action in actions_to_remove:
                self.menu.removeAction(action)

        # Remove the menu from the QGIS Bar
        if self.menu:
            menu_bar = self.iface.mainWindow().menuBar()
            menu_bar.removeAction(self.menu.menuAction())
            # deleteLater() is safer than 'del'; it waits for the event loop to finish
            self.menu.deleteLater()
            self.menu = None

        # Clean up the Toolbar
        if self.toolbar:
            for action in self.toolbar.actions():
                self.toolbar.removeAction(action)
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None

        # Explicitly delete actions to free up memory
        for action in self.actions_list:
            if action:
                action.deleteLater()
        self.actions_list = []

        # Remove any active dock panels (like the New Site panel)
        for panel in self.panels:
            self.iface.mainWindow().removeDockWidget(panel)
            panel.deleteLater()
        self.panels.clear()


    def prepare_gui(self):
        """function that holds all the information on the actions and calls their creation
         and addition to the menu and toolbar"""
        # action_name - string for the name of the action
        # action_icon - name of the icon to be used. will be joined to the filepath for icons folder
        # action_function - name of the function to be triggered
        # is_menu - bool representing if needing to be added to the menu
        # is_toolbar - bool representing if needing to be added to the toolbar

        # add functionality to export the data in CSV format for GeoGateway or Alloy
        # rules for this are set in the DTF document provided by Geoplace
        self.populate_gui("Export Data",
                     None,  # No icon needed, menu item only
                     ExportData,
                     True,
                     False)

        # allows for configuring, and saving, the map layers used in the plugin
        self.populate_gui("Layer settings",
                          None,  # No icon needed, menu item only
                          LSGSettings,
                          True,
                          False)
        
        self.populate_gui("Align Section",
                          os.path.join(self.icon_path, 'question.svg'),
                          AlignSection,
                          False,
                          True)

    def populate_gui(self, action_name, action_icon, action_function,
                     is_menu, is_toolbar):
        """Helper to create a QAction and bind it to a UI element.

        Args:
            action_name: The text label for the button/menu item.
            action_icon: Full system path to the icon file.
            action_function: The class/function to initialize when clicked.
            is_menu: If True, adds the action to the dropdown menu.
            is_toolbar: If True, adds the action to the icon toolbar.
        """

        new_action = QAction(QIcon(action_icon), action_name, self.iface.mainWindow())
        
        # We use a 'lambda' here because we need to pass 'self.iface' to the function
        # only when the button is actually clicked, not when the code is being read.
        new_action.triggered.connect(lambda: action_function(self.iface))
        
        # Keeping a reference in actions_list is VITAL. 
        # Without it, Python's memory management deletes the action instantly.
        self.actions_list.append(new_action)

        if is_menu:
            self.menu.addAction(new_action)

        if is_toolbar:
            self.toolbar.addAction(new_action)

    def prepare_panels(self):
        """Initialises and displays persistent side-panels (Dock Widgets)."""

        # We store the instance as a class attribute (self.new_site_instance)
        # to ensure it stays 'alive' while the user is interacting with it.
        self.new_site_instance = NewSite(self.iface, self.panels)
        
        
        