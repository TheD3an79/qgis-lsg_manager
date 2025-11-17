import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

# Load the UI file
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'Export_Dialog.ui'))


class ExportDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ExportDialog, self).__init__(parent)
        self.setupUi(self)
        # Connect any specific signals/slots here if needed, e.g.
        # self.my_button.clicked.connect(self.my_function)

        # Connect the updates only checkbox signal to toggle visibility of the date field
        self.chkUpdatesOnly.toggled.connect(self.toggle_date_field)

        # Ensure the date field is hidden initially if the checkbox is not checked
        self.dtbExportDate.setVisible(self.chkUpdatesOnly.isChecked())
        # Ensure the date field label is hidden initially if the checkbox is not checked
        self.lbl_date.setVisible(self.chkUpdatesOnly.isChecked())

    # Add custom methods for your form's logic here

    def toggle_date_field(self, checked):
        """Toggles the visibility of the date field and label."""
        self.dtbExportDate.setVisible(checked)
        self.lbl_date.setVisible(checked)
