import sys
from typing import List

from PyQt5 import QtCore, QtGui, QtWidgets
#from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QFrame, QLabel, QLineEdit, QComboBox, QPushButton, QGridLayout, QApplication, QDialogButtonBox
from qtpy.QtCore import Slot, QObject






# Rückgabewerte:
# Tupel: (err, user, pw1, lvl)
# err = errorcode:
# 0 = alles ok (username gefüllt, pw1 gefüllt und gleich pw2)
# 1 = username leer
# 2 = pw1 leer
# 3 = pw2 leer
# 4 = pw1 ungleich pw2
# 5 = Benutzerlevel leer
# -1 = Abbruch gedrückt
#user = eingetragenener username etc.

class new_user_ui(QtWidgets.QDialog):
    level: list[str]

    def __init__(self, level=None, parent=None):
        super().__init__(parent)
        if level is None or type(level) != list:
            self.level = ['1']
        frame_style = QFrame.Sunken | QFrame.Panel
        self.resize(350,250)

        self._username_label = QLabel("Benutzername*")
        #self._username_label.setFrameStyle(frame_style)
        self.INP_username = QLineEdit()
        self.INP_username.setFrame(True)
        #self.INP_username.setValidator() #"abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ")


        self._password_label = QLabel("Passwort*")
        #self._password_label.setFrameStyle(frame_style)
        self.INP_password = QLineEdit()

        self.INP_password.setEchoMode(QLineEdit.Password)

        self._password2_label = QLabel("Passwort wiederholen*")
        #self._password2_label.setFrameStyle(frame_style)
        self.INP_password2 = QLineEdit()
        self.INP_password2.setEchoMode(QLineEdit.Password)

        self._level_label = QLabel("Benutzerlevel*")
        # self._level_label.setFrameStyle(frame_style)
        self.CMB_level = QComboBox()
        self.CMB_level.addItems(self.level)

        self.btnBox = QDialogButtonBox()
        self.btnBox.setStandardButtons(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.btnBox.rejected.connect(self.clickedCancel)
        self.btnBox.accepted.connect(self.clickedSave)

        # self.BTN_save.clicked.connect(self.accept)
        # self.BTN_cancel.clicked.connect(self.clickedCancel)
        self.INP_username.textChanged.connect(self._inputChanged)
        self.INP_password.textChanged.connect(self._inputChanged)
        self.INP_password2.textChanged.connect(self._inputChanged)

        self._status_label = QLabel("Status:")
        self._status_content = QLabel()

        self.setWindowTitle("Benutzer anlegen")

        layout = QGridLayout(self)

        layout.addWidget(self._username_label, 0, 0)
        layout.addWidget(self.INP_username, 0, 1)
        layout.addWidget(self._password_label, 1, 0)
        layout.addWidget(self.INP_password, 1, 1)
        layout.addWidget(self._password2_label, 2, 0)
        layout.addWidget(self.INP_password2, 2, 1)
        layout.addWidget(self._level_label, 3, 0)
        layout.addWidget(self.CMB_level, 3, 1)
        # layout.addWidget(self.BTN_save, 4, 0)
        # layout.addWidget(self.BTN_cancel, 4, 1)
        layout.addWidget(self._status_label,4,0)
        layout.addWidget(self._status_content, 4, 1)
        layout.addWidget(self.btnBox, 5, 0)

    def __get_input(self):
        user = self.INP_username.text()
        pw1 = self.INP_password.text()
        pw2 = self.INP_password2.text()
        lvl = self.CMB_level.currentText()
        return (user, pw1, pw2, lvl)

    @Slot()
    def _inputChanged(self):
        super().__init__()
        user = self.INP_username.text()
        pw1 = self.INP_password.text()
        pw2 = self.INP_password2.text()
        lvl = self.CMB_level.currentText()
        err = 0
        status = ""
        if len(user) <= 0:
            status += "Username ist leer!\n"
            err = 1
        if len(pw1) <= 0 or user == pw1:
            status += "Passwort ist leer oder gleich Benutzername!\n"
            err = 2
        if len(pw2) <= 0:
            status += "Passwort Wiederholung ist leer!\n"
            err = 3
        if pw1 != pw2:
            status += "Passwörter stimmen nicht überein.\n"
            err = 4
        if len(lvl) <= 0:
            status += "Kein Benutzerlevel ausgewählt.\n"
            err = 5
        self._status_content.setText(status)
        if err == 0:
            status = "ok"
            self._status_content.setText("Benutzer kann angelegt werden.")

        return status

    @Slot()
    def clickedSave(self):
        print("accepted! gedrückt")
        if self._inputChanged() == "ok":
            try:
                return self.__get_input()
            finally:
                self.done(0)
                self.close()
        else:
            self._status_content.setText(self._inputChanged())

    @Slot()
    def clickedCancel(self):
        print("rejected! gedrückt")
        self.INP_password.clear()
        self.INP_password2.clear()
        self.INP_username.clear()
        try:
            return (None, None, None, None)
        finally:
            self.close()
            #sys.exit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    newui = new_user_ui()
    sys.exit(newui.exec())
