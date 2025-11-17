# from qgis.core import QgsApplication
from qgis.PyQt.QtCore import pyqtSlot
import os
from qgis.core import QgsSettings

from ..gui.forms.Export_Dialog import ExportDialog

# TODO:6 - write code to export LG
# TODO:7 - write code to export AD
# TODO:8 - write code to export updates only


class ExportData:
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

            # TODO:6 - write code to export LG
            # TODO:7 - write code to export AD
            # TODO:8 - write code to export updates only
