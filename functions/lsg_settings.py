from qgis.PyQt.QtCore import pyqtSlot
import os
from qgis.core import QgsSettings, QgsProject

from ..gui.forms.lsg_settings_dialog import SettingsDialog


class LSGSettings:
    """Manages plugin configuration and persistent user settings.

    This class handles the retrieval and storage of preferred map layers 
    (ESU, Road Links, etc.) using QGIS's global settings registry, ensuring 
    the plugin remembers user selections across different sessions.

    Attributes:
        iface: Reference to the QGIS Interface.
        settings_dialog: The UI form for user interaction.
        global_settings: QgsSettings object for local hard-drive storage.
    """


    def __init__(self, iface):
        """Initialises the settings manager and displays the configuration form."""
        self.iface = iface
        # Initialise the GUI form. We create it here so it only loads 
        # when the user specifically requests settings.
        self.settings_dialog = SettingsDialog()
        self.settings_dialog.show()

        # QgsSettings saves data to the user's registry (Windows) or .conf file (Linux/Mac).
        # This is how we make the plugin 'remember' things after QGIS is closed.
        self.global_settings = QgsSettings()

        # Placeholders for the actual QgsMapLayer objects
        self.mlc_esu = None
        self.mlc_road_link = None
        self.mlc_sites = None
        self.mlc_reinstatements = None
        self.mlc_interests = None
        self.mlc_designations = None

        # Load existing saved data into the form immediately
        self.initialise_settings_form()


    def initialise_settings_form(self):
        """Retrieves saved layer IDs and populates the dialog's combo boxes.

        This method acts as the 'bridge' between the stored strings on the 
        hard drive and the actual layer objects inside the current QGIS project.
        """

        # 1. Fetch layers from the registry using our helper function
        lyr_esu = self.retrieve_layer("lyr_esu")
        lyr_road_link = self.retrieve_layer("lyr_road_link")
        lyr_sites = self.retrieve_layer("lyr_sites")
        lyr_reinstatements = self.retrieve_layer("lyr_reinstatements")
        lyr_interests = self.retrieve_layer("lyr_interests")
        lyr_designation = self.retrieve_layer("lyr_designation")

        # 2. Update the UI widgets (mlc stands for MapLayerComboBox)
        self.settings_dialog.mlc_esu.setLayer(lyr_esu)
        self.settings_dialog.mlc_road_link.setLayer(lyr_road_link)
        self.settings_dialog.mlc_sites.setLayer(lyr_sites)
        self.settings_dialog.mlc_reinstatements.setLayer(lyr_reinstatements)
        self.settings_dialog.mlc_interests.setLayer(lyr_interests)
        self.settings_dialog.mlc_designations.setLayer(lyr_designation)

        # 3. Open the dialog as a 'Modal' window (exec_ blocks code until closed)
        # result is True if the user clicks 'OK/Save', False if 'Cancel'
        result = self.settings_dialog.exec_()

        if result:
            # Extract the layers currently selected in the UI
            self.mlc_esu = self.settings_dialog.mlc_esu.currentLayer()
            self.mlc_road_link = self.settings_dialog.mlc_road_link.currentLayer()
            self.mlc_sites = self.settings_dialog.mlc_sites.currentLayer()
            self.mlc_reinstatements = self.settings_dialog.mlc_reinstatements.currentLayer()
            self.mlc_interests = self.settings_dialog.mlc_interests.currentLayer()
            self.mlc_designations = self.settings_dialog.mlc_designations.currentLayer()

            # Persist these selections to the hard drive for next time
            self.save_layer_id(self.mlc_esu, "lyr_esu")
            self.save_layer_id(self.mlc_road_link, "lyr_road_link")
            self.save_layer_id(self.mlc_sites, "lyr_sites")
            self.save_layer_id(self.mlc_reinstatements, "lyr_reinstatements")
            self.save_layer_id(self.mlc_interests, "lyr_interests")
            self.save_layer_id(self.mlc_designations, "lyr_designation")


    def save_layer_id(self, map_layer, variable_name):
        """Saves a layer's unique ID to the QGIS global settings.

        Args:
            map_layer: The QgsMapLayer object to save.
            variable_name: The key name used to store the ID in settings.
        """

        # We prefix with 'lsg_manager/' to avoid clashing with other plugins
        variable_string = "lsg_manager/" + variable_name

        if map_layer:
            # We save the .id() (a unique string) rather than the object itself
            layer_id = map_layer.id()
            self.global_settings.setValue(variable_string, layer_id)


    @staticmethod
    def retrieve_layer(variable_name):
        """Finds a layer in the current project using a stored ID.

        Args:
            variable_name: The key name used to look up the ID in settings.

        Returns:
            QgsMapLayer: The matching layer object if found, otherwise None.
        """

        settings = QgsSettings()
        variable_string = "lsg_manager/" + variable_name
        # Get the ID string
        saved_layer_id = settings.value(variable_string)

        if saved_layer_id:
            # Look up the ID in the currently open QGIS project
            layer = QgsProject.instance().mapLayers().get(saved_layer_id)
            return layer
        return None
