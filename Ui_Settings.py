# -*- coding: utf-8 -*-

from pathlib import Path
import cv2
import mariadb
import pandas as pd
import rberi_lib
from PyQt5.QtWidgets import QDialog, QLineEdit, QMessageBox, QFileDialog
from cryptography.fernet import Fernet
from Beringungsoberflaeche.Einstellungen.settingswindow import Ui_SettingsWindow


class Ui_Settings(QDialog):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self.ui = Ui_SettingsWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Einstellungen")

        self.password_button_text = self.ui.BTN_password_show.text()
        self.db_conn_status = False
        self.mariaDB_engine = None
        # Datenbankverbindung muss erst überprüft werden (Hauptprogramm von dem Einstellungen aus aufgerufen wird.)
        self.ui.LBL_DB_green.setVisible(False)
        self.ui.LBL_DB_red.setVisible(False)
        self.path = None
        self._qss_path = None

        self.key = ""
        self.BilderPfad = ""
        self.hilfeBilderPfad = ""
        self.debug = ""
        self.mit_anmeldung = ""
        self.tbl_name_ringserie = ""
        self.age_adult_allowed = ""
        self.zoom_seitenbreite = ""
        self.version = ""
        self.kontaktdaten = ""
        self.mariabackuppath = ""
        self.hinweis = ""
        self.drucker_vendor_id = ""
        self.drucker_typ_id = ""
        self.usb_vol_name = ""

        self.ui.BTN_save.clicked.connect(self._save_clicked)
        self.ui.BTN_close.clicked.connect(self._close_clicked)
        self.ui.BTN_help_host.clicked.connect(lambda: self._help_clicked("host"))
        self.ui.BTN_help_port.clicked.connect(lambda: self._help_clicked("port"))
        self.ui.BTN_help_user.clicked.connect(lambda: self._help_clicked("user"))
        self.ui.BTN_help_database.clicked.connect(lambda: self._help_clicked("database"))
        self.ui.BTN_password_show.clicked.connect(lambda: self._password_show(self.ui.BTN_password_show.text()))
        self.ui.BTN_bilder_file.clicked.connect(self._bilder_filedialog)
        self.ui.BTN_qss_file.clicked.connect(self._qss_filedialog)
        self.ui.BTN_DB_connect.clicked.connect(self._db_connection)
        self.ui.BTN_camera.clicked.connect(self._camera_test)
        self.ui.INP_camera_port.setText("0")

        self.__getSettings()

        if kwargs:
            for kw in kwargs:
                if kw == 'nocon' and not kwargs[kw]:
                    self._db_connection()
                elif kw == 'nocon' and kwargs[kw]:
                    pass
        else:
            self._db_connection()

    def __getSettings(self):
        file = open('basic_definitions.ini', 'r')
        content = file.readlines()

        for l in content:
            if "self.DB_host" in l:
                host = l[l.find("=") + 1:].strip()
                self.ui.INP_DB_host.setText(host)
            elif "self.DB_user" in l:
                user = l[l.find("=") + 1:].strip()
                self.ui.INP_DB_user.setText(user)
            elif "self.DB_port=" in l:
                port = l[l.find("=") + 1:].strip()
                self.ui.INP_DB_port.setText(port)
            elif "self.DB_database=" in l:
                db = l[l.find("=") + 1:].strip()
                self.ui.INP_DB_database.setText(db)
            elif "self.ringnummern_laenge=" in l:
                ringl = l[l.find("=") + 1:].strip()
                self.ui.INP_ringnr_laenge.setText(ringl)
            elif "self.key" in l:
                self.key = l[l.find("=") + 1:].strip()
                self.key = self.key.encode()
                f = Fernet(self.key)
            elif "self.DB_password" in l:
                pw = l[l.find("=") + 1:].strip()
                token = f.decrypt(pw.encode())
                pw = token.decode()
                self.ui.INP_DB_password.setText(pw)
            elif "self.camport" in l:
                camp = l[l.find("=") + 1:].strip()
                self.ui.INP_camera_port.setText(camp)
            elif "self.qss" in l:
                qss = l[l.find("=") + 1:].strip()
                self.ui.INP_qss_file.setText(qss)
            elif "self.BilderPfad" in l:
                txt = l[l.find("=") + 1:].strip()
                self.BilderPfad = txt
                self.ui.INP_bilder_dir.setText(txt)
            elif "self.hilfeBilderPfad" in l:
                txt = l[l.find("=") + 1:].strip()
                self.hilfeBilderPfad = txt
                self.ui.INP_hilfebilder_dir.setText(txt)
            elif "self.debug" in l:
                txt = l[l.find("=") + 1:].strip()
                self.debug = txt
            elif "self.mit_anmeldung" in l:
                txt = l[l.find("=") + 1:].strip()
                self.mit_anmeldung = txt
            elif "self.tbl_name_ringserie" in l:
                txt = l[l.find("=") + 1:].strip()
                self.tbl_name_ringserie = txt
            elif "self.age_adult_allowed" in l:
                txt = l[l.find("=") + 1:].strip()
                self.age_adult_allowed = txt
            elif "self.zoom_seitenbreite" in l:
                txt = l[l.find("=") + 1:].strip()
                self.zoom_seitenbreite = txt
            elif "self.version" in l:
                txt = l[l.find("=") + 1:].strip()
                self.version = txt
            elif "self.kontaktdaten" in l:
                txt = l[l.find("=") + 1:].strip()
                self.kontaktdaten = txt
            elif "self.mariabackuppath" in l:
                txt = l[l.find("=") + 1:].strip()
                self.mariabackuppath = txt
            elif "self.HINWEIS" in l:
                txt = l[l.find("=") + 1:].strip()
                self.hinweis = txt
            elif "self.drucker_vendor_id" in l:
                txt = l[l.find("=") + 1:].strip()
                self.drucker_vendor_id = txt
            elif "self.drucker_typ_id" in l:
                txt = l[l.find("=") + 1:].strip()
                self.drucker_typ_id = txt
            elif "self.usb_vol_name" in l:
                txt = l[l.find("=") + 1:].strip()
                self.usb_vol_name = txt

    def _load_further_data(self):
        df_defaults = pd.read_sql("SELECT * FROM defaults", self.mariaDB_engine)
        df_stationen = pd.read_sql("SELECT * FROM stationen", self.mariaDB_engine)
        df_zentralen = pd.read_sql("SELECT * FROM zentralen", self.mariaDB_engine)
        self.ui.CMB_Station.addItems(df_stationen["Name"])
        self.ui.CMB_Zentrale.addItems(df_zentralen["Name"])
        station_sec_key = df_defaults.loc[0, "Station"]
        zentrale_sec_key = df_defaults.loc[0, "Zentrale"]
        for l in df_stationen.iterrows():
            if l[1][0] == station_sec_key:
                self.ui.CMB_Station.setCurrentText(str(l[1][1]))
        for l in df_zentralen.iterrows():
            if l[1][0] == zentrale_sec_key:
                self.ui.CMB_Zentrale.setCurrentText(str(l[1][1]))

    def _save_clicked(self):
        if self._get_connection():
            text = "erfolgreich aufgebaut. "
        else:
            text = "NICHT erfolgreich aufgebaut!! Ohne Datenbankverbindung können nur die Datenbank-Einstellungen " \
                   "gespeichert werden. Sollten diese falsch sein, kann keine Verbindung mehr zur Datenbank " \
                   "aufgebaut werden! Weißt Du genau was Du tust?"
        msgb = QMessageBox(QMessageBox.Warning, "Wirklich speichern?", "Einstellungen wirklich speichern? "
                                                                       "Die Datenbankverbindung wurde " + text,
                           QMessageBox.Yes | QMessageBox.No)
        msgb.setDefaultButton(QMessageBox.No)
        if msgb.exec_() != QMessageBox.Yes:
            return

        try:
            msg_txt = ""
            ringnr_num = 0
            if self.ui.INP_ringnr_laenge.text():
                ringnr_num = int(self.ui.INP_ringnr_laenge.text())
            if ringnr_num < 8:
                ringnr_num = 8
                msg_txt = "Ringnummer muss eine Länge von 8 Zeichen haben."
            elif ringnr_num > 12:
                ringnr_num = 12
                msg_txt = "Ringnummer darf maximal eine Länge von 12 Zeichen haben."
        except Exception as e:
            msgb = QMessageBox()
            msgb.setWindowTitle("Ringnummernlänge")
            msgb.setText("Die Ringnummernlänge muss numerisch zwischen 8 und 12 liegen.")
            msgb.setDetailedText(f"Exception: {e}")
            msgb.setStandardButtons(QMessageBox.Ok)
            msgb.exec_()
            return

        camport = self.ui.INP_camera_port.text()
        qss = self.ui.INP_qss_file.text()

        new_content = []
        txt = "FIN_19780617_20240525\n"
        new_content.append(txt)
        txt = "self.key=7mwDo5p3mft4qW3DJzhwKzC65vgYWgW45FhL_0DOg2E=\n"
        new_content.append(txt)
        txt = "self.DB_host=" + self.ui.INP_DB_host.text() + "\n"
        new_content.append(txt)
        txt = "self.DB_user=" + self.ui.INP_DB_user.text()  + "\n"
        new_content.append(txt)
        txt = "self.DB_port=" + self.ui.INP_DB_port.text() + "\n"
        new_content.append(txt)
        txt = "self.DB_database=" + self.ui.INP_DB_database.text() + "\n"
        new_content.append(txt)
        fernet_dings = Fernet(self.key)
        token = fernet_dings.encrypt(self.ui.INP_DB_password.text().encode())
        pw = token.decode()
        txt = "self.DB_password=" + pw + "\n"
        new_content.append(txt)
        txt = "self.ringnummern_laenge=" + str(ringnr_num) + "\n"
        new_content.append(txt)
        txt = "self.camport=" + str(camport) + "\n"
        new_content.append(txt)
        txt = "self.qss=" + str(qss) + "\n"
        new_content.append(txt)
        txt = "self.BilderPfad=" + self.ui.INP_bilder_dir.text() + "\n"
        new_content.append(txt)
        txt = "self.hilfeBilderPfad=" + self.ui.INP_hilfebilder_dir.text() + "\n"
        new_content.append(txt)
        txt = "self.debug=" + str(self.debug) + "\n"
        new_content.append(txt)
        txt = "self.mit_anmeldung=" + str(self.mit_anmeldung) + "\n"
        new_content.append(txt)
        txt = "self.tbl_name_ringserie=" + str(self.tbl_name_ringserie) + "\n"
        new_content.append(txt)
        txt = "self.age_adult_allowed=" + str(self.age_adult_allowed) + "\n"
        new_content.append(txt)
        txt = "self.zoom_seitenbreite=" + str(self.zoom_seitenbreite) + "\n"
        new_content.append(txt)
        txt = "self.version=" + str(self.version) + "\n"
        new_content.append(txt)
        txt = "self.kontaktdaten=" + str(self.kontaktdaten) + "\n"
        new_content.append(txt)
        txt = "self.mariabackuppath=" + str(self.mariabackuppath) + "\n"
        new_content.append(txt)
        txt = "self.HINWEIS=" + str(self.hinweis) + "\n"
        new_content.append(txt)
        txt = "self.drucker_vendor_id=" + str(self.drucker_vendor_id) + "\n"
        new_content.append(txt)
        txt = "self.drucker_typ_id=" + str(self.drucker_typ_id) + "\n"
        new_content.append(txt)
        txt = "self.usb_vol_name=" + str(self.usb_vol_name) + "\n"
        new_content.append(txt)

        file = open("basic_definitions.ini", "w")
        file.writelines(new_content)
        file.close()

        if self._get_connection():
            df_defaults = pd.read_sql("SELECT * FROM defaults", self.mariaDB_engine)
            df_stationen = pd.read_sql("SELECT * FROM stationen", self.mariaDB_engine)
            df_zentralen = pd.read_sql("SELECT * FROM zentralen", self.mariaDB_engine)
            stations_name = self.ui.CMB_Station.currentText()
            zentrale_name = self.ui.CMB_Zentrale.currentText()
            stations_sec_key = 1
            zentrale_sec_key = 1

            for line in df_stationen.iterrows():
                if str(line[1][1]) == stations_name:
                    stations_sec_key = line[1][0]
            for line in df_zentralen.iterrows():
                if line[1][1] == zentrale_name:
                    zentrale_sec_key = line[1][0]
            cursor = self.mariaDB_engine.cursor()
            if stations_sec_key is None:
                stations_sec_key = 1
            if zentrale_sec_key is None:
                zentrale_sec_key = 1
            if self.BilderPfad is None:
                self.BilderPfad = "not set"
            SQL_text = ("UPDATE defaults SET Station=" + str(stations_sec_key) + ", " +
                        "Zentrale=" + str(zentrale_sec_key) + ", Bilderverzeichnis='" + self.BilderPfad + "' WHERE defaultID=1")
            cursor.execute(SQL_text)
            self.mariaDB_engine.commit()
        self.accept()

    def _close_clicked(self):
        self.reject()

    def _help_clicked(self, source=""):
        if source == 'host':
            msgB = QMessageBox(QMessageBox.Information, "Information", "Der Host ist die IP unter der die Datenbank "
                                                                       "zu suchen ist. Läuft der DB-Server lokal, kann "
                                                                       "hier entweder \n\n127.0.0.1 oder \nlocalhost "
                                                                       "\n\neingetragen werden. Läuft die Datenbank "
                                                                       "auf einem Server, der über das Internet "
                                                                       "verbunden werden muss, ist die entsprechende "
                                                                       "IP des Servers einzutragen.",
                               QMessageBox.Ok)
            msgB.exec_()
            return
        elif source == 'user':
            msgB = QMessageBox(QMessageBox.Information, "Information", "Hier muss der Username des Users eingetragen "
                                                                       "werden, der für die Datenbank Admin-Rechte "
                                                                       "hat, also lesen und schreiben kann.",
                               QMessageBox.Ok)
            msgB.exec_()
            return
        elif source == 'port':
            msgB = QMessageBox(QMessageBox.Information, "Information", "Der Port über den der Server erreichbar ist. "
                                                                       "Standardport für MariaDB-Datenbanken ist \n\n"
                                                                       "3306",
                               QMessageBox.Ok)
            msgB.exec_()
            return
        elif source == 'database':
            msgB = QMessageBox(QMessageBox.Information, "Information", "Name der Datenbank. Bitte beachten, dass nur "
                                                                       "der Name (ohne Hochkommata) angegeben werden "
                                                                       "muss und nicht der "
                                                                       "Pfad. Diesen generiert sich MariaDB selbst.",
                               QMessageBox.Ok)
            msgB.exec_()
            return

    def _password_show(self, status=""):
        if status == self.password_button_text:
            self.ui.INP_DB_password.setEchoMode(QLineEdit.Normal)
            self.ui.BTN_password_show.setText("******")
        else:
            self.ui.INP_DB_password.setEchoMode(QLineEdit.Password)
            self.ui.BTN_password_show.setText(self.password_button_text)

    def _bilder_filedialog(self):
        # self.ui.INP_bilder_dir.clear()
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            path = Path(dir_name).as_posix()
            self.ui.INP_bilder_dir.setText(str(path))

    def _bilder_filedialog(self):
        # self.ui.INP_bilder_dir.clear()
        dir_name = QFileDialog.getExistingDirectory(self, "Select a Directory")
        if dir_name:
            path = Path(dir_name).as_posix()
            self.ui.INP_hilfebilder_dir.setText(str(path))

    def _qss_filedialog(self):
        file_name = QFileDialog.getOpenFileName(self, "Wähle qss-File")
        # print(f"[0] = {file_name[0]}, [1] = {file_name[1]}")
        if file_name:
            self._qss_path = Path(file_name[0]).as_posix()
            self.ui.INP_qss_file.setText(str(self._qss_path))

    def _db_connection(self):
        try:
            user = self.ui.INP_DB_user.text()
            password = self.ui.INP_DB_password.text()
            host = self.ui.INP_DB_host.text()
            try:
                port = int(self.ui.INP_DB_port.text())
            except ValueError as e:
                msgb = QMessageBox(QMessageBox.Warning, "Fehler ...", "Port muss eine Ganzzahl sein.", QMessageBox.Ok)
                msgb.exec_()
                return
            database = self.ui.INP_DB_database.text()
            self.mariaDB_engine = mariadb.connect(user=user, password=password, host=host, port=port, database=database)
            if self._get_connection():
                self._set_connection(1)
                self._load_further_data()
            else:
                self._set_connection(0)
        except mariadb.Error as excp:
            print(f"Error connecting to MariaDB Platform.: {excp}")
            x = QMessageBox()
            x.setWindowTitle("Fehler!")
            x.setText(f"Es trat ein Verbindungsfehler auf.")
            x.setDetailedText(f"Detaillierte Systemfehlermeldung aus mariaDB: \n\n{excp}")
            x.addButton(QMessageBox.Ok)
            x.exec_()
            self._set_connection(0)
            return

    def _set_connection(self, status=0):
        if status == 0:
            self.ui.LBL_DB_green.setVisible(False)
            self.ui.LBL_DB_red.setVisible(True)
            self.db_conn_status = False
        elif status == 1:
            self.ui.LBL_DB_green.setVisible(True)
            self.ui.LBL_DB_red.setVisible(False)
            self.db_conn_status = True

    def _get_connection(self):
        try:
            self.mariaDB_engine.ping()
        except:
            return False
        return True

    def _camera_test(self):
        def klick(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                self.no_click = False
        cam_port = int(self.ui.INP_camera_port.text())

        cam = cv2.VideoCapture(cam_port, cv2.CAP_DSHOW)
        if not cam.isOpened():
            a = rberi_lib.QMessageBoxB('yn', f"Kann die Kamera auf Slot {cam_port} nicht öffnen. Soll der nächste Slot "
                                             f"getestet werden?", 'Kamerafehler').exec_()
            if a == QMessageBox.Yes:
                if self.ui.CMB_camera_source.currentIndex() < self.ui.CMB_camera_source.maxCount() - 2:
                    self.ui.CMB_camera_source.setCurrentIndex(self.ui.CMB_camera_source.currentIndex())
                    self._camera_test()
                else:
                    rberi_lib.QMessageBoxB('ok', 'Keine weiteren Slots gefunden.', 'Kamerafehler').exec_()
            else:
                return

        self.no_click = True
        result, image = cam.read()
        if not result:
            rberi_lib.QMessageBoxB('ok', f"Kein Videostream der Kamera gefunden. Stelle sicher, dass die Kamera im "
                                         f"Videomodus ist.", 'Kamerafehler').exec_()
            return

        cv2.namedWindow('Kameratest', cv2.WINDOW_KEEPRATIO)
        cv2.setWindowTitle('Kameratest', 'Beliebige Taste um Fenster zu schliessen ... ')
        cv2.resizeWindow('Kameratest', 1280, 720)

        cv2.namedWindow('Kameratest')
        cv2.setMouseCallback('Kameratest', klick)

        while cv2.waitKey(1) < 0 and result and self.no_click:
            result, image = cam.read()
            cv2.imshow('Kameratest', image)

        try:
            cam.release()
            cv2.destroyWindow("Kameratest")
        except Exception as excp:
            self.ui.statusbar.showMessage(f"Kameratest-Fenster nicht mehr gefunden ... kein Handlungsbedarf! Excp: {excp}",
                                          3000)
            cv2.destroyAllWindows()

