from qgis.PyQt.QtWidgets import QMenu, QAction, QToolBar
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import pyqtSlot
import os

from .gui.gui_manager import GuiManager


class LSGManagerPlugin:
    def __init__(self, iface):
        self.iface = iface

        # initialise the gui manager class
        self.guiManager = GuiManager(self.iface)


    def initGui(self):
        """Add the menu, toolbar and actions when the plugin is activated"""
        self.guiManager.initialiseGui()

    @pyqtSlot()
    def unload(self):
        """Remove the menu and actions when the plugin is deactivated"""
        self.guiManager.unloadGui()
