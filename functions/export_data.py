# from qgis.core import QgsApplication
import numbers
import os
import csv
import pandas as pd
from datetime import datetime as dt
from qgis.PyQt.QtCore import pyqtSlot
from qgis.core import QgsSettings
from qgis.core import QgsVectorLayer
from qgis.core import QgsFeatureRequest
from qgis.core import QgsExpression
from qgis.PyQt.QtCore import QDate

from collections import defaultdict

from ..gui.forms.Export_Dialog import ExportDialog
from .lsg_settings import LSGSettings

# TODO:6 - write code to export LG
# TODO:7 - write code to export AD
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
        """setting/reading glabal settings and populating the export_dialog form,
        and directing to the correct export function"""
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

    # TODO:7 - write code to export AD
    # TODO:8 - write code to export updates only
    # TODO:9 - Write code to export ESU's with the additional data Alloy requires - Risk scores,
    #   HRCN, PRoW overlap - and any others that come later
    # TODO:10 - add error checking for ensuring esu and sites tables are good and error for if not
    # TODO:11 - add progress feedback for the user on each stage
    # TODO:12 - declare the row variables then use them to create the rows - to aid in readability

    # Also add functionality to select after a given date? or will it require a different way
    # off doing this? i.e. if something is updated in one table it will need to be pulled out
    # of the tables?

    def export_lg(self, esu_layer, sites_layer, file_path):
        """Export the LG data in the format set by the Goeplace DTF Specification"""

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

            # order the sites table by its SITE_CODE attribute

            # Create the request object
            sites_request = QgsFeatureRequest()
            # create the sql expression to filter with (all live features)
            sites_filter_expression_string = f'"SITE_STREET_END_DATE" IS NULL'
            # add the expression to the request
            sites_request.setFilterExpression(sites_filter_expression_string)
            # Define the sort clause: sort by the "SITE_CODE" field
            sites_clause = QgsFeatureRequest.OrderByClause('SITE_CODE')
            # Create the order using the defiend clause
            sites_orderby = QgsFeatureRequest.OrderBy([sites_clause])
            # Add the sort clause to the request
            sites_request.setOrderBy(sites_orderby)

            # get the esu_feaures and put them into a dictionary for quick access rather
            # than calling getFeatures() multiple times which adds a large time cost
            # select all live ESUs from the esu_layer then order by the siteCode
            # Create the request object and ensure no geometry is copied and only the required attributes
            esu_request = QgsFeatureRequest() \
                .setFlags(QgsFeatureRequest.NoGeometry) \
                .setSubsetOfAttributes(['ESUID', 'SITE_CODE', 'Type_3', 'Type_4', 'Type_5', 'NCR'], esu_layer.fields())
            # create the sql expression to filter with (all live features)
            esu_filter_expression_string = f'"ESU_END_DATE" IS NULL'
            # add the expression to the request
            esu_request.setFilterExpression(esu_filter_expression_string)
            # Define the sort clause: sort by the "SITE_CODE" field
            esu_clause = QgsFeatureRequest.OrderByClause('SITE_CODE')
            # Create the order using the defiend clause
            esu_orderby = QgsFeatureRequest.OrderBy([esu_clause])
            # Add the sort clause to the request
            esu_request.setOrderBy(esu_orderby)

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



            # write the First stage - DTF tables 11, 15, 17 - SITE_CODE level

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
                street_end_date = ""  # always null because we only select live dates
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

            # select all live ESUs from the esu_layer sorted on the siteCode.
            esu_request = QgsFeatureRequest()
            # create the sql expression to filter with (all live features)
            esu_filter_expression_string = f'"ESU_END_DATE" IS NULL'
            # add the expression to the request
            esu_request.setFilterExpression(esu_filter_expression_string)
            # Define the sort clause: sort by the "SITE_CODE" field
            esu_clause = QgsFeatureRequest.OrderByClause('SITE_CODE')
            # Create the order using the defiend clause
            esu_orderby = QgsFeatureRequest.OrderBy([esu_clause])
            # Add the sort clause to the request
            esu_request.setOrderBy(esu_orderby)

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
                esu_end_date = ""  # always null because we only select live dates
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
                hd_end_date = ""  # always null because we only select live dates
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

    def export_ad(self, interest_layer, reinstatement_layer, designation_layer, file_path):
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

            # Create the request object
            interest_request = QgsFeatureRequest()
            # create the sql expression to filter with (all live features)
            interest_filter_expression_string = f'"END_DATE" IS NULL'
            # add the expression to the request
            interest_request.setFilterExpression(interest_filter_expression_string)
            # Define the sort clause: sort by the "SITE_CODE" field
            interest_clause = QgsFeatureRequest.OrderByClause('SITE_CODE')
            # Create the order using the defiend clause
            interest_orderby = QgsFeatureRequest.OrderBy([interest_clause])
            # Add the sort clause to the request
            interest_request.setOrderBy(interest_orderby)

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
                    record_end_date = ""  # always blank because we only select live features
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

            # Create the request object
            reinstatement_request = QgsFeatureRequest()
            # create the sql expression to filter with (all live features)
            reinstatement_filter_expression_string = f'"END_DATE" IS NULL'
            # add the expression to the request
            reinstatement_request.setFilterExpression(reinstatement_filter_expression_string)
            # Define the sort clause: sort by the "SITE_CODE" field
            reinstatement_clause = QgsFeatureRequest.OrderByClause('SITE_CODE')
            # Create the order using the defiend clause
            reinstatement_orderby = QgsFeatureRequest.OrderBy([reinstatement_clause])
            # Add the sort clause to the request
            reinstatement_request.setOrderBy(reinstatement_orderby)

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
                    record_end_date = ""  # always blank because we only select live features
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

            # Create the request object
            designation_request = QgsFeatureRequest()
            # create the sql expression to filter with (all live features)
            designation_filter_expression_string = f'"END_DATE" IS NULL'
            # add the expression to the request
            designation_request.setFilterExpression(designation_filter_expression_string)
            # Define the sort clause: sort by the "SITE_CODE" field
            designation_clause = QgsFeatureRequest.OrderByClause('SITE_CODE')
            # Create the order using the defiend clause
            designation_orderby = QgsFeatureRequest.OrderBy([designation_clause])
            # Add the sort clause to the request
            designation_request.setOrderBy(designation_orderby)

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
                    record_end_date = ""  # always blank because we only select live features
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

    @staticmethod
    def remove_null_value(value):
        """ removes the null value that is printed to csv and returns a blank char"""
        if value:
            return value
        return ""

    @staticmethod
    def add_zero_if_value(value_check, value_target):
        """ returns a zero if the value matches the target value"""
        if value_check == value_target:
            return 0
        return ""

    @staticmethod
    def round_coords(coord):
        """ if the variable is a number then round it, if not then just return the value
            this is needed because NULL values are replaced with blank strings"""
        if isinstance(coord, numbers.Number) and not isinstance(coord, bool):
            return round(coord, 2)
        return coord
