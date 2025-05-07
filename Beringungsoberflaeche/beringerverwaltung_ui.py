# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt
import pandas as pd
from Beringungsoberflaeche.beringer.untitled.beringerverwaltung import Ui_beringerverwaltung


class CMB_nachname_class(QtWidgets.QComboBox):
    def focusOutEvent(self, event):
        Dialog_beringerverwaltung.lookup_ringers()
        super().focusOutEvent(event)

class Dialog_beringerverwaltung(QtWidgets.QDialog):
    def __init__(self, userlevel='nok', ringer_df=pd.DataFrame({})):
        super().__init__(parent=None)
        self.ringer_df = ringer_df
        # vorn_sort = self.ringer_df.drop_duplicates('vorname', keep=False)
        #self.CMB_vorname.addItems(vorn_sort['vorname'].sort_values())

        self.ui = Ui_beringerverwaltung()
        self.ui.setupUi(self)

        self.ui.TBL_beringer.cellChanged.connect(self.check_for_names)
        self.ui.BTN_neu.clicked.connect(self.neuerEintrag)
        self.ui.BTN_speichern.clicked.connect(self.speichern)
        self.ui.BTN_abbrechen.clicked.connect(self.abbrechen)
        self.ui.BTN_schliessen.clicked.connect(self.close)
        self.ui.BTN_aktivieren.clicked.connect(self.aktivieren)

        # self.setupUi() // alte Fassung! Blöd!
        self.ui.BTN_speichern.setEnabled(False)
        self.userlevel = userlevel
        if userlevel != 'ok':
            self.ui.BTN_speichern.setVisible(False)

        self.ui.CMB_nachname_2.setVisible(False)
        self.ui.label_2.setVisible(False)
        self.ui.TBL_beringer.setVisible(True)
        self.ui.TBL_beringer.resizeColumnsToContents()
        self.ui.CMB_nachname.setFocus()

        self.neu_flag = False
        self.edit_flag = False
        self.row_to_save = {}

        self.setup_ringer()

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

        self.ui.CMB_nachname.addItems(list_ringer)
        self.ui.CMB_nachname.setCurrentIndex(-1)
        self.ui.CMB_nachname.currentIndexChanged.connect(self.lookup_ringers)

    def create_start_state(self):
        self.ui.CMB_nachname.setCurrentIndex(-1)
        self.ui.CMB_nachname.setEnabled(True)
        self.ui.BTN_neu.setEnabled(True)
        self.ui.BTN_speichern.setEnabled(False)
        if self.userlevel != 'ok':
            self.ui.BTN_speichern.setVisible(False)
        self.ui.CMB_nachname_2.setCurrentIndex(-1)
        self.ui.CMB_nachname_2.setVisible(False)
        self.ui.label_2.setVisible(False)
        self.ui.TBL_beringer.clearContents()
        self.ui.TBL_beringer.setRowCount(0)
        self.neu_flag = False
        self.edit_flag = False

    def aktivieren(self):
        if self.ui.TBL_beringer.rowCount() < 0:
            return
        else:
            if self.ui.TBL_beringer.cellWidget(0, 10).checkState == Qt.Checked:
                wiederfang = 0
            else:
                wiederfang = 1
            self.row_to_save = {
                "vorname": self.ui.TBL_beringer.item(0, 0).text(),
                "nachname": self.ui.TBL_beringer.item(0, 1).text(),
                "strasse": self.ui.TBL_beringer.item(0, 2).text(),
                "plz": self.ui.TBL_beringer.item(0, 3).text(),
                "stadt": self.ui.TBL_beringer.item(0, 4).text(),
                "land": self.ui.TBL_beringer.item(0, 5).text(),
                "telefon": self.ui.TBL_beringer.item(0, 6).text(),
                "fax": self.ui.TBL_beringer.item(0, 7).text(),
                "email": self.ui.TBL_beringer.item(0, 8).text(),
                "anmerkung": self.ui.TBL_beringer.item(0, 9).text(),
                "wiederfang": wiederfang,
                "only-year": 1
            }

            self.create_start_state()
            self.accept()

    def check_for_names(self,row,col):
        if self.ui.CMB_nachname.currentIndex() < 0 and not self.neu_flag:
            self.ui.BTN_speichern.setEnabled(False)
            return
        if (self.ui.TBL_beringer.item(0,0)) and (self.ui.TBL_beringer.item(0,1)) and \
                (self.ui.TBL_beringer.item(0,0).text() != "") and \
                (self.ui.TBL_beringer.item(0,1).text() != ""):
            self.ui.BTN_speichern.setEnabled(True)
        else:
            self.ui.BTN_speichern.setEnabled(False)

    def abbrechen(self):
        self.create_start_state()

    def neuerEintrag(self):
        self.ui.CMB_nachname.setEnabled(False)
        self.ui.CMB_nachname_2.setVisible(False)
        self.ui.label_2.setVisible(False)
        self.neu_flag = True
        self.edit_flag = True
        self.ui.TBL_beringer.setVisible(True)
        self.ui.CMB_nachname.setCurrentIndex(-1)

        new_df = pd.DataFrame({"vorname": [""], "nachname": [""], "strasse": [""], "plz": [""], "ort": [""], "land": [""],
                               "telefon": [""], "telefax": [""], "email": [""], "anmerkung": [""], "zeige_wiederfaenge": 0})
        self.fill_table(new_df)
        self.ui.BTN_speichern.setVisible(True)

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

        if self.ui.TBL_beringer.cellWidget(0, 10).checkState == Qt.Checked:
            wiederfang = 0
        else:
            wiederfang = 1
        self.row_to_save = {
            "vorname": self.ui.TBL_beringer.item(0,0).text(),
            "nachname": self.ui.TBL_beringer.item(0,1).text(),
            "strasse": self.ui.TBL_beringer.item(0, 2).text(),
            "plz": self.ui.TBL_beringer.item(0, 3).text(),
            "stadt": self.ui.TBL_beringer.item(0, 4).text(),
            "land": self.ui.TBL_beringer.item(0, 5).text(),
            "telefon": self.ui.TBL_beringer.item(0, 6).text(),
            "fax": self.ui.TBL_beringer.item(0, 7).text(),
            "email": self.ui.TBL_beringer.item(0, 8).text(),
            "anmerkung": self.ui.TBL_beringer.item(0, 9).text(),
            "wiederfang": wiederfang,
            "only-year": 0
        }
        self.create_start_state()

        self.accept()

    def lookup_ringers(self):
        if self.ui.CMB_nachname.currentIndex() < 0:
            return
        txt = self.ui.CMB_nachname.currentText()
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
            self.ui.TBL_beringer.setVisible(True)
            self.ui.TBL_beringer.setEnabled(True)

    def fill_table(self, dataframe):
        self.ui.TBL_beringer.setRowCount(len(dataframe))
        if len(dataframe) > 0:
            for i in range(len(dataframe)):
                self.ui.TBL_beringer.setItem(i, 0, QTableWidgetItem(dataframe.iloc[i]["vorname"]))
                self.ui.TBL_beringer.setItem(i, 1, QTableWidgetItem(dataframe.iloc[i]["nachname"]))
                self.ui.TBL_beringer.setItem(i, 2, QTableWidgetItem(dataframe.iloc[i]["strasse"]))
                self.ui.TBL_beringer.setItem(i, 3, QTableWidgetItem(str(dataframe.iloc[i]["plz"])))
                self.ui.TBL_beringer.setItem(i, 4, QTableWidgetItem(dataframe.iloc[i]["ort"]))
                self.ui.TBL_beringer.setItem(i, 5, QTableWidgetItem(dataframe.iloc[i]["land"]))
                self.ui.TBL_beringer.setItem(i, 6, QTableWidgetItem(dataframe.iloc[i]["telefon"]))
                self.ui.TBL_beringer.setItem(i, 7, QTableWidgetItem(dataframe.iloc[i]["telefax"]))
                self.ui.TBL_beringer.setItem(i, 8, QTableWidgetItem(dataframe.iloc[i]["email"]))
                self.ui.TBL_beringer.setItem(i, 9, QTableWidgetItem(dataframe.iloc[i]["anmerkung"]))

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
                self.ui.TBL_beringer.setCellWidget(i, 10, cell_widget)
                self.ui.TBL_beringer.resizeColumnsToContents()