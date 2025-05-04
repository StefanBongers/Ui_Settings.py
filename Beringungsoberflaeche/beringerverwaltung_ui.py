# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QEvent
import pandas as pd


class CMB_nachname_class(QtWidgets.QComboBox):
    def focusOutEvent(self, event):
        Ui_beringerverwaltung.lookup_ringers()
        super().focusOutEvent(event)

class Ui_beringerverwaltung(QtWidgets.QDialog):
    def __init__(self, userlevel='nok', ringer_df=pd.DataFrame({})):
        super().__init__(parent=None)
        self.ringer_df = ringer_df
        # vorn_sort = self.ringer_df.drop_duplicates('vorname', keep=False)
        #self.CMB_vorname.addItems(vorn_sort['vorname'].sort_values())
        self.setupUi()
        self.BTN_speichern.setEnabled(False)
        self.userlevel = userlevel
        if userlevel != 'ok':
            self.BTN_speichern.setVisible(False)

        self.CMB_vorname.setVisible(False)
        self.label_2.setVisible(False)
        self.TBL_beringer.setVisible(True)
        self.CMB_nachname.setFocus()

        self.neu_flag = False
        self.edit_flag = False
        self.row_to_save = {}

        self.setup_ringer()

    def setupUi(self):
        self.setObjectName("beringerverwaltung")
        self.resize(1132, 341)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        #sizePolicy.setHorizontalStretch(0)
        #sizePolicy.setVerticalStretch(0)
        #sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        #self.setSizePolicy(sizePolicy)
        self.layoutWidget = QtWidgets.QWidget(self)
        self.layoutWidget.setGeometry(QtCore.QRect(20, 20, 1101, 301))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.CMB_nachname = QtWidgets.QComboBox(self.layoutWidget)
        self.CMB_nachname.setMinimumSize(QtCore.QSize(200, 0))
        self.CMB_nachname.setObjectName("CMB_nachname")
        self.gridLayout.addWidget(self.CMB_nachname, 1, 0, 1, 1)
        self.label = QtWidgets.QLabel(self.layoutWidget)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 1, 2, 1, 1)
        self.CMB_vorname = QtWidgets.QComboBox(self.layoutWidget)
        self.CMB_vorname.setMinimumSize(QtCore.QSize(200, 0))
        self.CMB_vorname.setObjectName("CMB_vorname")
        self.gridLayout.addWidget(self.CMB_vorname, 1, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.layoutWidget)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 0, 1, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.TBL_beringer = QtWidgets.QTableWidget(self.layoutWidget)
        self.TBL_beringer.setEnabled(True)
        self.TBL_beringer.setMaximumSize(QtCore.QSize(16777215, 150))
        self.TBL_beringer.setObjectName("TBL_beringer")
        self.TBL_beringer.setColumnCount(11)
        self.TBL_beringer.setRowCount(1)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setVerticalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(5, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(6, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(7, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(8, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(9, item)
        item = QtWidgets.QTableWidgetItem()
        self.TBL_beringer.setHorizontalHeaderItem(10, item)
        self.TBL_beringer.horizontalHeader().setDefaultSectionSize(100)
        self.TBL_beringer.verticalHeader().setVisible(False)
        self.TBL_beringer.verticalHeader().setHighlightSections(True)
        self.verticalLayout.addWidget(self.TBL_beringer)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.BTN_speichern = QtWidgets.QPushButton(self.layoutWidget)
        self.BTN_speichern.setObjectName("BTN_speichern")
        self.horizontalLayout_2.addWidget(self.BTN_speichern)
        self.BTN_neu = QtWidgets.QPushButton(self.layoutWidget)
        self.BTN_neu.setObjectName("BTN_neu")
        self.horizontalLayout_2.addWidget(self.BTN_neu)
        self.BTN_abbrechen = QtWidgets.QPushButton(self.layoutWidget)
        self.BTN_abbrechen.setObjectName("BTN_abbrechen")
        self.horizontalLayout_2.addWidget(self.BTN_abbrechen)
        self.BTN_aktivieren = QtWidgets.QPushButton(self.layoutWidget)
        self.BTN_aktivieren.setObjectName("BTN_aktivieren")
        self.horizontalLayout_2.addWidget(self.BTN_aktivieren)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.BTN_schliessen = QtWidgets.QPushButton(self.layoutWidget)
        self.BTN_schliessen.setMinimumSize(QtCore.QSize(200, 25))
        self.BTN_schliessen.setObjectName("BTN_schliessen")
        self.horizontalLayout_3.addWidget(self.BTN_schliessen)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem2)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        self.verticalLayout.addLayout(self.verticalLayout_2)

        self.retranslateUi()

        self.TBL_beringer.cellChanged.connect(self.check_for_names)
        self.BTN_neu.clicked.connect(self.neuerEintrag)
        self.BTN_speichern.clicked.connect(self.speichern)
        self.BTN_abbrechen.clicked.connect(self.abbrechen)
        self.BTN_schliessen.clicked.connect(self.close)
        self.BTN_aktivieren.clicked.connect(self.aktivieren)

    def retranslateUi(self):
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("beringerverwaltung", "Beringerverwaltung"))
        self.label.setText(_translate("beringerverwaltung", "Nachname:"))
        self.label_2.setText(_translate("beringerverwaltung", "Vorname:"))
        item = self.TBL_beringer.verticalHeaderItem(0)
        item.setText(_translate("beringerverwaltung", "1"))
        item = self.TBL_beringer.horizontalHeaderItem(0)
        item.setText(_translate("beringerverwaltung", "Vorname"))
        item = self.TBL_beringer.horizontalHeaderItem(1)
        item.setText(_translate("beringerverwaltung", "Nachname"))
        item = self.TBL_beringer.horizontalHeaderItem(2)
        item.setText(_translate("beringerverwaltung", "Straße"))
        item = self.TBL_beringer.horizontalHeaderItem(3)
        item.setText(_translate("beringerverwaltung", "PLZ"))
        item = self.TBL_beringer.horizontalHeaderItem(4)
        item.setText(_translate("beringerverwaltung", "Stadt"))
        item = self.TBL_beringer.horizontalHeaderItem(5)
        item.setText(_translate("beringerverwaltung", "Land"))
        item = self.TBL_beringer.horizontalHeaderItem(6)
        item.setText(_translate("beringerverwaltung", "Telefon"))
        item = self.TBL_beringer.horizontalHeaderItem(7)
        item.setText(_translate("beringerverwaltung", "Fax"))
        item = self.TBL_beringer.horizontalHeaderItem(8)
        item.setText(_translate("beringerverwaltung", "Email"))
        item = self.TBL_beringer.horizontalHeaderItem(9)
        item.setText(_translate("beringerverwaltung", "Anmerkung"))
        item = self.TBL_beringer.horizontalHeaderItem(10)
        item.setText(_translate("beringerverwaltung", "Wiederfanganzeige"))
        self.BTN_speichern.setText(_translate("beringerverwaltung", "Speichern"))
        self.BTN_neu.setText(_translate("beringerverwaltung", "Neu..."))
        self.BTN_abbrechen.setText(_translate("beringerverwaltung", "Abbrechen"))
        self.BTN_aktivieren.setText(_translate("beringerverwaltung", "Beringer für aktuelles Jahr freischalten"))
        self.BTN_schliessen.setText(_translate("beringerverwaltung", "Schließen"))

    def setup_ringer(self):
        list_ringer = []
        # self.ringer_df.drop_duplicates('nachname', keep='first', inplace=True)
        self.ringer_df.sort_values(by='nachname', inplace=True)
        self.ringer_df.dropna(how='any')

        txt2append = ""
        for index, ringer_serie in self.ringer_df.iterrows():
            if len(str(ringer_serie['nachname'])) > 0:
                txt2append = str(ringer_serie['nachname'])
                if len(str(ringer_serie['vorname'])) > 0:
                    txt2append += ", " + ringer_serie['vorname']
            if len(txt2append) > 0:
                list_ringer.append(txt2append)

        self.CMB_nachname.addItems(list_ringer)
        self.CMB_nachname.setCurrentIndex(-1)
        self.CMB_nachname.currentIndexChanged.connect(self.lookup_ringers)

    def create_start_state(self):
        self.CMB_nachname.setCurrentIndex(-1)
        self.CMB_nachname.setEnabled(True)
        self.BTN_neu.setEnabled(True)
        self.BTN_speichern.setEnabled(False)
        if self.userlevel != 'ok':
            self.BTN_speichern.setVisible(False)
        self.CMB_vorname.setCurrentIndex(-1)
        self.CMB_vorname.setVisible(False)
        self.label_2.setVisible(False)
        self.TBL_beringer.clearContents()
        self.TBL_beringer.setRowCount(0)
        self.neu_flag = False
        self.edit_flag = False

    def aktivieren(self):
        if self.TBL_beringer.rowCount() < 0:
            return
        else:
            if self.TBL_beringer.cellWidget(0, 10).checkState == Qt.Checked:
                wiederfang = 0
            else:
                wiederfang = 1
            self.row_to_save = {
                "vorname": self.TBL_beringer.item(0, 0).text(),
                "nachname": self.TBL_beringer.item(0, 1).text(),
                "strasse": self.TBL_beringer.item(0, 2).text(),
                "plz": self.TBL_beringer.item(0, 3).text(),
                "stadt": self.TBL_beringer.item(0, 4).text(),
                "land": self.TBL_beringer.item(0, 5).text(),
                "telefon": self.TBL_beringer.item(0, 6).text(),
                "fax": self.TBL_beringer.item(0, 7).text(),
                "email": self.TBL_beringer.item(0, 8).text(),
                "anmerkung": self.TBL_beringer.item(0, 9).text(),
                "wiederfang": wiederfang,
                "only-year": 1
            }

            self.create_start_state()
            self.accept()

    def check_for_names(self,row,col):
        if self.CMB_nachname.currentIndex() < 0 and not self.neu_flag:
            self.BTN_speichern.setEnabled(False)
            return
        if (self.TBL_beringer.item(0,0)) and (self.TBL_beringer.item(0,1)) and \
                (self.TBL_beringer.item(0,0).text() != "") and \
                (self.TBL_beringer.item(0,1).text() != ""):
            self.BTN_speichern.setEnabled(True)
        else:
            self.BTN_speichern.setEnabled(False)

    def abbrechen(self):
        self.create_start_state()

    def neuerEintrag(self):
        self.CMB_nachname.setEnabled(False)
        self.CMB_vorname.setVisible(False)
        self.label_2.setVisible(False)
        self.neu_flag = True
        self.edit_flag = True
        self.TBL_beringer.setVisible(True)
        self.CMB_nachname.setCurrentIndex(-1)

        new_df = pd.DataFrame({"vorname": [""], "nachname": [""], "strasse": [""], "plz": [""], "ort": [""], "land": [""],
                               "telefon": [""], "telefax": [""], "email": [""], "anmerkung": [""], "zeige_wiederfaenge": 0})
        self.fill_table(new_df)
        self.BTN_speichern.setVisible(True)

    def get_row_to_save(self):
        return self.row_to_save

    def speichern(self):
        if not self.neu_flag:
            msgb = QtWidgets.QMessageBox()
            msgb.setWindowTitle("Speichern ...")
            msgb.setText("Den Datensatz wirklich überschreiben?")
            msgb.setIcon(QtWidgets.QMessageBox.Warning)
            msgb.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)

            if msgb.exec_() != QtWidgets.QMessageBox.Yes:
                return

        if self.TBL_beringer.cellWidget(0, 10).checkState == Qt.Checked:
            wiederfang = 0
        else:
            wiederfang = 1
        self.row_to_save = {
            "vorname": self.TBL_beringer.item(0,0).text(),
            "nachname": self.TBL_beringer.item(0,1).text(),
            "strasse": self.TBL_beringer.item(0, 2).text(),
            "plz": self.TBL_beringer.item(0, 3).text(),
            "stadt": self.TBL_beringer.item(0, 4).text(),
            "land": self.TBL_beringer.item(0, 5).text(),
            "telefon": self.TBL_beringer.item(0, 6).text(),
            "fax": self.TBL_beringer.item(0, 7).text(),
            "email": self.TBL_beringer.item(0, 8).text(),
            "anmerkung": self.TBL_beringer.item(0, 9).text(),
            "wiederfang": wiederfang,
            "only-year": 0
        }
        self.create_start_state()

        self.accept()

    def lookup_ringers(self):
        if self.CMB_nachname.currentIndex() < 0:
            return
        txt = self.CMB_nachname.currentText()
        nachname = txt.split(", ")[0]
        if len(txt.split(", ")) > 1:
            vorname = txt.split(", ")[1]
        else:
            vorname = ''
        df_new = pd.DataFrame()
        for index, value in self.ringer_df.iterrows():
            if str(value['nachname']) == nachname and str(value['vorname']) == vorname:
                df_new = df = pd.concat([df_new, value.to_frame().T])

        if not df_new.empty:
            self.fill_table(df_new)
            self.TBL_beringer.setVisible(True)
            self.TBL_beringer.setEnabled(True)

    def fill_table(self, dataframe):
        self.TBL_beringer.setRowCount(len(dataframe))
        if len(dataframe) > 0:
            for i in range(len(dataframe)):
                self.TBL_beringer.setItem(i, 0, QTableWidgetItem(dataframe.iloc[i]["vorname"]))
                self.TBL_beringer.setItem(i, 1, QTableWidgetItem(dataframe.iloc[i]["nachname"]))
                self.TBL_beringer.setItem(i, 2, QTableWidgetItem(dataframe.iloc[i]["strasse"]))
                self.TBL_beringer.setItem(i, 3, QTableWidgetItem(str(dataframe.iloc[i]["plz"])))
                self.TBL_beringer.setItem(i, 4, QTableWidgetItem(dataframe.iloc[i]["ort"]))
                self.TBL_beringer.setItem(i, 5, QTableWidgetItem(dataframe.iloc[i]["land"]))
                self.TBL_beringer.setItem(i, 6, QTableWidgetItem(dataframe.iloc[i]["telefon"]))
                self.TBL_beringer.setItem(i, 7, QTableWidgetItem(dataframe.iloc[i]["telefax"]))
                self.TBL_beringer.setItem(i, 8, QTableWidgetItem(dataframe.iloc[i]["email"]))
                self.TBL_beringer.setItem(i, 9, QTableWidgetItem(dataframe.iloc[i]["anmerkung"]))

                cell_widget = QtWidgets.QWidget()
                chk_bx = QtWidgets.QCheckBox()
                if dataframe.iloc[i]["zeige_wiederfaenge"] == 0:
                    chk_bx.setCheckState(Qt.Checked)
                elif dataframe.iloc[i]["zeige_wiederfaenge"] == 1:
                    chk_bx.setCheckState(Qt.Unchecked)
                lay_out = QtWidgets.QHBoxLayout(cell_widget)
                lay_out.addWidget(chk_bx)
                lay_out.setAlignment(Qt.AlignCenter)
                lay_out.setContentsMargins(0, 0, 0, 0)
                cell_widget.setLayout(lay_out)
                cell_widget.checkState = chk_bx.checkState()
                self.TBL_beringer.setCellWidget(i, 10, cell_widget)