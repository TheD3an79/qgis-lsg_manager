from qgis.PyQt.QtCore import pyqtSlot
import os
from qgis.core import QgsSettings, QgsProject

from ..gui.forms.lsg_settings_dialog import SettingsDialog


class LSGSettings:
    def __init__(self, iface):
        self.iface = iface
        # this code is in the plugin builder code, but I don't have any attributes for first_start in my code
        # brought the dialog initiation out of the if statement
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        # if self.first_start == True:
        #     self.first_start = False
        self.settings_dialog = SettingsDialog()

        # show the dialog
        self.settings_dialog.show()
        # initialise the global settings * these are unique for each user and saved on their hard drive
        self.global_settings = QgsSettings()

        # initialise the form variables for assignment later
        self.mlc_esu = None
        self.mlc_road_link = None
        self.mlc_sites = None
        self.mlc_reinstatements = None
        self.mlc_interests = None
        self.mlc_designations = None

        # initialise the data in the form and await instruction
        self.initialise_settings_form()

    def initialise_settings_form(self):
        """setting/reading glabal settings and populating the settings form"""
        # retrieves the map layers from the global settings if a value is stored
        lyr_esu = self.retrieve_layer("lyr_esu")
        lyr_road_link = self.retrieve_layer("lyr_road_link")
        lyr_sites = self.retrieve_layer("lyr_sites")
        lyr_reinstatements = self.retrieve_layer("lyr_reinstatements")
        lyr_interests = self.retrieve_layer("lyr_interests")
        lyr_designation = self.retrieve_layer("lyr_designation")

        # use layer found from global settings to populate the map layer combo boxes
        self.settings_dialog.mlc_esu.setLayer(lyr_esu)
        self.settings_dialog.mlc_road_link.setLayer(lyr_road_link)
        self.settings_dialog.mlc_sites.setLayer(lyr_sites)
        self.settings_dialog.mlc_reinstatements.setLayer(lyr_reinstatements)
        self.settings_dialog.mlc_interests.setLayer(lyr_interests)
        self.settings_dialog.mlc_designations.setLayer(lyr_designation)

        # Run the dialog event loop
        result = self.settings_dialog.exec_()
        # See if Save was pressed
        if result:
            # set the internal values for the layers from the checkboxes
            self.mlc_esu = self.settings_dialog.mlc_esu.currentLayer()
            self.mlc_road_link = self.settings_dialog.mlc_road_link.currentLayer()
            self.mlc_sites = self.settings_dialog.mlc_sites.currentLayer()
            self.mlc_reinstatements = self.settings_dialog.mlc_reinstatements.currentLayer()
            self.mlc_interests = self.settings_dialog.mlc_interests.currentLayer()
            self.mlc_designations = self.settings_dialog.mlc_designations.currentLayer()

            # Save values from output, UPRN and Auth code to global settings
            self.save_layer_id(self.mlc_esu, "lyr_esu")
            self.save_layer_id(self.mlc_road_link, "lyr_road_link")
            self.save_layer_id(self.mlc_sites, "lyr_sites")
            self.save_layer_id(self.mlc_reinstatements, "lyr_reinstatements")
            self.save_layer_id(self.mlc_interests, "lyr_interests")
            self.save_layer_id(self.mlc_designations, "lyr_designation")

    def save_layer_id(self, map_layer, variable_name):
        """Saves the ID of the selected layer in the checkbox to global settings"""

        variable_string = "lsg_manager/" + variable_name

        if map_layer:
            layer_id = map_layer.id()
            self.global_settings.setValue(variable_string, layer_id)

    def retrieve_layer(self, variable_name):
        """Returns the layer from the ID in the global settings by using the variable_name"""

        variable_string = "lsg_manager/" + variable_name
        saved_layer_id = self.global_settings.value(variable_string)

        if saved_layer_id:
            layer = QgsProject.instance().mapLayers().get(saved_layer_id)
            if layer:
                return layer
