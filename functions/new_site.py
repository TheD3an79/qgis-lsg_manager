# from datetime import datetime
from qgis.core import QgsSettings
from qgis.core import QgsFeatureRequest
from qgis.core import QgsRectangle
from qgis.core import QgsPointXY
from qgis.core import QgsFeature
from qgis.core import QgsGeometry
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt
from PyQt5.QtCore import QDateTime as QtCoreDateTime

from ..gui.forms.New_Site_Panel import NewSitePanel
from .lsg_settings import LSGSettings


class NewSite:
    """
    Main Manager for creating new Local Street Gazetteer (LSG) records.

    This class handles the logic for the 'New Site' side-panel. It loads 
    the necessary map layers, sets up the user interface, and connects 
    the 'Create' button to the processing logic.

    Attributes:
        iface: The QGIS interface object (allows access to the map and bars).
        new_site_panel: The actual visual form/window where users type data.
        layers: References to the ESU, Sites, Interests, and Reinstatement tables.
    """

    def __init__(self, iface, panels):
        """
        Set up the tool when the plugin is first opened.
        """
        self.iface = iface
        self.panels = panels

        # --- 1. SET UP THE USER INTERFACE (GUI) ---
        self.new_site_panel = NewSitePanel()

        # Create a 'Dock Widget' (a panel that can be pinned to the side of QGIS)
        dock = QDockWidget("LSG New Site", self.iface.mainWindow())
        dock.setObjectName("LSGNewSite")
        dock.setWidget(self.new_site_panel)
        
        # Place the panel on the right-hand side of the screen
        self.iface.addDockWidget(Qt.RightDockWidgetArea, dock)
        
        # Keep track of the panel in the list of active panels
        self.panels.append(dock)

        # --- 2. PREPARE SETTINGS AND DATA FIELDS ---
        # Load user-specific settings saved on the local computer
        self.global_settings = QgsSettings()

        # A dictionary to map human-readable names to the input boxes on the form.
        # This makes it easier to loop through and check for empty fields later.
        self.fields = {
            "USRN": self.new_site_panel.txtUSRN,
            "Street Name/Description": self.new_site_panel.txtName,
            "Locality": self.new_site_panel.txtLocality,
            "Town": self.new_site_panel.txtTown,
            "X1": self.new_site_panel.txtX1,
            "Y1": self.new_site_panel.txtY1,
            "X2": self.new_site_panel.txtX2,
            "Y2": self.new_site_panel.txtY2
        }

        # Create 'Empty' variables (Placeholders) to store form data later
        self.int_usrn = None
        self.str_name = None
        self.str_locality = None
        self.str_town = None
        self.int_surface = None
        self.int_type = None
        self.int_state = None
        self.dt_start_date = None
        self.flt_x1 = None
        self.flt_y1 = None
        self.flt_x2 = None
        self.flt_y2 = None

        # --- 3. Create instances for the required map layers ---
        # These create containers for the map layers to be populated at run time and used as required
        self.layer_esu = None
        self.layer_sites = None
        self.layer_interests = None
        self.layer_reinstatement = None

        # Get the current system time to use as the 'Entry Date' for all records
        self.current_datetime = QtCoreDateTime.currentDateTime()

        # --- 4. THE ACTION ---
        # When the 'Create' button is clicked, run the 'create_new_site' function
        self.new_site_panel.btnCreate.clicked.connect(self.create_new_site)


    def create_new_site(self):
        """
        The main controller function that runs the site creation process.

        This function executes a sequence of validation checks and database 
        updates in a specific order. Each step must return True for the 
        process to continue to the next stage.

        Steps involved:
            1. Validate form completeness and coordinates.
            2. Check for duplicate records.
            3. Update the LSG layer and various database tables.
            4. Show a final success message.

        Returns:
            None: This function handles its own errors via popups.
        """

        # STEP 1: Verify the user has filled out all mandatory form fields
        if self.check_form_values():

            # Read those values from the UI into variables we can use
            self.get_form_values()

            # get reference to the tables required
            self.retrieve_map_references()

            # STEP 2: Logic checks - ensure site isn't a duplicate and coordinates make sense
            if self.check_record_is_new():

                if self.check_coordinate_validity():
                    
                    # STEP 3: Category checks - ensure Type and State dropdowns are valid
                    if self.check_comboboxes():

                        # STEP 4: Database Updates 
                        # These functions update the actual GIS layers and SQL tables.
                        # We use 'if' statements so that if one table fails, the rest stop.
                        
                        if self.populate_lsg_layer(): 
                            
                            if self.populate_sites_table():                                
                                
                                if self.populate_reinstatement_table():
                                    
                                    if self.populate_interest_table():
                                        
                                        # FINAL STEP: Success!
                                        self.show_completion_message()


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
            "New site created", 
            level=0
        )


    # bool return
    def check_form_values(self) -> bool:
        """
        Check if the user filled out all required parts of the form.
    
        Args:
            None (uses self.fields)

        Returns:
            bool: True if the form is complete, False if errors were found.
        """

        # Check all fields except "Locality" because that one isn't manadatory
        missing_fields = [name for name, widget in self.fields.items()
        if name != "Locality" and not widget.text().strip()]

        # if there are any missing fields then a pop up box is opened detailing the missing fields
        if missing_fields:
            msg = f"The following fields are required: {', '.join(missing_fields)}"
            QtWidgets.QMessageBox.warning(iface.mainWindow(), "Validation Error", msg)
            return False
        return True


    def get_form_values(self):
        """
        Extract user input from the New Site Panel and store it in variables.

        This function reads the text, numbers, and dates from the user interface 
        and converts them into the correct Python data formats (int, float, etc.) 
        so the database can process them.

        Args:
            None (reads directly from self.new_site_panel)

        Returns:
            None (updates class attributes like self.int_usrn)
        """

        # --- Text and Number Data ---
        # Note: Validation for empty fields was done in check_form_values()
        
        # Convert USRN to a whole number (Integer)
        self.int_usrn = int(self.new_site_panel.txtUSRN.text())
        
        # Standard text strings
        self.str_name = self.new_site_panel.txtName.text()
        self.str_locality = self.new_site_panel.txtLocality.text()
        self.str_town = self.new_site_panel.txtTown.text()

        # --- Dropdown Menus (Comboboxes) ---
        # We add +1 because index starts at 0, but our database IDs usually start at 1
        self.int_surface = self.new_site_panel.cboSurface.currentIndex() + 1
        self.int_type = self.new_site_panel.cboType.currentIndex() + 1
        self.int_state = self.new_site_panel.cboState.currentIndex() + 1

        # --- Dates and Coordinates ---
        # Format example: (2026, 4, 10, 14, 16, 32)
        self.dt_start_date = self.new_site_panel.dteStartDate.dateTime()
        
        # Convert X and Y text strings into decimal numbers (Floats)
        self.flt_x1 = float(self.new_site_panel.txtX1.text())
        self.flt_y1 = float(self.new_site_panel.txtY1.text())
        self.flt_x2 = float(self.new_site_panel.txtX2.text())
        self.flt_y2 = float(self.new_site_panel.txtY2.text())

    
    def check_record_is_new(self) -> bool:
        """
        Check if the USRN already exists in the database to prevent duplicates.

        This function searches the 'Sites' layer for any existing record 
        where the SITE_CODE matches the USRN entered in the form.

        Returns:
            bool: True if the site is new (not found), False if it already exists.
        """

        # 1. Create a search query (expression)
        # This is like saying: SELECT * FROM sites WHERE SITE_CODE = [USRN]
        expr = f'"SITE_CODE" = {self.int_usrn}'
        request = QgsFeatureRequest().setFilterExpression(expr)

        # 2. Run the search on the Sites layer
        features = self.layer_sites.getFeatures(request)
        
        # 3. Check if we actually found a record
        # .nextFeature() tries to grab the first result. If it finds one, it means 
        # the USRN is already taken.
        if features.nextFeature(QgsFeature()):
            msg = f"{self.int_usrn} already exists in the Sites table."
            
            # Alert the user that they can't use this USRN
            QtWidgets.QMessageBox.warning(iface.mainWindow(), "Validation Error", msg)
            return False
            
        else:
            # No matching record found, so it is safe to create a new one
            return True

    
    def check_coordinate_validity(self) -> bool:
        """
        Verify that the entered X and Y coordinates fall within the allowed area.

        This prevents users from entering coordinates that are outside the 
        geographic boundary (Bounding Box) of the authority.

        Returns:
            bool: True if both points are inside the boundary, False otherwise.
        """

        # 1. Define the 'Boundary Box' for the authority (DCC).
        # Format: QgsRectangle(xmin, ymin, xmax, ymax)
        # Coordinates must be between 397800,311000 and 455700,400780
        auth_bbox = QgsRectangle(397800, 311000, 455700, 400780)

        # 2. Convert the raw numbers from the form into QGIS Point objects
        start_coord = QgsPointXY(self.flt_x1, self.flt_y1)
        end_coord = QgsPointXY(self.flt_x2, self.flt_y2)

        # 3. Put points into a dictionary so we can check them both easily
        coord_dict = {
            'Start coord': start_coord,
            'End coord': end_coord 
        }

        # 4. Check if the boundary 'contains' each point.
        # This line creates a list of any points that fell OUTSIDE the box.
        invalid_coords = {n:p for (n,p) in coord_dict.items() if not auth_bbox.contains(p)}

        # 5. If there are any invalid coordinates, tell the user which ones
        if invalid_coords:
            # Get the names (keys) of the bad coordinates (e.g., "Start coord")
            invalid_names = ', '.join(invalid_coords.keys())
            msg = f"The following coordinates are not within the authority: {invalid_names}"
            
            QtWidgets.QMessageBox.warning(iface.mainWindow(), "Validation Error", msg)
            return False

        return True

    def populate_lsg_layer(self) -> bool:
        """
        Create a new map feature and save it to the LSG (Local Street Gazetteer) layer.

        This function handles the 'Spatial' part of the process: it draws the 
        line on the map and fills in the underlying data table (attributes).

        Returns:
            bool: True if the save was successful, False if the database rejected it.
        """

        # --- 1. GEOMETRY: Draw the line on the map ---
        # Converts our X/Y numbers into a QGIS 'Polyline' (a line connecting two points)
        start_point = QgsPointXY(self.flt_x1, self.flt_y1)
        end_point = QgsPointXY(self.flt_x2, self.flt_y2)
        line_geom = QgsGeometry.fromPolylineXY([start_point, end_point])

        # --- 2. INITIALISE: Prepare a new blank row (Feature) ---
        # This tells QGIS to create a new record that matches the columns of our layer
        feat = QgsFeature(self.layer_esu.fields())
        feat.setGeometry(line_geom)

        # --- 3. ATTRIBUTES: Fill in the table columns ---
        
        # These fields are generic to all new sites so should be the same for PROW, LFP etc.
        feat.setAttribute('ESUID', self.create_esuid(start_point, end_point))
        feat.setAttribute('ESU_ENTRY_DATE', self.current_datetime)
        feat.setAttribute('ESU_LAST_UPDATE_DATE', self.current_datetime)
        feat.setAttribute('ESU_START_DATE', self.dt_start_date)
        feat.setAttribute('ESU_TOLERANCE', 10)  # Standard default
        feat.setAttribute('ESU_DIRECTION', 1)  # Standard default
        feat.setAttribute('Updated', 3)         # Internal tracking value
        feat.setAttribute('HD_ENTRY_DATE', self.current_datetime)
        feat.setAttribute('HD_LAST_UPDATE_DATE', self.current_datetime)
        feat.setAttribute('HD_START_START', self.dt_start_date) # Note: Field is misspelled in DB

        # These fields, and values, are only relevant to road records of type 1 & 2 
        # so should be refactored when further types of records are added - e.g. PROW, LFP, Type 3, 4, 5
        feat.setAttribute('SITE_CODE', self.int_usrn)
        feat.setAttribute('Primary_Route', "N/A")
        feat.setAttribute('Cway_Risk_Score', "999")
        feat.setAttribute('Fway_Risk_Score', "999")
        feat.setAttribute('Hway_Route_Code', "N/A")
        feat.setAttribute('Fway_Route_Code', "N/A")
        feat.setAttribute('Cway_Hierarchy', "Private")
        feat.setAttribute('Fway_Hierarchy', "N/A")
        feat.setAttribute('Comments', "Private")
        feat.setAttribute('HighRisk_Cycle_Route', "N")
        feat.setAttribute('HD_DEDICATION_CODE', 12)
        feat.setAttribute('HD_PROW', 0)
        feat.setAttribute('HD_NCR', 0)

        # Logic for Road Types: Links the USRN to the correct 'Type' column
        if self.int_type == 1:
            feat.setAttribute('Type_1', self.int_usrn)
        elif self.int_type == 2:
            feat.setAttribute('Type_2', self.int_usrn)
        
        # --- 4. ADD FEATURE: Start session but do NOT commit ---
        if not self.layer_esu.isEditable():
            self.layer_esu.startEditing() # Open the layer for changes
        
        if self.layer_esu.addFeature(feat):
            # self.layer_esu.commitChanges() # let the user save the changes
            self.layer_esu.triggerRepaint() # Update the map view so the line appears
            return True
        else:
            # If something went wrong, undo any partial changes
            self.layer_esu.rollBack()
            QtWidgets.QMessageBox.warning(iface.mainWindow(), "Unsuccessful write",
                                        "Write to LSG table failed")
            return False
        

    @staticmethod
    def create_esuid(start_point: QgsPointXY, end_point: QgsPointXY) -> str:
        """
        Generate a unique ID (ESUID) based on the center of the line.

        The ID is created by calculating the middle point (centroid) of the 
        line and joining the X and Y coordinates together with a '0' in between.

        Args:
            start_point (QgsPointXY): The beginning of the line.
            end_point (QgsPointXY): The end of the line.

        Returns:
            str: A combined text ID, e.g., '4437010346425'.
        """

        # 1. Calculate the 'Easting' center (X coordinate)
        # We add the two X values and divide by 2 to find the middle.
        # int() rounds it to the nearest whole number.
        x_centroid = int((start_point.x() + end_point.x()) / 2)

        # 2. Calculate the 'Northing' center (Y coordinate)
        y_centroid = int((start_point.y() + end_point.y()) / 2)

        # 3. Create the ID string
        # We convert the numbers to text (str) so we can glue them together.
        # Result format: [Easting] + 0 + [Northing]
        esuid = str(x_centroid) + '0' + str(y_centroid)

        return esuid

    def populate_sites_table(self) -> bool:
        """
        Create a new record in the Sites attribute table using the form data.

        This function fills in the database-only fields (like names and towns) 
        that complement the map line created in the LSG layer.

        Returns:
            bool: True if the record was saved, False if the save failed.
        """

        # --- 1. INITIALISE: Prepare a new blank row ---
        # We grab the 'schema' (column list) from the sites layer first
        feat = QgsFeature(self.layer_sites.fields())        

        # --- 2. ATTRIBUTES: Map the user's input to the table columns ---
        feat.setAttribute('SITE_CODE', self.int_usrn)
        feat.setAttribute('SITE_TYPE', self.int_type)
        feat.setAttribute('SITE_AUTH', self.get_site_auth(self.int_usrn))
        feat.setAttribute('SITE_STATE', self.int_state)
        feat.setAttribute('SITE_START_DATE', self.dt_start_date)
        feat.setAttribute('SITE_SURFACE', self.int_surface)
        feat.setAttribute('SITE_STREET_START_DATE', self.dt_start_date)
        feat.setAttribute('SITE_NAME', self.str_name)
        feat.setAttribute('SITE_TOWN', self.str_town)
        
        # System tracking dates (created today)
        feat.setAttribute('SITE_ENTRY_DATE', self.current_datetime)
        feat.setAttribute('SITE_LAST_UPDATE_DATE', self.current_datetime)        
        
        feat.setAttribute('SITE_TOLERANCE', 10)  # Default metadata        

        # Only add Locality if the user actually typed something in (since it's optional)
        if self.str_locality:
            feat.setAttribute('SITE_LOCALITY', self.str_locality)        

        # Store the coordinates as raw numbers in the table
        feat.setAttribute('X1', self.flt_x1)
        feat.setAttribute('Y1', self.flt_y1)
        feat.setAttribute('X2', self.flt_x2)
        feat.setAttribute('Y2', self.flt_y2)        

        # --- 3. ADD FEATURE: Start session but do NOT commit ---
        if not self.layer_sites.isEditable():
            self.layer_sites.startEditing()
        
        if self.layer_sites.addFeature(feat):
            # self.layer_sites.commitChanges() # let the user save the changes
            return True
        else:
            # If this fails, the LSG line might have already been created.
            # We alert the user so they can check for "orphaned" records.
            self.layer_sites.rollBack()
            QtWidgets.QMessageBox.warning(
                iface.mainWindow(), 
                "Unsuccessful write",
                "Write to Site table failed. Please check the LSG layer for a duplicate line."
            )
            return False      
            
        
    @staticmethod
    def get_site_auth(site_code: int) -> int:
        """
        Determine the Authority (Council) ID based on the USRN number range.

        Each local authority is assigned a specific range of USRN numbers. 
        This function identifies which council a site belongs to so the 
        correct 'SITE_AUTH' code can be saved to the database.

        Args:
            site_code (int): The USRN number provided by the user.

        Returns:
            int: The 4-digit Authority ID (e.g., 1050 for DCC). 
                 Returns 0 if the USRN doesn't match any known authority.
        """

        # We check if the site_code falls 'between' two numbers for each council
        
        if 600000 <= site_code <= 699999:        # Amber Valley Borough Council (AVBC)
            return 1005
        elif 3300000 <= site_code <= 3399999:    # Bolsover District Council (BDC)
            return 1010
        elif 7100000 <= site_code <= 7199999:    # Chesterfield Borough Council (CBC)
            return 1015
        elif 14000000 <= site_code <= 14099999:  # Erewash Borough Council (EBC)
            return 1025
        elif 17300000 <= site_code <= 17399999:  # High Peak Borough Council (HPBC)
            return 1030
        elif 27700000 <= site_code <= 27799999:  # North East Derbyshire District Council (NEDDC)
            return 1035
        elif 35400000 <= site_code <= 35499999:  # South Derbyshire District Council (SDDC)
            return 1040
        elif 10900000 <= site_code <= 10999999:  # Derbyshire Dales District Council (DDDC)
            return 1045
        elif 80900000 <= site_code <= 80999999:  # Derbyshire County Council (DCC)
            return 1050        
        else:
            # If the number doesn't fit any range above, return 0 as a 'Not Found' flag
            return 0
        

    def check_comboboxes(self) -> bool:
        """
        Ensure the selected 'Type' and 'State' are supported by this version.

        Since this tool is still in development, some dropdown options (like 
        Closed states or higher Type numbers) haven't been coded yet. This 
        check prevents the program from crashing or saving incomplete data.

        Returns:
            bool: True if the selection is supported, False if it is not.
        """

        # 1. Check the 'Type' (e.g., Road, Footpath, etc.)
        # Currently, only Type 1 and Type 2 are finished.
        if self.int_type < 3: 
            
            # 2. Check the 'State' (e.g., Open, Under Construction)
            # Currently, only State 1 and State 2 are finished.
            # State 3 (Closed) and State 4 (Addressing only) are not ready.
            if self.int_state < 3:
                return True
            else:
                # Tell the user that their 'State' choice isn't ready yet
                QtWidgets.QMessageBox.warning(
                    iface.mainWindow(), 
                    "Unsupported functionality",
                    "State 3 (Closed) and State 4 (Addressing) are not implemented yet."
                )
                return False
        else:
            # Tell the user that their 'Type' choice (3, 4, or 5) isn't ready yet
            QtWidgets.QMessageBox.warning(
                iface.mainWindow(), 
                "Unsupported functionality",
                "Road Types 3, 4, and 5 are not implemented yet."
            )
            return False
    

    def populate_reinstatement_table(self) -> bool:
        """
        Create a record in the Reinstatement table with site-specific data.

        This function records the construction/reinstatement details for the new site.
        Most values here are set to standard defaults required by the database.

        Returns:
            bool: True if successful, False if the write failed.
        """

        # --- 1. INITIALISE: Prepare a new blank row ---
        feat = QgsFeature(self.layer_reinstatement.fields())        

        # --- 2. ATTRIBUTES: Populate fields ---
        feat.setAttribute('SITE_CODE', self.int_usrn)
        feat.setAttribute('START_DATE', self.dt_start_date)
        feat.setAttribute('LAST_UPDATE_DATE', self.current_datetime)
        
        # Fixed Values: These are mandatory defaults for this type of record
        feat.setAttribute('TYPE', 9)
        feat.setAttribute('WHOLE_ROAD', True)
        feat.setAttribute('ASD_COORDINATE', False)
        feat.setAttribute('AUTH', 1050)        # Fixed code for DCC
        feat.setAttribute('DISTRICT_AUTH', 999) # Placeholder/Generic district

        # --- 3. ADD FEATURE: Start session but do NOT commit ---
        # Check the layer to see if it is in edit mode and if not the make it editable
        if not self.layer_reinstatement.isEditable():
            self.layer_reinstatement.startEditing()
        
        if self.layer_reinstatement.addFeature(feat):
            # self.layer_reinstatement.commitChanges()  # leave the record for the user to save
            return True
        else:
            # If this fails, records might already exist in the LSG and Sites tables.
            # We alert the user so they know this is a partial failure.
            self.layer_reinstatement.rollBack()
            
            QtWidgets.QMessageBox.warning(
                iface.mainWindow(), 
                "Unsuccessful write",
                "Write to Reinstatement table failed. Please check the LSG and Sites tables for orphaned records."
            )
            return False  
        
    def populate_interest_table(self) -> bool:
        """
        Create a record in the Interests table using form and system data.

        This is the final table update in the process. It records the 
        legal/stakeholder interest for the new site.

        Returns:
            bool: True if the record was successfully saved, False otherwise.
        """

        # --- 1. INITIALISE: Prepare a new blank row ---
        # We use the field structure (columns) from the interests layer
        feat = QgsFeature(self.layer_interests.fields())        

        # --- 2. ATTRIBUTES: Populate the table columns ---
        feat.setAttribute('SITE_CODE', self.int_usrn)
        feat.setAttribute('AUTH', 999) # Placeholder authority code for unadopted sections
        feat.setAttribute('START_DATE', self.dt_start_date)
        feat.setAttribute('LAST_UPDATE_DATE', self.current_datetime)
        
        # Boolean flags: True/False settings for the database
        feat.setAttribute('WHOLE_ROAD', True)
        feat.setAttribute('ASD_COORDINATE', False)        
        
        # Fixed ID codes: 
        # Status 3 and Type 1 are standard requirements for new interest records
        feat.setAttribute('STATUS', 3)
        feat.setAttribute('TYPE', 1)

        # --- 3. ADD FEATURE: Start session but do NOT commit ---
        if not self.layer_interests.isEditable():
            self.layer_interests.startEditing()
        
        if self.layer_interests.addFeature(feat):
            # self.layer_interests.commitChanges() # let the user save the changes
            return True
        else:
            # If this final step fails, previous tables (LSG, Sites, Reinstatement)
            # will already have their data. We warn the user to check for consistency.
            self.layer_interests.rollBack()
            
            QtWidgets.QMessageBox.warning(
                iface.mainWindow(), 
                "Unsuccessful write",
                "Write to Interest table failed. Please check LSG, Sites, and Reinstatement tables for orphaned records."
            )
            return False
        
    def retrieve_map_references(self):
        """
        Calls the LSGSettings class and retrieves reference to the relevant map layers
        """
        # These grab the specific GIS layers needed for the database updates
        self.layer_esu = LSGSettings.retrieve_layer(self, "lyr_esu")
        self.layer_sites = LSGSettings.retrieve_layer(self, "lyr_sites")
        self.layer_interests = LSGSettings.retrieve_layer(self, "lyr_interests")
        self.layer_reinstatement = LSGSettings.retrieve_layer(self, "lyr_reinstatements")
