# -*- coding: utf-8 -*-
import datetime
from sqlalchemy import Engine
import sqlalchemy as sa
import pandas as pd
from PyQt5.QtCore import QDateTime

import rberi_lib
from PyQt5.QtWidgets import QDialog, QMessageBox
from Beringungsoberflaeche.tagebucheintrag import Ui_Dialog


class Tagebucheintrag(QDialog):
    def __init__(self, db_eng: Engine, debug: bool = False, current_user: str = "reit", parent=None, **kwargs):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.engine = db_eng
        self.debug = debug
        self.user = current_user
        self.df_ringer = pd.DataFrame()
        self.saved = False

        self.ui.DTE_zeitstempel.setDateTime(QDateTime.currentDateTime())

        try:
            with self.engine.connect() as conn_local:
                self.df_ringer = pd.read_sql_query(sa.text("SELECT nachname, vorname, ringer_new FROM ringer WHERE jahr = '" +
                                                   str(datetime.date.today().year) + "'"), conn_local)
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
            with self.engine.connect() as conn_local:
                conn_local.execute(sa.text(sql_text))
                conn_local.commit()
            self.saved = True
            self.close()
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

    def close(self):
        if not self.saved:
            if rberi_lib.QMessageBoxB('yn', 'Vorher speichern?', 'Speichern?').exec_() == QMessageBox.Yes:
                self.save()
        super().close()
