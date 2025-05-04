# -*- coding: utf-8 -*-
import datetime

import mariadb
import numpy as np
import pandas as pd
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QMessageBox, QTableWidgetItem, QTableWidget, QGridLayout, QPushButton, QHeaderView, )
from mariadb import Connection

import rberi_lib
from basic_definitions import constants
from Beringungsoberflaeche.ringserieneingabe.dialogringserieneingabe import Ui_DialogRingserienEingabe


def write_df_to_qtable(df, table):
    for i in range(table.rowCount()):
        table.removeRow(i)
    table.setRowCount(df.shape[0])

    # getting data from df is computationally costly so convert it to array first
    df_array = df.values
    for row in range(df.shape[0]):
        for col in range(df.shape[1]):
            table.setItem(row, col, QTableWidgetItem(str(df_array[row, col])))


def check_integrity_ringseries(engine: Connection) -> bool:
    try:
        engine.ping()
    except Connection.InterfaceError:
        rberi_lib.QMessageBoxB('ok', 'Keine Datenbankverbindung. Programm endet.', 'Datenbankproblem').exec_()
        return False
    sql_t = "SELECT ringtypRef, status FROM " + constants().get_tbl_name_ringserie()
    proof_dict = {}
    engine.reset()  # damit wir sicher die neueste Datenbank haben

    try:
        df = pd.read_sql(sql_t, engine)
    except Exception as excp:
        rberi_lib.QMessageBoxB('ok', 'Konnte die Ringserien nicht aus der DB lesen. Siehe Details.',
                               "Fehlermeldung", ['Aus ringserienverwaltung.py / check_integrity_ringseries',
                                                 'Exception:', str(excp)]).exec_()
        return False

    for index, row in df.iterrows():
        if row.ringtypRef in proof_dict:
            if row.status == 1 and row.status in proof_dict[row.ringtypRef]:
                return False
            elif row.status == 1 and row.status not in proof_dict[row.ringtypRef]:
                proof_dict[row.ringtypRef] += [row.status]
        else:
            proof_dict[row.ringtypRef] = [row.status]
    return True


def activate_next_package(engine: Connection, ringtypref: int) -> int:
    try:
        engine.ping()
    except Connection.InterfaceError:
        return -1
    if ringtypref is None:
        return -1
    df = pd.read_sql('SELECT ringserieID, paketnummer, status FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                     'WHERE ' + 'status = 0 and ringtypRef = ' + str(ringtypref), engine)
    if df.empty:
        rberi_lib.QMessageBoxB('ok', f'Es konnte zum Ringtyp "{ringtypref}" kein lagerhaltiges Paket '
                                     'gefunden werden. Ganz schlecht. Stationsleitung und/oder Management informieren!',
                               'Ringnummernfehler.').exec_()
        return -1
    else:
        paket_min_nr = df['paketnummer'].min(numeric_only=True)
        if paket_min_nr >= 0:
            ringserie_id = df['ringserieID'].loc[df['paketnummer'].idxmin()]
            sql_t = ('UPDATE ' + constants().get_tbl_name_ringserie() + ' ' +
                     'SET status = 1, letztevergebenenummer = 0 WHERE ringserieID = ' + str(ringserie_id))
            try:
                cursor = engine.cursor()
                cursor.execute(sql_t)
                engine.commit()
                cursor.close()
                return ringserie_id
            except Exception as excp:
                rberi_lib.QMessageBoxB('ok', 'Konnte das nächste Ringnummernpaket nicht aktiveren. '
                                             'Vermutlich keine Verbindung zur Datenbank.', 'Datenbankfehler',
                                       f'Exception: {excp}').exec_()
                return -1
        else:
            rberi_lib.QMessageBoxB('ok', f'Es konnte zum Ringtyp "{ringtypref}" kein lagerhaltiges Paket '
                                         'gefunden werden. Es existieren vielleicht inaktive Pakete? Blöd. Ganz blöd.',
                                   'Ringnummernfehler.').exec_()
            return -1


def get_ringtypref(engine: Connection, art: str, sex: int = 1) -> int:
    """

    :param engine:
    :param art:
    :param sex:
    :return:
    -1 : no connection
    -2 : Datenbankfehler (Abfrage)
    -3 : art nicht gefunden
    -4 : keine weibliche Ringnnummernreferenz gefunden
    -5 : allgemeiner Fehler
    """
    try:
        engine.ping()
    except mariadb.InterfaceError:
        return -1
    try:
        art_df = pd.read_sql("SELECT ringtypMaleRef, ringtypFemaleRef FROM arten WHERE deutsch = '" + art + "'", engine)
    except Exception as err:
        return -2
    if art_df.empty:
        return .3
    if sex == 1:
        return int(art_df.iat[0, 0])
    elif sex == 2:
        try:
            return_val = int(art_df.iat[0, 1])
        except Exception as err:
            return -4
    else:
        return -5

def get_last_given_nmb(engine: Connection, ringtypref: int = None, ringserie: str = None, ) -> int:
    try:
        engine.ping()
    except Connection.InterfaceError:
        return -1
    if ringtypref is None and ringserie is None:
        return -1
    if ringtypref is not None and ringserie is not None:
        df = pd.read_sql('SELECT ringserie, ringtypRef FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringserie="' + str(ringserie) + '" and ringtypRef =' + str(ringtypref), engine)
        if df.empty:
            return -1
    if ringserie is not None and ringtypref is None:
        df = pd.read_sql('SELECT ringserie, ringtypRef FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringserie="' + str(ringserie) + '" AND status = 1', engine)
        if df.empty:
            return -1
        ringtypref = int(df['ringtypRef'].iloc[0])
    if ringtypref is not None:
        df = pd.read_sql('SELECT * FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringtypRef =' + str(ringtypref) + ' ' + 'and status = 1', engine)
        if df.empty:
            return -1
        if df.shape[0] != 1:
            return -1
        if df['letztevergebenenummer'].iloc[0] is None:
            last_nmb = int(df['ringnummerStart'].iloc[0]) - 1
        else:
            last_nmb = int(df['letztevergebenenummer'].iloc[0])
            if last_nmb == 0:
                last_nmb = int(df['ringnummerStart'].iloc[0]) - 1
        return last_nmb
    else:
        return -1


def get_next_nr(engine: Connection, ringtypref: int = None, ringserie: str = None, ) -> (int, int, str):
    """
    Ermittelt die nächste zu vergebende Ringnummer anhand der übergebenen Parameter RingtypRef oder Ringserie.
    Es wird KEINE Änderung vorgenommen sondern nur die nächste Ringnummer ermittelt und zurückgegeben.
    :param engine: Die Connection zur Database
    :param ringtypref: Die Referenznummer des Ringtyps
    :param ringserie: Die Ringserie (2-stellig)
    :return:
    Tuple: \n
    int: nächste Ringnummer der Serie/des Ringtyps ODER -1 bei Fehler
    int: Anzahl verbleibender Ringe auf Paket/Schnur ODER -1 bei Fehler
    str: 2-stellige Ringserie ODER Fehlertext bei Fehler
    """
    try:
        engine.ping()
    except Connection.InterfaceError:
        return -1, -1, 'Keine Verbindung zur Datenbank.'
    if ringtypref is None and ringserie is None:
        return -1, -1, 'Keine Serie und kein Ringtyp übergeben. Mindestens eine Angabe ist erforderlich.'
    if ringtypref is not None and ringserie is not None:
        df = pd.read_sql('SELECT ringserie, ringtypRef FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringserie="' + str(ringserie) + '" and ringtypRef =' + str(ringtypref), engine)
        if df.empty:
            return -1, -1, f'Ringserie "{ringserie}" und Ringtyp "{ringtypref}" passen nicht zueinander.'
    if ringserie is not None and ringtypref is None:
        df = pd.read_sql('SELECT ringserie, ringtypRef FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringserie="' + str(ringserie) + '" AND status = 1', engine)
        if df.empty:
            return (-1, -1, f'Zur Ringserie {ringserie} gibt es kein aktives Ringnummernpaket. Bitte Stationsleitung '
                            f'informieren, denn es muss ein entsprechendes Paket aktiviert werden.')
        ringtypref = int(df['ringtypRef'].iloc[0])
    if ringtypref is not None:
        df = pd.read_sql('SELECT * FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringtypRef =' + str(ringtypref) + ' ' + 'and status = 1', engine)
        if df.empty:
            return (-1, -1, f'Zum Ringtyp {ringtypref} gibt es kein aktives Ringnummernpaket. Bitte Stationsleitung '
                            f'informieren, denn es muss ein entsprechendes Paket aktiviert werden.')
        if df.shape[0] != 1:
            return -1, -1, f'Es wurde mehr als ein aktives Ringnummernpaket gefunden. Das darf nicht sein!'
        if df['letztevergebenenummer'].iloc[0] is None:
            last_nmb = int(df['ringnummerStart'].iloc[0]) - 1
        else:
            last_nmb = int(df['letztevergebenenummer'].iloc[0])
            if last_nmb == 0:
                last_nmb = int(df['ringnummerStart'].iloc[0]) - 1
        ende_nmb = int(df['ringnummerEnde'].iloc[0])
        return last_nmb + 1, ende_nmb - last_nmb, str(df['ringserie'].iloc[0])
    return -1, -1, 'Unbekannter Fehler. Ganz schlecht. Bitte Entwickler kontaktieren: mail@sseyfert.de'


def get_next_paket_infos(engine: Connection, ringtypref: int = None, ringserie: str = None, ) -> (int, tuple):
    """

    :param engine:
    :param ringtypref:
    :param ringserie:
    :return:
        tuple: (int, tuple):
            int : nächste Paketnummer oder -1 bei Fehler
            tuple : Infos über das nächste Paket:
                (Fehlermessage oder '', '' oder Ringserie, '' oder Startnummer, '' oder Endnummer,
                '' oder letzte vergebene Nummer)

    """
    try:
        engine.ping()
    except Connection.InterfaceError:
        return -1, ('Keine Verbindung zur Datenbank.', '', '', '', '', '')
    if ringtypref is None and ringserie is None:
        return -1, ('Keine Serie und kein Ringtyp übergeben. Mindestens eine Angabe ist erforderlich.', '', '', '',
                    '', '')
    if ringtypref is not None and ringserie is not None:
        df = pd.read_sql('SELECT ringserie, ringtypRef FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringserie="' + str(ringserie) + '" and ringtypRef =' + str(ringtypref), engine)
        if df.empty:
            return -1, (f'Ringserie "{ringserie}" und Ringtyp "{ringtypref}" passen nicht zueinander.', '', '', '',
                        '', '')
    if ringserie is not None and ringtypref is None:
        df = pd.read_sql('SELECT ringserie, ringtypRef FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringserie="' + str(ringserie) + '"', engine)
        if df.empty:
            return -1, (f'Zur Ringserie {ringserie} gibt es kein aktives Ringnummernpaket. Bitte Stationsleitung '
                        f'informieren, denn es muss ein entsprechendes Paket aktiviert werden.', '', '', '', '', '')
        ringtypref = int(df['ringtypRef'].iloc[0])
    if ringtypref is not None:
        df = pd.read_sql('SELECT * FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringtypRef =' + str(ringtypref) + ' ' + 'and status = 1', engine)
        if df.empty:
            return -1, (f'Zum Ringtyp {ringtypref} gibt es kein aktives Ringnummernpaket. Bitte Stationsleitung '
                        f'informieren, denn es muss ein entsprechendes Paket aktiviert werden.', '', '', '', '', '')
        if df.shape[0] != 1:
            return -1, (f'Es wurde mehr als ein aktives Ringnummernpaket gefunden. Das darf nicht sein!', '', '', '',
                        '', '')

        df_next_packages = pd.read_sql('SELECT * FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                                       'WHERE ringtypRef = ' + str(ringtypref) + ' AND status = 0', engine)
        if not df_next_packages.empty:
            df_next_package_index = df_next_packages['paketnummer'].idxmin()
            next_package_nmb = int(df_next_packages['paketnummer'].loc[df_next_package_index])
            next_package_info = ('', df_next_packages['ringserie'].loc[df_next_package_index],
                             df_next_packages['ringnummerStart'].loc[df_next_package_index],
                             df_next_packages['ringnummerEnde'].loc[df_next_package_index],
                             df_next_packages['letztevergebenenummer'].loc[df_next_package_index])
            return next_package_nmb, next_package_info
        else:
            return -1, f"Es gibt kein weiteres Paket! Ggf. Ringe nachbestellen! Info an das Management, bitte!"


def increment_last_nr(engine: Connection, ringtypref: int = None, ringserie: str = None, ) -> (int, str):
    """

    :param engine:
    :param ringtypref:
    :param ringserie:
    :return:
    TUPLE (int, str):\n
    int: neue Nummer (neue letzte vergebene) ---- ODER -1 bei Fehler\n
    str: Fehlertext ---- ODER '' bei Fehler
    """
    try:
        engine.ping()
    except Connection.InterfaceError:
        return -1, 'Keine Verbindung zur Datenbank.'
    engine.reset()
    if ringtypref is None and ringserie is None:
        return -1, 'Keine Serie und kein Ringtyp übergeben. Mindestens eine Angabe ist erforderlich.'
    if ringtypref is not None and ringserie is not None:
        df = pd.read_sql('SELECT ringserie, ringtypRef FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringserie="' + str(ringserie) + '" and ringtypRef =' + str(ringtypref), engine)
        if df.empty:
            return -1, f'Ringserie "{ringserie}" und Ringtyp "{ringtypref}" passen nicht zueinander.'
    if ringserie is not None and ringtypref is None:
        df = pd.read_sql('SELECT ringserie, ringtypRef FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringserie="' + str(ringserie) + '"', engine)
        if df.empty:
            return (-1, f'Zur Ringserie {ringserie} gibt es kein aktives Ringnummernpaket. Bitte Stationsleitung '
                        f'informieren, denn es muss ein entsprechendes Paket aktiviert werden.')
        ringtypref = int(df['ringtypRef'].iloc[0])
    if ringtypref is not None:
        df = pd.read_sql('SELECT * FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                         'WHERE ringtypRef =' + str(ringtypref) + ' ' + 'and status = 1', engine)
        if df.empty:
            return (-1, f'Zum Ringtyp {ringtypref} gibt es kein aktives Ringnummernpaket. Bitte Stationsleitung '
                        f'informieren, denn es muss ein entsprechendes Paket aktiviert werden.')
        if df.shape[0] != 1:
            return -1, f'Es wurde mehr als ein aktives Ringnummernpaket gefunden. Das darf nicht sein!'
        if df['letztevergebenenummer'].iloc[0] is None:
            last_nmb = int(df['ringnummerStart'].iloc[0]) - 1
        else:
            last_nmb = int(df['letztevergebenenummer'].iloc[0])
            ende_nmb = int(df['ringnummerEnde'].iloc[0])
            if last_nmb == 0:
                last_nmb = int(df['ringnummerStart'].iloc[0]) - 1
            elif last_nmb + 1 == ende_nmb:
                # 0) Erstmal muss dann die Nummer um eins erhöht werden!
                # 1) status auf 2 setzen ("ausgeflogen" :) = alle Ringe der Schnur wurden in die Freiheit entlassen)
                # 2) inventur auf 0 setzen (ist ja definitiv nicht mehr da)
                # 3) nächste paketnummer suchen (min aus allen paketen mit der ringtypRef und status = 0)
                # 4) gefundene paketnummer ==> status auf 1 setzen (aktiv)
                # 5) Integrität checken
                # 6) letztevergebenenummer auf 0 ringnummerStart setzen, da wir in der increment - Funktion sind.

                # 1) + 2)

                ringserie_id = int(df['ringserieID'].iloc[0])
                sql_t = ('UPDATE ' + constants().get_tbl_name_ringserie() + ' ' + 'SET status = 2, inventur = 0 ' +
                         'WHERE ringserieID = ' + str(ringserie_id))
                try:
                    cursor = engine.cursor()
                    cursor.execute(sql_t)
                    engine.commit()
                except Exception as excp:
                    return (-1, f'Update der abgeschlossenen Ringserie hat nicht geklappt. Das ist ganz, ganz, GANZ '
                                f'schlecht und darf nicht passieren. '
                                f'Unbedingt Entwickler kontaktieren bevor es weitergeht.\n'
                            f'Exception: {excp}')

                # 3) + 4) + 6)
                new_id = activate_next_package(engine, ringtypref)

                # 5)
                if not check_integrity_ringseries(engine):
                    rberi_lib.QMessageBoxB('ok', 'Integrität der verwalteten Ringserien leider nicht vorhanden.',
                                           'Schwerer Ausnahmefehler.').exec_()
                    return -1, 'Integrität nicht vorhanden!'

                # Fortsetzung: 3) + 4) + 6)
                if new_id == -1:
                    rberi_lib.QMessageBoxB('ok', 'Es sollte eigentlich das nächste Ringnummernpaket '
                                                 'aktiviert worden sein. Dies hat aber leider nicht geklappt. Bitte '
                                                 'nochmal'
                                                 'probieren. Falls es wieder nicht klappt, muss leider der Admin '
                                                 'kontaktiert'
                                                 'werden: mail@sseyfert.de', 'Schwerer Fehler').exec_()
                    return -1, 'Aktivierung des nächste Pakets konnte leider nicht durchgeführt werden.'
                else:
                    df_tmp = pd.read_sql('SELECT * FROM ' + constants().get_tbl_name_ringserie() + ' ' +
                                         'WHERE ringserieID = ' + str(new_id), engine)
                    start_nr = df_tmp['ringnummerStart'].loc[0] - 1
                    sql_t = ('UPDATE ' + constants().get_tbl_name_ringserie() + ' ' +
                             'SET letztevergebenenummer = ' + str(start_nr) + ' WHERE ringserieID = ' + str(new_id))
                    try:
                        cursor = engine.cursor()
                        cursor.execute(sql_t)
                        engine.commit()
                        cursor.close()
                        #return start_nr, ''
                    except Exception as excp:
                        rberi_lib.QMessageBoxB('ok', 'Letzte vergebene Ringnummer konnte nicht geschrieben '
                                                     'werden. Schwerer Ausnahmefehler. Bitte Entwickler kontaktieren: '
                                                     'mail@sseyfert.de', 'Schwerer Ausnahmefehler',
                                               f'Exception : {excp}')
                        return -1, 'Letzte vergebene Ringnummer konnte nicht geschrieben werden.'

        # last_nmb um eins erhöhen und schreiben
        new_nmb = last_nmb + 1
        ringserie_id = int(df['ringserieID'].iloc[0])
        try:
            sql_t = ('UPDATE ' + constants().get_tbl_name_ringserie() + ' ' + 'SET letztevergebenenummer = ' +
                     str(new_nmb) + ' ' + 'WHERE ringserieID = ' + str(ringserie_id))
            cursor = engine.cursor()
            cursor.execute(sql_t)
            engine.commit()
            cursor.close()
            return new_nmb, ''
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Letzte vergebene Ringnummer konnte nicht erhöht werden. Ganz blöd. '
                                         'Bitte Entwickler kontaktieren: mail@sseyfert.de', 'Schwerer Ausnahmefehler',
                                   f'Exception: {excp}').exec_()
            return -1, 'Letzte vergebene Ringnummer konnte nicht geschrieben werden.'
    return -1, 'Unbekannter Fehler. Ganz schlecht. Bitte Entwickler kontaktieren: mail@sseyfert.de'


def show_beispiel():
    rberi_lib.QMessageBoxB('ok', f'Anzahl Ringe pro "Schnur" = 100\nStartnummer = 333001\n'
                                 'Endnummer = 334000\n\nDas Programm legt dann automatisch 10 Pakete in der '
                                 'richtige Reihenfolge an. Sollte die letzte vorhandene Paketnummer der Serie/Typ-'
                                 'Kombination z.B. 77 betragen, würden 78-87 angelegt werden.', 'Beispiel').exec_()


class _RingSerienVerwaltung(QDialog):
    def __init__(self, engine: Connection, parent=None):
        super().__init__(parent)
        self.flag_neue_serie = False
        self.ui = Ui_DialogRingserienEingabe()
        self.ui.setupUi(self)
        self.ui.TBL_ringserien.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        self._engine = engine
        self.bd = constants()
        self.ui.groupBox_zusatzeingabe.setVisible(True)
        self.ui.groupBox_zusatzeingabe.setEnabled(False)

        self.df_ringserien = pd.read_sql("SELECT DISTINCT ringserie FROM " + self.bd.get_tbl_name_ringserie(), engine)
        self.set_ringserie_inhalt(self.df_ringserien['ringserie'].tolist())

        self.df_ringtypen = pd.read_sql("SELECT ringtypID, klasse, material, durchmesser FROM ringtyp", engine)
        ringtypen_list = []
        for ind, val in self.df_ringtypen.iterrows():
            ringtypen_list.append(str(val['klasse']) + ", " + str(val['material']) + ", " +
                                  str(val['durchmesser']) + " mm")

        self.ui.CMB_neueSerie_ringtyp_auswahl.addItems(ringtypen_list)
        ownview = self.ui.CMB_neueSerie_ringtyp_auswahl.view()
        ownview.setFixedWidth(200)
        self.ui.CMB_ringserienauswahl.currentIndexChanged.connect(self.set_table_content)
        self.ui.BTN_neueSerie_anlegen.clicked.connect(self.new_ringserie)
        self.ui.BTN_info.clicked.connect(self.info)
        self.ui.BTN_neue_ringserie.clicked.connect(self.add_new_range_numbers)
        self.ui.BTN_beispiel_eingabe_ringserie.clicked.connect(show_beispiel)
        self.ui.BTN_ringtypenliste.clicked.connect(self.fill_TBL_ringtypen)
        self.ui.BTN_close.clicked.connect(self.close)
        self.ui.TBL_ringserien.status_changed.connect(self.ui.BTN_spezial.setEnabled)
        self.ui.BTN_clear.clicked.connect(self.ui.TBL_ringserien.clearContents)
        # self.ui.INP_anz_ring_schnur.textChanged.connect(self.ui.INP_start_ringnummer_neue_serie.setFocus)
        self.ui.INP_anz_ring_schnur.returnPressed.connect(self.ui.INP_start_ringnummer_neue_serie.setFocus)
        self.ui.INP_anz_ring_schnur.editingFinished.connect(self.ui.INP_start_ringnummer_neue_serie.setFocus)

    def get_forecast(self, restanzahl: int, rtypRef: str) -> datetime.date:
        try:
            df_serie = pd.read_sql("SELECT ringserie FROM ringserie WHERE ringtyp_Ref = " + str(rtypRef), self.get_engine())
        except Exception as err:
            return datetime.date(1900, 1, 1)
        year_start = datetime.date.today().year - 5
        year_end = year_start + 4
        dat_start = str(year_start) + "-06-30"
        dat_end = str(year_end) + "-11-07"
        sql_query_text = "SELECT ringnummer FROM esf WHERE datum >= '" + dat_start + "' and datum <= '" + dat_end + "' and ("
        if df_serie.empty:
            return datetime.date(2099, 1, 1)
        for ind, val in df_serie.iterrows():
            if ind == 0:
                sql_query_text += "SUBSTRING(ringnummer, 1, 2) = '" + val['ringserie'] + "'"
            else:
                sql_query_text += " OR SUBSTRING(ringnummer, 1, 2) = '" + val['ringserie'] + "'"
        sql_query_text += ") and fangart = 'e'"
        print(sql_query_text)
        try:
            df_esf = pd.read_sql(sql_query_text, self.get_engine())
        except Exception as err:
            return datetime.date(1900, 1, 1)
        gesamt_anz = df_esf.shape[0]
        anz_pro_tag = gesamt_anz / 5 / 131
        print("Durchscnittliche Anzahl des Ringtyps " + str(rtypRef) + " pro Tag:" + str(anz_pro_tag))
        if anz_pro_tag > 0:
            verbleibende_Tage = restanzahl / anz_pro_tag
        else:
            return datetime.date(2099, 1, 1)
        rest_tage_bis_saisonende = 0
        if (datetime.date(datetime.date.today().year, 6, 30) <= datetime.date.today() <=
                datetime.date(datetime.date.today().year, 11, 7)):
            rest_tage_bis_saisonende = datetime.date(datetime.date.today().year,  11, 7) - datetime.date.today()
        if verbleibende_Tage <= rest_tage_bis_saisonende:
            return datetime.date.today() + datetime.timedelta(days=verbleibende_Tage)
        else:
            if datetime.date(datetime.date.today().year, 6, 30) <= datetime.date.today():       # nach 07.11.
                start_forecast_year = datetime.date.today().year + 1
            else:   # vor 30.06.
                start_forecast_year = datetime.date.today().year
            forecast_ganze_jahre = verbleibende_Tage // 131
            forecast_year = start_forecast_year + int(forecast_ganze_jahre)
            verbleibende_Tage_im_letzten_jahr = verbleibende_Tage - forecast_ganze_jahre * 131
            forecast_datum = datetime.date(forecast_year, 6, 30) + datetime.timedelta(verbleibende_Tage_im_letzten_jahr)
            print("forecast_datum = " + str(forecast_datum))
            return forecast_datum

    def info(self):
        self.info_diag = QDialog(self)
        self.info_diag.setWindowTitle("Info über vorhandene Ringserien")
        self.info_diag.resize(1024, 800)
        self.info_diag.layout = QGridLayout(self.info_diag)
        tbl = QTableWidget()
        tbl.setColumnCount(5)

        item = QTableWidgetItem("Ringserie")
        tbl.setHorizontalHeaderItem(0, item)
        item = QTableWidgetItem("Ringtyp")
        tbl.setHorizontalHeaderItem(1, item)
        item = QTableWidgetItem("Durchmesser")
        tbl.setHorizontalHeaderItem(2, item)
        item = QTableWidgetItem("Anz. vorhanden")
        tbl.setHorizontalHeaderItem(3, item)
        item = QTableWidgetItem("reicht bis")
        tbl.setHorizontalHeaderItem(4, item)
        try:
            df_ringtyp = pd.read_sql("SELECT ringtypID, klasse, durchmesser FROM ringtyp", self.get_engine())
            df_serien = pd.read_sql("SELECT * FROM " + self.bd.get_tbl_name_ringserie() + " WHERE status = 0 OR status = 1",
                                    self.get_engine())
        except Exception as err:
            rberi_lib.QMessageBoxB('ok', 'Fehler bei der Datenbankabfrage.', 'Datenbankfehler', [str(err)]).exec_()
            return

        self.info_diag.layout.addWidget(tbl, 0, 0)
        self.info_diag.btn = QPushButton("ok")
        self.info_diag.layout.addWidget(self.info_diag.btn, 1, 0)
        self.info_diag.btn.clicked.connect(self.info_diag.close)
        for rtyp in pd.unique(df_serien['ringtypRef'].values.ravel()):        # ints! Referenz auf die ringtypID
            ringtyp_klasse = df_ringtyp.query("ringtypID == " + str(rtyp))['klasse'].iloc[0]
            ringtyp_durchmesser = df_ringtyp.query("ringtypID == " + str(rtyp))['durchmesser'].iloc[0]
            df_spezial = df_serien.query("ringtypRef == " + str(rtyp))
            arr = pd.unique(df_spezial['ringserie'].values.ravel())
            flag = False
            for serie in arr:
                df_spezial_spezial = df_spezial.query('ringserie == "' + str(serie) + '"')
                ringserie = str(serie)
                vorhanden = 0
                for ind, val in df_spezial_spezial.iterrows():
                    try:
                        if int(val['status']) == 1 and not np.isnan(val['letztevergebenenummer']):
                            anz_einzeln = int(val['ringnummerEnde']) - int(val['letztevergebenenummer'])
                            vorhanden += anz_einzeln
                        else:
                            anz_einzeln = int(val['ringnummerEnde']) - int(val['ringnummerStart'])
                            vorhanden += anz_einzeln
                    except Exception as err:
                        vorhanden = -999

                tbl.setRowCount(tbl.rowCount() + 1)
                tbl.setItem(tbl.rowCount()-1, 0, QTableWidgetItem(ringserie))
                tbl.setItem(tbl.rowCount()-1, 1, QTableWidgetItem(str(ringtyp_klasse)))
                tbl.setItem(tbl.rowCount()-1, 2, QTableWidgetItem(str(ringtyp_durchmesser)))
                itemX = QTableWidgetItem()
                # itemX.setText(str(vorhanden))
                itemX.setData(Qt.DisplayRole, vorhanden)
                tbl.setItem(tbl.rowCount()-1, 3, itemX)
                itemY = QTableWidgetItem()
                try:
                    itemY.setData(Qt.DisplayRole, self.get_forecast(vorhanden, rtyp).strftime("%Y-%m-%d"))
                except Exception as err:
                    flag = True
                    itemY.setData(Qt.DisplayRole, "Fehler!")
                tbl.setItem(tbl.rowCount()-1, 4, itemY)
        if flag:
            rberi_lib.QMessageBoxB('ok', 'Es gab Fehler bei der Forecastberechnung! Spalte ist mit "Fehler" markiert.',
                                   'Interner Fehler!', str(err)).exec_()
        tbl.resizeColumnsToContents()
        tbl.setSortingEnabled(True)
        tbl.sortByColumn(4, Qt.AscendingOrder)
        self.info_diag.exec()



    def fill_TBL_ringtypen(self):
        for i in range(self.ui.TBL_ringtypen.rowCount()):
            self.ui.TBL_ringtypen.removeRow(i)
        sql_text = "SELECT klasse, material, durchmesser, hoehe, staerke, farbe, bemerkung FROM ringtyp"
        try:
            df_ringtyp = pd.read_sql(sql_text, self.get_engine())
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Kann die Ringtypen nicht einlesen. Datenbank verbunden?',
                                   'Fehler', str(excp)).exec_()
            return
        write_df_to_qtable(df_ringtyp, self.ui.TBL_ringtypen)
        """self.ui.TBL_ringserien.setItemDelegateForRows()
        self.ui.TBL_ringserien.resizeRowsToContents()"""
        for i in range(self.ui.TBL_ringserien.rowCount()):
            self.ui.TBL_ringserien.setRowHeight(i, 10)

    def get_ringserie(self):
        return self.ui.CMB_ringserienauswahl.currentText()

    def get_engine(self):
        return self._engine

    def get_id_of_row(self, row: int) -> int:
        serie = self.ui.TBL_ringserien.item(row, 0).text()
        typ = self.ui.TBL_ringserien.item(row, 1).text()
        start = self.ui.TBL_ringserien.item(row, 2).text()
        end = self.ui.TBL_ringserien.item(row, 3).text()
        paket = self.ui.TBL_ringserien.item(row, 4).text()

        df = pd.read_sql("SELECT ringserieID FROM " + constants().get_tbl_name_ringserie() + " " + "WHERE " +
                         "ringserie = '" + serie + "' and ringtypRef = " + typ + " and ringnummerStart = " + start +
                         " and ringnummerEnde = " + end + ' and paketnummer = ' + paket, self.get_engine())
        if df.empty:
            return -1
        else:
            return int(df['ringserieID'][0])

    def set_ringserie_inhalt(self, content=None):
        if content is None:
            content_ = [""]
        else:
            content_ = [""]
            for el in content:
                content_.append(el)
        self.ui.CMB_ringserienauswahl.addItems(content_)
        self.ui.CMB_ringserienauswahl.setCurrentIndex(-1)

    def get_anz_ringe(self) -> int:
        """

        :return:
        int : Anzahl Ringe auf Schnur/Schlauch/Einheit/Paket
        -1 : Fehler
        """
        nmb = self.ui.INP_anz_ring_schnur.text()
        if len(nmb) == 0:
            return 0
        if "," in nmb or "." in nmb:
            rberi_lib.QMessageBoxB('ok', 'Anzahl Ringe auf Schnur muss eine natürliche Zahl sein.', 'Fehler').exec_()
            self.ui.INP_anz_ring_schnur.clear()
            self.ui.INP_anz_ring_schnur.setFocus()
            return -1
        if nmb.isnumeric():
            return int(nmb)
        else:
            rberi_lib.QMessageBoxB('ok', 'Anzahl Ringe auf Schnur muss eine natürliche Zahl sein.', 'Fehler').exec_()
            self.ui.INP_anz_ring_schnur.clear()
            self.ui.INP_anz_ring_schnur.setFocus()
            return -1

    def get_startnummer(self) -> int:
        """

        :return:
        int : Startnummer
        -1  : Fehler
        """
        nmb = self.ui.INP_start_ringnummer_neue_serie.text()
        if "," in nmb or "." in nmb:
            rberi_lib.QMessageBoxB('ok', 'Startnummer muss eine natürliche Zahl sein.', 'Fehler').exec_()
            self.ui.INP_start_ringnummer_neue_serie.clear()
            self.ui.INP_start_ringnummer_neue_serie.setFocus()
            return -1
        if nmb.isnumeric():
            return int(nmb)
        else:
            rberi_lib.QMessageBoxB('ok', 'Startnummer muss eine natürliche Zahl sein.', 'Fehler').exec_()
            self.ui.INP_start_ringnummer_neue_serie.clear()
            self.ui.INP_start_ringnummer_neue_serie.setFocus()
            return -1

    def get_endnummer(self) -> int:
        """

        :return:
        int : Endnummer
        -1  : Fehler
        """
        nmb = self.ui.INP_end_ringnummer_neue_serie.text()
        if "," in nmb or "." in nmb:
            rberi_lib.QMessageBoxB('ok', 'Endnummer muss eine natürliche Zahl sein.', 'Fehler').exec_()
            self.ui.INP_end_ringnummer_neue_serie.clear()
            self.ui.INP_end_ringnummer_neue_serie.setFocus()
            return -1
        if nmb.isnumeric():
            return int(nmb)
        else:
            rberi_lib.QMessageBoxB('ok', 'End muss eine natürliche Zahl sein.', 'Fehler').exec_()
            self.ui.INP_end_ringnummer_neue_serie.clear()
            self.ui.INP_end_ringnummer_neue_serie.setFocus()
            return -1

    def get_zusatz(self) -> str:
        """

        :return:
        string : Zusatztext (keine Verifizierung)
        """
        return self.ui.INP_zusatz.text()

    def get_neue_ringserie(self) -> str:
        """

        :return:
        string : die neu anzulegende Ringserie (kann nicht größer als 2 sein)
        """
        return self.ui.INP_neueSerie_ringserie.text()

    def get_typ_zur_serie(self) -> int:
        """

        :return:
        int : RingtypRef
        -1  : Fehler
        """
        val = self.ui.CMB_ringserienauswahl.currentText()
        sql_text = ("SELECT ringtypRef FROM " + self.bd.get_tbl_name_ringserie() + " WHERE ringserie = '" +
                    val + "'")
        try:
            df_ringtyp = pd.read_sql(sql_text, self.get_engine())
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Es konnte kein Ringtyp zur Serie gefunden werden.', "Fehler",
                                   str(excp)).exec_()
            return -1
        if df_ringtyp.empty:
            return -1
        else:
            return int(df_ringtyp['ringtypRef'].iloc[0])

    def get_neuen_ringtyp(self) -> int:
        """

        :return:
        int : RingtypReferenz für neu anzulegende Serie (aus Kombobox wird die ID extrahiert werden)
        """
        val = self.ui.CMB_neueSerie_ringtyp_auswahl.currentText()
        vals = val.split(",")
        vals = [j.strip() for j in vals]
        new_vals = vals[2].split(" ")
        # new_digit = new_vals[0].strip().replace('.', ',')
        sql_text = ("SELECT ringtypID FROM ringtyp WHERE klasse = '" + str(vals[0].strip()) + "' and material = '" +
                    str(vals[1].strip()) + "' and durchmesser = " + str(new_vals[0].strip()))
        df_ringtyp = pd.read_sql(sql_text, self.get_engine())
        if df_ringtyp.empty:
            return -1
        else:
            return int(df_ringtyp['ringtypID'].iloc[0])

    def save_table(self):
        for i in range(self.ui.TBL_ringserien.rowCount()):
            id_self = str(self.get_id_of_row(i))
            df_status = pd.read_sql("SELECT status FROM " + constants().get_tbl_name_ringserie() + " " +
                                    "WHERE ringserieID = " + id_self, self.get_engine())
            if self.ui.TBL_ringserien.item(i, 6).text() != str(df_status['status'].iloc[0]):
                sql_t = ("UPDATE " + constants().get_tbl_name_ringserie() + " " +
                         "SET status=" + self.ui.TBL_ringserien.item(i, 6).text() + " " + "WHERE ringserieID ="
                         + id_self)
                cursor = self.get_engine().cursor()
                try:
                    cursor.execute(sql_t)
                    self.get_engine().commit()
                    cursor.close()
                except Exception as excp:
                    rberi_lib.QMessageBoxB('ok', 'Fehler beim Schreiben eines Datensatzes.', 'Warnung',
                                           str(excp)).exec_()
                    return

    def set_table_content(self) -> int:
        """

        :param:
        :return:
        -1 : Fehler
        0  : alles ok, keine Vorkommnisse
        1  : alles ok, aber Vorkommnisse
        """

        if self.ui.BTN_spezial.isEnabled():
            answer = rberi_lib.QMessageBoxB('yn', 'Es wurden Änderungen an der Tabelle vorgenommen. '
                                                  'Sollen die Änderungen vorher gespeichert werden?', 'Warnung').exec_()
            if answer == QMessageBox.Yes:
                self.save_table()
        content = {"ringserie": "", "ringtypRef": "", "ringnummerStart": 0, "ringnummerEnde": 1,
                   "paketnummer": 99999, "letztevergebenenummer": 1, "status": 3, "bemerkung": "dummy"}
        content = pd.DataFrame(data=content, index=[0])
        try:
            content = pd.read_sql("SELECT ringserie, ringtypRef, ringnummerStart, ringnummerEnde, " +
                                  "paketnummer, letztevergebenenummer, status, bemerkung FROM " +
                                  self.bd.get_tbl_name_ringserie() + " WHERE ringserie = '" +
                                  self.get_ringserie() + "'", self.get_engine())
        except Exception as excp:
            QMessageBox(QMessageBox.Warning, 'Fehler',
                        f'Die aktuellen Pakete der Ringserien können nicht eingelesen werden.\n' +
                        f'Exception: \n{excp}').exec_()

        write_df_to_qtable(content, self.ui.TBL_ringserien)
        self.ui.TBL_ringserien.resizeColumnsToContents()
        # das sortieren funktioniert irgendwie nicht (so gut). Da man aber per Mausklick sortieren kann,
        # lassen wir es hier weg.
        # self.ui.TBL_ringserien.sortByColumn(1, Qt.AscendingOrder)
        self.ui.BTN_spezial.setEnabled(False)
        return 0

    def get_next_package_number(self, ringtyp: int) -> int:
        """

        :param ringtyp: ringtypID
        :return:
        -1: Fehler / es wurden keine Serien für den Ringtyp 'ringtyp' gefunden.
        int: Nummer des nächsten Pakets (wenn also 1-7 gefunden wurden, wird 8 zurückgegeben)
        """
        sql_text = "SELECT paketnummer FROM " + self.bd.tbl_name_ringserie + " WHERE ringtypRef=" + str(ringtyp)
        try:
            df_ringserien = pd.read_sql(sql_text, self.get_engine())
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Fehler beim Einlesen der Paketnummern für den Ringtyp. Vermutlich '
                                         'ist die Datenbank nicht verbunden.', 'Fehler', str(excp)).exec_()
            return -1
        if df_ringserien.empty:
            answer = rberi_lib.QMessageBoxB('yn', 'Ringtyp wurde noch nicht angelegt/verwendet. Jetzt anlegen?',
                                            'Ringserie anlegen ...',
                                            'Wenn eine Ringserie noch nicht angelegt ist, '
                                            'kann das verschiedene Ursachen haben. Z.B. kann die "alte" Ringserie '
                                            'abgelaufen/fertig sein und die neue muss angelegt werden.').exec_()
            if answer == QMessageBox.Yes:
                return 1
            else:
                return -1
        else:
            return int(df_ringserien['paketnummer'].max()) + 1

    def new_ringserie(self):
        a = rberi_lib.QMessageBoxB('cyn', 'Dies bedeutet, dass die Ringserie, die Du eingeben möchtest, '
                                          'bisher noch nicht auf der Station verwendet wurde. Wenn Du nur einen neuen '
                                          'Nummernbereich eingeben möchtest, wähle bitte die bisherige Ringserie links '
                                          'aus und nutze die untere Eingabemaske für das Hinzufügen neuer Nummern.'
                                          '\n\nSolltest Du tatsächlich eine neue Ringserie anlegen wollen?',
                                   'Neue Ringserie?').exec_()
        if a == QMessageBox.Yes:
            self.set_flag_neue_serie(True)
        else:
            self.set_flag_neue_serie(False)

    def set_flag_neue_serie(self, val: bool = False):
        self.flag_neue_serie = val
        if val:
            self.ui.groupBox_zusatzeingabe.setVisible(True)
            self.ui.groupBox_zusatzeingabe.setEnabled(True)
        else:
            self.ui.groupBox_zusatzeingabe.setVisible(True)
            self.ui.groupBox_zusatzeingabe.setEnabled(False)
            self.ui.INP_neueSerie_ringserie.clear()
            self.ui.CMB_neueSerie_ringtyp_auswahl.setCurrentIndex(-1)

    def get_flag_neue_serie(self):
        return self.flag_neue_serie

    def proof_status(self) -> bool:
        status = False
        start_nr = self.get_startnummer()
        end_nr = self.get_endnummer()
        if start_nr != -1 and end_nr != -1:
            anz_ringe = end_nr - start_nr + 1
            anr_ringe_eingabe = self.get_anz_ringe()
            if self.ui.INP_anz_ring_schnur.text() == "":
                self.ui.INP_anz_ring_schnur.setText(str(anz_ringe))
            elif anr_ringe_eingabe != -1 and anz_ringe % anr_ringe_eingabe != 0:
                answer = rberi_lib.QMessageBoxB('yn', 'Anzahl Ringe passt nicht mit Start- und Endwert zusammen. Soll '
                                                      'automatisch korrigiert werden?', 'Anzahl Ringe',
                                                [f'Anzahl laut Eingabe: {anr_ringe_eingabe}',
                                                 f'Berechnete Anzahl: {anz_ringe}']).exec_()
                if answer == QMessageBox.Yes:
                    self.ui.INP_anz_ring_schnur.setText(str(anz_ringe))

        if self.get_flag_neue_serie():
            if len(self.get_neue_ringserie()) >= 1:
                if self.get_neuen_ringtyp() != -1:
                    status = True
        else:
            status = True

        return status

    def add_new_range_numbers(self) -> int:
        """
        1) Neue Ringserie oder nur neue Nummern?
        2) Prüfen ob alle Eingaben konsistent sind...
        3) Datensatz schreiben und Aktualisierung der Tabelle
        4) Setzen des Flags self.flag_neue_serie auf False
        :return:
        0 = alles ok
        1 = Fehler
        """
        # 1) neue Ringserie oder "nur" neue Nummern?
        serie = ''
        if self.get_flag_neue_serie():
            serie = self.ui.INP_neueSerie_ringserie.text()
            if serie in self.df_ringserien['ringserie'].tolist():
                rberi_lib.QMessageBoxB('ok', 'Ringserie ist doch schon vorhanden! Mensch!',
                                       'Eingabefehler!').exec_()
                self.set_flag_neue_serie(False)
                return 1
            else:
                if self.proof_status():
                    self.add_new_series_in_packages()
                else:
                    return 1
        else:
            if self.proof_status():
                self.add_new_packages()
        # 3) Aktualisierung der Tabelle
        if len(serie) > 0:
            oldserie = serie
        else:
            oldserie = self.ui.CMB_ringserienauswahl.currentText()

        self.ui.CMB_ringserienauswahl.clear()
        self.df_ringserien = pd.read_sql("SELECT DISTINCT ringserie FROM " + self.bd.get_tbl_name_ringserie(),
                                         self.get_engine())
        self.set_ringserie_inhalt(self.df_ringserien['ringserie'].tolist())
        self.ui.CMB_ringserienauswahl.setCurrentText(oldserie)
        self.set_flag_neue_serie(False)

    def get_anz_packages(self) -> int:
        """

        :return:
        int : Anzahl Pakete wenn ohne Rest teilbar (Endnummer - Startnummer) / Anzahl_Ringe_je_Schnur
        -1  : wenn ein Rest über bleibt. (also irgendwas nicht stimmt)
        """
        mod_wert = (self.get_endnummer() - self.get_startnummer() + 1) % self.get_anz_ringe()
        if mod_wert != 0:
            return -1
        else:
            return int((self.get_endnummer() - self.get_startnummer() + 1) / self.get_anz_ringe())

    """cursor.execute("INSERT INTO ringer (ringer_alt, jahr, ringer_new, station, vorname, strasse, "
                   "plz, ort, land, telefon, telefax, email, anmerkung, zeige_wiederfaenge, "
                   "nachname) "
                   "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                   (ringer_alt, jahr, ringer_neu, station, eintrag['vorname'],
                    eintrag['strasse'], str(eintrag['plz']), eintrag['stadt'], eintrag['land'],
                    eintrag['telefon'], eintrag['fax'], eintrag['email'], eintrag['anmerkung'],
                    eintrag['wiederfang'], eintrag['nachname']))"""

    def add_new_packages(self):
        if self.get_anz_packages() > 0:
            ringserie = self.get_ringserie()
            ringserieZusatz = self.get_zusatz()
            ringtypRef = self.get_typ_zur_serie()
            # ringnummerEnde = self.get_endnummer()
            schnurlaenge = self.get_anz_ringe()
            ringnummerStart = self.get_startnummer() - schnurlaenge
            paketnummerStart = self.get_next_package_number(ringtypRef)
            if paketnummerStart == -1:
                return
            bemerkung = "angelegt am " + datetime.datetime.now().strftime("%Y-%m-%d, %H:%M")

            for i in range(1, self.get_anz_packages() + 1):
                ringnummerStart = ringnummerStart + schnurlaenge
                ringnummerEnde = ringnummerStart + schnurlaenge - 1
                paketnummer = paketnummerStart + (i - 1)
                letztevergebenenummer = None
                if paketnummerStart == 1:
                    status = 1
                else:
                    status = 0
                inventur = 1

                sql_text = ("INSERT INTO " + self.bd.get_tbl_name_ringserie() + " (ringserie, ringserieZusatz, " +
                            "ringtypRef, ringnummerStart, ringnummerEnde, paketnummer, letztevergebenenummer, " +
                            "status, inventur, bemerkung) " +
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
                try:
                    self.get_engine().cursor().execute(sql_text, (ringserie, ringserieZusatz, ringtypRef,
                                                                  ringnummerStart, ringnummerEnde, paketnummer,
                                                                  letztevergebenenummer, status, inventur, bemerkung))
                    self.get_engine().commit()
                except Exception as excp:
                    rberi_lib.QMessageBoxB('ok', 'Anlage hat nicht geklappt.', 'Fehler', str(excp)).exec_()
        else:
            rberi_lib.QMessageBoxB('ok', 'Die Differenz der End- und Startnummer ist nicht durch '
                                         'die Anzahl der Ringe je Schnur restlos teilbar. D.h. es gibt eine '
                                         'Schnur, die nicht vollständig ist. Bitte gebe diese Schnur einzeln '
                                         'ein. Sollte sie am Anfang der Serie stehen, gib sie als erste ein, '
                                         'sollte sie in der Mitte irgendwo stehen, gib erst die Serie davor, '
                                         'dann die einzelne Schnur und dann die Serie danach ein. Sollte sie '
                                         'sich am Ende befinden, gib die Serie bis zur Schnur ein und dann die '
                                         'unvollständige. Solltest Du keine Ahnung haben, was dieser Hilfetext '
                                         'bedeutet, frage bitte jemanden, DER SICH DAMIT AUSKENNT UND '
                                         'MACHE DICH NICHT UNGLÜCKLICH!!').exec_()
            return

    def add_new_series_in_packages(self):
        if self.get_anz_packages() > 0:
            ringserie = self.get_neue_ringserie()
            ringserieZusatz = self.get_zusatz()
            ringtypRef = self.get_neuen_ringtyp()
            schnurlaenge = self.get_anz_ringe()
            ringnummerStart = self.get_startnummer() - schnurlaenge
            paketnummerStart = self.get_next_package_number(ringtypRef)
            if paketnummerStart == -1:
                return
            bemerkung = "angelegt am " + datetime.datetime.now().strftime("%Y-%m-%d, %H:%M")

            for i in range(1, self.get_anz_packages() + 1):
                ringnummerStart = ringnummerStart + schnurlaenge
                ringnummerEnde = ringnummerStart + schnurlaenge - 1
                paketnummer = paketnummerStart + (i - 1)
                letztevergebenenummer = None
                if paketnummerStart == 1:
                    status = 1
                else:
                    status = 0
                inventur = 1

                sql_text = ("INSERT INTO " + self.bd.get_tbl_name_ringserie() + " (ringserie, ringserieZusatz, " +
                            "ringtypRef, ringnummerStart, ringnummerEnde, paketnummer, letztevergebenenummer, " +
                            "status, inventur, bemerkung) " +
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
                try:
                    self.get_engine().cursor().execute(sql_text, (ringserie, ringserieZusatz, ringtypRef,
                                                                  ringnummerStart, ringnummerEnde, paketnummer,
                                                                  letztevergebenenummer, status, inventur, bemerkung))
                    self.get_engine().commit()
                except Exception as excp:
                    rberi_lib.QMessageBoxB('ok', 'Anlage hat nicht geklappt.', 'Fehler', str(excp)).exec_()
        else:
            rberi_lib.QMessageBoxB('ok', 'Die Differenz der End- und Startnummer ist nicht durch '
                                         'die Anzahl der Ringe je Schnur restlos teilbar. D.h. es gibt eine '
                                         'Schnur, die nicht vollständig ist. Bitte gebe diese Schnur einzeln '
                                         'ein. Sollte sie am Anfang der Serie stehen, gib sie als erste ein, '
                                         'sollte sie in der Mitte irgendwo stehen, gib erst die Serie davor, '
                                         'dann die einzelne Schnur und dann die Serie danach ein. Sollte sie '
                                         'sich am Ende befinden, gib die Serie bis zur Schnur ein und dann die '
                                         'unvollständige. Solltest Du keine Ahnung haben, was dieser Hilfetext '
                                         'bedeutet, frage bitte jemanden, DER SICH DAMIT AUSKENNT UND '
                                         'MACHE DICH NICHT UNGLÜCKLICH!!').exec_()
            return
