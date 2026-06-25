from qgis.core import edit
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QMessageBox
from PyQt5.QtCore import QDateTime as QtCoreDateTime

from .lsg_settings import LSGSettings

class AdoptSection:
    """
    Sets the To_Check field to True for all the selected ESUID's
    """

    def __init__(self, iface):
        """
        Initialises the tool and starts the alignment process.

        Args:
            iface: The QGIS interface instance.
        """

        self.iface = iface

        # # Create a timestamp when the tool is clicked to keep dates consistent
        self.current_datetime = QtCoreDateTime.currentDateTime()

        # get reference to the Data Table Layers
        self.data_table_layers = []
        self.get_map_references()  # assigns the above layers

        self.adopt_section()


    def adopt_section(self):
        """
        
        """ 

        if self.iface.activeLayer().selectedFeatureCount() == 0:
            print("Warning: No features are currently selected in the active layer.")
        else:
            # create lists to hold the ESUID's and Site_Codes
            selected_features = self.iface.activeLayer().selectedFeatures()

            # Extract all ESUID's
            esuid_list = [feat['ESUID'] for feat in selected_features if feat['ESUID'] is not None]

            # edit data table layers
            for esu in esuid_list:
                self.edit_data_layer_tables(esu)


    def get_map_references(self):
        """
        
        """
        # get a list of all of the loaded LSG geopackage layers
        lsg_geopackage_layers = LSGSettings.retrieve_geopackage_layers()


        # Assign the list of data table layers
        # Define the suffixes you want to exclude
        excluded_suffixes = ("LSG", "Sites", "Interests", "Reinstatements", "Designations")
        # Filter out any layer whose name ends with any of those suffixes
        self.data_table_layers = [
            layer for layer in lsg_geopackage_layers 
            if not layer.name().endswith(excluded_suffixes)
        ]    

    
    def edit_data_layer_tables(self, esuid):
        """
        Directly updates the 'To_Check' field to True for features matching the given esuid.
        If the esuid cannot be found in a layer, it displays a popup message box listing them.
        """
        missing_records = []

        for table in self.data_table_layers:
            to_check_idx = table.fields().indexOf('To_Check')
            last_updated_idx = table.fields().indexOf('Last_Updated')
            
            # Request features that match the query
            # Wrap esuid in quotes if it is a string field: f'"esuid" = \'{esuid}\''
            features = list(table.getFeatures(f'"esuid" = {esuid}'))
            
            if not features:
                # Keep track of the table name where ESUID was missing
                missing_records.append(f"• Layer: '{table.name()}' (ESUID: {esuid})")
                continue

            if not table.isEditable():
                table.startEditing()

            for feature in features:
                if to_check_idx != -1:
                    table.changeAttributeValue(feature.id(), to_check_idx, True)
                if last_updated_idx != -1:
                    table.changeAttributeValue(feature.id(), last_updated_idx, self.current_datetime)

        # If any layers were flagged as missing, display the message box dialogue
        if missing_records:
            message_text = "The specified ESUID could not be located in the following table layers:\n\n"
            message_text += "\n".join(missing_records)
            
            QMessageBox.warning(
                iface.mainWindow(), 
                "Missing ESUID Alert", 
                message_text
        )
