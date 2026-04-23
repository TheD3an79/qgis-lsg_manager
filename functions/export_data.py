# from qgis.core import QgsApplication
import numbers
# import os
import csv
# import pandas as pd
from datetime import datetime as dt
# from qgis.PyQt.QtCore import pyqtSlot
from qgis.core import QgsSettings
# from qgis.core import QgsVectorLayer
from qgis.core import QgsFeatureRequest
# from qgis.core import QgsExpression
# from qgis.PyQt.QtCore import QDate
from qgis.utils import iface
from qgis.core import Qgis

from collections import defaultdict

from ..gui.forms.Export_Dialog import ExportDialog
from .lsg_settings import LSGSettings


# TODO:8 - write code to export updates only
# TODO:9 - Write code to export ESU's with the additional data Alloy requires - Risk scores,
#   HRCN, PRoW overlap - and any others that come later


class ExportData:
    """Class to manage the export data form and functionality. this class will read and write
    the layers used in the global settings. The class will also export the LG and AD files
    required for geoplace and an update only version requird for Alloy"""

    def __init__(self, iface):
        self.iface = iface
        # this code is in the plugin builder code, but I don't have any attributes for first_start in my code
        # brought the dialog initiation out of the if statement
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        # if self.first_start == True:
        #     self.first_start = False
        self.export_dialog = ExportDialog()

        # show the dialog
        self.export_dialog.show()
        # initialise the global settings * these are unique for each user and saved on their hard drive
        self.global_settings = QgsSettings()

        # initialise the form variables for assignment later
        self.fp_output = None
        self.fld_uprn = None
        self.fld_auth_code = None
        self.b_lg_checked = None
        self.b_ad_checked = None
        self.b_updates_checked = None
        self.dt_export_date = None

        # initialise the data in the form and await instruction
        self.initialise_export_form()

    def initialise_export_form(self):
        """
        Load export settings, display the dialog, and trigger the data export processes.

        This function retrieves saved user preferences (like file paths and ID codes) 
        from the global settings to prepopulate the form. If the user clicks 'OK', 
        it saves the new inputs and launches the specific LG or AD export routines.

        Returns:
            None
        """
        # store the value of the output filepath from global settings, returns nothing if it doesn't exist
        s_output_filepath = self.global_settings.value("lsg_manager/output_fp")
        # store the value of the UPRN string from global settings, returns nothing if it doesn't exist
        s_uprn_value = self.global_settings.value("lsg_manager/uprn")
        # store the value of the auth code string from global settings, returns nothing if it doesn't exist
        s_auth_code_value = self.global_settings.value("lsg_manager/auth_code")

        # use global settings to populate the Output filepath UPRN and Auth Code fileds
        self.export_dialog.fpbExportPath.setFilePath(s_output_filepath)
        self.export_dialog.txtUPRN.setText(s_uprn_value)
        self.export_dialog.txtAuthCode.setText(s_auth_code_value)

        # Run the dialog event loop
        result = self.export_dialog.exec_()
        # See if OK was pressed
        if result:
            self.fp_output = self.export_dialog.fpbExportPath.filePath()
            self.fld_uprn = self.export_dialog.txtUPRN.text()
            self.fld_auth_code = self.export_dialog.txtAuthCode.text()
            self.b_lg_checked = self.export_dialog.chkExportLG.isChecked()
            self.b_ad_checked = self.export_dialog.chkExportAD.isChecked()
            self.b_updates_checked = self.export_dialog.chkUpdatesOnly.isChecked()
            self.dt_export_date = self.export_dialog.dtbExportDate.date()

            # # testing only - print to console
            # print(self.fp_output)
            # print(self.fld_uprn)
            # print(self.fld_auth_code)
            # print(self.b_lg_checked)
            # print(self.b_ad_checked)
            # print(self.b_updates_checked)
            # print(self.dt_export_date)

            # Save values from output, UPRN and Auth code to global settings
            self.global_settings.setValue("lsg_manager/output_fp", self.fp_output)
            self.global_settings.setValue("lsg_manager/uprn", self.fld_uprn)
            self.global_settings.setValue("lsg_manager/auth_code", self.fld_auth_code)

            # check which combination of checklists were selected and run required functions
            # if update only then
            # get the valid date

            # think of way to ensure that update works into workflow withput too much hassle
            # if LG update
            if self.b_lg_checked:
                layer_esu = LSGSettings.retrieve_layer(self, "lyr_esu")
                layer_sites = LSGSettings.retrieve_layer(self, "lyr_sites")
                # check ESU and Sites layers are valid and send over to export_lg
                if layer_esu.isValid() & layer_sites.isValid():
                    # print("Layers valid")
                    self.export_lg(layer_esu, layer_sites, self.fp_output)
                else:
                    print("Layers not valid")

            # if AD update
            if self.b_ad_checked:
                layer_interest = LSGSettings.retrieve_layer(self, "lyr_interests")
                layer_reinstatement = LSGSettings.retrieve_layer(self, "lyr_reinstatements")
                layer_designation = LSGSettings.retrieve_layer(self, "lyr_designation")
                # check Reinstatement, Interests and Designations layers are valid and send over to export_ad
                if layer_interest.isValid() & layer_reinstatement.isValid() & layer_designation.isValid():
                    # print("Layers valid")
                    self.export_ad(layer_interest, layer_reinstatement, layer_designation, self.fp_output)
                else:
                    print("Layers not valid")

            # if Alloy update
            # check ESU layer is valid and send over to export_Alloy

    # TODO:8 - write code to export updates only
    # TODO:9 - Write code to export ESU's with the additional data Alloy requires - Risk scores,
    #   HRCN, PRoW overlap - and any others that come later
    # TODO:10 - add error checking for ensuring esu and sites tables are good and error for if not
    # TODO:11 - add progress feedback for the user on each stage
    # TODO:12 - declare the row variables then use them to create the rows - to aid in readability

    # Also add functionality to select after a given date? or will it require a different way
    # off doing this? i.e. if something is updated in one table it will need to be pulled out
    # of the tables?
    # export lg/ad could be called with the desired expressions built in, or a call to a function
    # to define them within based on flags in the gui. this would avoid the need to rewrite them
    # again when exporting for Alloy. keep in mind that each table has a slightly different name
    # for the end_date field. this could be rationalised in a new table structure?

    def export_lg(self, esu_layer, sites_layer, file_path):
        """
        Export LG data to a CSV file following the GeoPlace DTF Specification.

        This function processes Street and ESU (Elementary Street Unit) data, 
        grouping ESUs by their associated site codes and writing them out in 
        a specific hierarchical format (Record Types 10, 11, 12, and 15).

        Args:
            esu_layer (QgsVectorLayer): The map layer containing ESU (line) data.
            sites_layer (QgsVectorLayer): The map layer containing Site/Street attribute data.
            file_path (str): The directory where the exported CSV should be saved.
        """

        write_path = file_path + "\\1050_lg.csv"
        run_date = dt.today().date()  # yyyy-mm-dd
        run_time = dt.today().strftime('%H%M%S')  # HHMMSS

        # declare this here because it is constant through all rows
        change_type = "I"

        # open writer
        # Open the file in write mode ('w')
        # Use newline='' as recommended by Python's csv module documentation
        with open(write_path, mode='w', newline='') as csv_file:
            writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_STRINGS)

            # this is the line number field which runs throughout the export for each stage
            # except the header, metadata and trailer lines
            pro_order = 1

            # write the header - DTF table 10
            # define the variables to be written, variable names match the DTF specification
            record_identifier = 10
            swa_org_name_text = "DERBYSHIRE"
            swa_org_ref = 1050
            volume_number = 1
            dtf_version = "8.1.2.10"
            file_type = "F"

            # define the row11 line
            header = [
                record_identifier,
                swa_org_name_text,
                swa_org_ref,
                run_date,
                volume_number,
                run_date,
                run_time,
                dtf_version,
                file_type]
            # write the row11 line to csv
            writer.writerow(header)

            # create the required expression string. this will be dependent on the type of export
            # required e.g. geogateway/alloy and lsg/ad. could be created automatically based on parametres?
            expression = '"SITE_STREET_END_DATE" IS NULL'
            # create the feature request
            sites_request = self.create_feature_request(expression)

            # create the required expression string. this will be dependent on the type of export
            # required e.g. geogateway/alloy and lsg/ad. could be created automatically based on parametres?
            expression = '"ESU_END_DATE" IS NULL'
            # create a list of required field names
            field_names = ['ESUID', 'SITE_CODE', 'Type_3', 'Type_4', 'Type_5', 'NCR']
            # create the feature request
            esu_request = self.create_feature_request(expression, attributes=True,
                                                      fields=field_names,
                                                      layer=esu_layer
                                                      )

            # create a list of the attributes returned by the feature request
            all_features = [feature for feature in esu_layer.getFeatures(esu_request)]

            # initialise a grouped dictionary to contain the esu data grouped by site code
            esu_data = defaultdict(list)

            # group the features by the site code
            for feature in all_features:
                site_code = feature['SITE_CODE']
                esu_data[site_code].append(feature)

            # add the Type_3 grouped features to esu_data
            for feature in all_features:
                site_code = feature['Type_3']
                esu_data[site_code].append(feature)

            # add the Type_4 grouped features to esu_data
            for feature in all_features:
                site_code = feature['Type_4']
                esu_data[site_code].append(feature)

            # add the Type_5 grouped features to esu_data
            for feature in all_features:
                site_code = feature['Type_5']
                esu_data[site_code].append(feature)

            # add the NCR grouped features to esu_data
            for feature in all_features:
                site_code = feature['NCR']
                esu_data[site_code].append(feature)

            # write the First stage - DTF tables 11, 15, 12 - SITE_CODE level

            # iterate over the sites table to obtain the data for the 11 & 15 records
            # and then find the relevant 12's in the ESU layer

            # get site_code from sites then get all the features from LSG

            for site_feature in sites_layer.getFeatures(sites_request):
                # assign row11 and 15 pro_orders in advance because row12's will be created first
                row11_pro_order = pro_order
                row15_pro_order = pro_order + 1
                pro_order += 2  # ensures the number is ready for the row12 records

                # get the site_code from the sites table that will be used
                usrn = site_feature["SITE_CODE"]

                # create a list to hold the row12 lines - they are written after the row11 & row15 records
                row12s = []
                # counter for number of ESUIDs - needed for row11
                esu_count = 0
                # get all the esuids that match the usrn
                esuid_list = esu_data.get(usrn, [])
                for esu_feature in esuid_list:
                    esu_pro_order = pro_order
                    pro_order += 1
                    esuid = int(esu_feature["ESUID"])
                    esu_count += 1

                    record_identifier = 12
                    usrn_version = 1
                    esu_version = 1

                    # define the row12 line
                    line = [
                        record_identifier,
                        change_type,
                        esu_pro_order,
                        usrn,
                        usrn_version,
                        esuid,
                        esu_version
                    ]
                    # change "" values to None so that the quotes are not printed
                    line = [None if item == "" or item == "NULL" else item for item in line]
                    # append each line to the row12s list for writing later
                    row12s.append(line)

                # write row11
                # define the variables to be written, variable names match the DTF specification
                record_identifier = 11
                record_type = site_feature["SITE_TYPE"]
                swa_org_ref_naming = site_feature["SITE_AUTH"]
                state = site_feature["SITE_STATE"]
                state_date = site_feature["SITE_START_DATE"].toPyDate()  # yyyy-mm-dd
                street_surface = site_feature["SITE_SURFACE"]
                version = 1
                record_entry_date = site_feature["SITE_ENTRY_DATE"].toPyDate()  # yyyy-mm-dd
                last_update_date = site_feature["SITE_LAST_UPDATE_DATE"].toPyDate()  # yyyy-mm-dd
                street_start_date = site_feature["SITE_START_DATE"].toPyDate()  # yyyy-mm-dd
                # End_Date field can be NULL or hold a date. the .toPyDate() function will error if value is NULL
                street_end_date = self.getEndDate(site_feature["SITE_STREET_END_DATE"])

                # try:
                #     site_feature["SITE_STREET_END_DATE"].toPyDate()
                # except:  # I don't know which exception this is
                #     street_end_date = ""
                # else:
                #     street_end_date = site_feature["SITE_STREET_END_DATE"].toPyDate()  # yyyy-mm-dd
                street_start_x = self.round_coords(site_feature["X1"])
                street_start_y = self.round_coords(site_feature["Y1"])
                street_end_x = self.round_coords(site_feature["X2"])
                street_end_y = self.round_coords(site_feature["Y2"])
                street_tolerance = site_feature["SITE_TOLERANCE"]

                # define the row11 line
                line = [
                    record_identifier,
                    change_type,
                    row11_pro_order,
                    usrn,
                    record_type,
                    swa_org_ref_naming,
                    state,
                    state_date,
                    street_surface,
                    version,
                    record_entry_date,
                    last_update_date,
                    street_start_date,
                    street_end_date,
                    street_start_x,
                    street_start_y,
                    street_end_x,
                    street_end_y,
                    street_tolerance,
                    esu_count
                ]
                # change "" values to None so that the quotes are not printed
                line = [None if item == "" or item == "NULL" else item for item in line]
                # write the row11 line to csv
                writer.writerow(line)

                # write row15
                # define the variables to be written, variable names match the DTF specification
                record_identifier = 15
                street_descriptor = site_feature["SITE_NAME"]
                locality_name = self.remove_null_value(site_feature["SITE_LOCALITY"])
                town_name = site_feature["SITE_TOWN"]
                administrative_are = "Derbyshire"
                language = "ENG"

                # define the row15 line
                line = [
                    record_identifier,
                    change_type,
                    row15_pro_order,
                    usrn,
                    street_descriptor,
                    locality_name,
                    town_name,
                    administrative_are,
                    language
                ]
                # change "" values to None so that the quotes are not printed
                line = [None if item == "" or item == "NULL" else item for item in line]
                # write the row15 line to csv
                writer.writerow(line)

                # write the row12's
                writer.writerows(row12s)

            # write the Second stage - DTF tables 13, 17 & 14 - ESUID level

            # create the required expression string. this will be dependent on the type of export
            # required e.g. geogateway/alloy and lsg/ad. could be created automatically based on parametres?
            expression = '"ESU_END_DATE" IS NULL'
            # create the feature request
            esu_request = self.create_feature_request(expression, geom=True)

            # get the features from the ESU layer that match the request criteria
            esu_features = esu_layer.getFeatures(esu_request)
            for esu_feature in esu_features:
                esuid = int(esu_feature["ESUID"])
                # assign row13 and 17 pro_orders in advance because row14's will be created first
                row13_pro_order = pro_order
                row17_pro_order = pro_order + 1
                pro_order += 2  # ensures the number is ready for the row14 records

                # initialise a count to record the number of vertices - needed in row13 record
                vertex_count = 0
                # get the geometry of the feature
                geom = esu_feature.geometry()
                # initialise a list to hold the row14 records - they are written afer the row13 and row17 records
                row14s = []
                # iterate over each vertex writing to row14s and increasing the vertex count and pro_order
                for vertex in geom.vertices():
                    vertex_count += 1
                    # define the variables to be written, variable names match the DTF specification
                    record_identifier = 14
                    esu_version = 1
                    esu_x_coord = self.round_coords(vertex.x())
                    esu_y_coord = self.round_coords(vertex.y())

                    # define the row14 line
                    line = [
                        record_identifier,
                        change_type,
                        pro_order,
                        esuid,
                        esu_version,
                        vertex_count,
                        esu_x_coord,
                        esu_y_coord
                    ]
                    # change "" values to None so that the quotes are not printed
                    line = [None if item == "" or item == "NULL" else item for item in line]
                    # append each line to the row12s list for writing later
                    row14s.append(line)
                    pro_order += 1

                # write the row13 record
                # define the variables to be written, variable names match the DTF specification
                record_identifier = 13
                esu_version = 1
                esu_tolerance = esu_feature["ESU_TOLERANCE"]
                esu_entry_date = esu_feature["ESU_ENTRY_DATE"].date().toPyDate()  # yyyy-mm-dd
                esu_start_date = esu_feature["ESU_START_DATE"].date().toPyDate()  # yyyy-mm-dd
                esu_last_update_date = esu_feature["ESU_LAST_UPDATE_DATE"].date().toPyDate()  # yyyy-mm-dd
                # End_Date field can be NULL or hold a date. the .toPyDate() function will error if value is NULL
                esu_end_date = self.getEndDate(esu_feature["ESU_END_DATE"])
                # try:
                #     site_feature["ESU_END_DATE"].toPyDate()
                # except:  # I don't know which exception this is
                #     esu_end_date = ""
                # else:
                #     esu_end_date = site_feature["ESU_END_DATE"].toPyDate()  # yyyy-mm-dd
                esu_direction = esu_feature["ESU_DIRECTION"]

                # define the row13 line
                line = [
                    record_identifier,
                    change_type,
                    row13_pro_order,
                    esuid,
                    esu_version,
                    vertex_count,
                    esu_tolerance,
                    esu_entry_date,
                    esu_start_date,
                    esu_last_update_date,
                    esu_end_date,
                    esu_direction
                ]
                # change "" values to None so that the quotes are not printed
                line = [None if item == "" or item == "NULL" else item for item in line]
                # write the row13 line to csv
                writer.writerow(line)

                # write the row17 record
                # define the variables to be written, variable names match the DTF specification
                record_identifier = 17
                sequence_number = 1
                highway_dedication_code = esu_feature["HD_DEDICATION_CODE"]
                record_entry_date = esu_feature["HD_ENTRY_DATE"].date().toPyDate()  # yyyy-mm-dd
                last_update_date = esu_feature["HD_LAST_UPDATE_DATE"].date().toPyDate()  # yyy-mm-dd
                record_end_date = ""  # always null because we only select live dates
                hd_start_date = esu_feature["HD_START_START"].date().toPyDate()  # yyyy-mm-dd
                # End_Date field can be NULL or hold a date. the .toPyDate() function will error if value is NULL
                hd_end_date = self.getEndDate(esu_feature["ESU_END_DATE"])
                # try:
                #     esu_feature["ESU_END_DATE"].toPyDate()
                # except:  # I don't know which exception this is
                #     hd_end_date = ""
                # else:
                #     hd_end_date = esu_feature["ESU_END_DATE"].toPyDate()  # yyyy-mm-dd
                hd_seasonal_start_date = ""
                hd_seasonal_end_date = ""
                hd_start_time = ""
                hd_end_time = ""
                hd_prow = esu_feature["HD_PROW"]
                hd_ncr = esu_feature["HD_NCR"]
                hd_quiet_route = 0
                hd_obstruction = 0
                hd_planning_order = 0
                hd_works_prohibited = 0

                # define the row17 line
                line = [
                    record_identifier,
                    change_type,
                    row17_pro_order,
                    esuid,
                    sequence_number,
                    highway_dedication_code,
                    record_entry_date,
                    last_update_date,
                    record_end_date,
                    hd_start_date,
                    hd_end_date,
                    hd_seasonal_start_date,
                    hd_seasonal_end_date,
                    hd_start_time,
                    hd_end_time,
                    hd_prow,
                    hd_ncr,
                    hd_quiet_route,
                    hd_obstruction,
                    hd_planning_order,
                    hd_works_prohibited
                ]
                # change "" values to None so that the quotes are not printed
                line = [None if item == "" or item == "NULL" else item for item in line]
                # write the row17 line to csv
                writer.writerow(line)

                # write the row14 lines to csv
                writer.writerows(row14s)

            # write the LSG Metadata - DTF table 29
            # define the variables to be written, variable names match the DTF specification
            record_identifier = 29
            ter_of_use = "Derbyshire"
            linked_data = ""
            ngaz_freq = "M"
            custodian_name = "Highways Systems"
            custodian_uprn = 10070103225
            uprn = 1050
            co_ord_system = "British National Grid"
            co_ord_unit = "Metres"
            class_scheme = "DEC-NSG v8.1"
            language = "ENG"
            character_set = "UTF - 8"
            content_motorway_trunk_road = 99
            content_private_street = 99
            content_prn = 99
            content_classified_road = 99
            content_prow_footpath = 0  # this needs updating
            content_prow_bridleway = 0  # this needs updating
            content_prow_restricted_byway = 0  # this needs updating
            content_prow_boat = 0  # this needs updating
            content_national_cycle_route = 0  # this needs updating

            # define the row29 line
            line = [
                record_identifier,
                ter_of_use,
                linked_data,
                ngaz_freq,
                custodian_name,
                custodian_uprn,
                uprn,
                co_ord_system,
                co_ord_unit,
                run_date,
                class_scheme,
                run_date,
                language,
                character_set,
                content_motorway_trunk_road,
                content_private_street,
                content_prn,
                content_classified_road,
                content_prow_footpath,
                content_prow_bridleway,
                content_prow_restricted_byway,
                content_prow_boat,
                content_national_cycle_route,
            ]
            # change "" values to None so that the quotes are not printed
            line = [None if item == "" else item for item in line]
            # write the row29 line to csv
            writer.writerow(line)

            # Write the Trailer - DTF table 99
            # define the variables to be written, variable names match the DTF specification
            record_identifier = 99
            next_volume_number = 0

            # define the row29 line
            row99 = [
                record_identifier,
                next_volume_number,
                pro_order,
                run_date,
                run_time
            ]
            # write the row29 line to csv
            writer.writerow(row99)

        # for testing
        end_time = dt.today().strftime('%H%M%S')
        time_taken = (float(end_time) - float(run_time)) / 60
        print(f"LG Time taken = {time_taken} minutes")
        iface.messageBar().pushMessage("Success", "LG Exported successfully", level=Qgis.Info, duration=3)

    def export_ad(self, interest_layer, reinstatement_layer, designation_layer, file_path):
        """
        Export Associated Data (AD) layers to CSV following DTF specifications.

        This function processes 'Interests', 'Reinstatements', and 'Designations' 
        associated with street records. It handles the formatting of Record Types 
        10, 61, 62, and 63 for the final export file.

        Args:
            interest_layer (QgsVectorLayer): Layer containing street interest data.
            reinstatement_layer (QgsVectorLayer): Layer containing reinstatement category data.
            designation_layer (QgsVectorLayer): Layer containing street designation data.
            file_path (str): The directory where the 1050_ad.csv file will be saved.
        """

        write_path = file_path + "\\1050_ad.csv"
        run_date = dt.today().date()  # yyyy-mm-dd
        run_time = dt.today().strftime('%H%M%S')  # HHMMSS

        # declare this here because it is constant through all rows
        change_type = "I"

        # open writer
        # Open the file in write mode ('w')
        # Use newline='' as recommended by Python's csv module documentation
        with open(write_path, mode='w', newline='') as csv_file:
            writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_STRINGS)

            # this is the line number field which runs throughout the export for each stage
            # except the header, metadata and trailer lines
            pro_order = 0

            # write the header - DTF table 10
            # define the variables to be written, variable names match the DTF specification
            record_identifier = 10
            swa_org_name_text = "DERBYSHIRE"
            swa_org_ref = 1050
            volume_number = 1
            dtf_version = "8.1.2.10"
            file_type = "F"

            # define the row11 line
            header = [
                record_identifier,
                swa_org_name_text,
                swa_org_ref,
                run_date,
                volume_number,
                run_date,
                run_time,
                dtf_version,
                file_type]
            # write the row11 line to csv
            writer.writerow(header)

            # write the interest record - DTF table 61 ##################################

            # create the required expression string. this will be dependent on the type of export
            # required e.g. geogateway/alloy and lsg/ad. could be created automatically
            expression = '"END_DATE" IS NULL'
            # create the feature request
            interest_request = self.create_feature_request(expression)

            # initialise a grouped dictionary to contain the esu data grouped by site code
            interest_data = defaultdict(list)

            # group the features by the site code
            for feature in interest_layer.getFeatures(interest_request):
                site_code = feature['SITE_CODE']
                interest_data[site_code].append(feature)

            # get a list of site_codes to iterate through
            site_code_list = list(interest_data.keys())

            # iterate through each site_code in the list
            for usrn in site_code_list:

                # counter for number of records with same site_code - needed for sequence no
                interest_count = 0
                # get all the interest records that match the site_code
                interest_list = interest_data.get(usrn, [])
                for interest_feature in interest_list:
                    pro_order += 1
                    interest_count += 1

                    # define the variables to be written, variable names match the DTF specification
                    record_identifier = 61
                    swa_org_ref_authority = 1050
                    district_ref_authority = interest_feature["AUTH"]
                    record_start_date = interest_feature["START_DATE"].toPyDate()  # yyyy-mm-dd
                    last_update_date = interest_feature["LAST_UPDATE_DATE"].toPyDate()  # yyyy-mm-dd
                    # End_Date field can be NULL or hold a date. the .toPyDate() function will error if value is NULL
                    record_end_date = self.getEndDate(interest_feature["END_DATE"])
                    # try:
                    #     interest_feature["END_DATE"].toPyDate()
                    # except:  # I don't know which exception this is
                    #     record_end_date = ""
                    # else:
                    #     record_end_date = interest_feature["END_DATE"].toPyDate()  # yyyy-mm-dd
                    whole_road = int(interest_feature["WHOLE_ROAD"])
                    asd_coordinate = self.add_zero_if_value(whole_road, 0)  # asd table not implemented yet
                    asd_coordinate_count = ""  # asd coordinate table not implemented yet
                    additional_street_location_text = self.remove_null_value(interest_feature["TEXT"])
                    swa_org_ref_maintaining = self.remove_null_value(interest_feature["MAINTAINANCE_AUTH"])
                    street_status = interest_feature["STATUS"]
                    interest_type = interest_feature["TYPE"]
                    start_x = self.round_coords(self.remove_null_value(interest_feature["X1"]))
                    start_y = self.round_coords(self.remove_null_value(interest_feature["Y1"]))
                    end_x = self.round_coords(self.remove_null_value(interest_feature["X2"]))
                    end_y = self.round_coords(self.remove_null_value(interest_feature["Y2"]))

                    # define the row61 line
                    line = [
                        record_identifier,
                        change_type,
                        pro_order,
                        usrn,
                        interest_count,
                        swa_org_ref_authority,
                        district_ref_authority,
                        record_start_date,
                        last_update_date,
                        record_end_date,
                        whole_road,
                        asd_coordinate,
                        asd_coordinate_count,
                        additional_street_location_text,
                        swa_org_ref_maintaining,
                        street_status,
                        interest_type,
                        start_x,
                        start_y,
                        end_x,
                        end_y
                    ]
                    # change "" values to None so that the quotes are not printed
                    line = [None if item == "" or item == "NULL" else item for item in line]
                    # write the row61 line to csv
                    writer.writerow(line)

            # write the construction (reinstatement) record - DTF table 62 ################

            # create the required expression string. this will be dependent on the type of export
            # required e.g. geogateway/alloy and lsg/ad. could be created automatically
            expression = '"END_DATE" IS NULL'
            # create the feature request
            reinstatement_request = self.create_feature_request(expression)

            # initialise a grouped dictionary to contain the esu data grouped by site code
            reinstatement_data = defaultdict(list)

            # group the features by the site code
            for feature in reinstatement_layer.getFeatures(reinstatement_request):
                site_code = feature['SITE_CODE']
                reinstatement_data[site_code].append(feature)

            # get a list of site_codes to iterate through
            site_code_list = list(reinstatement_data.keys())

            # iterate through each site_code in the list
            for usrn in site_code_list:

                # counter for number of records with same site_code - needed for sequence no
                reinstatement_count = 0
                # get all the interest records that match the site_code
                reinstatement_list = reinstatement_data.get(usrn, [])
                for reinstatement_feature in reinstatement_list:
                    pro_order += 1
                    reinstatement_count += 1

                    # define the variables to be written, variable names match the DTF specification
                    record_identifier = 62
                    usrn = reinstatement_feature["SITE_CODE"]
                    record_start_date = reinstatement_feature["START_DATE"].toPyDate()  # yyyy-mm-dd
                    last_update_date = reinstatement_feature["LAST_UPDATE_DATE"].toPyDate()  # yyyy-mm-dd
                    # End_Date field can be NULL or hold a date. the .toPyDate() function will error if value is NULL
                    record_end_date = self.getEndDate(reinstatement_feature["END_DATE"])
                    # try:
                    #     reinstatement_feature["END_DATE"].toPyDate()
                    # except:  # I don't know which exception this is
                    #     record_end_date = ""
                    # else:
                    #     record_end_date = reinstatement_feature["END_DATE"].toPyDate()  # yyyy-mm-dd
                    construction_type = 1  # alaways 1?
                    reinstatement_type_code = reinstatement_feature["TYPE"]
                    aggregate_abbrasion_value = ""  # not implemented yet
                    polished_stone_value = ""  # not implemented yet
                    frost_heave_susceptibility = ""  # not implemented yet
                    stepped_joint = ""  # not implemented yet
                    whole_road = int(reinstatement_feature["WHOLE_ROAD"])
                    asd_coordinate = self.add_zero_if_value(whole_road, 0)  # asd_table not implemented yet
                    asd_coordinate_count = ""  # asd_table not implemented yet
                    construction_location_text = self.remove_null_value(reinstatement_feature["TEXT"])
                    construction_start_x = self.round_coords(self.remove_null_value(reinstatement_feature["X1"]))
                    construction_start_y = self.round_coords(self.remove_null_value(reinstatement_feature["Y1"]))
                    construction_end_x = self.round_coords(self.remove_null_value(reinstatement_feature["X2"]))
                    construction_end_y = self.round_coords(self.remove_null_value(reinstatement_feature["Y2"]))
                    construction_description = ""  # always blank?
                    swa_org_ref_consultant = 1050  # add manually for now but the "AUTH" field needs cleaning up
                    district_ref_consultant = self.remove_null_value(reinstatement_feature["DISTRICT_AUTH"])

                    # define the row62 line
                    line = [
                        record_identifier,
                        change_type,
                        pro_order,
                        usrn,
                        record_start_date,
                        last_update_date,
                        record_end_date,
                        reinstatement_count,
                        construction_type,
                        reinstatement_type_code,
                        aggregate_abbrasion_value,
                        polished_stone_value,
                        frost_heave_susceptibility,
                        stepped_joint,
                        whole_road,
                        asd_coordinate,
                        asd_coordinate_count,
                        construction_location_text,
                        construction_start_x,
                        construction_start_y,
                        construction_end_x,
                        construction_end_y,
                        construction_description,
                        swa_org_ref_consultant,
                        district_ref_consultant
                    ]
                    # change "" values to None so that the quotes are not printed
                    line = [None if item == "" or item == "NULL" else item for item in line]
                    # write the row62 line to csv
                    writer.writerow(line)

            # write the special designation record - DTF table 63 #######################

            # create the required expression string. this will be dependent on the type of export
            # required e.g. geogateway/alloy and lsg/ad. could be created automatically
            expression = '"END_DATE" IS NULL'
            # create the feature request
            designation_request = self.create_feature_request(expression)

            # initialise a grouped dictionary to contain the esu data grouped by site code
            designation_data = defaultdict(list)

            # group the features by the site code
            for feature in designation_layer.getFeatures(designation_request):
                site_code = feature['SITE_CODE']
                designation_data[site_code].append(feature)

            # get a list of site_codes to iterate through
            site_code_list = list(designation_data.keys())

            # iterate through each site_code in the list
            for usrn in site_code_list:

                # counter for number of records with same site_code - needed for sequence no
                designation_count = 0
                # get all the interest records that match the site_code
                designation_list = designation_data.get(usrn, [])
                for designation_feature in designation_list:
                    pro_order += 1
                    designation_count += 1

                    # define the variables to be written, variable names match the DTF specification
                    record_identifier = 63
                    usrn = designation_feature["SITE_CODE"]
                    street_special_desig_code = designation_feature["DESIGNATION_CODE"]
                    whole_road = int(designation_feature["WHOLE_ROAD"])
                    record_start_date = designation_feature["START_DATE"].toPyDate()  # yyyy-mm-dd
                    last_update_date = designation_feature["LAST_UPDATE_DATE"].toPyDate()  # yyyy-mm-dd
                    # End_Date field can be NULL or hold a date. the .toPyDate() function will error if value is NULL
                    record_end_date = self.getEndDate(designation_feature["END_DATE"])
                    # try:
                    #     designation_feature["END_DATE"].toPyDate()
                    # except:  # I don't know which exception this is
                    #     record_end_date = ""
                    # else:
                    #     record_end_date = designation_feature["END_DATE"].toPyDate()  # yyyy-mm-dd
                    asd_coordinate = self.add_zero_if_value(whole_road, 0)  # asd_table not implemented yet
                    asd_coordinate_count = ""  # asd_table not implemented yet
                    special_desig_periodicty_code = designation_feature["PERIODICITY_CODE"]
                    special_desig_location_text = self.remove_null_value(designation_feature["LOCATION_TEXT"])
                    special_desig_start_x = self.round_coords(self.remove_null_value(designation_feature["X1"]))
                    special_desig_start_y = self.round_coords(self.remove_null_value(designation_feature["Y1"]))
                    special_desig_end_x = self.round_coords(self.remove_null_value(designation_feature["X2"]))
                    special_desig_end_y = self.round_coords(self.remove_null_value(designation_feature["Y2"]))
                    special_desig_start_date = ""
                    special_desig_end_date = ""
                    special_desig_start_time = str(designation_feature["START_TIME"]).rjust(4, "0")  # ensure HHMM
                    special_desig_end_time = str(designation_feature["END_TIME"]).rjust(4, "0")  # ensure HHMM
                    special_desig_description = self.remove_null_value(designation_feature["DESCRIPTION"])
                    swa_org_ref_consultant = designation_feature["DISTRICT_AUTH"]
                    district_ref_consultant = designation_feature["AUTH"]
                    source_text = self.remove_null_value(designation_feature["TEXT"])

                    # define the row63 line
                    line = [
                        record_identifier,
                        change_type,
                        pro_order,
                        usrn,
                        designation_count,
                        street_special_desig_code,
                        whole_road,
                        record_start_date,
                        last_update_date,
                        record_end_date,
                        asd_coordinate,
                        asd_coordinate_count,
                        special_desig_periodicty_code,
                        special_desig_location_text,
                        special_desig_start_x,
                        special_desig_start_y,
                        special_desig_end_x,
                        special_desig_end_y,
                        special_desig_start_date,
                        special_desig_end_date,
                        special_desig_start_time,
                        special_desig_end_time,
                        special_desig_description,
                        swa_org_ref_consultant,
                        district_ref_consultant,
                        source_text
                    ]
                    # change "" values to None so that the quotes are not printed
                    line = [None if item == "" or item == "NULL" else item for item in line]
                    # write the row63 line to csv
                    writer.writerow(line)

            # write the metadata record - DTF table 69 ##################################

            # define the variables to be written, variable names match the DTF specification
            record_identifier = 69
            ter_of_use = "Derbyshire"
            linked_data = ""
            ngaz_freq = "M"
            custodian_name = "Highways Systems"  # change to Network Intelligence in-line with new structure name?
            custodian_uprn = 10070103225  # this is the code from the settings, change it so not hard coded
            auth_code = 1050
            co_ord_system = "British National Grid"
            co_ord_unit = "Metres"
            class_scheme = "DEC-NSG v8.1"
            language = "ENG"
            character_set = "UTF - 8"
            md_protected_street = 0
            md_traffic_sensitive = 99
            md_sed = 0
            md_proposed_sed = 50
            md_level_crossing = 0
            md_env_sensitive_area = 0
            md_structures_not_sed = 0
            md_pipelines_and_cables = 0
            md_priority_lanes = 0
            md_lane_rental = 0
            md_early_notification = 0
            md_special_events = 0
            md_parking = 0
            md_ped_cross_and_signals = 0
            md_speed_limit = 0
            md_trans_auth_app = 0
            md_strategic_route = 0
            md_street_light = 0
            md_drainage_and_flood = 0
            md_unusual_layout = 0
            md_local_consider = 0
            md_winter_main_route = 0
            md_hgv_route = 0
            hd_emergency_route = 0

            # define the row69 line
            line = [
                record_identifier,
                ter_of_use,
                linked_data,
                ngaz_freq,
                custodian_name,
                custodian_uprn,
                auth_code,
                co_ord_system,
                co_ord_unit,
                run_date,
                class_scheme,
                run_date,
                language,
                character_set,
                md_protected_street,
                md_traffic_sensitive,
                md_sed,
                md_proposed_sed,
                md_level_crossing,
                md_env_sensitive_area,
                md_structures_not_sed,
                md_pipelines_and_cables,
                md_priority_lanes,
                md_lane_rental,
                md_early_notification,
                md_special_events,
                md_parking,
                md_ped_cross_and_signals,
                md_speed_limit,
                md_trans_auth_app,
                md_strategic_route,
                md_street_light,
                md_drainage_and_flood,
                md_unusual_layout,
                md_local_consider,
                md_winter_main_route,
                md_hgv_route,
                hd_emergency_route
            ]
            # change "" values to None so that the quotes are not printed
            line = [None if item == "" or item == "NULL" else item for item in line]
            # write the row69 line to csv
            writer.writerow(line)
            # write the trailer record - DTF table 99 ###################################

            # define the variables to be written, variable names match the DTF specification
            record_identifier = 99
            next_volume_number = 0
            pro_order += 1

            # define the row99 line
            line = [
                record_identifier,
                next_volume_number,
                pro_order,
                run_date,
                run_time
            ]
            # write the row99 line to csv
            writer.writerow(line)
            # for testing
            end_time = dt.today().strftime('%H%M%S')
            time_taken = (float(end_time) - float(run_time)) / 60
            print(f"AD Time taken = {time_taken} minutes")
            iface.messageBar().pushMessage("Success", "AD Exported successfully", level=Qgis.Info, duration=3)

    @staticmethod
    def remove_null_value(value):
        """
        Convert 'None' or 'Null' data into an empty string for CSV export.

        In GIS data, empty fields often return a 'None' type. Writing 'None' 
        directly to a CSV can break data specifications; this helper ensures 
        those fields appear as a clean, blank space instead.

        Args:
            value: The data value to check (could be a String, Int, or None).

        Returns:
            The original value if it exists, or an empty string ("") if the value is null.
        """
        # --- 1. CHECK: If the value has content, send it back ---
        if value:
            return value
            
        # --- 2. FALLBACK: If value is None or Empty, return a blank string ---
        return ""

    @staticmethod
    def add_zero_if_value(value_check, value_target):
        """
        Check a value against a target and return a zero if they match.

        This is a helper function used to ensure specific database fields 
        meet DTF requirements by providing a '0' as a default value when 
        certain conditions are met, rather than leaving the field empty.

        Args:
            value_check: The current data value you are inspecting.
            value_target: The specific value that triggers the zero (e.g., a "None" or a specific code).

        Returns:
            int or str: Returns 0 if a match is found, otherwise returns an empty string ("").
        """
        # --- 1. COMPARISON: Check if the input matches our specific target ---
        if value_check == value_target:
            return 0
        
        # --- 2. DEFAULT: Return a blank string if no match is found ---
        return ""

    @staticmethod
    def round_coords(coord):
        """
        Round coordinate values to two decimal places for spatial accuracy.

        This helper ensures that X/Y coordinates meet the DTF specification 
        formatting. It safely ignores non-numeric data (like empty strings 
        or NULLs) to prevent the code from crashing during the export process.

        Args:
            coord: The coordinate value to be processed (expected Float or Int).

        Returns:
            The coordinate rounded to 2 decimal places if it's a number, 
            otherwise returns the original value.
        """

        # --- 1. TYPE CHECK: Verify if the input is a valid number ---
        # We exclude Booleans because Python treats True/False as 1/0
        if isinstance(coord, numbers.Number) and not isinstance(coord, bool):
            # --- 2. FORMAT: Round to 2 decimal places (e.g., 123.456 -> 123.46) ---
            return round(coord, 2)
            
        # --- 3. FALLBACK: Return original value if it's a string/NULL ---
        return coord

    @staticmethod
    def create_feature_request(expression, sort="SITE_CODE",
                               geom=False, attributes=False, **kwargs):
        """
        Build a customized QgsFeatureRequest to filter and sort map data.

        Instead of downloading every piece of data from a layer (which is slow), 
        this function creates a 'request' that only asks for exactly what we 
        need—specific rows, specific columns, or no geometry.

        Args:
            expression (str): The SQL-style filter (e.g., '"STATUS" = 1').
            sort (str): The field name to sort by. Defaults to "SITE_CODE".
            geom (bool): If False, ignores spatial data to speed up the request.
            attributes (bool): If True, only fetches the columns listed in 'fields'.
            **kwargs: Expects 'fields' (list) and 'layer' (QgsVectorLayer) if attributes is True.

        Returns:
            QgsFeatureRequest: The configured request object ready for getFeatures().
        """

        # --- 1. INITIALISE: Create the empty request object ---
        request = QgsFeatureRequest()

        # --- 2. GEOMETRY: Speed up processing if we only need text/table data ---
        if not geom:
            request.setFlags(QgsFeatureRequest.NoGeometry)

        # --- 3. ATTRIBUTES: Limit the 'columns' returned to save memory ---
        if attributes:
            fields = kwargs.get('fields', None)
            layer = kwargs.get('layer', None)
            # This tells QGIS: "Only look at these specific fields in this layer"
            request.setSubsetOfAttributes(fields, layer.fields())

        # --- 4. FILTER: Apply the SQL-style expression ---
        # Only features matching this string (e.g., 'Date is NULL') will be returned
        request.setFilterExpression(expression)

        # --- 5. SORTING: Define how the results should be ordered ---
        sort_clause = QgsFeatureRequest.OrderByClause(sort)
        orderby = QgsFeatureRequest.OrderBy([sort_clause])
        request.setOrderBy(orderby)

        return request

    @staticmethod
    def getEndDate(end_date_field):
        """
        Safely convert a QGIS date field to a Python date or a blank string.

        In QGIS, 'NULL' dates cause errors when you try to convert them 
        to Python dates. This function acts as a safety wrapper: if a 
        date exists, it formats it; if it's NULL, it returns an empty 
        string instead of crashing the export.

        Args:
            end_date_field: The raw value from the QGIS attribute table.

        Returns:
            str: A formatted date (yyyy-mm-dd) or an empty string for NULL values.
        """

        # --- 1. ATTEMPT: Try to convert the field to a standard Python date ---
        try:
            # .toPyDate() is the standard QGIS method for date conversion
            street_end_date = end_date_field.toPyDate()
            
        # --- 2. CATCH: Handle cases where the field is NULL or invalid ---
        except:  
            # If conversion fails (common with NULLs), we default to a blank string
            street_end_date = ""
            
        # --- 3. RETURN: Pass back the safe value for the CSV writer ---
        return street_end_date
