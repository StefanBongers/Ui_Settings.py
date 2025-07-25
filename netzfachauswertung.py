# -*- coding: utf-8 -*-
import datetime
import mariadb
import pandas as pd
from PyQt5.QtCore import QDate, Qt

import rberi_lib
from PyQt5.QtWidgets import QDialog, QFileDialog, QButtonGroup, QTableWidgetItem
from Beringungsoberflaeche.netzfach_auswertung import Ui_Dialog


class Netzfach_Auswertung(QDialog):
    def __init__(self, db_eng: mariadb.Connection, debug: bool = False, current_user: str = "reit", parent=None, **kwargs):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.TBL_resultat.setStyleSheet("""
            font-size: 11px;
        """)
        self.ui.DTE_start.setDate(QDate(datetime.date.today().year, 6, 30))
        self.ui.DTE_ende.setDate(QDate(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day))

        self.engine = db_eng
        self.debug = debug
        self.first_header = "---"
        self.normiert = False
        self.user = current_user


        # Connections:
        self.ui.BTN_go.clicked.connect(self.go)
        self.ui.BTN_schliessen.clicked.connect(self.close)
        self.ui.BTN_export.clicked.connect(self.export)
        self.radiobutton_group_date = QButtonGroup()
        self.radiobutton_group_date.addButton(self.ui.RBTN_halloffame)
        self.ui.RBTN_halloffame.clicked.connect(self.halloffame_clicked)
        self.ui.RBTN_saison.clicked.connect(self.saison_clicked)
        self.radiobutton_group_date.addButton(self.ui.RBTN_saison)

        self.radiobutton_group_nets = QButtonGroup()
        self.radiobutton_group_nets.addButton(self.ui.RBTN_alle)
        self.radiobutton_group_nets.addButton(self.ui.RBTN_hi)
        self.radiobutton_group_nets.addButton(self.ui.RBTN_vo)
        self.radiobutton_group_nets.addButton(self.ui.RBTN_hi_li)
        self.radiobutton_group_nets.addButton(self.ui.RBTN_hi_re)
        self.radiobutton_group_nets.addButton(self.ui.RBTN_vo_li)
        self.radiobutton_group_nets.addButton(self.ui.RBTN_vo_re)
        self.ui.RBTN_alle.setChecked(True)

        self.radiobutton_group_diff = QButtonGroup()
        self.radiobutton_group_diff.addButton(self.ui.RBTN_gr3_jahre_faecher)
        self.radiobutton_group_diff.addButton(self.ui.RBTN_gr3_netze_jahre)
        self.radiobutton_group_diff.addButton(self.ui.RBTN_gr3_netze_faecher)
        self.set_group_visibility(False)
        self.ui.CMB_netz.currentIndexChanged.connect(self.netz_auswahl)

        self.netze = pd.DataFrame()
        try:
            self.netze = pd.read_sql("SELECT Netz, zuordnung FROM netze WHERE aktiv = 1", self.engine)
        except Exception as err:
            rberi_lib.QMessageBoxB("yn", "Datenbankfehler. Siehe Details.", "Datenbankfehler", str(err)).exec_()
            return
        self.ui.CMB_netz.addItem("")
        self.ui.CMB_netz.addItems(self.netze['Netz'])
        self.ui.CMB_netz.setCurrentIndex(0)
        self.ui.CHB_normiert.clicked.connect(self.normiert_clicked)
        self.ui.DTE_ende.dateChanged.connect(self.DTE_changed)
        self.ui.DTE_start.dateChanged.connect(self.DTE_changed)

    def go(self):
        sql_txt = self.get_query_text()
        if self.debug:
            print("Zusammengebauter Text für die SQL-Suche: \n"+ sql_txt)

        df = pd.DataFrame()
        try:
            df = pd.read_sql(sql_txt, self.engine)
        except Exception as err:
            rberi_lib.QMessageBoxB('ok', 'Datenbank- oder SQL-Fehler. Siehe Details.', 'Fehler', str(err)).exec_()
            return

        """answ = QMessageBox.Yes
        if self.ui.DTE_ende.date().year() > self.ui.DTE_start.date().year():
            # Wenn es mehr als ein Jahr ist wird abgefragt, ob die Anzeige nach Jahren differenziert werden soll, oder
            # ob die Netze einzeln angezeigt werden sollen über den Gesamtzeitraum...
            answ = rberi_lib.QMessageBoxB('yn', 'Der Zeitraum umfasst mehrere Jahre. Variante 1: sollen in den Zeilen '
                                                'die Netze '
                                         'einzeln aufgelistet werden und der gesamte Zeitraum betrachtet werden, '
                                         'oder Variante 2: sollen in den Zeilen die Jahre differenziert werden und dafür alle '
                                         '(ausgewählten) Netze zusammengefasst werden? Für Variante 1 bitte YES/JA drücken und '
                                                'für Variante 2 '
                                         'NO/NEIN.', 'Entscheidung!', 'Kompliziert? '
                                         'Ja! Aber DU wolltest diese Auswertung machen und wenn Du nicht weißt, was Du willst, '
                                         'solltest Du vielleicht in die Politik gehen und nicht hier Auswertungen machen wollen '
                                         'von denen Du KEINE Ahnung zu haben ... egal, entschuldige. Entscheide Dich!').exec_()"""

        if self.ui.RBTN_gr3_netze_faecher.isChecked():
            # Zeilen: Netze
            # gesamter Zeitraum
            # wenn Normierung: auf Netz gesamt

            df_1 = df[df['fach'].str.contains("1")]
            df_2 = df[df['fach'].str.contains("2")]
            df_3 = df[df['fach'].str.contains("3")]
            df_4 = df[df['fach'].str.contains("4")]
            self.ui.TBL_resultat.setHorizontalHeaderItem(0, QTableWidgetItem(self.first_header))
            self.ui.TBL_resultat.setColumnCount(5)
            self.ui.TBL_resultat.setHorizontalHeaderItem(1, QTableWidgetItem("Fach 1"))
            self.ui.TBL_resultat.setHorizontalHeaderItem(2, QTableWidgetItem("Fach 2"))
            self.ui.TBL_resultat.setHorizontalHeaderItem(3, QTableWidgetItem("Fach 3"))
            self.ui.TBL_resultat.setHorizontalHeaderItem(4, QTableWidgetItem("Fach 4"))
            # wir holen uns alle Netze die aufgelistet werden müssen aus dem original dataframe
            # über die einträge kann man dann iterieren
            df_netze = df.drop_duplicates(subset=['netz'], keep='first', inplace=False)
            df_netze = df_netze.reset_index(drop=True)
            self.ui.TBL_resultat.setRowCount(df_netze.shape[0])
            self.ui.PRGB.setMaximum(df_netze.shape[0])

            for row, content in df_netze.iterrows():
                self.ui.PRGB.setValue(row)
                self.ui.PRGB.setFormat("Fortschritt: %p%")
                _item = QTableWidgetItem()
                _item1 = QTableWidgetItem()
                _item2 = QTableWidgetItem()
                _item3 = QTableWidgetItem()
                _item4 = QTableWidgetItem()

                _item.setData(Qt.DisplayRole, content['netz'])
                self.ui.TBL_resultat.setItem(row, 0, _item)
                anz_1 = df_1.query("netz == '" + content["netz"] + "'").shape[0]
                anz_2 = df_2.query("netz == '" + content["netz"] + "'").shape[0]
                anz_3 = df_3.query("netz == '" + content["netz"] + "'").shape[0]
                anz_4 = df_4.query("netz == '" + content["netz"] + "'").shape[0]
                if self.normiert:
                    anz_float = 0.0
                    sum = int(anz_1) + int(anz_2) + int(anz_3) + int(anz_4)
                    if sum > 0:
                        anz_float = int(anz_1) * 100 / sum
                        _item1.setData(Qt.DisplayRole, "{:.0f}".format(anz_float)+"%")
                        anz_float = int(anz_2) * 100 / sum
                        _item2.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        anz_float = int(anz_3) * 100 / sum
                        _item3.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        anz_float = int(anz_4) * 100 / sum
                        _item4.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                    else:
                        anz_float = 0.0
                        _item1.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        _item2.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        _item3.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        _item4.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                else:
                    _item1.setData(Qt.DisplayRole, int(anz_1))
                    _item2.setData(Qt.DisplayRole, int(anz_2))
                    _item3.setData(Qt.DisplayRole, int(anz_3))
                    _item4.setData(Qt.DisplayRole, int(anz_4))
                self.ui.TBL_resultat.setItem(row, 1, _item1)
                self.ui.TBL_resultat.setItem(row, 2, _item2)
                self.ui.TBL_resultat.setItem(row, 3, _item3)
                self.ui.TBL_resultat.setItem(row, 4, _item4)
            self.ui.PRGB.setValue(df_netze.shape[0])
        elif self.ui.RBTN_gr3_jahre_faecher.isChecked():
            # hier muss noch rein, dass nur gecleared werden soll, wenn vorher nicht normiert war... bzw. neue abfrage
            self.ui.TBL_resultat.clear()
            ende_year = self.ui.DTE_ende.date().year()
            start_year = self.ui.DTE_start.date().year()
            anz_year = ende_year - start_year
            self.ui.TBL_resultat.setRowCount(anz_year)
            self.ui.TBL_resultat.setColumnCount(5)
            self.ui.TBL_resultat.setHorizontalHeaderItem(1, QTableWidgetItem("Fach 1"))
            self.ui.TBL_resultat.setHorizontalHeaderItem(2, QTableWidgetItem("Fach 2"))
            self.ui.TBL_resultat.setHorizontalHeaderItem(3, QTableWidgetItem("Fach 3"))
            self.ui.TBL_resultat.setHorizontalHeaderItem(4, QTableWidgetItem("Fach 4"))
            i = -1
            self.ui.TBL_resultat.setHorizontalHeaderItem(0, QTableWidgetItem(self.first_header))
            self.ui.PRGB.setMaximum(anz_year)
            self.ui.PRGB.setValue(0)
            for year in range(start_year, ende_year):
                i += 1
                _item = QTableWidgetItem()
                _item.setData(Qt.DisplayRole, int(year))
                self.ui.TBL_resultat.setItem(i, 0, _item)

                df_1 = pd.DataFrame()
                df_2 = pd.DataFrame()
                df_3 = pd.DataFrame()
                df_4 = pd.DataFrame()
                df_1 = df[df['fach'].str.contains("1")]
                df_1['datum'] = pd.to_datetime(df_1['datum'])
                df_1 = df_1[df_1['datum'].dt.year == year]
                df_2 = df[df['fach'].str.contains("2")]
                df_2['datum'] = pd.to_datetime(df_2['datum'])
                df_2 = df_2[df_2['datum'].dt.year == year]
                df_3 = df[df['fach'].str.contains("3")]
                df_3['datum'] = pd.to_datetime(df_3['datum'])
                df_3 = df_3[df_3['datum'].dt.year == year]
                df_4 = df[df['fach'].str.contains("4")]
                df_4['datum'] = pd.to_datetime(df_4['datum'])
                df_4 = df_4[df_4['datum'].dt.year == year]

                _item1 = QTableWidgetItem()
                _item2 = QTableWidgetItem()
                _item3 = QTableWidgetItem()
                _item4 = QTableWidgetItem()

                anz_1 = df_1.shape[0]
                anz_2 = df_2.shape[0]
                anz_3 = df_3.shape[0]
                anz_4 = df_4.shape[0]

                if self.normiert:
                    anz_float = 0.0
                    sum = int(anz_1) + int(anz_2) + int(anz_3) + int(anz_4)
                    if sum > 0:
                        anz_float = int(anz_1) * 100 / sum
                        _item1.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        anz_float = int(anz_2) * 100 / sum
                        _item2.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        anz_float = int(anz_3) * 100 / sum
                        _item3.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        anz_float = int(anz_4) * 100 / sum
                        _item4.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                    else:
                        anz_float = 0.0
                        _item1.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        _item2.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        _item3.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                        _item4.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                else:
                    _item1.setData(Qt.DisplayRole, int(anz_1))
                    _item2.setData(Qt.DisplayRole, int(anz_2))
                    _item3.setData(Qt.DisplayRole, int(anz_3))
                    _item4.setData(Qt.DisplayRole, int(anz_4))
                self.ui.TBL_resultat.setItem(i, 1, _item1)
                self.ui.TBL_resultat.setItem(i, 2, _item2)
                self.ui.TBL_resultat.setItem(i, 3, _item3)
                self.ui.TBL_resultat.setItem(i, 4, _item4)
            self.ui.PRGB.setValue(anz_year)
        elif self.ui.RBTN_gr3_netze_jahre.isChecked():
            if self.ui.CHB_fach1.isChecked():
                fach = 1
                df_fach = df[df['fach'].str.contains("1")]
            elif self.ui.CHB_fach2.isChecked():
                fach = 2
                df_fach = df[df['fach'].str.contains("2")]
            elif self.ui.CHB_fach3.isChecked():
                fach = 3
                df_fach = df[df['fach'].str.contains("3")]
            elif self.ui.CHB_fach4.isChecked():
                fach = 4
                df_fach = df[df['fach'].str.contains("4")]
            else:
                rberi_lib.QMessageBoxB("ok", "Bitte Fach auswählen.", "Fehlende Auswahl.").exec_()
                return

            self.ui.TBL_resultat.setHorizontalHeaderItem(0, QTableWidgetItem(self.first_header))

            self.ui.TBL_resultat.clear()
            ende_year = self.ui.DTE_ende.date().year()
            start_year = self.ui.DTE_start.date().year()
            anz_year = ende_year - start_year
            self.ui.TBL_resultat.setColumnCount(anz_year + 2)
            for i in range(anz_year + 1):
                self.ui.TBL_resultat.setHorizontalHeaderItem(i+1, QTableWidgetItem(str(start_year + i)))

            df_netze = df.drop_duplicates(subset=['netz'], keep='first', inplace=False)
            df_netze = df_netze.reset_index(drop=True)
            self.ui.TBL_resultat.setRowCount(df_netze.shape[0])
            self.ui.PRGB.setMaximum(df_netze.shape[0])
            self.ui.PRGB.setValue(0)
            for row, content in df_netze.iterrows():
                # self.ui.TBL_resultat.setVerticalHeaderItem(row, QTableWidgetItem(content['netz']))
                self.ui.PRGB.setValue(row)
                self.ui.TBL_resultat.setItem(row, 0, QTableWidgetItem(content['netz']))
                df_tmp = df_fach[df_fach['netz'].str.contains(content['netz'])]
                for i in range(start_year, ende_year + 1):
                    df_tmp2 = df_tmp.query("jahr == @i")
                    _item = QTableWidgetItem()
                    if self.ui.CHB_normiert.isChecked():
                        df_tmp3 = df[df['netz'].str.contains(content['netz'])]
                        df_jahreszahl_pro_netz = df_tmp3.query("jahr == @i")
                        normierungsfaktor = df_jahreszahl_pro_netz.shape[0]
                        anz_float = int(df_tmp2.shape[0]) * 100 / normierungsfaktor if normierungsfaktor > 0 else 0
                        _item.setData(Qt.DisplayRole, "{:.0f}".format(anz_float) + "%")
                    else:
                        _item.setData(Qt.DisplayRole, df_tmp2.shape[0])
                    self.ui.TBL_resultat.setItem(row, i-start_year+1, _item)
            self.ui.PRGB.setValue(self.ui.PRGB.maximum())

    def close(self):
        super().close()

    def export(self):
        save_path = str(QFileDialog.getExistingDirectory(None, "Select Directory"))
        save_path = save_path.replace("/", "\\")
        filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + "_" + self.user + "_NetzfachAuswertung"
        complete_filename = '{0}\\{1}{2}'.format(save_path, filename, '.csv')
        try:
            self.get_table_as_df().to_csv(complete_filename, header=True, index=True)
        except PermissionError as excp:
            rberi_lib.QMessageBoxB('ok', "Keine Berechtigung zum Speichern in diesem Verzeichnis.",
                                   "Berechtigung", excp.strerror).exec_()
        except FileNotFoundError as excp:
            rberi_lib.QMessageBoxB('ok', "Verzeichnis nicht gefunden. Bitte erneut versuchen.",
                                   "Kein Verzeichnis", excp.strerror).exec_()

    def halloffame_clicked(self):
        self.ui.DTE_start.setDate(QDate(1963, 6, 30))
        self.ui.DTE_ende.setDate(QDate(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day))

    def saison_clicked(self):
        self.ui.DTE_start.setDate(QDate(datetime.date.today().year, 6, 30))
        self.ui.DTE_ende.setDate(QDate(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day))

    def set_group_visibility(self, visible: bool = False):
        self.ui.RBTN_gr3_netze_faecher.setEnabled(visible)
        self.ui.RBTN_gr3_netze_jahre.setEnabled(visible)
        self.ui.RBTN_gr3_jahre_faecher.setEnabled(visible)
        self.ui.CHB_fach1.setEnabled(visible)
        self.ui.CHB_fach2.setEnabled(visible)
        self.ui.CHB_fach3.setEnabled(visible)
        self.ui.CHB_fach4.setEnabled(visible)

    def DTE_changed(self):
        if self.ui.DTE_ende.date().year() - self.ui.DTE_start.date().year() > 0:
            self.set_group_visibility(True)
        else:
            self.set_group_visibility(False)

    def netz_auswahl(self):
        if self.ui.CMB_netz.currentIndex() != 0:
            self.ui.RBTN_alle.setChecked(False)
        else:
            self.ui.RBTN_alle.setChecked(True)

    def normiert_clicked(self):
        self.normiert = True if self.ui.CHB_normiert.isChecked() else False

    def get_table_as_df(self, **kwargs):
        number_of_rows = self.ui.TBL_resultat.rowCount()
        number_of_columns = self.ui.TBL_resultat.columnCount()
        items = []
        for x in range(self.ui.TBL_resultat.columnCount()):
            if self.ui.TBL_resultat.horizontalHeaderItem(x) is not None:
                items.append(self.ui.TBL_resultat.horizontalHeaderItem(x).text())
            else:
                items.append("")
        tmp_df = pd.DataFrame(
            columns=items,  # Fill columns
            index=range(number_of_rows)  # Fill rows
        )

        copymode = False
        if kwargs:
            for kwarg in kwargs:
                if kwarg == 'only_copy':
                    copymode = kwargs[kwarg]

        for i in range(number_of_rows):
            if self.ui.TBL_resultat.item(i, 0) is None and not copymode:
                self.ui.TBL_resultat.removeRow(i)
                continue
            for j in range(number_of_columns):
                try:
                    if self.ui.TBL_resultat.item(i, j) is not None:
                        tmp_df.iloc[i, j] = int(self.ui.TBL_resultat.item(i, j).text())
                    else:
                        tmp_df.iloc[i, j] = None
                except ValueError:
                    try:
                        if self.ui.TBL_resultat.item(i, j) is not None:
                            tmp_df.iloc[i, j] = pd.to_datetime(self.ui.TBL_resultat.item(i, j).text()).dt.date
                        else:
                            tmp_df.iloc[i, j] = None
                    except Exception as excp:
                        if self.ui.TBL_resultat.item(i, j) is not None:
                            tmp_df.iloc[i, j] = self.ui.TBL_resultat.item(i, j).text()
                        else:
                            tmp_df.iloc[i, j] = None
                        if self.debug:
                            print(f"Exception: {excp}")

        tmp_df = tmp_df.set_index([tmp_df.columns[0]])
        return tmp_df

    def get_query_text(self) -> str:
        if self.ui.CMB_netz.currentIndex() != 0:
            self.first_header = "Netz " + self.ui.CMB_netz.currentText()
            return ("SELECT ringnummer, fach, netz, datum, jahr FROM esf WHERE datum >= '" + self.ui.DTE_start.date().toString(
                "yyyy-MM-dd") +
                    "' AND datum <= '" + self.ui.DTE_ende.date().toString("yyyy-MM-dd") + "' AND netz = '" + self.ui.CMB_netz.currentText() +
                    "'")
        elif self.ui.RBTN_alle.isChecked():
            self.first_header = "Alle Netze"
            return ("SELECT ringnummer, fach, netz, datum, jahr FROM esf WHERE datum >= '" + self.ui.DTE_start.date().toString(
                "yyyy-MM-dd") +
                    "' AND datum <= '" + self.ui.DTE_ende.date().toString("yyyy-MM-dd") + "'")
        else:
            df_nets_to_select = pd.DataFrame()
            if self.ui.RBTN_hi.isChecked():
                self.first_header = "Netze hinten"
                try:
                    df_nets_to_select = pd.read_sql("SELECT Netz from netze WHERE left(zuordnung, 3) LIKE 'hi_'", self.engine)
                except Exception as err:
                    rberi_lib.QMessageBoxB("ok", "Datenbankfehler oder Abfragefehler. Siehe Details.",
                                           "Datenbankfehler", str(err)).exec_()
                    return

            elif self.ui.RBTN_vo.isChecked():
                self.first_header = "Netze vorne"
                try:
                    df_nets_to_select = pd.read_sql("SELECT Netz from netze WHERE left(zuordnung, 3) LIKE 'vo_'", self.engine)
                except Exception as err:
                    rberi_lib.QMessageBoxB("ok", "Datenbankfehler oder Abfragefehler. Siehe Details.",
                                           "Datenbankfehler", str(err)).exec_()
                    return
            elif self.ui.RBTN_hi_li.isChecked():
                self.first_header = "Netze hinten links"
                try:
                    df_nets_to_select = pd.read_sql("SELECT Netz from netze WHERE left(zuordnung, 5) LIKE 'hi_li'", self.engine)
                except Exception as err:
                    rberi_lib.QMessageBoxB("ok", "Datenbankfehler oder Abfragefehler. Siehe Details.",
                                           "Datenbankfehler", str(err)).exec_()
                    return
            elif self.ui.RBTN_hi_re.isChecked():
                self.first_header = "Netze hinten rechts"
                try:
                    df_nets_to_select = pd.read_sql("SELECT Netz from netze WHERE left(zuordnung, 5) LIKE 'hi_re'", self.engine)
                except Exception as err:
                    rberi_lib.QMessageBoxB("ok", "Datenbankfehler oder Abfragefehler. Siehe Details.",
                                           "Datenbankfehler", str(err)).exec_()
                    return
            elif self.ui.RBTN_vo_li.isChecked():
                self.first_header = "Netze vorne links"
                try:
                    df_nets_to_select = pd.read_sql("SELECT Netz from netze WHERE left(zuordnung, 5) LIKE 'vo_li'", self.engine)
                except Exception as err:
                    rberi_lib.QMessageBoxB("ok", "Datenbankfehler oder Abfragefehler. Siehe Details.",
                                           "Datenbankfehler", str(err)).exec_()
                    return
            elif self.ui.RBTN_vo_re.isChecked():
                self.first_header = "Netze vorne rechts"
                try:
                    df_nets_to_select = pd.read_sql("SELECT Netz from netze WHERE left(zuordnung, 5) LIKE 'vo_re'", self.engine)
                except Exception as err:
                    rberi_lib.QMessageBoxB("ok", "Datenbankfehler oder Abfragefehler. Siehe Details.",
                                           "Datenbankfehler", str(err)).exec_()
                    return

            txt_netze = "("
            for row_index, row_content in df_nets_to_select.iterrows():
                txt_netze += "'" + str(row_content[0]) + "',"
            txt_netze = txt_netze[:-1] + ")"
            return ("SELECT ringnummer, fach, netz, datum, jahr FROM esf WHERE datum >= '" + self.ui.DTE_start.date().toString(
                "yyyy-MM-dd") +
                    "' AND datum <= '" + self.ui.DTE_ende.date().toString("yyyy-MM-dd") + "' AND netz in " + txt_netze)


