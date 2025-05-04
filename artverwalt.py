# -*- coding: utf-8 -*-
import datetime

import pandas as pd
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (QMessageBox, QWidget, QComboBox, QPlainTextEdit, QLineEdit,
                             QCheckBox, QDialog, QVBoxLayout, QPushButton, )
from typing import Literal
from mariadb import Connection
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from scipy import stats

import rberi_lib
from basic_definitions import constants
from Beringungsoberflaeche.artenverwaltung.artenverwaltung.widget import Ui_Widget
from Beringungsoberflaeche.artenverwaltung.artenverwaltung.dialog_toleranzen import Ui_Dialog


def get_ringtypref(txt: str) -> str:
    txt = txt.split(";")
    if txt[0] == 'TypID':
        return 'Null'
    return txt[0]


class DiagWind(QDialog):
    mw_ueber = pyqtSignal(int)
    std_ueber = pyqtSignal(int)

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.BTN_std_uebernehmen = QPushButton()
        self.BTN_mw_uebernehmen = QPushButton()
        self.BTN_std_uebernehmen.setText('Stdandard-Abweichung übernehmen')
        self.BTN_mw_uebernehmen.setText('Mittelwert übernehmen')
        # self.BTN_std_uebernehmen.setGeometry(10,10,100,25)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(self.BTN_std_uebernehmen)
        layout.addWidget(self.BTN_mw_uebernehmen)
        self.setLayout(layout)
        self.setWindowTitle('Gaußverteilung')

        self.BTN_std_uebernehmen.clicked.connect(self.stdab_uebernehmen)
        self.BTN_mw_uebernehmen.clicked.connect(self.mw_uebernehmen)

    def stdab_uebernehmen(self):
        self.std_ueber.emit(1)

    def mw_uebernehmen(self):
        self.mw_ueber.emit(1)


class ToleranzenWindow(QDialog):
    saveSignal = pyqtSignal(dict)

    def __init__(self, df_art: type(pd.DataFrame), engine: Connection, parent=None):
        QDialog.__init__(self, parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.df_art = df_art
        self.set_values()
        self.engine = engine
        self.ui_diag = DiagWind()
        self.art_mw = 0.0
        self.art_stdab = 0.0
        self.faktor_up = 0.0
        self.faktor_low = 0.0
        self.df2save = None

        self.ui.BTN_teilfeder_diag.clicked.connect(self.teilfeder_diagramm)
        self.ui.BTN_fluegel_diag.clicked.connect(self.fluegel_diagramm)
        self.ui.BTN_quot_diag.clicked.connect(self.quot_diagramm)
        self.ui.BTN_masse_diag.clicked.connect(self.masse_diagramm)
        self.ui.BTN_speichern.clicked.connect(self.write_df_to_save)
        self.ui.BTN_abbruch.clicked.connect(self.reject)

    def set_values(self):
        self.ui.INP_teilfeder_mw.setText(str(self.df_art['f_ex'].iloc[0]))
        self.ui.INP_teilfeder_stdab.setText(str(self.df_art['f_s'].iloc[0]))
        self.ui.INP_teilfeder_tol_neg.setText(str(self.df_art['f_d_neg'].iloc[0]))
        self.ui.INP_teilfeder_tol_pos.setText(str(self.df_art['f_d_pos'].iloc[0]))

        self.ui.INP_fluegel_mw.setText(str(self.df_art['w_ex'].iloc[0]))
        self.ui.INP_fluegel_stdab.setText(str(self.df_art['w_s'].iloc[0]))
        self.ui.INP_fluegel_tol_neg.setText(str(self.df_art['w_d_neg'].iloc[0]))
        self.ui.INP_fluegel_tol_pos.setText(str(self.df_art['w_d_pos'].iloc[0]))

        self.ui.INP_masse_mw.setText(str(self.df_art['g_ex'].iloc[0]))
        self.ui.INP_masse_stdab.setText(str(self.df_art['g_s'].iloc[0]))
        self.ui.INP_masse_tol_neg.setText(str(self.df_art['g_d_neg'].iloc[0]))
        self.ui.INP_masse_tol_pos.setText(str(self.df_art['g_d_pos'].iloc[0]))

        self.ui.INP_quot_mw.setText(str(self.df_art['quo_f3_flg_ex'].iloc[0]))
        self.ui.INP_quot_stdab.setText(str(self.df_art['quo_f3_flg_s'].iloc[0]))
        self.ui.INP_quot_tol_neg.setText(str(self.df_art['quo_f3_flg_d_neg'].iloc[0]))
        self.ui.INP_quot_tol_pos.setText(str(self.df_art['quo_f3_flg_d_pos'].iloc[0]))

    def teilfeder_diagramm(self):
        self.ui_diag.figure.clear()
        ax = self.ui_diag.figure.add_subplot(111)

        df_esf_art = pd.read_sql('SELECT teilfeder FROM esf WHERE art = "' + self.df_art['esf_kurz'][0] +
                                 '" AND teilfeder > 0', self.engine)
        q1 = df_esf_art.quantile(0.25)
        q3 = df_esf_art.quantile(0.75)
        iqr = q3 - q1
        lower_lim = q1 - 1.5 * iqr
        upper_lim = q3 + 1.5 * iqr
        outliers_15_low = df_esf_art < lower_lim
        outliers_15_up = df_esf_art > upper_lim
        df_esf_art_clean = df_esf_art[~(outliers_15_low | outliers_15_up)]
        df_esf_art_clean = df_esf_art_clean.dropna()
        y_data = stats.norm.pdf(df_esf_art_clean['teilfeder'], df_esf_art_clean['teilfeder'].mean(),
                                df_esf_art_clean['teilfeder'].std())
        x_data = df_esf_art_clean['teilfeder']

        ax.plot(x_data, y_data, 'o', label='Daten aus DB')
        ax.axvline(df_esf_art_clean['teilfeder'].mean() +
                   float(self.ui.INP_teilfeder_tol_pos.text()) * df_esf_art_clean['teilfeder'].std(),
                   color='green', label="Toleranz 'oben'")
        ax.axvline(
            df_esf_art_clean['teilfeder'].mean() - float(self.ui.INP_teilfeder_tol_neg.text()) * df_esf_art_clean[
                'teilfeder'].std(), color='red', label="Toleranz 'unten'")
        ax.axvline(df_esf_art_clean['teilfeder'].mean(), color='darkgrey',
                   label=f"Mittelwert ({df_esf_art_clean['teilfeder'].mean():.3f})")
        ax.axvline(df_esf_art_clean['teilfeder'].mean() + df_esf_art_clean['teilfeder'].std(), color='grey',
                   label=f'Std.-Abw. ({df_esf_art_clean['teilfeder'].std():.3f})')
        ax.legend()
        ax.set_title('Teilfederlänge "' + self.df_art['deutsch'].iloc[0] + '" über alle Datensätze:',
                     loc='center')
        ax.grid(True, color="grey", linewidth="0.4", axis='both', which='both')
        ax.set_xlabel('Teilfederlänge H3 [mm]')
        self.ui_diag.canvas.draw()
        self.ui_diag.mw_ueber.connect(lambda param: self.overtake_val(param, df_esf_art_clean['teilfeder'].mean(),
                                                                      self.ui.INP_teilfeder_mw))
        self.ui_diag.std_ueber.connect(lambda param: self.overtake_val(param, df_esf_art_clean['teilfeder'].std(),
                                                                       self.ui.INP_teilfeder_stdab))
        self.ui_diag.exec_()

# alt: 97.1907

    def overtake_val(self, i: int, mw: float, obj: QWidget):
        if i == 1:
            obj.setText(f"{mw:.4f}")
            if self:
                pass

    def fluegel_diagramm(self):
        self.ui_diag.figure.clear()
        ax = self.ui_diag.figure.add_subplot(111)

        df_esf_art = pd.read_sql('SELECT fluegel FROM esf WHERE art = "' + self.df_art['esf_kurz'][0] +
                                 '" AND fluegel > 0', self.engine)
        q1 = df_esf_art.quantile(0.25)
        q3 = df_esf_art.quantile(0.75)
        iqr = q3 - q1
        lower_lim = q1 - 1.5 * iqr
        upper_lim = q3 + 1.5 * iqr
        outliers_15_low = df_esf_art < lower_lim
        outliers_15_up = df_esf_art > upper_lim
        df_esf_art_clean = df_esf_art[~(outliers_15_low | outliers_15_up)]
        df_esf_art_clean = df_esf_art_clean.dropna()
        y_data = stats.norm.pdf(df_esf_art_clean['fluegel'], df_esf_art_clean['fluegel'].mean(),
                                df_esf_art_clean['fluegel'].std())
        x_data = df_esf_art_clean['fluegel']
        ax.plot(x_data, y_data, 'o', label='Daten aus DB')
        ax.axvline(
            df_esf_art_clean['fluegel'].mean() + float(self.ui.INP_fluegel_tol_pos.text()) * df_esf_art_clean[
                'fluegel'].std(), color='green', label="Toleranz 'oben'")
        ax.axvline(
            df_esf_art_clean['fluegel'].mean() - float(self.ui.INP_fluegel_tol_neg.text()) * df_esf_art_clean[
                'fluegel'].std(), color='red', label="Toleranz 'unten'")
        ax.axvline(df_esf_art_clean['fluegel'].mean(), color='darkgrey',
                   label=f"Mittelwert ({df_esf_art_clean['fluegel'].mean():.3f})")
        ax.axvline(df_esf_art_clean['fluegel'].mean() + df_esf_art_clean['fluegel'].std(), color='grey',
                   label=f'Std.-Abw. ({df_esf_art_clean['fluegel'].std():.3f})')
        ax.legend()
        ax.set_title('Flügellänge "' + self.df_art['deutsch'].iloc[0] + '" über alle Datensätze:',
                     loc='center')
        ax.grid(True, color="grey", linewidth="0.4", axis='both', which='both')
        ax.set_xlabel('Flügellänge [mm]')
        self.ui_diag.canvas.draw()
        self.ui_diag.mw_ueber.connect(lambda param: self.overtake_val(param, df_esf_art_clean['fluegel'].mean(),
                                                                      self.ui.INP_fluegel_mw))
        self.ui_diag.std_ueber.connect(lambda param: self.overtake_val(param, df_esf_art_clean['fluegel'].std(),
                                                                       self.ui.INP_fluegel_stdab))
        self.ui_diag.exec_()

    def quot_diagramm(self):
        self.ui_diag.figure.clear()
        ax = self.ui_diag.figure.add_subplot(111)

        df_esf_art = pd.read_sql('SELECT teilfeder, fluegel FROM esf WHERE art = "' + self.df_art['esf_kurz'][0] +
                                 '" AND fluegel > 0 AND teilfeder > 0', self.engine)
        df_esf_art_q = df_esf_art['teilfeder']/df_esf_art['fluegel']

        q1 = df_esf_art_q.quantile(0.25)
        q3 = df_esf_art_q.quantile(0.75)
        iqr = q3 - q1
        lower_lim = q1 - 1.5 * iqr
        upper_lim = q3 + 1.5 * iqr
        outliers_15_low = df_esf_art_q < lower_lim
        outliers_15_up = df_esf_art_q > upper_lim
        df_esf_art_clean = df_esf_art_q[~(outliers_15_low | outliers_15_up)]
        df_esf_art_clean = df_esf_art_clean.dropna()
        y_data = stats.norm.pdf(df_esf_art_clean, df_esf_art_clean.mean(),
                                df_esf_art_clean.std())
        x_data = df_esf_art_clean
        ax.plot(x_data, y_data, 'o', label='Daten aus DB')
        ax.axvline(
            df_esf_art_clean.mean() + float(self.ui.INP_quot_tol_pos.text()) * df_esf_art_clean.std(), color='green',
            label="Toleranz 'oben'")
        ax.axvline(
            df_esf_art_clean.mean() - float(self.ui.INP_quot_tol_neg.text()) * df_esf_art_clean.std(), color='red',
            label="Toleranz 'unten'")
        ax.axvline(df_esf_art_clean.mean(), color='darkgrey',
                   label=f"Mittelwert ({df_esf_art_clean.mean():.3f})")
        ax.axvline(df_esf_art_clean.mean() + df_esf_art_clean.std(), color='grey',
                   label=f'Std.-Abw. ({df_esf_art_clean.std():.3f})')
        ax.legend()
        ax.set_title('Verhältnis H3/Flügel "' + self.df_art['deutsch'].iloc[0] + '" über alle Datensätze:',
                     loc='center')
        ax.grid(True, color="grey", linewidth="0.4", axis='both', which='both')
        ax.set_xlabel('Quotient H3/Flügel')

        self.ui_diag.canvas.draw()
        self.ui_diag.mw_ueber.connect(lambda param: self.overtake_val(param, df_esf_art_clean.mean(),
                                                                      self.ui.INP_quot_mw))
        self.ui_diag.std_ueber.connect(lambda param: self.overtake_val(param, df_esf_art_clean.std(),
                                                                       self.ui.INP_quot_stdab))
        self.ui_diag.exec_()

    def masse_diagramm(self):
        self.ui_diag.figure.clear()
        ax = self.ui_diag.figure.add_subplot(111)

        df_esf_art = pd.read_sql('SELECT gewicht FROM esf WHERE art = "' + self.df_art['esf_kurz'][0] +
                                 '" AND gewicht > 0', self.engine)

        q1 = df_esf_art.quantile(0.25)
        q3 = df_esf_art.quantile(0.75)
        iqr = q3 - q1
        lower_lim = q1 - 1.5 * iqr
        upper_lim = q3 + 1.5 * iqr
        outliers_15_low = df_esf_art < lower_lim
        outliers_15_up = df_esf_art > upper_lim
        df_esf_art_clean = df_esf_art[~(outliers_15_low | outliers_15_up)]
        df_esf_art_clean = df_esf_art_clean.dropna()
        y_data = stats.norm.pdf(df_esf_art_clean, df_esf_art_clean.mean(),
                                df_esf_art_clean.std())
        x_data = df_esf_art_clean
        ax.plot(x_data, y_data, 'o', label='Daten aus DB')
        val1 = df_esf_art_clean.mean()
        val2 = float(self.ui.INP_masse_tol_pos.text())
        val2a = float(self.ui.INP_masse_tol_neg.text())
        val3 = df_esf_art_clean.std()
        val4 = val1 + val2 * val3
        val5 = val1 - val2a * val3
        ax.axvline(val4[0], color='green', label="Toleranz 'oben'")
        ax.axvline(val5[0], color='red', label="Toleranz 'unten'")
        ax.axvline(val1[0], color='darkgrey', label=f"Mittelwert ({val1['gewicht']:.3f})")
        ax.axvline(val1[0] + val3[0], color='grey', label=f'Std.-Abw. ({val3['gewicht']:.3f})')
        ax.legend()
        ax.set_title('Masse "' + self.df_art['deutsch'].iloc[0] + '" über alle Datensätze:', loc='center')
        ax.grid(True, color="grey", linewidth="0.4", axis='both', which='both')
        ax.set_xlabel('Masse [g]')
        self.ui_diag.canvas.draw()
        self.ui_diag.mw_ueber.connect(lambda param: self.overtake_val(param, val1['gewicht'], self.ui.INP_masse_mw))
        self.ui_diag.std_ueber.connect(lambda param: self.overtake_val(param, val3['gewicht'], self.ui.INP_masse_stdab))
        self.ui_diag.exec_()

    def write_df_to_save(self):
        try:
            self.df2save = {
                "teilfeder_mw": rberi_lib.return_float(self.ui.INP_teilfeder_mw.text()),
                "teilfeder_std": rberi_lib.return_float(self.ui.INP_teilfeder_stdab.text()),
                "teilfeder_faktor_min": rberi_lib.return_float(self.ui.INP_teilfeder_tol_neg.text()),
                "teilfeder_faktor_max": rberi_lib.return_float(self.ui.INP_teilfeder_tol_pos.text()),
                "fluegel_mw": rberi_lib.return_float(self.ui.INP_fluegel_mw.text()),
                "fluegel_std": rberi_lib.return_float(self.ui.INP_fluegel_stdab.text()),
                "fluegel_faktor_min": rberi_lib.return_float(self.ui.INP_fluegel_tol_neg.text()),
                "fluegel_faktor_max": rberi_lib.return_float(self.ui.INP_fluegel_tol_pos.text()),
                "quot_mw": rberi_lib.return_float(self.ui.INP_quot_mw.text()),
                "quot_std": rberi_lib.return_float(self.ui.INP_quot_stdab.text()),
                "quot_faktor_min": rberi_lib.return_float(self.ui.INP_quot_tol_neg.text()),
                "quot_faktor_max": rberi_lib.return_float(self.ui.INP_quot_tol_pos.text()),
                "masse_mw": rberi_lib.return_float(self.ui.INP_masse_mw.text()),
                "masse_std": rberi_lib.return_float(self.ui.INP_masse_stdab.text()),
                "masse_faktor_min": rberi_lib.return_float(self.ui.INP_masse_tol_neg.text()),
                "masse_faktor_max": rberi_lib.return_float(self.ui.INP_masse_tol_pos.text()),
                "show_quot_msg": 1 if self.ui.CHB_quot_anzeigen.isChecked() else 0,
                "show_masse_msg": 1 if self.ui.CHB_masse_anzeigen.isChecked() else 0,
            }
            self.saveSignal.emit(self.df2save)
            self.accept()
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Die zu speichernden Werte konnten nicht geschrieben werden.',
                                   'Kritischer Fehler!', str(excp)).exec_()

    def check_df_2_save(self):
        if self.df2save:
            return True
        else:
            return False


class ArtverwaltungWindow(QWidget):
    loggingNeeded = pyqtSignal(str, datetime.datetime, str, str)

    def __init__(self, engine: Connection, parent=None):
        QWidget.__init__(self, parent)
        self.tol_window = None
        self.tolerances = None
        self.logging = {}
        self.ui = Ui_Widget()
        self.ui.setupUi(self)
        self._engine = engine
        self.bd = constants()
        self.counter = 0
        self.bearbeitungs_status = 0
        self.start_list = []
        self.ende_list = []

        self.ui.BTN_toleranzen.setEnabled(False)

        if self.engine_connected():
            self.df_arten = pd.read_sql('SELECT * FROM arten', self.get_engine())
            self.df_arten_sort = self.df_arten.sort_values(by=['deutsch'])
        else:
            rberi_lib.QMessageBoxB('ok', 'Keine Datenbankverbindung.', 'Datenbankfehler').exec_()
            self.close()

        self.ui.CMB_arten.setEditable(True)

        if self.ui.CMB_arten.count() <= 0:
            for el in self.df_arten_sort.deutsch.tolist():
                self.ui.CMB_arten.addItem(el)
                # erstmalig werden die Werte des Vogels rechts eingetragen...

        self.fill_values()

        self.ui.BTN_close.clicked.connect(self.on_close_click)
        self.ui.BTN_cancel.clicked.connect(self.on_cancel_click)
        self.ui.BTN_bearb.clicked.connect(self.on_bearb_click)
        self.ui.BTN_save.clicked.connect(self.on_save_click)
        self.ui.BTN_neu.clicked.connect(self.on_new_click)
        self.ui.BTN_ringtyp_liste.clicked.connect(self.ringtyp_list_click)
        self.ui.CMB_arten.currentIndexChanged.connect(self.new_art_selected)
        self.ui.BTN_toleranzen.clicked.connect(self.toleranzen_click)

        self.ui.INP_ArtD.textChanged.connect(lambda: self.leave_necc_edit(sender=self.ui.INP_ArtD))
        self.ui.INP_ArtL.textChanged.connect(lambda: self.leave_necc_edit(sender=self.ui.INP_ArtL))
        self.ui.INP_ArtE.textChanged.connect(lambda: self.leave_necc_edit(sender=self.ui.INP_ArtE))
        self.ui.INP_ESF_kurz.textChanged.connect(lambda: self.leave_necc_edit(sender=self.ui.INP_ESF_kurz))

    def engine_connected(self) -> bool:
        try:
            self._engine.ping()
        except ConnectionError:
            return False
        return True

    def get_engine(self):
        if self.engine_connected():
            return self._engine
        else:
            return None

    def ringtyp_list_click(self):
        pass

    def toleranzen_click(self):
        df_selected_art = pd.read_sql(
            'SELECT * FROM arten WHERE deutsch="' + str(self.ui.CMB_arten.currentText()) + '"', self.get_engine())
        if df_selected_art.empty:
            return

        self.tol_window = ToleranzenWindow(df_selected_art, self.get_engine())
        self.tol_window.saveSignal.connect(self.setTolerances2Save)

        self.tol_window.exec_()
        # 'hier müssen dann signale/slots gemacht werden fürs speichern'

    def setTolerances2Save(self, vals: dict):
        if not vals:
            return
        if len(vals) <= 0:
            return
        self.ende_list.append('Bullshit')  # nur damit der Speichern Button auch aktiviert wird :)
        if not self.set_state_tuple('gleich'):
            self.ui.BTN_save.setEnabled(True)
        self.tolerances = vals
        
    def getTolerances(self):
        """
                "teilfeder_mw"
                "teilfeder_std"
                "teilfeder_faktor_min"
                "teilfeder_faktor_max"
                "fluegel_mw"
                "fluegel_std"
                "fluegel_faktor_min"
                "fluegel_faktor_max"
                "quot_mw"
                "quot_std"
                "quot_faktor_min"
                "quot_faktor_max"
                "masse_mw"
                "masse_std"
                "masse_faktor_min"
                "masse_faktor_max"
                "show_quot_msg": 1 wenn ja sonst 0,
                "show_masse_msg": 1 wenn ja sonst 0,
        :return: 
        """
        return self.tolerances

    def new_art_selected(self):
        self.fill_values()

    def on_new_click(self):
        self.ui.CMB_arten.setCurrentText("")
        self.clear_artenverwaltung()
        self.clear_artenverwaltung('use')
        self.set_state_tuple("start")
        self.ui.CMB_arten.setEnabled(False)
        self.ui.BTN_bearb.setEnabled(False)
        self.ui.BTN_neu.setEnabled(False)
        self.ui.BTN_close.setEnabled(False)

    def leave_necc_edit(self, sender=None):
        text = ""
        if sender is not None:
            if isinstance(sender, QComboBox):
                text = sender.currentText()
            elif isinstance(sender, QPlainTextEdit):
                text = sender.toPlainText()
            elif isinstance(sender, QLineEdit):
                text = sender.text()
        if len(text) <= 0:
            # content.setStyleSheet("background-color: #rrggbb;")
            if isinstance(sender, QLineEdit):
                sender.setStyleSheet("background-color: rgb(255, 171, 145)")
            self.ui.BTN_save.setEnabled(False)
            self.ui.BTN_toleranzen.setEnabled(False)
        else:
            if isinstance(sender, QLineEdit):
                sender.setStyleSheet("background-color: rgb(0, 0, 0)")
            self.ui.BTN_save.setEnabled(True)
            self.ui.BTN_toleranzen.setEnabled(False)

    def on_save_click(self):
        fehlermeldung = []
        fehler_text = ""
        if len(self.ui.INP_ArtD.text()) <= 0:
            fehlermeldung.append("Artname deutsch")
        if len(self.ui.INP_ArtL.text()) <= 0:
            fehlermeldung.append("Artname lateinisch")
        if len(self.ui.INP_ArtE.text()) <= 0:
            fehlermeldung.append("Artname englisch")
        if len(self.ui.INP_ESF_kurz.text()) <= 0:
            fehlermeldung.append("ESF Kurzname")
        if len(self.ui.CMB_ringtyp_male.currentText()) <= 0:
            fehlermeldung.append("Ringtyp")

        if len(fehlermeldung) == 1:
            fehler_text = "Folgendes Feld fehlt: \n\n" + fehlermeldung[0]
        elif len(fehlermeldung) > 1:
            fehler_text = "Folgende Felder fehlen: \n\n"
            for el in fehlermeldung:
                fehler_text += el + "\n"
        else:
            pass

        if len(fehlermeldung) > 0:
            missingargs_ui = QMessageBox()
            missingargs_ui.setIcon(QMessageBox.Warning)
            missingargs_ui.setWindowTitle("Fehlende Daten ... ")
            missingargs_ui.setText("Bitte fülle alle benötigen (*) Felder aus!")
            missingargs_ui.setDetailedText(fehler_text)
            missingargs_ui.setStandardButtons(QMessageBox.Ok)
            missingargs_ui.setDefaultButton(QMessageBox.Ok)
            missingargs_ui.exec_()
            return
        else:
            # es sind schon mal alle notwendigen Felder befüllt.
            # Prüfung, ob die Art schon vorhanden ist
            ringtypfemale = 'NULL' if self.ui.CMB_ringtyp_female.currentIndex() == 0 else get_ringtypref(
                self.ui.CMB_ringtyp_female.currentText())
            if self.ui.INP_ArtL.text() in self.df_arten["lateinisch"].tolist():
                really_update = QMessageBox()
                really_update.setIcon(QMessageBox.Question)
                really_update.setWindowTitle("Datenänderung")
                really_update.setText("Es existiert bereits ein Eintrag '" + self.ui.INP_ArtD.text() + "' (" +
                                      self.ui.INP_ArtL.text() + "). Sicher überschreiben?")
                really_update.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                really_update.setDefaultButton(QMessageBox.No)
                x = really_update.exec_()
                if x == QMessageBox.Yes:
                    try:
                        cursor = self.get_engine().cursor()
                        sql_txt = ("UPDATE arten SET deutsch='" + self.ui.INP_ArtD.text() + "', " +
                                   "lateinisch ='" + self.ui.INP_ArtL.text() + "', " +
                                   "englisch ='" + self.ui.INP_ArtE.text() + "', " +
                                   "esf_kurz ='" + self.ui.INP_ESF_kurz.text() + "', " +
                                   "erbe_kurz ='" + self.ui.INP_erbe_kurz.text() + "', " +
                                   "prg_art =" + ('1' if self.ui.CHB_programmart.isChecked() else '0') + ", " +
                                   "mri_art =" + ('1' if self.ui.CHB_mriart.isChecked() else '0') + ", " +
                                   "ringtypMaleRef =" + get_ringtypref(self.ui.CMB_ringtyp_male.currentText()) + ", " +
                                   "ringtypFemaleRef =" + ringtypfemale + ", " +
                                   "juv_moult =" + ('1' if self.ui.CHB_juv_mauser.isChecked() else '0') + ", " +
                                   "sex_determ =" + ('1' if self.ui.CHB_sex_moegl.isChecked() else '0') + ", " +
                                   "bemerkung ='" + self.ui.INP_Bemerkung.toPlainText() + "', " +
                                   "euring ='" + self.ui.INP_euring.text() + "', ")
                        if self.tolerances:
                            sql_txt += "f_ex = " + str(self.tolerances['teilfeder_mw']) + ", "
                            sql_txt += "f_s = " + str(self.tolerances['teilfeder_std']) + ", "
                            sql_txt += "f_d_neg = " + str(self.tolerances['teilfeder_faktor_min']) + ", "
                            sql_txt += "f_d_pos = " + str(self.tolerances['teilfeder_faktor_max']) + ", "
                            sql_txt += "w_ex = " + str(self.tolerances['fluegel_mw']) + ", "
                            sql_txt += "w_s = " + str(self.tolerances['fluegel_std']) + ", "
                            sql_txt += "w_d_neg = " + str(self.tolerances['fluegel_faktor_min']) + ", "
                            sql_txt += "w_d_pos = " + str(self.tolerances['fluegel_faktor_max']) + ", "
                            sql_txt += "quo_f3_flg_ex = " + str(self.tolerances['quot_mw']) + ", "
                            sql_txt += "quo_f3_flg_s = " + str(self.tolerances['quot_std']) + ", "
                            sql_txt += "quo_f3_flg_d_neg = " + str(self.tolerances['quot_faktor_min']) + ", "
                            sql_txt += "quo_f3_flg_d_pos = " + str(self.tolerances['quot_faktor_max']) + ", "
                            sql_txt += "show_q_msg = " + str(self.tolerances['show_quot_msg']) + ", "
                            sql_txt += "g_ex = " + str(self.tolerances['masse_mw']) + ", "
                            sql_txt += "g_s = " + str(self.tolerances['masse_std']) + ", "
                            sql_txt += "g_d_neg = " + str(self.tolerances['masse_faktor_min']) + ", "
                            sql_txt += "g_d_pos = " + str(self.tolerances['masse_faktor_max']) + ", "
                            sql_txt += "show_g_msg = " + str(self.tolerances['show_masse_msg']) + " "

                        if sql_txt[-1] == ',':
                            sql_txt = sql_txt[:-1]
                        elif sql_txt[-1] == ' ' and sql_txt[-2] == ',':
                            sql_txt = sql_txt[:-2]
                        sql_txt += " "
                        sql_txt += "WHERE deutsch = '" + self.ui.INP_ArtD.text() + "'"
                        print(sql_txt)
                        cursor.execute(sql_txt)
                        self.get_engine().commit()
                        cursor.close()
                        self.set_logging(datetime.datetime.now(), "verwaltung",
                                         "Artverwaltung: '" + self.ui.INP_ArtD.text() + "' wurde geändert.")
                        self.set_bearbeitungsstatus(False)
                        self.clear_artenverwaltung()
                    except Exception as exc:
                        rberi_lib.QMessageBoxB('ok', "Fehler beim Überschreiben des Datensatzes für '" +
                                               self.ui.INP_ArtD.text() + "'. Siehe Details für die genaue " +
                                               "Fehlerbeschreibung. Bitte kontaktiert den " +
                                               "Support!", "Fehlermeldung", str(exc)).exec_()
                else:
                    return
            else:
                try:
                    cursor = self.get_engine().cursor()
                    if self.tolerances:
                        tol_txt_set = ("f_ex, f_s, f_d_neg, f_d_pos, w_ex, w_s, w_d_neg, w_d_pos, quo_f3_flg_ex, "
                                       "quo_f3_flg_s, quo_f3_flg_d_neg, quo_f3_flg_d_pos, show_q_msg, g_ex, g_s, "
                                       "g_d_neg,g_d_pos, show_g_msg")
                        tol_txt_val = (str(self.tolerances['teilfeder_mw']) + ", " +
                                       str(self.tolerances['teilfeder_std']) + ", " +
                                       str(self.tolerances['teilfeder_faktor_min']) + ", " +
                                       str(self.tolerances['teilfeder_faktor_max']) + ", " +
                                       str(self.tolerances['fluegel_mw']) + ", " +
                                       str(self.tolerances['fluegel_std']) + ", " +
                                       str(self.tolerances['fluegel_faktor_min']) + ", " +
                                       str(self.tolerances['fluegel_faktor_max']) + ", " +
                                       str(self.tolerances['quot_mw']) + ", " +
                                       str(self.tolerances['quot_std']) + ", " +
                                       str(self.tolerances['quot_faktor_min']) + ", " +
                                       str(self.tolerances['quot_faktor_max']) + ", " +
                                       str(self.tolerances['show_quot_msg']) + ", " +
                                       str(self.tolerances['masse_mw']) + ", " +
                                       str(self.tolerances['masse_std']) + ", " +
                                       str(self.tolerances['masse_faktor_min']) + ", " +
                                       str(self.tolerances['masse_faktor_max']) + ", " +
                                       str(self.tolerances['show_masse_msg']))
                    else:
                        tol_txt_set = ""
                        tol_txt_val = ""
                    cursor.execute(
                        "INSERT INTO arten (deutsch, lateinisch, englisch, esf_kurz, erbe_kurz, prg_art, mri_art, "
                        "ring_serie, ringtypMaleRef, ringtypFemaleRef, juv_moult, sex_determ, bemerkung, euring, " +
                        tol_txt_set + ") "
                        "VALUES ('" +
                        self.ui.INP_ArtD.text() + "', '" +
                        self.ui.INP_ArtL.text() + "', '" +
                        self.ui.INP_ArtE.text() + "', '" +
                        self.ui.INP_ESF_kurz.text() + "', '" +
                        self.ui.INP_erbe_kurz.text() + "', " +
                        str(self.ui.CHB_programmart.isChecked()) + ", " +
                        str(self.ui.CHB_mriart.isChecked()) +
                        ", NULL, " +
                        get_ringtypref(self.ui.CMB_ringtyp_male.currentText()) + ", " +
                        ringtypfemale + ", " +
                        str(self.ui.CHB_juv_mauser.isChecked()) + ", " +
                        str(self.ui.CHB_sex_moegl.isChecked()) + ", '" +
                        self.ui.INP_Bemerkung.toPlainText() + "', '" +
                        self.ui.INP_euring.text() + "', " +
                        tol_txt_val + ")")
                    self.get_engine().commit()
                    cursor.close()
                    self.set_logging(datetime.datetime.now(), "verwaltung",
                                     "Artverwaltung: '" + self.ui.INP_ArtD.text() + "' wurde hinzugefügt.")
                    rberi_lib.QMessageBoxB('ok', "Es wurde erfolgreich ein neuer Datensatz hinzugefügt:\n\n" +
                                           self.ui.INP_ArtD.text() + " (" + self.ui.INP_ArtL.text() + ")",
                                           'Info').exec_()
                    self.set_bearbeitungsstatus(False)
                    self.clear_artenverwaltung()
                except Exception as exc:
                    rberi_lib.QMessageBoxB('ok', "Fehler beim Speichern des Datensatzes für '" +
                                           self.ui.INP_ArtD.text() + "'. Siehe Details für die genaue " +
                                           "Fehlerbeschreibung. Bitte kontaktiert den Support!", "Fehler",
                                           str(exc)).exec_()

    def set_logging(self, zeitstempel: datetime.datetime, kennung: str, change: str):
        self.loggingNeeded.emit('unknown', zeitstempel, kennung, change)

    def get_logging(self):
        return self.logging

    def on_cancel_click(self):
        if not self.get_bearbeitungsstatus():
            self.clear_artenverwaltung()
        else:
            self.set_state_tuple("ende")
            if not self.set_state_tuple("gleich"):
                self.query_verwerfen("not exit")
            else:
                self.set_bearbeitungsstatus(False)
                self.clear_artenverwaltung()

    def on_close_click(self):
        if not self.get_bearbeitungsstatus():
            self.close()
            self.destroy(True, True)
        else:
            self.query_verwerfen("exit")

    def clear_artenverwaltung(self, setting='lock'):
        for el in range(self.ui.GRID_Artenverwaltung.count()):
            item = self.ui.GRID_Artenverwaltung.itemAt(el).widget()
            if (isinstance(item, QLineEdit)) or (isinstance(item, QPlainTextEdit)):
                if setting == "lock":
                    item.clear()
                    #                    p = item.viewport().palette()
                    item.setStyleSheet("background-color: rgb(0, 0, 0)")
                    #                    p.setColor(item.viewport().backgroundRole(), QtGui.QColor(255, 255, 255))
                    #                    item.viewport().setPalette(p)
                    item.setEnabled(False)
                elif setting == "use":
                    item.setEnabled(True)
            elif isinstance(item, QCheckBox):
                if setting == "lock":
                    item.setChecked(False)
                    item.setEnabled(False)
                elif setting == "use":
                    item.setEnabled(True)
            elif isinstance(item, QComboBox):
                if setting == "lock":
                    item.setCurrentIndex = 0
                    item.setEnabled(False)
                elif setting == "use":
                    item.setEnabled(True)

        for el in range(self.ui.gridLayout.count()):
            item = self.ui.gridLayout.itemAt(el).widget()
            if isinstance(item, QComboBox):
                if setting == "lock":
                    item.setCurrentIndex = 0
                    item.setEnabled(False)
                elif setting == "use":
                    item.setEnabled(True)

        if setting == "lock":
            self.ui.BTN_save.setEnabled(False)
            self.ui.BTN_toleranzen.setEnabled(False)
        elif setting == "use":
            self.ui.BTN_save.setEnabled(True)
            self.ui.BTN_toleranzen.setEnabled(True)

        self.ui.CMB_arten.setEnabled(True)
        self.ui.BTN_bearb.setEnabled(True)
        self.ui.BTN_neu.setEnabled(True)
        self.ui.BTN_close.setEnabled(True)

    def on_bearb_click(self):
        # hier wird (einmalig) alle ringserien aus arten in ringserien eingetragen... - erstbefüllung
        #    for art in self.df_arten.iterrows():
        #        self.df_ringserien = pd.read_sql('SELECT * FROM ringserie', engine)
        #        print(art[1][7])
        #        print(self.df_ringserien.ringserie.tolist())
        #        if art[1][7] not in self.df_ringserien.ringserie.tolist():
        #            print(art[1][7] + " nicht enthalten!")
        #            cursor.execute("INSERT INTO ringserie (ringserie, material) VALUES (%s, %s)", (str(art[1][7]),"!"))
        #            engine.commit()
        #    pass

        df_selected_art = pd.read_sql(
            'SELECT * FROM arten WHERE deutsch="' + str(self.ui.CMB_arten.currentText()) + '"', self.get_engine())
        if df_selected_art.empty:
            return

        if not self.bearbeitungs_status:
            self.set_bearbeitungsstatus(True)
        for el in range(self.ui.GRID_Artenverwaltung.count()):
            item = self.ui.GRID_Artenverwaltung.itemAt(el).widget()
            # print(f'el = {el}')
            if item is not None:
                # print(f'el = {el} mit item.objectName() = {item.objectName()}')
                if self.bd.get_debug():
                    print(str(item.objectName) + " ... isEnabled = " + str(item.isEnabled()))
                item.setEnabled(True)
        for el in range(self.ui.gridLayout.count()):
            item = self.ui.gridLayout.itemAt(el).widget()
            if item is not None:
                if self.bd.get_debug():
                    print(f'Objektname = {item.objectName()} ... isEnabled = {item.isEnabled()}')
                item.setEnabled(True)
                print(f'Objektname = {item.objectName()} ... isEnabled = {item.isEnabled()}')

        self.ui.BTN_save.setEnabled(True)
        self.ui.BTN_toleranzen.setEnabled(True)
        if self.ui.CMB_arten.currentText() != "":
            self.fill_values()
        self.set_state_tuple("start")
        self.ui.CMB_arten.setEnabled(False)
        self.ui.BTN_bearb.setEnabled(False)
        self.ui.BTN_neu.setEnabled(False)
        self.ui.BTN_close.setEnabled(False)

    def fill_values(self):
        # self.counter += 1
        # print(f"fill_values aufgerufen ... {self.counter}. Mal")

        if self.ui.CMB_ringtyp_male.count() <= 0:
            df_ringtypen = pd.read_sql('SELECT * FROM ringtyp', self.get_engine())
            self.ui.CMB_ringtyp_male.addItem("TypID; Klasse; Material; Durchmesser [mm]")
            self.ui.CMB_ringtyp_female.addItem("TypID; Klasse; Material; Durchmesser [mm]")
            for index, el_series in df_ringtypen.iterrows():
                el_txt = (str(el_series.ringtypID) + "; " + str(el_series.klasse) + "; " + str(el_series.material) + "; " +
                          str(el_series.durchmesser))
                self.ui.CMB_ringtyp_male.addItem(el_txt)
                self.ui.CMB_ringtyp_female.addItem(el_txt)

        df_selected_art = pd.read_sql(
            'SELECT * FROM arten WHERE deutsch="' + str(self.ui.CMB_arten.currentText()) + '"', self.get_engine())
        if len(df_selected_art) > 0:
            typ_male_id = str(df_selected_art["ringtypMaleRef"].iloc[0])
            typ_female_id = str(df_selected_art["ringtypFemaleRef"].iloc[0])
            for el in range(self.ui.CMB_ringtyp_male.count()):
                if typ_male_id in self.ui.CMB_ringtyp_male.itemText(el):
                    self.ui.CMB_ringtyp_male.setCurrentText(self.ui.CMB_ringtyp_male.itemText(el))
            if typ_female_id != 'None':
                for el in range(self.ui.CMB_ringtyp_female.count()):
                    if typ_female_id in self.ui.CMB_ringtyp_female.itemText(el):
                        self.ui.CMB_ringtyp_female.setCurrentText(self.ui.CMB_ringtyp_female.itemText(el))
                    else:
                        self.ui.CMB_ringtyp_female.setCurrentIndex(0)
            else:
                self.ui.CMB_ringtyp_female.setCurrentText(self.ui.CMB_ringtyp_female.itemText(0))


            """if not isinstance(typ_female_id, type(None)):
                if typ_female_id != 'None':
                    self.ui.CMB_ringtyp_female.setEnabled(True)
                    for el in range(self.ui.CMB_ringtyp_female.count()):
                        if typ_female_id in self.ui.CMB_ringtyp_female.itemText(el):
                            self.ui.CMB_ringtyp_female.setCurrentText(self.ui.CMB_ringtyp_female.itemText(el))
                else:
                    self.ui.CMB_ringtyp_female.setEnabled(False)
            else:
                self.ui.CMB_ringtyp_female.setEnabled(False)"""
            self.ui.INP_ArtD.setText(df_selected_art["deutsch"][0])
            self.ui.INP_ArtL.setText(df_selected_art["lateinisch"][0])
            self.ui.INP_ArtE.setText(df_selected_art["englisch"][0])
            self.ui.INP_ESF_kurz.setText(df_selected_art["esf_kurz"][0])
            self.ui.INP_erbe_kurz.setText(df_selected_art["erbe_kurz"][0])
            self.ui.CHB_programmart.setChecked(df_selected_art["prg_art"][0])
            self.ui.CHB_mriart.setChecked(df_selected_art["mri_art"][0])
            self.ui.CHB_juv_mauser.setChecked(df_selected_art["juv_moult"][0])
            self.ui.CHB_sex_moegl.setChecked(df_selected_art["sex_determ"][0])
            self.ui.INP_Bemerkung.setPlainText(df_selected_art["bemerkung"][0])
            self.ui.INP_euring.setText(df_selected_art["euring"][0])
        else:
            self.clear_artenverwaltung()

    def query_verwerfen(self, source: Literal['not exit', 'exit'] = 'not exit'):
        if rberi_lib.QMessageBoxB('cyn', 'Es wird gerade ein Datensatz bearbeitet. Eingabe wirklich verwerfen?',
                                  "Eingabe verwerfen?").exec_() == QMessageBox.Yes:
            self.set_bearbeitungsstatus(False)
            self.clear_artenverwaltung()
            if source == "exit":
                self.close()

    def set_bearbeitungsstatus(self, val: bool = True):
        self.bearbeitungs_status = val

    def get_bearbeitungsstatus(self):
        return self.bearbeitungs_status

    def set_state_tuple(self, state: Literal['start', 'ende', 'gleich'] = 'gleich'):
        if state == "start":
            self.start_list += (self.ui.INP_ArtD.text() + self.ui.INP_ArtL.text() + self.ui.INP_ArtE.text() +
                                self.ui.INP_ESF_kurz.text() + self.ui.INP_erbe_kurz.text() +
                                self.ui.CMB_ringtyp_male.currentText() +
                                self.ui.CMB_ringtyp_female.currentText() +
                                (str(self.ui.CHB_programmart.isChecked())) +
                                (str(self.ui.CHB_mriart.isChecked())) +
                                (str(self.ui.CHB_juv_mauser.isChecked())) +
                                (str(self.ui.CHB_sex_moegl.isChecked())) +
                                self.ui.INP_Bemerkung.toPlainText() + self.ui.INP_euring.text())
        elif state == "ende":
            self.ende_list += (self.ui.INP_ArtD.text() + self.ui.INP_ArtL.text() + self.ui.INP_ArtE.text() +
                               self.ui.INP_ESF_kurz.text() + self.ui.INP_erbe_kurz.text() +
                               self.ui.CMB_ringtyp_male.currentText() +
                               self.ui.CMB_ringtyp_female.currentText() +
                               (str(self.ui.CHB_programmart.isChecked())) +
                               (str(self.ui.CHB_mriart.isChecked())) +
                               (str(self.ui.CHB_juv_mauser.isChecked())) +
                               (str(self.ui.CHB_sex_moegl.isChecked())) +
                               self.ui.INP_Bemerkung.toPlainText() + self.ui.INP_euring.text())
        elif state == "gleich":
            if self.start_list == self.ende_list:
                return True
            else:
                return False
        else:
            return False
