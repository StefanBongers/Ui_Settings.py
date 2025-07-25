# -*- coding: utf-8 -*-
import datetime
import mariadb
import pandas as pd
from PyQt5.QtCore import QDateTime

import rberi_lib
from PyQt5.QtWidgets import QDialog
from Beringungsoberflaeche.tagebucheintrag import Ui_Dialog


class Tagebucheintrag(QDialog):
    def __init__(self, db_eng: mariadb.Connection, debug: bool = False, current_user: str = "reit", parent=None, **kwargs):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.engine = db_eng
        self.debug = debug
        self.user = current_user
        self.df_ringer = pd.DataFrame()

        self.ui.DTE_zeitstempel.setDateTime(QDateTime.currentDateTime())

        try:
            self.df_ringer = pd.read_sql("SELECT nachname, vorname, ringer_new FROM ringer WHERE jahr = '" +
                                         str(datetime.date.today().year) + "'", self.engine)
        except Exception as err:
            rberi_lib.QMessageBoxB('ok', 'Datenbankfehler.', "Datenbankfehler.", str(err)).exec_()
            return

        if isinstance(kwargs['ringer'], list) and len(kwargs['ringer']) > 0:
            self.ui.CMB_ringer.addItems(kwargs['ringer'])
        else:
            for index, inhalt in self.df_ringer.iterrows():
                self.ui.CMB_ringer.addItem(inhalt['nachname'] + ", " + inhalt['vorname'])

        # connections:
        self.ui.BTN_close.clicked.connect(self.close)
        self.ui.BTN_save.clicked.connect(self.save)

    def save(self):
        if self.debug:
            print(self.get_id_from_ringer())
        sql_text = ("INSERT INTO tagebuch (datum, beringer_ref, beringer_name, ringnummer, fehlertext) VALUES ('" +
                    self.ui.DTE_zeitstempel.dateTime().toString("yyyy-MM-dd hh:mm:ss") + "', '" +
                    self.get_id_from_ringer() + "', '" + self.ui.CMB_ringer.currentText() + "', '" +
                    self.ui.LE_ringnummer.text() + "', '" + self.ui.PTE_fehlertext.toPlainText() + "')")
        if self.debug:
            print("SQL_TEXT : " + sql_text)
        try:
            cursor = self.engine.cursor()
            cursor.execute(sql_text)
            self.engine.commit()
            cursor.close()
        except Exception as err:
            rberi_lib.QMessageBoxB('ok', 'Datensatz konnte nicht gespeichert werden. Schwerer Ausnahmefehler! Siehe '
                                         'Details!', 'Ausnahmefehler', str(err)).exec_()
            return

    def get_id_from_ringer(self) -> str:
        name = self.ui.CMB_ringer.currentText()
        names = name.split(',')
        nachname = names[0].strip()
        vorname = names[1].strip()

        return_value = self.df_ringer.query("nachname == @nachname & vorname == @vorname")['ringer_new'].iloc[0]
        return return_value





