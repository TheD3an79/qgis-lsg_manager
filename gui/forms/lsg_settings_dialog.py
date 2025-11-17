import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

# Load the UI file
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'Settings_Dialog.ui'))


class SettingsDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)
        # Connect any specific signals/slots here if needed, e.g.
        # self.my_button.clicked.connect(self.my_function)

    # Add custom methods for your form's logic here
