from qgis.PyQt import QtWidgets
from PyQt5.QtCore import QDateTime as QtCoreDateTime
from qgis.core import QgsFeature
from qgis.core import QgsGeometry

from .lsg_settings import LSGSettings


class AlignSection:
    """
    Handles the alignment of LSG sections to RoadLink geometries.

    This class automates the process of "ending" an old ESU feature and creating 
    new ones based on the geometry of selected RoadLinks, while preserving 
    original attributes.

    Attributes:
        iface: QGIS interface object provided by the plugin.
        current_datetime: The timestamp used for date fields.
        layer_esu: The map layer where ESU data is stored.
        layer_road_link: The map layer containing reference RoadLinks.
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

        # Load the layers defined in the plugin settings
        self.layer_esu = LSGSettings.retrieve_layer("lyr_esu")
        self.layer_road_link = LSGSettings.retrieve_layer("lyr_road_link")

        # Set up "empty buckets" (placeholders) to store data later
        self.selected_esu_feature = None  
        self.esu_attributes = None  
        self.old_esuid = None 
        self.selected_road_link_features = None  
        self.road_link_geometry = []

        # Immediately run the main logic
        self.align_section()


    def align_section(self):
        """
        The main controller that runs the steps of the alignment in order.
        
        1. Finds the selected ESU.
        2. Finds the selected RoadLinks.
        3. Updates the old ESU with an end-date.
        4. Creates new ESU features using the RoadLink shapes.
        """

        # Step 1: Get the single ESU feature the user wants to update
        self.selected_esu_feature = self.retrieve_esu_feature()

        if self.selected_esu_feature:
            # Step 2: Get the RoadLink features to copy the shape from
            self.selected_road_link_features = self.retrieve_road_link_feature()
            self.retrieve_attributes()

            if self.selected_road_link_features:
                # Store the shapes (geometry) and the original ESU ID
                self.road_link_geometry = self.retrieve_geometry(self.selected_road_link_features)
                self.old_esuid = self.selected_esu_feature[0]["ESUID"]

                # Step 3: Set the end date on the existing feature
                if self.end_date_existing_feature():
                    # Step 4: Create the new features based on the new shapes
                    if self.create_lsg_features():
                        self.show_completion_message()


    # return a feature or None
    def retrieve_esu_feature(self):
        """
        Checks the ESU layer and ensures exactly one feature is selected.

        Returns:
            list[QgsFeature] or None: The selected feature if valid, else None.
        """
        selected_feature = self.layer_esu.selectedFeatures()

        # Check if user forgot to select anything
        if not selected_feature:
            self._show_warning("Unsuccessful ESU Selection", "No features are selected in the ESU_layer.")
        # Check if user selected too many things
        elif len(selected_feature) > 1:
            self._show_warning("Unsuccessful ESU Selection", "Please select only one ESU feature.")
        else:
            return selected_feature
        
        return None
    
    
    # returns the attributes of a feature
    def retrieve_attributes(self):
        """Copies the attribute data from the selected ESU feature into memory."""
        self.esu_attributes = self.selected_esu_feature[0].attributeMap() 
    

    def retrieve_road_link_feature(self):
        """
        Checks the RoadLink layer for selected features.

        Returns:
            list[QgsFeature] or None: List of selected RoadLinks or None.
        """
        selected_features = self.layer_road_link.selectedFeatures()

        if not selected_features:
            self._show_warning("Unsuccessful RoadLink Selection", "No features are selected in the RoadLink.")
        else:            
            return selected_features
        
        return None
    
    
    @staticmethod
    def retrieve_geometry(selected_features):
        """
        Extracts the geometric shapes from a list of features.

        Args:
            selected_features (list): A list of QgsFeature objects.

        Returns:
            list[QgsGeometry]: A list of valid shapes.
        """
        selected_geometries = []
        for feature in selected_features:
            geom = feature.geometry()
            if not geom.isNull():
                selected_geometries.append(geom)
        return selected_geometries
    
    
    def end_date_existing_feature(self) -> bool:
        """ 
        Marks the currently selected ESU feature as 'finished'.
        
        It updates the ESU_END_DATE and ESU_LAST_UPDATE_DATE fields 
        with the current time.

        Returns:
            bool: True if the update was successful.
        """
        # Find the column positions for the dates
        idx_end_date = self.layer_esu.fields().indexOf('ESU_END_DATE')
        idx_last_update = self.layer_esu.fields().indexOf('ESU_LAST_UPDATE_DATE')
        
        # Mapping: {Column_Number: New_Value}
        attr_map = {
            idx_end_date: self.current_datetime,
            idx_last_update: self.current_datetime
        }

        # Put the layer into "Edit Mode" if it isn't already
        if not self.layer_esu.isEditable():
            self.layer_esu.startEditing()

        # Apply the changes to the specific feature ID
        if self.layer_esu.changeAttributeValues(self.selected_esu_feature[0].id(), attr_map):
            self.layer_esu.triggerRepaint()
            return True
        else:
            self._show_warning("Unsuccessful attribute edit", "Original ESU feature could not be edited")
            self.layer_esu.rollBack()
            return False
        
    
    def create_lsg_features(self) -> bool:
        """
        Creates new ESU entries using RoadLink shapes and original ESU attributes.

        This function clears the unique ID (fid) and end date for the new records
        so that QGIS/Database can treat them as fresh, active entries.

        Returns:
            bool: True if features were successfully added.
        """
        layer = self.layer_esu
        if not layer.isEditable():
            layer.startEditing()

        # Identify columns we need to clear/change
        fid_index = layer.fields().indexOf('fid')
        end_date_index = layer.fields().indexOf('ESU_END_DATE')
        
        new_features = []
        # Get the list of data values from the original ESU
        source_attributes = self.selected_esu_feature[0].attributes()

        for geom in self.road_link_geometry:
            # Create a blank new feature with the correct columns
            feat = QgsFeature(layer.fields())
            feat.setGeometry(geom)

            # Copy the old values into a new list
            new_attrs = list(source_attributes)
            
            # Clear the ID (so a new unique one is made) and the End Date (so it's active)
            if fid_index != -1:
                new_attrs[fid_index] = None 
            if end_date_index != -1:
                new_attrs[end_date_index] = None 
            
            feat.setAttributes(new_attrs)
            
            # Add the new IDs and update timestamps
            feat.setAttribute("ESUID", self.create_esuid(geom))
            feat.setAttribute("ESU_LAST_UPDATE_DATE", self.current_datetime)
            feat.setAttribute("OLDESUID", self.old_esuid)            
            
            new_features.append(feat)

        # Save all new features into the layer at once
        if layer.addFeatures(new_features):
            return True
        return False
    
    
    def _show_warning(self, title, message):
        """Helper to display warning popups to the user."""
        QtWidgets.QMessageBox.warning(self.iface.mainWindow(), title, message)
        

    @staticmethod
    def create_esuid(geometry: QgsGeometry) -> str:
        """
        Generate a unique ID (ESUID) based on the center of the geometry.

        Args:
            geometry (QgsGeometry): The line geometry to calculate the ID from.

        Returns:
            str: A combined text ID, e.g., '4437010346425'.
        """
        # 1. Get the centroid of the geometry
        centroid_geom = geometry.centroid()
        centroid_point = centroid_geom.asPoint()

        # 2. Extract X and Y as integers
        x_centroid = int(centroid_point.x())
        y_centroid = int(centroid_point.y())

        # 3. Create the ID string
        esuid = f"{x_centroid}0{y_centroid}"

        return esuid
    

    def show_completion_message(self):
        """
        Display a success notification in the QGIS interface.

        This uses the QGIS message bar (the bar at the top of the map view) 
        to inform the user that the site creation process finished without errors.

        Args:
            None
        """

        # self.iface.messageBar() finds the notification area at the top of QGIS.
        # .pushMessage() takes three parts: (Title, Message, Level)
        # Level 0 is the code for a Green (Success) message.
        self.iface.messageBar().pushMessage(
            "Success", 
            "New feature(s) created", 
            level=0
        )