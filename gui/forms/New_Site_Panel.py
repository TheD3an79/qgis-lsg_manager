import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtCore import QRegularExpression
from qgis.PyQt.QtGui import QRegularExpressionValidator

# Load the UI file
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'New_Site_Panel.ui'))


class NewSitePanel(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(NewSitePanel, self).__init__(parent)
        self.setupUi(self)
        # Connect any specific signals/slots here if needed, e.g.
        # self.my_button.clicked.connect(self.my_function)

        regex_letters = QRegularExpression(r"^[a-zA-Z\s]*$")
        regex_numbers = QRegularExpression(r"^\d*$")
        regex_coordinate = QRegularExpression(r"^[\d\.]*$")

        # # set the text boxes to only accept the relevant types of characters e.g. letters or numbers
        self.txtUSRN.setValidator(QRegularExpressionValidator(regex_numbers, self.txtUSRN))  # limit to numbers
        self.txtName.setValidator(QRegularExpressionValidator(regex_letters, self.txtName))  # limit to letters
        self.txtLocality.setValidator(QRegularExpressionValidator(regex_letters, self.txtLocality))  # limit to letters
        self.txtTown.setValidator(QRegularExpressionValidator(regex_letters, self.txtTown))  # limit to letters
        self.txtX1.setValidator(QRegularExpressionValidator(regex_coordinate, self.txtX1))  # limit to numbers with decimals
        self.txtY1.setValidator(QRegularExpressionValidator(regex_coordinate, self.txtY1))  # limit to numbers with decimals
        self.txtX2.setValidator(QRegularExpressionValidator(regex_coordinate, self.txtX2))  # limit to numbers with decimals
        self.txtY2.setValidator(QRegularExpressionValidator(regex_coordinate, self.txtY2))  # limit to numbers with decimals

    # Add custom methods for your form's logic here


