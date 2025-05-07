import csv
import math
import os
import subprocess
import time
from ctypes import c_ushort, c_ulong
from typing import Literal

import cv2
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import win32api
import win32con
import win32gui
import wmi
from PIL import Image
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QFontMetrics
from _ctypes import Structure

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure as FigBon
# from qtpy import QtWebEngineWidgets

from usbmonitor import USBMonitor

import mariadb
import sys
import numpy as np
import pandas as pd
from escpos.printer import Usb

import ringserienverwaltung
import artverwalt
import rberi_lib

from datetime import datetime, timedelta, date
from kalendar import Pentad
from PyQt5.QtWidgets import (QPushButton, QLabel, QLineEdit, QGridLayout, QComboBox, QMessageBox, QDialog,
                             QTableWidgetItem, QTreeWidgetItem, QTreeWidgetItemIterator, QFileDialog, QWidget,
                             QVBoxLayout, QShortcut, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView,
                             QMainWindow, QCheckBox, QRadioButton, QTableWidget, QHBoxLayout, QListWidget,
                             QListWidgetItem, QPlainTextEdit)
from PyQt5 import QtWidgets, QtGui, QtCore, sip, QtWebEngineWidgets
from PyQt5.QtCore import QDate, QTime, Qt, QEvent, QObject, QRegularExpression, pyqtSignal, pyqtSlot, QEventLoop, QTimer
from cryptography.fernet import Fernet
from img_viewer import ImageViewer

from calendar import monthrange

from Beringungsoberflaeche.dialog_new_user import Ui_Dialogs
from Beringungsoberflaeche.beringerverwaltung_ui import Dialog_beringerverwaltung
from Beringungsoberflaeche.Hauptfenster_neu.mainwindow_V2 import Ui_MainWindow
from Beringungsoberflaeche.Hauptfenster_neu.walinder import Ui_Form as UiWalinder
from Beringungsoberflaeche.search_gui.dialog import Ui_Dialog
from Beringungsoberflaeche.datenblatt_zwei.ui_datenblatt_zwei import Ui_Ui_Datenblatt_zwei as Ui_db2
from Beringungsoberflaeche.Hauptfenster_neu.search_ringnb_form import Ui_Form as Ui_search_ringnb_form
from Beringungsoberflaeche.Hauptfenster_neu.benutzereinstellungen import Ui_Dialog as Ui_Dialog_usersettings
from ringserienverwaltung import _RingSerienVerwaltung as Ui_RingSerienVerwaltung
from Ui_Settings import Ui_Settings

matplotlib.use('Qt5Agg')

# ToDo

#
# Device change events (WM_DEVICECHANGE wParam)
#
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEQUERYREMOVE = 0x8001
DBT_DEVICEQUERYREMOVEFAILED = 0x8002
DBT_DEVICEMOVEPENDING = 0x8003
DBT_DEVICEREMOVECOMPLETE = 0x8004
DBT_DEVICETYPESSPECIFIC = 0x8005
DBT_CONFIGCHANGED = 0x0018
#
# type of device in DEV_BROADCAST_HDR
#
DBT_DEVTYP_OEM = 0x00000000
DBT_DEVTYP_DEVNODE = 0x00000001
DBT_DEVTYP_VOLUME = 0x00000002
DBT_DEVTYPE_PORT = 0x00000003
DBT_DEVTYPE_NET = 0x00000004

#
# media types in DBT_DEVTYP_VOLUME
#
DBTF_MEDIA = 0x0001
DBTF_NET = 0x0002

WORD = c_ushort
DWORD = c_ulong


class DEV_BROADCAST_HDR(Structure):
    _fields_ = [
        ("dbch_size", DWORD),
        ("dbch_devicetype", DWORD),
        ("dbch_reserved", DWORD)
    ]


class DEV_BROADCAST_VOLUME(Structure):
    _fields_ = [
        ("dbcv_size", DWORD),
        ("dbcv_devicetype", DWORD),
        ("dbcv_reserved", DWORD),
        ("dbcv_unitmask", DWORD),
        ("dbcv_flags", WORD)
    ]


class Notification(QObject):
    stickAdded = pyqtSignal(str)

    def __init__(self):
        super().__init__(parent=None)

        message_map = {
            win32con.WM_DEVICECHANGE: self.onDeviceChange
        }

        wc = win32gui.WNDCLASS()
        hinst = wc.hInstance = win32api.GetModuleHandle(None)
        wc.lpszClassName = "DeviceChangeDemo"
        wc.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wc.hbrBackground = win32con.COLOR_WINDOW
        wc.lpfnWndProc = message_map
        classAtom = win32gui.RegisterClass(wc)
        style = win32con.WS_OVERLAPPED | win32con.WS_SYSMENU
        self.hwnd = win32gui.CreateWindow(
            classAtom,
            "Device Change Demo",
            style,
            0, 0,
            win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT,
            0, 0,
            hinst, None
        )
        self.added_drive = None

    def onDeviceChange(self, hwnd, msg, wparam, lparam) -> int:
        #
        # WM_DEVICECHANGE:
        #  wParam - type of change: arrival, removal etc.
        #  lParam - what's changed?
        #    if it's a volume then...
        #  lParam - what's changed more exactly
        #
        """

        :param hwnd:
        :param msg:
        :param wparam:
        :param lparam:
        :return:
        1 - wenn Medium hinzugefügt wurde
        2 - sonst
        """
        if self:
            print(f"hwnd = {hwnd}")
            print(f"msg = {msg}")
            print(f"wparam = {wparam}")
            print(f"lparam = {lparam}")

        dev_broadcast_hdr = DEV_BROADCAST_HDR.from_address(lparam)
        if wparam == DBT_DEVICEARRIVAL:
            if bd.get_debug():
                print("Something's arrived")
            if dev_broadcast_hdr.dbch_devicetype == DBT_DEVTYP_VOLUME:
                if bd.get_debug():
                    print("It's a volume!")
                dev_broadcast_volume = DEV_BROADCAST_VOLUME.from_address(lparam)
                drive_letter = drive_from_mask(dev_broadcast_volume.dbcv_unitmask)
                if bd.get_debug():
                    print("in drive", chr(ord("A") + drive_letter))
                self.added_drive = chr(ord("A") + drive_letter)
                self.stickAdded.emit(self.added_drive)
        return 1


class Backup_GUI2(QDialog):
    def __init__(self):
        super().__init__(parent=None)

        self.backup_command = []
        self.laufwerk = ""
        self.fullback_needed = False

        self.setWindowTitle("Tägliches Backup")
        self.resize(1000, 700)
        self.layout = QVBoxLayout()

        self.button_backup = QPushButton('Backup!')
        self.button_backup.setVisible(False)
        self.button_backup.clicked.connect(self.backup_clicked)
        self.info = QListWidget()
        self.info.addItem(QListWidgetItem("Bitte USB - Stick einstecken ... "))
        self.info.addItem(QListWidgetItem("Suche nach NEUEM Speichermedium ... "))
        self.info.setAutoScroll(True)

        self.spacerItem = QtWidgets.QSpacerItem(10, 30, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)

        self.layout.addWidget(self.info)
        self.layout.addItem(self.spacerItem)
        self.layout.addWidget(self.button_backup)

        self.setLayout(self.layout)
        self.deviceNotification = Notification()

        self.deviceNotification.stickAdded.connect(self.usb_stick_added)

    @pyqtSlot(str)
    def usb_stick_added(self, laufwerk: str):
        self.laufwerk = laufwerk
        self.info.addItem(QListWidgetItem('... Speichermedium GEFUNDEN! Laufwerk: ' + self.laufwerk))
        wochentage = {0: 'Montag', 1: 'Dienstag', 2: 'Mittwoch', 3: 'Donnerstag', 4: 'Freitag', 5: 'Samstag', 6: 'Sonntag'}
        heutiger_wochentag = wochentage[datetime.today().weekday()]
        if heutiger_wochentag in os.listdir(self.laufwerk + ":\\"):
            # backup_dir = self.laufwerk + ":\\" + heutiger_wochentag
            # backup_dir = os.path.join(self.laufwerk, heutiger_wochentag)
            backup_dir = self.laufwerk + ":\\" + heutiger_wochentag
        else:
            rberi_lib.QMessageBoxB('ok', 'Dies scheint der falsche USB Stick zu sein. Der Backup - Stick muss die Wochentage '
                                         'als Verzeichnisse im Grundverzeichnis enthalten. Also ' + self.laufwerk +
                                   ':\\Montag\\, '
                                   + self.laufwerk + ':\\Dienstag\\ etc.', 'Falsches Speichermedium', qss=bd.get_qss()).exec_()
            return

        mariabackup_path = bd.get_mariabackuppath()

        if len(os.listdir(backup_dir)) <= 0:
            self.fullback_needed = True
            self.backup_command = [mariabackup_path, "--backup", "--target-dir=" + backup_dir, "--databases=" +
                                   bd.get_database(), "--user=" + bd.get_user(), "--password=" + bd.get_p_deco()]
        else:
            self.fullback_needed = False
            inc_number = np.array([], dtype=int)
            for inc in os.listdir(backup_dir):
                if "inc" in inc:
                    inc_number = np.append(inc_number, int(inc[3:]))
            if not np.size(inc_number):
                last_inc_path = backup_dir
                new_inc_path = os.path.join(backup_dir, "inc1")
            else:
                last_inc = inc_number.max()
                new_inc = last_inc + 1
                last_inc_path = os.path.join(backup_dir, "inc" + str(last_inc))
                new_inc_path = os.path.join(backup_dir, "inc" + str(new_inc))

            if bd.get_debug():
                print(f"last_inc_path = {last_inc_path}")
                print(f"new_inc_path = {new_inc_path}")

            self.backup_command = [mariabackup_path, "--backup", "--target-dir=" + new_inc_path, "--incremental-basedir=" +
                                   last_inc_path, "--databases=" + bd.get_database(), "--user=" + bd.get_user(),
                                   "--password=" + bd.get_p_deco()]

        self.button_backup.setVisible(True)

    def backup_clicked(self):
        self.info.addItem(QListWidgetItem('Starte Backup-Prozedere ... '))
        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec_()
        if len(self.backup_command) > 0:
            if bd.get_debug():
                print(f"backup_command für subprocess.run = {self.backup_command}")
            try:
                with (subprocess.Popen(self.backup_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8')
                      as result):
                    while True:
                        realtime_output = result.stdout.readline()
                        if realtime_output == '' and result.poll() is not None:
                            break
                        if realtime_output:
                            self.info.addItem(QListWidgetItem(realtime_output.strip()))
                            self.info.scrollToBottom()
                            loop = QEventLoop()
                            QTimer.singleShot(5, loop.quit)
                            loop.exec_()

                            # print(realtime_output)

            except Exception as excp:
                rberi_lib.QMessageBoxB('ok', 'Datenbanksicherung fehlgeschlagen. Siehe Details.', 'Datenbankfehler',
                                       str(excp), qss=bd.get_qss()).exec_()
                return
        else:
            rberi_lib.QMessageBoxB('ok', 'Das Backup kann nicht erzeugt werden. Grund ist unbekannt. Der Befehl ist Null. '
                                         'Fehlercode 1314, bitte ein Feedback mit Fehlercode absetzen. Danke!',
                                   'BackupFehler', qss=bd.get_qss()).exec_()

        self.info.addItem(QListWidgetItem('Erfolgreich beendet! Fenster schließt in 3 Sekunden ...'))
        self.info.scrollToBottom()
        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec_()
        self.info.addItem(QListWidgetItem('Fenster schließt in 2 Sekunden ...'))
        self.info.scrollToBottom()
        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec_()
        self.info.addItem(QListWidgetItem('Fenster schließt in 1 Sekunde ...'))
        self.info.scrollToBottom()
        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec_()
        self.accept()


class Backup_GUI(QDialog):
    def __init__(self):
        super().__init__(parent=None)

        self.backup_command = []
        self.laufwerk = ""
        self.fullback_needed = False
        self.usb_found = False

        self.setWindowTitle("Tägliches Backup")
        self.resize(1000, 700)
        self.layout = QVBoxLayout()

        self.button_backup = QPushButton('Backup!')
        self.button_backup.setVisible(False)
        self.button_backup.clicked.connect(self.backup_clicked)
        self.info = QListWidget()
        self.info.addItem(QListWidgetItem("Bitte USB - Stick einstecken ... "))
        self.info.addItem(QListWidgetItem("Suche nach NEUEM Speichermedium ... "))
        self.info.setAutoScroll(True)

        self.spacerItem = QtWidgets.QSpacerItem(10, 30, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)

        self.layout.addWidget(self.info)
        self.layout.addItem(self.spacerItem)
        self.layout.addWidget(self.button_backup)

        self.setLayout(self.layout)
        self.monitor = None

        self.check_usb_drive()

    def usb_added(self, device_id: str, device_info: dict[str, dict[str, str | tuple[str, ...]]]):
        self.laufwerk = ""
        if self.usb_found:
            return
        c = wmi.WMI()
        for disk in c.Win32_LogicalDisk(DriveType=2):
            if disk.VolumeName is not None:
                if bd.get_usb_vol_name() in disk.VolumeName.lower():
                    self.laufwerk = str(disk.Caption)
            else:
                continue

        self.build_backup_command()

    def build_backup_command(self, buttonpressed=False):
        if len(self.laufwerk) <= 0:
            self.info.addItem(QListWidgetItem('Kein Speichermedium bzw. Laufwerk gefunden:  "' + self.laufwerk + '"'))
            return

        self.info.addItem(QListWidgetItem('... Speichermedium GEFUNDEN! Laufwerk: ' + self.laufwerk))
        wochentage = {0: 'Montag', 1: 'Dienstag', 2: 'Mittwoch', 3: 'Donnerstag', 4: 'Freitag', 5: 'Samstag', 6: 'Sonntag'}
        heutiger_wochentag = wochentage[datetime.today().weekday()]
        if not os.path.exists(self.laufwerk + chr(92)):
            rberi_lib.QMessageBoxB("ok", "Laufwerk '" + self.laufwerk + chr(92) + "' nicht gefunden.", "Laufwerkfehler",
                                   qss=bd.get_qss()).exec_()
            return
        if heutiger_wochentag in os.listdir(self.laufwerk):
            backup_dir = self.laufwerk + chr(92) + heutiger_wochentag
        else:
            rberi_lib.QMessageBoxB('ok', 'Dies scheint der falsche USB Stick zu sein. Der Backup - Stick muss die Wochentage '
                                         'als Verzeichnisse im Grundverzeichnis enthalten. Also ' + self.laufwerk +
                                   ':\\Montag\\, '
                                   + self.laufwerk + ':\\Dienstag\\ etc.', 'Falsches Speichermedium', qss=bd.get_qss()).exec_()
            return

        mariabackup_path = bd.get_mariabackuppath()

        if len(os.listdir(backup_dir)) <= 0:
            self.fullback_needed = True
            self.backup_command = [mariabackup_path, "--backup", "--target-dir=" + backup_dir, "--databases=" +
                                   bd.get_database(), "--user=" + bd.get_user(), "--password=" + bd.get_p_deco()]
        else:
            self.fullback_needed = False
            inc_number = np.array([], dtype=int)
            for inc in os.listdir(backup_dir):
                if "inc" in inc:
                    inc_number = np.append(inc_number, int(inc[3:]))
            if not np.size(inc_number):
                # last_inc_path = os.path.join(backup_dir, bd.get_database())
                last_inc_path = backup_dir
                new_inc_path = os.path.join(backup_dir, "inc1")
            else:
                last_inc = inc_number.max()
                new_inc = last_inc + 1
                last_inc_path = os.path.join(backup_dir, "inc" + str(last_inc))
                new_inc_path = os.path.join(backup_dir, "inc" + str(new_inc))

            if bd.get_debug():
                print(f"last_inc_path = {last_inc_path}")
                print(f"new_inc_path = {new_inc_path}")

            self.backup_command = [mariabackup_path, "--backup", "--target-dir=" + new_inc_path, "--incremental-basedir=" +
                                   last_inc_path, "--databases=" + bd.get_database(), "--user=" + bd.get_user(),
                                   "--password=" + bd.get_p_deco()]

        if not buttonpressed:
            self.info.addItem(QListWidgetItem('Bitte BackUp über den Button/Knopf unten starten ... '))
            self.button_backup.setVisible(True)
        else:
            self.backup_clicked()

    def usb_disconnect(self, device_id: str, device_info: dict[str, dict[str, str | tuple[str, ...]]]):
        if self.monitor is not None:
            self.monitor.stop_monitoring()

    def accept(self):
        if self.monitor is not None:
            self.monitor.stop_monitoring()
        super().accept()

    def backup_clicked(self):
        self.info.addItem(QListWidgetItem('Starte Backup-Prozedere ... '))
        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec_()
        if len(self.backup_command) > 0:
            try:
                if bd.get_debug():
                    print(f"backup_command für subprocess.run = {self.backup_command}")

                with (subprocess.Popen(
                        self.backup_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        encoding='utf-8',  # errors='replace',
                ) as result):

                    while True:
                        realtime_output = result.stdout.readline()
                        if realtime_output == '' and result.poll() is not None:
                            break
                        if realtime_output:
                            self.info.addItem(QListWidgetItem(realtime_output.strip()))
                            self.info.scrollToBottom()
                            loop = QEventLoop()
                            QTimer.singleShot(5, loop.quit)
                            loop.exec_()
            except Exception as excp:
                rberi_lib.QMessageBoxB('ok', 'Datenbanksicherung fehlgeschlagen. Siehe Details.', 'Datenbankfehler',
                                       str(excp), qss=bd.get_qss(), ).exec_()
                return
        else:
            rberi_lib.QMessageBoxB('ok', 'Das Backup kann nicht erzeugt werden. Grund ist unbekannt. Der Befehl ist Null. '
                                         'Fehlercode 1314, bitte ein Feedback mit Fehlercode absetzen. Danke!',
                                   'BackupFehler', qss=bd.get_qss()).exec_()

        self.info.addItem(QListWidgetItem('Erfolgreich beendet! Fenster schließt in 3 Sekunden ...'))
        self.info.scrollToBottom()
        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec_()
        self.info.addItem(QListWidgetItem('Fenster schließt in 2 Sekunden ...'))
        self.info.scrollToBottom()
        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec_()
        self.info.addItem(QListWidgetItem('Fenster schließt in 1 Sekunde ...'))
        self.info.scrollToBottom()
        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec_()
        self.accept()

    def check_usb_drive(self) -> bool:
        c = wmi.WMI()
        for disk in c.Win32_LogicalDisk(DriveType=2):
            if disk.VolumeName is not None:
                if bd.get_usb_vol_name() in disk.VolumeName.lower():
                    self.laufwerk = disk.Caption + chr(92)
                    answ = rberi_lib.QMessageBoxB('ync', 'Speichermedium "' + disk.VolumeName + '" in "' + disk.Caption +
                                                  '" gefunden. Backup starten?', "Info", qss=bd.get_qss()).exec_()
                    if answ == QMessageBox.Yes:
                        self.show()
                        self.build_backup_command(True)
                        return True
        self.monitor = USBMonitor()
        self.monitor.start_monitoring(on_connect=self.usb_added, on_disconnect=self.usb_disconnect)


class BD:
    def __init__(self, full_filepath):
        self.DB_host = ''
        self.DB_user = ''
        self.DB_port = 0
        self.DB_database = ''
        self.ringnummern_laenge = 0
        self.key = b'1'
        self.DB_password = b'1'
        self.hilfeBilderPfad = ''
        self.BilderPfad = ''
        self.debug = False
        self.mit_anmeldung = True
        self.tbl_name_ringserie = ''
        self.age_adult_allowed = False
        self.zoom_seitenbreite = True
        self.version = ''
        self.camport = 0
        self.qss = './qss/Darkorange/darkorange.qss'
        self.kontaktdaten = f'Stefan Bongers, mail@sseyfert.de, +49 176 2465 1751\nThomas Jascke, ??@??.??, +49 ... .... ....'
        self.mariabackuppath = r"C:\Program Files\MariaDB 11.4\bin\mariabackup.exe"
        self.drucker_vendor_id = 0x067B
        self.drucker_typ_id = 0x2305
        self.usb_vol_name = 'corsair'

        self.filepath = full_filepath
        if os.path.isfile(self.filepath):
            self.__read_file()
        else:
            rberi_lib.QMessageBoxB('ok', 'Achtung! Die Einstellungen konnten nicht geladen werden! Dateiname ist ungültig oder '
                                         'die Datei wurde nicht gefunden. Siehe Details. Anwendung wird geschlossen.',
                                   'Ladefehler',
                                   [f'Dateipfad = {self.filepath}', f'Ergebnis der Prüfung auf den Dateipfad: '
                                                                    f'{os.path.isfile(self.filepath)}'], qss=bd.get_qss()).exec_()
            logging(window.get_current_user(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'basic_definitions.py konnte nicht geladen werden.', 'aus CB.__init__')
            app.exit(1)

    def __read_file(self):
        file = open(self.filepath, 'r')
        content = file.readlines()

        wrong_file = True

        for _line in content:
            if "FIN_19780617_20240525" in _line:
                wrong_file = False
            elif "self.DB_host" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.DB_host = txt
            elif "self.DB_user" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.DB_user = txt
            elif "self.DB_port" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.DB_port = int(txt)
            elif "self.DB_database" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.DB_database = txt
            elif "self.key" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.key = txt.encode()
            elif "self.DB_password" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.DB_password = txt.encode()
            elif "self.ringnummern_laenge" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.ringnummern_laenge = int(txt)
            elif "self.camport" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.camport = int(txt)
            elif "self.qss" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.qss = txt
            elif "self.debug" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                if "True" in txt:
                    self.debug = True
            elif "self.mit_anmeldung" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                if "False" in txt:
                    self.mit_anmeldung = False
            elif "self.tbl_name_ringserie" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.tbl_name_ringserie = txt
            elif "self.age_adult_allowed" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                if "True" in txt:
                    self.age_adult_allowed = True
            elif "self.zoom_seitenbreite" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                if "False" in txt:
                    self.zoom_seitenbreite = True
            elif "self.version" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.version = txt
            elif "self.kontaktdaten" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.kontaktdaten = f'{txt}'
            elif "self.BilderPfad" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.BilderPfad = txt
            elif "self.hilfeBilderPfad" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.hilfeBilderPfad = txt
            elif "self.mariabackuppath" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.mariabackuppath = txt.encode('unicode_escape')
            elif "self.drucker_vendor_id" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                try:
                    self.drucker_vendor_id = int(txt)
                except ValueError:
                    self.drucker_vendor_id = 0x067B
            elif "self.drucker_typ_id" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                try:
                    self.drucker_typ_id = int(txt)
                except ValueError:
                    self.drucker_typ_id = 0x2305
            elif "self.usb_vol_name" in _line:
                txt = _line[_line.find("=") + 1:].strip()
                self.usb_vol_name = txt
            else:
                pass
        if wrong_file:
            rberi_lib.QMessageBoxB('ok', 'Die Daten die für die Einstellungen geladen werden soll, hat nicht die '
                                         'korrekte File-Identification-Number. Blöd. Ganz blöd. Und tschüss!',
                                   'Falsche FIN', qss=bd.get_qss()).exec_()
            app.exit(1)

    def get_key(self) -> bytes:
        return self.key

    def get_p(self) -> bytes:
        return self.DB_password

    def get_p_deco(self) -> str:
        f_ = Fernet(self.get_key())
        token_ = f_.decrypt(self.get_p())
        pw_ = token_.decode()
        return pw_

    def get_ringnummern_laenge(self) -> int:
        return self.ringnummern_laenge

    def get_debug(self) -> bool:
        """

        :return:
        TRUE : wenn Debug-Status AN/ON/TRUE
        FALSE : wenn Debug-Status AUS/OFF/FALSE
        """
        return self.debug

    def get_mit_anmeldung(self) -> bool:
        return self.mit_anmeldung

    def get_host(self) -> str:
        return self.DB_host

    def get_port(self) -> int:
        return self.DB_port

    def get_database(self) -> str:
        return self.DB_database

    def get_user(self) -> str:
        return self.DB_user

    def get_hilfepfad(self) -> str:
        return self.hilfeBilderPfad

    def get_tbl_name_ringserie(self) -> str:
        return self.tbl_name_ringserie

    def get_age_adult_allowed(self) -> bool:
        return self.age_adult_allowed

    def get_zoom_seitenbreite(self) -> bool:
        return self.zoom_seitenbreite

    def get_version(self) -> str:
        return self.version

    def get_kontaktdaten(self) -> str:
        return self.kontaktdaten

    def set_qss(self, qss) -> bool:
        if os.path.exists(qss):
            try:
                widget = QWidget()
                widget.setStyleSheet(qss)
                widget.destroy()
                self.qss = qss
                return True
            except:
                return False
        else:
            return False

    def get_qss(self) -> str:
        return self.qss
        # self.qss = './qss/Darkorange/darkorange.qss'

    def get_cam_port(self) -> int:
        return self.camport

    def get_hilfeBilderPfad(self) -> str:
        return self.hilfeBilderPfad

    def get_BilderPfad(self) -> str:
        return self.BilderPfad

    def get_mariabackuppath(self) -> str:
        return self.mariabackuppath

    def get_drucker_vendor_id(self) -> int:
        return self.drucker_vendor_id

    def get_drucker_typ_id(self) -> int:
        return self.drucker_typ_id

    def get_usb_vol_name(self) -> str:
        return str(self.usb_vol_name)


class GeierStates:
    """

    """

    def __init__(self):
        self.eingabe_ok = True

    def set_input_allowed(self, state: bool = False):
        self.eingabe_ok = state

    def get_input_allowed(self) -> bool:
        return self.eingabe_ok

    def ueber_geier(self):
        if self:
            pass
        txt = f'GEIER - GUI EINES INSIDERS ENTWICKELT fuer RINGER\n\n'
        txt += f'Version {bd.get_version()}\n\n'
        txt += f'Entwickelt von S. Bongers und T. Jaschke im Jahr 2023 und 2024\n\n'
        txt1 = bd.get_kontaktdaten()
        txt += f"{txt1:>6}\n\n"
        txt += f'Anmerkung:\n'
        txt2 = ('Die Entwicklung dieses Programms hat in reiner Freizeit stattgefunden. Daher ist es nicht auszuschließen, '
                'dass es zu Fehlern oder unerwarteten Reaktionen kommt. Bitte nutzt den Kontakt- und/oder den '
                'Feedback-Menueintrag.')
        txt += f'{txt2:>6}'

        rberi_lib.QMessageBoxB('ok', txt, 'Über Geier', icontyp='Information', qss=bd.get_qss()).exec_()


class CurrentUser:
    """
    ========================================================================================================================
    class CurrentUser
        init
        set(user, level)
                    sets current user and userlevel
        get_user
                    returns user (as String)
        get_level
                    returns level als int
    ========================================================================================================================
    """

    def __init__(self):
        self.user = ""
        self.lvl = 1

    def set(self, u='reit', lvl=1):
        self.user = u
        self.lvl = lvl

    def getuser(self) -> str:
        return self.user

    def getlevel(self) -> int:
        return int(self.lvl)


class Kontakt_Menu_GUI(QDialog):
    def __init__(self, menuaufruf: str = 'kontakt'):
        super().__init__(parent=None)
        self.cancel_ = QPushButton()
        self.save_ok = QPushButton()
        self.radio5 = QRadioButton()
        self.radio4 = QRadioButton()
        self.radio2 = QRadioButton()
        self.radio3 = QRadioButton()
        self.radio1 = QRadioButton()
        self.checkbox_anregung = QCheckBox()
        self.text_input = QLineEdit()
        self.label3 = QLabel()
        self.email_input = QLineEdit()
        self.label2 = QLabel()
        self.checkbox = QCheckBox()
        self.name_input = QLineEdit()
        self.label1 = QLabel()

        self.typ = menuaufruf

        if menuaufruf == 'kontakt':
            self.setWindowTitle('Kontaktformular')
        elif menuaufruf == 'feedback':
            self.setWindowTitle('Feedbackformular')

        self.setup_ui()
        self.connections()

    def get_typ(self):
        """
        
        :return:
        1, 'kontakt'
        2, 'feedback' 
        """
        if self.typ == 'kontakt':
            return 1, self.typ
        else:
            return 2, self.typ

    def setup_ui(self):
        layout = QGridLayout()
        self.label1.setText('Name:')
        self.checkbox.setText('Antwort erbeten')
        self.label2.setText('Email:')
        self.label3.setText('Nachricht:')
        self.text_input = rberi_lib.QTextEditFeedback()
        self.text_input.set_max_text_length(2000)
        self.text_input.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        self.checkbox_anregung.setText('Feedback enthält Anregung/Erweiterungs-/Änderungswunsch')
        self.checkbox_anregung.setChecked(False)

        layout2 = QHBoxLayout()

        self.radio1.setText('super geil!')
        self.radio2.setText('super!')
        self.radio3.setText('alles ok!')
        self.radio4.setText('schlechter als vorher')
        self.radio5.setText('schrecklich!!!')

        layout2.addWidget(self.radio1)
        layout2.addWidget(self.radio2)
        layout2.addWidget(self.radio3)
        layout2.addWidget(self.radio4)
        layout2.addWidget(self.radio5)

        widget_radiobuttons = QWidget()
        widget_radiobuttons.setLayout(layout2)

        self.save_ok.setText('Absenden')
        self.cancel_.setText('Lieber doch nicht')
        layout3 = QHBoxLayout()
        layout3.addWidget(self.save_ok)
        layout3.addWidget(self.cancel_)
        widget_buttons = QWidget()
        widget_buttons.setLayout(layout3)

        layout.addWidget(self.label1, 0, 0)
        layout.addWidget(self.name_input, 1, 0)
        layout.addWidget(self.checkbox, 2, 0)

        layout.addWidget(self.label2, 3, 0)
        layout.addWidget(self.email_input, 4, 0)
        spacerItem = QtWidgets.QSpacerItem(10, 30, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        layout.addItem(spacerItem, 5, 0)
        layout.addWidget(self.label3, 6, 0)
        layout.addWidget(self.text_input, 7, 0)
        layout.addWidget(self.checkbox_anregung, 8, 0)

        layout.addWidget(widget_radiobuttons, 9, 0)
        layout.addWidget(widget_buttons, 10, 0)

        if self.get_typ()[0] == 1:
            self.checkbox.setChecked(True)
            self.email_input.setVisible(True)
            self.checkbox_anregung.setVisible(False)
            self.radio1.setVisible(False)
            self.radio2.setVisible(False)
            self.radio3.setVisible(False)
            self.radio4.setVisible(False)
            self.radio5.setVisible(False)

        else:
            self.checkbox.setChecked(False)
            self.label2.setVisible(False)
            self.email_input.setVisible(False)
            self.label3.setText('Feedback:')

        self.label3.setText(self.label3.text() + " (" + str(self.text_input.get_max_text_length()) + "/" + str(
            self.text_input.get_max_text_length()) + ")")
        self.setLayout(layout)

    def connections(self):
        self.save_ok.clicked.connect(self.save)
        self.cancel_.clicked.connect(self.reject)
        self.checkbox.toggled.connect(self.kontakt_ja_nein)
        self.text_input.textChanged.connect(self.__format_label3)

    def __format_label3(self):
        if self.get_typ()[1] == 'kontakt':
            label3_schnipsel = 'Nachricht: '
        else:
            label3_schnipsel = 'Feedback :'
        self.label3.setText(label3_schnipsel + " (" + str(self.text_input.get_diff()) + "/" + str(
            self.text_input.get_max_text_length()) + ")")

    def save(self):
        txt = ''
        if not get_connection_status(engine):
            return
        if len(self.name_input.text()) <= 0:
            txt = 'Name'
        if self.checkbox.isChecked() and (len(self.email_input.text()) <= 0 or self.email_input.text().find("@") <= 0):
            if len(txt) > 0:
                txt += ', Email'
            else:
                txt = 'Email'
        if len(self.text_input.toPlainText()) <= 0:
            if len(txt) > 0:
                if self.get_typ()[0] == 1:
                    txt += ', Kontakttext'
                else:
                    txt += ', Feedbacktext'
            else:
                if self.get_typ()[0] == 1:
                    txt += 'Kontakttext'
                else:
                    txt += 'Feedbacktext'
        if (self.radio4.isChecked() or self.radio5.isChecked()) and not self.checkbox_anregung.isChecked():
            rberi_lib.QMessageBoxB('ok', 'Wer nur schlecht bewertet und keine Anregung hinterlässt, muss erst gar nichts '
                                         'sagen.', 'Verarschung?', qss=bd.get_qss()).exec_()
            self.reject()

        if len(txt) > 0:
            if txt.find(",") > 0:
                rberi_lib.QMessageBoxB('ok', f'Folgende Einträge fehlen: {txt}', 'Fehlende Einträge', qss=bd.get_qss()).exec_()
            else:
                rberi_lib.QMessageBoxB('ok', f'Folgender Eintrag fehlt: {txt}', 'Fehlende Einträge', qss=bd.get_qss()).exec_()
            return

        zeitstempel = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        name = self.name_input.text()
        email = self.email_input.text()
        kontaktaufnahme = 'Y' if self.checkbox.isChecked() else 'N'
        feedbacktext = self.text_input.toPlainText()
        verbesserung = 'Y' if self.checkbox_anregung.isChecked() else 'N'
        if self.radio1.isChecked():
            rating = '1'
        elif self.radio2.isChecked():
            rating = '2'
        elif self.radio3.isChecked():
            rating = '3'
        elif self.radio4.isChecked():
            rating = '4'
        elif self.radio5.isChecked():
            rating = '5'
        else:
            rating = None

        cursor = engine.cursor()
        try:
            cursor.execute('INSERT INTO beringung.feedback (zeitstempel, name, kontaktaufnahme, mail, text, verbesserung, '
                           'rating) VALUES (%s, %s, %s, %s, %s, %s, %s)', (zeitstempel, name, kontaktaufnahme, email,
                                                                           feedbacktext, verbesserung, rating))
            engine.commit()
            cursor.close()
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Konnte das Feedback leider nicht speichern. ', 'Datenbankfehler', str(excp),
                                   qss=bd.get_qss()).exec_()
            return

        self.accept()
        txt2 = ''
        if self.get_typ()[0] == 1:
            txt1 = 'Deine Nachricht'
            txt2 = ('Wir melden uns bei Dir! Dies kann jedoch einige Tage/Wochen dauern, da Deine Nachricht nur lokal '
                    'gespeichert wird und nicht versendet. Bitte habe daher ein wenig Geduld.')
        else:
            txt1 = 'Dein Feedback!'
            if len(email) > 0:
                txt2 = ('Wir melden uns bei Dir! Dies kann jedoch einige Tage/Wochen dauern, da Dein Feedback nur lokal '
                        'gespeichert wird und nicht versendet. Bitte habe daher ein wenig Geduld.')
        rberi_lib.QMessageBoxB('ok', f'Danke für {txt1}! {txt2}', 'Danke!', qss=bd.get_qss()).exec_()
        self.close()

    def kontakt_ja_nein(self):
        if self.checkbox.isChecked():
            self.label2.setVisible(True)
            self.email_input.setVisible(True)
        else:
            self.label2.setVisible(False)
            self.email_input.setVisible(False)


class MplCanvas(FigureCanvas):
    """
    ========================================================================================================================
    class MplCanvas
    ========================================================================================================================
    """

    def __init__(self, width=5, height=4, dpi=100):
        fig = FigBon(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)


class Loginpage(QtWidgets.QDialog):
    """
    ====================================================================================================================
    class Loginpage
        init(dataframe aller user, aktueller User)
                    baut das Login-Fenster auf. Die möglichen User kommen aus dem DataFrame, der aktuelle User aus
                    2. Param
        on_login_clicked
                    hier wird geprüft ob das eingegebene PW mit dem PW in der Datenbank übereinstimmt. DB-Verbindung
                    muss bestehen.
    ====================================================================================================================
    """

    def __init__(self, df_user, curr_user):
        super().__init__(parent=None)
        # Übergabeparameter: Daten aus der Benutzertabelle (Benutzernamen; Passwörter und Benutzerlevel)
        self.u = curr_user
        self.count_login = 0
        self.df_user = df_user
        self.setWindowTitle('Login')
        self.resize(350, 200)
        layout = QGridLayout()
        label1 = QLabel('Benutzername:')

        # aus dem übergebenen dataframe wird die Liste der Benutzer extrahiert und hier übergeben
        benutzer = df_user.username
        self.user_obj = QComboBox()
        self.user_obj.addItems(benutzer)
        self.user_obj.setCurrentText("reit")
        layout.addWidget(label1, 0, 0)
        layout.addWidget(self.user_obj, 0, 1)
        label2 = QLabel("Password:")
        self.user_pwd = QLineEdit()
        self.user_pwd.setEchoMode(QLineEdit.Password)
        layout.addWidget(label2, 1, 0)
        layout.addWidget(self.user_pwd, 1, 1)
        self.button_login = QPushButton('Login')
        layout.addWidget(self.button_login, 2, 0, 2, 2)
        self.setLayout(layout)
        self.user_pwd.setFocus(True)

        # Signals / Reconnections
        self.button_login.clicked.connect(self.on_login_clicked)

    def on_login_clicked(self):
        user_index = self.df_user.index[(self.df_user["username"] == self.user_obj.currentText())]
        password = self.df_user.password[user_index].tolist()
        f_ = Fernet(bd.get_key())
        token_ = f_.decrypt(password[0])
        pw_ = token_.decode()
        u_level = self.df_user.level[user_index].tolist()[0]
        add_text = ""

        if str(self.user_pwd.text()) == str(pw_):
            # passwort korrekt
            if self.count_login == 1:
                add_text = str(self.count_login) + " erfolgloser Anmeldeversuch!"
            elif self.count_login > 1:
                add_text = str(self.count_login) + " erfolglose Anmeldeversuche!"

            logging(self.user_obj.currentText(), datetime.now(), "login", add_text)
            self.u.set(self.user_obj.currentText(), u_level)
            self.accept()
        else:
            self.count_login += 1
            tit = "Fehlerhafter Login ... "
            msg = "Passwort/Benutzername-Kombination inkorrekt. Bitte nochmals versuchen ... "
            rberi_lib.QMessageBoxB('ok', msg, tit, icontyp='Warning', qss=bd.get_qss()).exec_()

    def auto_login(self, username: str = 'admin'):
        self.user_obj.setCurrentText(username)
        add_text = " --- Autologin über basic_definitions > mit_anmeldung = False"
        logging(username, datetime.now(), "login", add_text)
        user_index = self.df_user.index[(self.df_user["username"] == self.user_obj.currentText())]
        u_level = self.df_user.level[user_index].tolist()[0]
        self.u.set(self.user_obj.currentText(), u_level)
        self.accept()


class _UiSearch(QWidget):
    """
    =====================================================================================================================
    class ArtverwaltungWindow
        init
                Fenster wird aufgebaut, wenn DB-Verbindung besteht.

        new_art_selected
                connected to ComboBox "Arten". if index changed, this function is called, and calls ==> fill_values

        on_new_click
                connected to Button "Neu ...". New specie can be saved (Form cleared)

        leave_necc_edit
                called, if a obligatory field is empty and left

        on_save_click
                connected to Button "Speichern"

        on_cancel_click
                conneted to Button "Abbrechen"

        on_close_click
                connected to Button "Schließen"

        clear_artenverwaltung(setting=Literal['lock', 'use'])
            lock: Save-Button disenabled
            use: Save-Button enabled
                clear all form fields

        on_bearb_click
                enables the form to fill

        fill_values
                fills all values of a selected specie (from ComboBox Art)

        query_verwerfen(self, source: Literal['not exit', 'exit'] = 'not exit'):
            exit: if source of query is close-button: close window if accepted
                if editing mode and close/cancel is clicked, this function opens a "are you sure?" dialog.

        toggle_bearbeitungsstatus
                toggles the status of editing (0 == no editing, 1 == editing)

        get_bearbeitungsstatus
                returns status of editing

        set_state_tuple(self, state: Literal['start', 'ende', 'gleich']='gleich')
            state = start: saves the form-values into internal started-array
            state = ende: saves the form-values into internal finished-array
            state = gleich: compares both interal arrays. same ==> return true; different ==> return false
                if editing starts, this function can be called to save all form-values (internally). analog the same
                values can be saved (internally) if editing is finished. calling the function with 'gleich' makes
                the "are-you-sure?"-Dialog obsolet (no changes, function returns TRUE) or not
                (changes! func returns FALSE)

    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df_current = None
        self.vlayout = None
        self.toolbar = None
        self.sc = None
        self.plotWidget = None
        self.search_ui = Ui_Dialog()
        self.search_ui.setupUi(self)
        self.search_ui.CMB_art.installEventFilter(self)
        self.df_arten = pd.DataFrame()
        self.df_ringer = pd.DataFrame()

        self.__fill()
        self.__connect()

    """def keyPressEvent(self, e: QKeyEvent):
        print(f"e = {e.key()}")
        if self.search_ui.CMB_art.hasFocus() and (e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter):
            AllItems = [self.search_ui.CMB_art.itemText(i) for i in range(self.search_ui.CMB_art.count())]
            if self.search_ui.CMB_art.currentText() in AllItems:
                self.art_plus()"""

    def eventFilter(self, a0, a1: QEvent):
        if a1 == QtGui.QKeyEvent:
            if bd.get_debug():
                print(f"a0={a0}, a1={a1}")
            if a1.key() == Qt.Key_Return:
                AllItems = [self.search_ui.CMB_art.itemText(i) for i in range(self.search_ui.CMB_art.count())]
                if self.search_ui.CMB_art.currentText() in AllItems:
                    self.art_plus()
        return super(_UiSearch, self).eventFilter(a0, a1)

    def __connect(self):
        self.search_ui.BTN_art_plus.clicked.connect(self.art_plus)
        self.search_ui.BTN_ringer_plus.clicked.connect(self.ringer_plus)
        self.search_ui.RAD_alle.toggled.connect(self.art_alle_toggled)
        self.search_ui.RAD_alle_mri.toggled.connect(self.art_alle_mri_toggled)
        self.search_ui.BTN_tree_clear.clicked.connect(self.tree_clear)
        self.search_ui.BTN_ringerliste_loeschen.clicked.connect(self.tree_clear_ringer)
        self.search_ui.RAD_heute.toggled.connect(self.heute)
        self.search_ui.RAD_gestern.toggled.connect(self.gestern)
        self.search_ui.RAD_woche_sa.toggled.connect(self.woche_sa)
        self.search_ui.RAD_woche_sa_heute.toggled.connect(self.woche_sa_heute)
        self.search_ui.RAD_monat.toggled.connect(self.monat)
        self.search_ui.RAD_saison.toggled.connect(self.saison)
        self.search_ui.RAD_saison_last.toggled.connect(self.saison_last)
        self.search_ui.BTN_show.clicked.connect(self.__show)
        self.search_ui.RAD_spaltendiff_jahr.toggled.connect(self.spaltendiff_jahr)
        self.search_ui.RAD_spaltendiff_monat.toggled.connect(self.spaltendiff_monat)
        self.search_ui.RAD_spaltendiff_woche.toggled.connect(self.spaltendiff_woche)
        self.search_ui.RAD_spaltendiff_pentade.toggled.connect(self.spaltendiff_pentade)
        self.search_ui.RAD_spaltendiff_tag.toggled.connect(self.spaltendiff_tag)
        self.search_ui.RAD_spaltendiff_alter.toggled.connect(self.spaltendiff_alter)
        self.search_ui.RAD_spaltendiff_fangart.toggled.connect(self.spaltendiff_fangart)
        self.search_ui.RAD_spaltendiff_sex.toggled.connect(self.spaltendiff_sex)
        self.search_ui.RAD_spaltendiff_keine.toggled.connect(self.spaltendiff_keine)
        self.search_ui.BTN_export.clicked.connect(self.export)
        self.search_ui.BTN_grafik.clicked.connect(self.grafik)
        self.search_ui.TREE_arten.itemDoubleClicked.connect(self.doppelklick_tree_arten)
        self.search_ui.TREE_ringer.itemDoubleClicked.connect(self.doppelklick_tree_ringer)
        self.search_ui.BTN_saisongrenzen.clicked.connect(self.set_season_limits)
        self.search_ui.BTN_close.clicked.connect(self.close)
        self.search_ui.CHB_normiert.toggled.connect(lambda: self.toggle_normiert('inkl'))
        self.search_ui.CHB_normiert_exkl.toggled.connect(lambda: self.toggle_normiert('exkl'))
        self.search_ui.CHB_zeilendiff_summen.toggled.connect(self.zeilensummen)
        self.search_ui.CHB_summen.toggled.connect(self.summen)
        self.search_ui.RAD_spaltendiff_beringer.toggled.connect(self.spaltendiff_beringer)

        # self.search_ui.CMB_art.keyPressEvent.connect(self.enter_pressed)

    def __disconnect(self):
        self.search_ui.BTN_art_plus.clicked.disconnect(self.art_plus)
        self.search_ui.BTN_ringer_plus.clicked.disconnect(self.ringer_plus)
        self.search_ui.RAD_alle.toggled.disconnect(self.art_alle_toggled)
        self.search_ui.RAD_alle_mri.toggled.disconnect(self.art_alle_mri_toggled)
        self.search_ui.BTN_tree_clear.clicked.disconnect(self.tree_clear)
        self.search_ui.BTN_ringerliste_loeschen.clicked.disconnect(self.tree_clear_ringer)
        self.search_ui.RAD_heute.toggled.disconnect(self.heute)
        self.search_ui.RAD_gestern.toggled.disconnect(self.gestern)
        self.search_ui.RAD_woche_sa.toggled.disconnect(self.woche_sa)
        self.search_ui.RAD_woche_sa_heute.toggled.disconnect(self.woche_sa_heute)
        self.search_ui.RAD_monat.toggled.disconnect(self.monat)
        self.search_ui.RAD_saison.toggled.disconnect(self.saison)
        self.search_ui.RAD_saison_last.toggled.disconnect(self.saison_last)
        self.search_ui.BTN_show.clicked.disconnect(self.__show)
        self.search_ui.RAD_spaltendiff_jahr.toggled.disconnect(self.spaltendiff_jahr)
        self.search_ui.RAD_spaltendiff_monat.toggled.disconnect(self.spaltendiff_monat)
        self.search_ui.RAD_spaltendiff_woche.toggled.disconnect(self.spaltendiff_woche)
        self.search_ui.RAD_spaltendiff_tag.toggled.disconnect(self.spaltendiff_tag)
        self.search_ui.RAD_spaltendiff_alter.toggled.disconnect(self.spaltendiff_alter)
        self.search_ui.RAD_spaltendiff_fangart.toggled.disconnect(self.spaltendiff_fangart)
        self.search_ui.RAD_spaltendiff_sex.toggled.disconnect(self.spaltendiff_sex)
        self.search_ui.RAD_spaltendiff_keine.toggled.disconnect(self.spaltendiff_keine)
        self.search_ui.BTN_export.clicked.disconnect(self.export)
        self.search_ui.BTN_grafik.clicked.disconnect(self.grafik)
        self.search_ui.TREE_arten.itemDoubleClicked.disconnect(self.doppelklick_tree_arten)
        self.search_ui.TREE_ringer.itemDoubleClicked.disconnect(self.doppelklick_tree_ringer)
        self.search_ui.BTN_saisongrenzen.clicked.disconnect(self.set_season_limits)

    # def enter_pressed(self, e: QKeyEvent):

    def __fill(self):
        self.df_arten = pd.read_sql("SELECT deutsch, esf_kurz, mri_art FROM arten", engine)
        self.df_arten.sort_values(by='deutsch', inplace=True)
        self.search_ui.CMB_art.addItems(self.df_arten['deutsch'])
        self.search_ui.CMB_art.setCurrentIndex(-1)

        self.df_ringer = pd.read_sql("SELECT nachname, vorname, ringer_new FROM ringer", engine)
        self.df_ringer.sort_values(by='nachname', inplace=True)
        self.search_ui.CMB_ringer.addItems(self.df_ringer['nachname'] + ", " + self.df_ringer['vorname'])
        self.search_ui.CMB_ringer.setCurrentIndex(-1)

        self.search_ui.DTE_von.setDate(datetime.today())
        self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
        self.search_ui.DTE_bis.setDate(datetime.today())
        self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))

        self.search_ui.TREE_arten.resizeColumnToContents(0)

        if bd.get_debug():
            tree_item = QTreeWidgetItem()
            tree_item.setText(0, "Amsel")
            tree_item.setText(1, "TURMER")
            self.search_ui.TREE_arten.addTopLevelItem(tree_item)

    def art_plus(self):
        if self.search_ui.CMB_art.currentIndex() < 0:
            return
        art = self.search_ui.CMB_art.currentText()
        for el in iter_tree_widget(self.search_ui.TREE_arten):
            if el.text(0) == art:
                return
        df_h = self.df_arten[self.df_arten['deutsch'] == art]
        if df_h.empty:
            self.search_ui.CMB_art.clear()
            return

        tree_item = QTreeWidgetItem()
        tree_item.setText(0, self.search_ui.CMB_art.currentText())
        tree_item.setText(1, self.df_arten[self.df_arten['deutsch'] ==
                                           self.search_ui.CMB_art.currentText()]["esf_kurz"].values[0])
        self.search_ui.TREE_arten.addTopLevelItem(tree_item)
        self.search_ui.TREE_arten.resizeColumnToContents(0)

    def doppelklick_tree_arten(self, item: QTreeWidgetItem):
        sip.delete(item)
        if self:
            pass

    def doppelklick_tree_ringer(self, item: QTreeWidgetItem):
        sip.delete(item)
        if self:
            pass

    def tree_clear(self):
        self.search_ui.TREE_arten.clear()
        if self:
            pass

    def tree_clear_ringer(self):
        self.search_ui.TREE_ringer.clear()
        if self:
            pass

    def art_alle_toggled(self):
        self.tree_clear()
        for el, deutsch, esf_kurz, mri in self.df_arten.itertuples():
            tree_item = QTreeWidgetItem()
            tree_item.setText(0, deutsch)
            tree_item.setText(1, esf_kurz)
            self.search_ui.TREE_arten.addTopLevelItem(tree_item)
        self.search_ui.TREE_arten.resizeColumnToContents(0)

    def art_alle_mri_toggled(self):
        self.tree_clear()
        for el, deutsch, esf_kurz, mri in self.df_arten.itertuples():
            if mri == 1:
                tree_item = QTreeWidgetItem()
                tree_item.setText(0, deutsch)
                tree_item.setText(1, esf_kurz)
                self.search_ui.TREE_arten.addTopLevelItem(tree_item)
        self.search_ui.TREE_arten.resizeColumnToContents(0)

    def spaltendiff_jahr(self):
        pass

    def toggle_normiert(self, quelle: str):
        if quelle == 'inkl':
            if self.search_ui.CHB_normiert.isChecked():
                if self.search_ui.CHB_normiert_exkl.isChecked():
                    self.search_ui.CHB_normiert_exkl.setChecked(False)
        elif quelle == 'exkl':
            if self.search_ui.CHB_normiert_exkl.isChecked():
                if self.search_ui.CHB_normiert.isChecked():
                    self.search_ui.CHB_normiert.setChecked(False)

    def spaltendiff_monat(self):
        pass

    def spaltendiff_woche(self):
        if self.search_ui.CHB_median.isChecked():
            self.search_ui.CHB_median.setChecked(False)

    def spaltendiff_pentade(self):
        if self.search_ui.CHB_median.isChecked():
            self.search_ui.CHB_median.setChecked(False)

    def spaltendiff_tag(self):
        if self.search_ui.CHB_median.isChecked():
            self.search_ui.CHB_median.setChecked(False)

    def spaltendiff_alter(self):
        if self.search_ui.CHB_median.isChecked():
            self.search_ui.CHB_median.setChecked(False)

    def spaltendiff_fangart(self):
        if self.search_ui.CHB_median.isChecked():
            self.search_ui.CHB_median.setChecked(False)
        if self.search_ui.CHB_alle_faenge.isChecked():
            self.search_ui.CHB_alle_faenge.setChecked(False)

    def spaltendiff_sex(self):
        if self.search_ui.CHB_median.isChecked():
            self.search_ui.CHB_median.setChecked(False)

    def spaltendiff_keine(self):
        pass

    def spaltendiff_beringer(self):
        if self.search_ui.CHB_median.isChecked():
            self.search_ui.CHB_median.setChecked(False)

    def get_diff(self, typ: Literal['y', 'm', 'w', 'p', 'd', 'h', 'min', 's'] = 's') -> int:
        """
        Funktion gibt die Differenz von Enddatum und Startdatum an (aus den Widgets DTE_von und DTE_bis).
        Die gewünschte Einheit kann über den typ angegeben werden.
        :param typ:
        'y': Anzahl der Jahre
        'm': Anzahl der Monate
        'w': Anzahl der Wochen
        'p': Anzahl der Pentaden
        'd': Anzahl der Tage
        'h': Anzahl der Stunden
        'min': Anzahl der Minuten
        's': Anzahl der Sekunden
        :return:
        int: Anzahl der Einheiten (definiert im Parameter 'typ') zwischen DTE_von und DTE_bis
        """

        def yrs():
            return divmod(diff_s, yr_ct)[0]

        def months():
            if jahr_bis - jahr_von == 0:
                return monat_bis - monat_von + 1
            elif jahr_bis - jahr_von == 1:
                return 13 - monat_von + monat_bis
            elif jahr_bis - jahr_von > 1:
                return (13 - monat_von + monat_bis) + (jahr_bis - jahr_von - 1) * 12
            else:
                rberi_lib.QMessageBoxB('ok', "Enddatum muss nach Startdatum liegen.", qss=bd.get_qss()).exec_()

        def weeks():
            return divmod(diff_s, week_ct)[0]

        def pentades():
            if jahr_bis - jahr_von == 0:
                return Pentad.fromdate(bis.date().toPyDate()).pentad - Pentad.fromdate(von.date().toPyDate()).pentad + 1
            elif jahr_bis - jahr_von == 1:
                return 74 - Pentad.fromdate(von.date().toPyDate()).pentad + Pentad.fromdate(bis.date().toPyDate()).pentad
            elif jahr_bis - jahr_von > 1:
                return ((74 - Pentad.fromdate(von.date().toPyDate()).pentad + Pentad.fromdate(bis.date().toPyDate()).pentad) +
                        (jahr_bis - jahr_von - 1) * 73)
            else:
                rberi_lib.QMessageBoxB('ok', "Enddatum muss nach Startdatum liegen.", qss=bd.get_qss()).exec_()

        def days():
            return divmod(diff_s, day_ct)[0]

        def hrs():
            return divmod(diff_s, hour_ct)[0]

        def mins():
            return divmod(diff_s, minute_ct)[0]

        def secs():
            return diff_s

        yr_ct = 365 * 24 * 60 * 60  # 31.536.000
        week_ct = 60 * 60 * 24 * 7  # 604.800
        day_ct = 24 * 60 * 60  # 86.400
        hour_ct = 60 * 60  # 3.600
        minute_ct = 60
        von = self.search_ui.DTE_von.dateTime()
        bis = self.search_ui.DTE_bis.dateTime()
        diff_s = von.secsTo(bis)
        monat_bis = bis.date().month()
        jahr_bis = bis.date().year()
        monat_von = von.date().month()
        jahr_von = von.date().year()

        if typ == "y":
            return int(yrs())
        elif typ == "m":
            return int(months())
        elif typ == "w":
            return int(weeks())
        elif typ == "p":
            return int(pentades())
        elif typ == "d":
            return int(days())
        elif typ == "h":
            return int(hrs())
        elif typ == "min":
            return int(mins())
        else:
            return int(secs())

    def heute(self):
        self.search_ui.DTE_von.setDate(datetime.today())
        self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
        self.search_ui.DTE_bis.setDate(datetime.today())
        self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))

    def gestern(self):
        self.search_ui.DTE_von.setDate(datetime.today() - timedelta(1))
        self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
        self.search_ui.DTE_bis.setDate(datetime.today() - timedelta(1))
        self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))

    def woche_sa(self):  # weekday 0..6 - Montag..Sonntag
        diff2sa = 5 - datetime.today().weekday()
        if diff2sa > 0:  # also Montag bis Freitag
            self.search_ui.DTE_von.setDate(datetime.today() - timedelta(7 - diff2sa + 7))
            self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
            self.search_ui.DTE_bis.setDate(datetime.today() - timedelta(7 - diff2sa))
            self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))
        elif diff2sa == 0:  # also genau Samstag
            self.search_ui.DTE_von.setDate(datetime.today() - timedelta(7))
            self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
            self.search_ui.DTE_bis.setDate(datetime.today())
            self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))
        else:  # also Sonntag
            self.search_ui.DTE_von.setDate(datetime.today() - timedelta(8))
            self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
            self.search_ui.DTE_bis.setDate(datetime.today() - timedelta(1))
            self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))

    def woche_sa_heute(self):
        diff2sa = 5 - datetime.today().weekday()
        if diff2sa > 0:  # also Montag bis Freitag
            self.search_ui.DTE_von.setDate(datetime.today() - timedelta(7 - diff2sa))
            self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
            self.search_ui.DTE_bis.setDate(datetime.today())
            self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))
        elif diff2sa == 0:  # also genau Samstag
            self.search_ui.DTE_von.setDate(datetime.today() - timedelta(7))
            self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
            self.search_ui.DTE_bis.setDate(datetime.today())
            self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))
        else:  # also Sonntag
            self.search_ui.DTE_von.setDate(datetime.today() - timedelta(1))
            self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
            self.search_ui.DTE_bis.setDate(datetime.today())
            self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))

    def monat(self):
        self.search_ui.DTE_von.setDate(datetime.today().replace(day=1))
        self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
        self.search_ui.DTE_bis.setDate(datetime.today())
        self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))

    def saison(self):
        self.search_ui.DTE_von.setDate(datetime.today().replace(day=30, month=6))
        self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
        self.search_ui.DTE_bis.setDate(datetime.today())
        self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))

    def saison_last(self):
        year = datetime.today().year
        self.search_ui.DTE_von.setDate(QDate(year - 1, 6, 30))
        self.search_ui.DTE_von.setTime(QTime(0, 0, 0, 0))
        self.search_ui.DTE_bis.setDate(QDate(year - 1, 11, 8))
        self.search_ui.DTE_bis.setTime(QTime(23, 59, 59, 999))

    def set_season_limits(self):
        self.search_ui.DTE_von.setDate(QDate(self.search_ui.DTE_von.date().year(), 6, 30))
        self.search_ui.DTE_bis.setDate(QDate(self.search_ui.DTE_von.date().year(), 11, 7))

    def ringer_plus(self):
        if self.search_ui.CMB_ringer.currentIndex() < 0:
            return
        ringer = self.search_ui.CMB_ringer.currentText()
        for el in iter_tree_widget(self.search_ui.TREE_ringer):
            if el.text(0) == ringer:
                return
        tree_item = QTreeWidgetItem()
        nachname = ringer.split(",")[0].strip()
        vorname = ringer.split(",")[1].strip()

        df_h = self.df_ringer[self.df_ringer['nachname'] == nachname]
        if df_h.empty:
            self.search_ui.CMB_ringer.clear()
            return
        tree_item.setText(0, self.search_ui.CMB_ringer.currentText())
        tree_item.setText(1, self.df_ringer[(self.df_ringer['nachname'] == nachname) &
                                            (self.df_ringer['vorname'] == vorname)]["ringer_new"].values[0])
        self.search_ui.TREE_ringer.addTopLevelItem(tree_item)
        if bd.get_debug() == 0:
            self.search_ui.TREE_ringer.hideColumn(1)

    def __get_complex_df(self, df: pd.DataFrame, frame=0.00) -> pd.DataFrame:
        """
        Gibt den dataframe zurück, je nach Auswahl von Spaltendifferenzierung und gewünschtem Datum.
        :param df:
            Der Dataframe mit allen Arten und notw. Daten
        :param frame:
            Parameter für die Genauigkeit der Fortschrittsanzeige
        :return:
            pd.DataFrame()
        """
        start = {'y': self.search_ui.DTE_von.date().year(),
                 'm': self.search_ui.DTE_von.date().month(),
                 'w': self.search_ui.DTE_von.date().weekNumber()[0],
                 'd': self.search_ui.DTE_von.date().day(),
                 'h': self.search_ui.DTE_von.time().hour(),
                 'min': self.search_ui.DTE_von.time().minute(),
                 }
        ende = {'y': self.search_ui.DTE_bis.date().year(),
                'm': self.search_ui.DTE_bis.date().month(),
                'w': self.search_ui.DTE_bis.date().weekNumber()[0],
                'd': self.search_ui.DTE_bis.date().day(),
                'h': self.search_ui.DTE_bis.time().hour(),
                'min': self.search_ui.DTE_bis.time().minute(),
                }

        # das Skelett für den Dataframe wird initiiert.
        df_complex = pd.DataFrame()

        # es wird ausgelesen, wieviele Arten im df vorhanden sind
        art_anz_tmp = df['art'].unique().tolist()
        art_anz = [x for x in art_anz_tmp if x is not None]
        art_anz.sort()

        # falls es weniger arten sind, die wirklich gefangen wurden, wird der frame (also der maximal mögliche Fortschritt pro
        # Art, neuberechnen und gesetzt. Hintergrund: wählt man alle Arten aus, sind es angenommen 100. D.h. der initiierte
        # frame ist progressanzeige_max / 100 - zB 100000/100 = 1000 'Punkte' pro Art. Wenn aber von den 100 ausgewählten nur
        # 50 gefangen wurden, muss der frame entsprechend auf 2000 'Punkte' pro Art geändert werden (da ja auch nur gefangene
        # Arten ausgewertet werden).
        if self.search_ui.PRGB_dav.maximum() / len(art_anz) > frame:
            frame = self.search_ui.PRGB_dav.maximum() / len(art_anz)

        if not art_anz:
            return df_complex
        ages_tmp = df['alter'].unique().tolist()
        ages = [x for x in ages_tmp if x is not None]
        ages.sort()

        sexes_tmp = df['geschlecht'].unique().tolist()
        sexes = [x for x in sexes_tmp if x is not None]
        sexes.sort()

        fangarten_tmp = df['fangart'].unique().tolist()
        fangarten = [x for x in fangarten_tmp if x is not None]
        fangarten.sort()

        beringer_kuerzel_tmp = df['ringer'].unique().tolist()
        beringer_kuerzel = [x for x in beringer_kuerzel_tmp if x is not None]
        beringer_kuerzel.sort()

        df_ringer_auswahl = pd.DataFrame(columns=['ringer', 'namevoll'])
        for ringer in beringer_kuerzel:
            namevoll = (self.df_ringer.query('ringer_new == "' + ringer + '"')['nachname'].iloc[0] + ", " +
                        self.df_ringer.query('ringer_new == "' + ringer + '"')['vorname'].iloc[0])
            df_ringer_auswahl = df_ringer_auswahl._append({'ringer': ringer, 'namevoll': namevoll}, ignore_index=True)

        df_ringer_auswahl.sort_values(by='namevoll', inplace=True)

        """if self.get_diff('y') + 1 > 5 and self.search_ui.CHB_normiert.isChecked():
            df_jahresanzahl = pd.read_sql('SELECT fangart FROM esf WHERE jahr >= ' + str(start['y']) + ' and jahr <= ' +
                                          str(ende['y']), engine)"""
        # für jede Art wird der Eintrag in dem RüCKGABE-df erzeugt.
        artcnt = 0
        # start_val_glob = self.search_ui.PRGB_dav.value()
        for art in art_anz:
            val_glob = math.floor(artcnt * frame)
            self.search_ui.PRGB_dav.setValue(val_glob)
            if bd.get_debug():
                print(f"artcnt/artcnt_ges = {artcnt}/{len(art_anz)} --- value = {self.search_ui.PRGB_dav.value()}/10.000 -- "
                      f"frame = {frame}")

            df_art = df.loc[df['art'] == art]
            art_dt = self.df_arten.query('esf_kurz == "' + str(art) + '"')['deutsch'].iloc[0]

            if self.search_ui.RAD_spaltendiff_jahr.isChecked():
                normiert = False
                # Anzahl der Jahre (Bsp: Start: 01.01.2022 und Ende: 31.07.2022) - return 0, wir wollen aber ein Jahr sehen
                yrs = self.get_diff('y') + 1
                if yrs >= 5 and (self.search_ui.CHB_normiert.isChecked() or self.search_ui.CHB_normiert_exkl.isChecked()):
                    normiert = True
                normierungs_counter = 1
                normierungs_wert = {}
                if yrs >= 15:
                    normierungs_grad = 5
                else:
                    normierungs_grad = 3
                # Start-Wert der Progressbar
                start_val_lok = self.search_ui.PRGB_dav.value()
                for i in range(yrs):  # Start bei 0
                    val_lok = math.floor(i * frame / yrs)  # für den Progressbar-Fortschritt
                    self.search_ui.PRGB_dav.setValue(start_val_lok + val_lok)

                    # hier werden die Daten definiert, ab und bis wann die SQL-Abfrage erfolgen soll
                    date_stamp_start = date(start['y'] + i, 1, 1)
                    date_stamp_end = date(start['y'] + i, 12, 31)
                    if self.search_ui.CHB_erstfang.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        # df_complex.loc[0, str(start['y'] + i) + "\nErstfänge"] = len(df_h)
                        if not self.search_ui.CHB_normiert_exkl.isChecked():
                            df_complex.loc[str(art_dt) + " (e+k)", str(start['y'] + i)] = len(df_h)
                        if normiert:
                            if normierungs_counter < normierungs_grad:
                                normierungs_wert[normierungs_counter] = len(df_h)
                                normierungs_counter += 1
                                df_complex.loc[str(art_dt) + " (e+k (normiert))", str(start['y'] + i)] = len(df_h)
                            elif normierungs_counter >= normierungs_grad:
                                normierungs_wert[normierungs_counter] = len(df_h)
                                val2insert = 0
                                for j in range(0, normierungs_grad):
                                    val2insert += normierungs_wert[normierungs_counter - j]
                                val2insert = val2insert / normierungs_grad
                                df_complex.loc[str(art_dt) + " (e+k (normiert))", str(start['y'] + i)] = round(val2insert, 0)
                                normierungs_counter += 1
                            # df_complex.loc[str(art_dt) + " (e+k)", str(start['y'] + i)] = len(df_h)

                    if self.search_ui.CHB_alle_faenge.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end)]

                        # df_complex.loc[1, str(start['y'] + i) + "\ntotal"] = len(df_hilfs)
                        if not self.search_ui.CHB_normiert_exkl.isChecked():
                            df_complex.loc[str(art_dt) + " (e+k+w)", str(start['y'] + i)] = len(df_h)
                        if normiert:
                            if normierungs_counter < normierungs_grad:
                                normierungs_wert[normierungs_counter] = len(df_h)
                                normierungs_counter += 1
                                df_complex.loc[str(art_dt) + " (e+k+w (normiert))", str(start['y'] + i)] = len(df_h)
                            elif normierungs_counter >= normierungs_grad:
                                normierungs_wert[normierungs_counter] = len(df_h)
                                val2insert = 0
                                for j in range(0, normierungs_grad):
                                    val2insert += normierungs_wert[normierungs_counter - j]
                                val2insert = val2insert / normierungs_grad
                                df_complex.loc[str(art_dt) + " (e+k+w (normiert))", str(start['y'] + i)] = round(val2insert, 0)
                                normierungs_counter += 1

                    if self.search_ui.CHB_median.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        df_h["datum"] = pd.to_datetime(df_h["datum"])
                        if not df_h.empty:
                            median = math.floor(df_h['datum'].astype('int64').median())
                            result = np.datetime64(median, "ns")
                            ts = pd.to_datetime(str(result))
                            d = ts.strftime('%Y-%m-%d')
                            # df_complex.loc[2, str(start['y'] + i) + "\nMedian(E)"] = d
                        else:
                            d = "---"
                            # df_complex.loc[2, str(start['y'] + i) + "\nMedian(E)"] = d
                        df_complex.loc[str(art_dt) + "(Median (e+k))", str(start['y'] + i)] = d

            elif self.search_ui.RAD_spaltendiff_periode.isChecked():
                # Anzahl der Jahre (Bsp: Start: 01.01.2022 und Ende: 31.07.2022) - return 0, wir wollen aber ein Jahr sehen
                yrs = self.get_diff('y') + 1
                # Start-Wert der Progressbar
                start_val_lok = self.search_ui.PRGB_dav.value()
                for i in range(yrs):  # Start bei 0
                    val_lok = math.floor(i * frame / yrs)  # für den Progressbar-Fortschritt
                    self.search_ui.PRGB_dav.setValue(start_val_lok + val_lok)

                    # hier werden die Daten definiert, ab und bis wann die SQL-Abfrage erfolgen soll
                    date_stamp_start = date(start['y'] + i, start['m'], start['d'])
                    date_stamp_end = date(start['y'] + i, ende['m'], ende['d'])
                    if self.search_ui.CHB_erstfang.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        # df_complex.loc[0, str(start['y'] + i) + "\nErstfänge"] = len(df_h)
                        df_complex.loc[str(art_dt) + " (e+k)", str(start['y'] + i)] = len(df_h)

                    if self.search_ui.CHB_alle_faenge.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end)]
                        df_complex.loc[str(art_dt) + " (e+k+w)", str(start['y'] + i)] = len(df_h)

            elif self.search_ui.RAD_spaltendiff_monat.isChecked():
                jahr = start['y']
                monat = start['m']
                mts = self.get_diff('m')
                if mts == 0:
                    mts = 1
                start_val_lok = self.search_ui.PRGB_dav.value()
                for i in range(mts):  # Start bei 0
                    val_lok = math.floor(i * frame / mts)
                    self.search_ui.PRGB_dav.setValue(start_val_lok + val_lok)
                    date_stamp_start = date(jahr, monat, 1)
                    date_stamp_end = date(jahr, monat, monthrange(jahr, monat)[1])
                    if self.search_ui.CHB_erstfang.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        if len(df_h) > 0:
                            df_complex.loc[str(art_dt) + " (e+k)", str(jahr) + "-" + str(monat)] = len(df_h)
                        else:
                            df_complex.loc[str(art_dt) + " (e+k)", str(jahr) + "-" + str(monat)] = 0
                    if self.search_ui.CHB_alle_faenge.isChecked():
                        df_hilfs = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end)]
                        if len(df_hilfs) > 0:
                            df_complex.loc[str(art_dt) + " (e+k+w)", str(jahr) + "-" + str(monat)] = len(df_hilfs)
                        else:
                            df_complex.loc[str(art_dt) + " (e+k+w)", str(jahr) + "-" + str(monat)] = 0
                    if self.search_ui.CHB_median.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        df_h["datum"] = pd.to_datetime(df_h["datum"])
                        if not df_h.empty:
                            median = math.floor(df_h['datum'].astype('int64').median())
                            result = np.datetime64(median, "ns")
                            ts = pd.to_datetime(str(result))
                            d = ts.strftime('%Y-%m-%d')
                            # df_complex.loc[0, str(jahr) + "-" + str(monat) + "\nMedian(E)"] = d
                        else:
                            d = "---"
                        df_complex.loc[str(art_dt) + " (Median(e+k))", str(jahr) + "-" + str(monat)] = d
                    if monat < 12:
                        monat += 1
                    else:
                        monat = 1
                        jahr += 1

            elif self.search_ui.RAD_spaltendiff_woche.isChecked():
                start_date = (date(start['y'], start['m'], start['d']) -
                              timedelta(days=date(start['y'], start['m'], start['d']).weekday()))
                wks = self.get_diff('w') + 1
                start_val_lok = self.search_ui.PRGB_dav.value()
                for i in range(wks):  # Start bei 0
                    val_lok = math.floor(i * frame / wks)  # 28*52 = 1456 → bei einer Art: 100/1456 = 0,06868132
                    self.search_ui.PRGB_dav.setValue(start_val_lok + val_lok)
                    date_stamp_start = start_date + timedelta(days=7 * i)
                    date_stamp_end = date_stamp_start + timedelta(days=7)
                    wochennummer = QDate(date_stamp_start.year, date_stamp_start.month,
                                         date_stamp_start.day).weekNumber()[0]
                    if self.search_ui.CHB_erstfang.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        if len(df_h) > 0:
                            df_complex.loc[art_dt + ") e+k", str(date_stamp_start) + "...\n" + str(date_stamp_end) +
                                           "\n(week: " + str(wochennummer) + ")"] = len(df_h)
                        else:
                            df_complex.loc[art_dt + ") e+k", str(date_stamp_start) + "...\n" + str(date_stamp_end) +
                                           "\n(week: " + str(wochennummer) + ")"] = 0
                    if self.search_ui.CHB_alle_faenge.isChecked():
                        df_hilfs = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end)]
                        if len(df_hilfs) > 0:
                            df_complex.loc[art_dt + ") e+k+w", str(date_stamp_start) + "...\n" + str(date_stamp_end) +
                                           "\n(week: " + str(wochennummer) + ")"] = len(df_hilfs)
                        else:
                            df_complex.loc[art_dt + ") e+k+w", str(date_stamp_start) + "...\n" + str(date_stamp_end) +
                                           "\n(week: " + str(wochennummer) + ")"] = 0
                    if self.search_ui.CHB_median.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        df_h["datum"] = pd.to_datetime(df_h["datum"])
                        if not df_h.empty:
                            median = math.floor(df_h['datum'].astype('int64').median())
                            result = np.datetime64(median, "ns")
                            ts = pd.to_datetime(str(result))
                            d = ts.strftime('%Y-%m-%d')
                            # df_complex.loc[0, str(date_stamp_start) + "...\n" + str(date_stamp_end) + "\n(week: " +
                            #                 str(wochennummer) + ")\nMedian(E)"] = d
                        else:
                            d = "---"
                        df_complex.loc[art_dt + " (Median(e+k))", str(date_stamp_start) + "...\n" + str(date_stamp_end) +
                                       "\n(week: " + str(wochennummer) + ")"] = d

            elif self.search_ui.RAD_spaltendiff_tag.isChecked():
                dys = self.get_diff('d') + 1
                start_val_lok = self.search_ui.PRGB_dav.value()
                for i in range(dys):  # Start bei 0
                    val_lok = math.floor(i * frame / dys)
                    self.search_ui.PRGB_dav.setValue(start_val_lok + val_lok)
                    date_stamp_start = date(start['y'], start['m'], start['d']) + timedelta(days=i)
                    if self.search_ui.CHB_erstfang.isChecked():
                        df_h = df_art.loc[(df_art["datum"] == date_stamp_start) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        if len(df_h) > 0:
                            df_complex.loc[art_dt + " (e+k)", str(date_stamp_start)] = len(df_h)
                        else:
                            df_complex.loc[art_dt + " (e+k)", str(date_stamp_start)] = 0
                    if self.search_ui.CHB_alle_faenge.isChecked():
                        df_hilfs = df_art.loc[(df_art["datum"] == date_stamp_start)]
                        if len(df_hilfs) > 0:
                            df_complex.loc[art_dt + " (e+k+w)", str(date_stamp_start)] = len(df_hilfs)
                        else:
                            df_complex.loc[art_dt + " (e+k+w)", str(date_stamp_start)] = 0
                    if self.search_ui.CHB_median.isChecked():
                        df_h = df_art.loc[(df_art["datum"] == date_stamp_start) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        df_h["datum"] = pd.to_datetime(df_h["datum"])
                        if not df_h.empty:
                            median = math.floor(df_h['datum'].astype('int64').median())
                            result = np.datetime64(median, "ns")
                            ts = pd.to_datetime(str(result))
                            d = ts.strftime('%Y-%m-%d')
                            # df_complex.loc[0, str(date_stamp_start) + "\nMedian(E)"] = d
                        else:
                            d = "---"
                        df_complex.loc[art_dt + " (Median(e+k))", str(date_stamp_start)] = d

            elif self.search_ui.RAD_spaltendiff_pentade.isChecked():
                start_date = Pentad.fromdate(self.search_ui.DTE_von.date().toPyDate()).todate()
                start_p = Pentad.fromdate(self.search_ui.DTE_von.date().toPyDate())
                end_p = Pentad.fromdate(self.search_ui.DTE_bis.date().toPyDate())
                curr_p = start_p
                curr_date = start_date

                # nur für die Fortschrittsanzeige:
                pentaden = self.get_diff('p') + 1
                start_val_lok = self.search_ui.PRGB_dav.value()
                i = 0

                while (end_p.year == start_p.year and end_p.pentad > curr_p.pentad) or (end_p.year > curr_p.year):
                    val_lok = math.floor(i * frame / pentaden)
                    self.search_ui.PRGB_dav.setValue(start_val_lok + val_lok)
                    next_p = curr_p + 1
                    next_date_start = next_p.todate()
                    if self.search_ui.CHB_erstfang.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= curr_date) & (df_art["datum"] < next_date_start) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        if len(df_h) > 0:
                            df_complex.loc[art_dt + " (e+k)", str(curr_date) + "\n(P" + str(curr_p.pentad) + ")"] = len(df_h)
                        else:
                            df_complex.loc[art_dt + " (e+k)", str(curr_date) + "\n(P" + str(curr_p.pentad) + ")"] = 0
                    if self.search_ui.CHB_alle_faenge.isChecked():
                        df_hilfs = df_art.loc[(df_art["datum"] >= curr_date) & (df_art["datum"] < next_date_start)]
                        if len(df_hilfs) > 0:
                            df_complex.loc[art_dt + " (e+k+w)", str(curr_date) + "\n(P" + str(curr_p.pentad) + ")"] = len(
                                df_hilfs)
                        else:
                            df_complex.loc[art_dt + " (e+k+w)", str(curr_date) + "\n(P" + str(curr_p.pentad) + ")"] = 0
                    if self.search_ui.CHB_median.isChecked():
                        df_h = df_art.loc[(df_art["datum"] >= curr_date) & (df_art["datum"] < next_date_start) &
                                          ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                        df_h["datum"] = pd.to_datetime(df_h["datum"])
                        if not df_h.empty:
                            median = math.floor(df_h['datum'].astype('int64').median())
                            result = np.datetime64(median, "ns")
                            ts = pd.to_datetime(str(result))
                            d = ts.strftime('%Y-%m-%d')
                            # df_complex.loc[0, str(date_stamp_start) + "...\n" + str(date_stamp_end) + "\n(week: " +
                            #                 str(wochennummer) + ")\nMedian(E)"] = d
                        else:
                            d = "---"
                        df_complex.loc[art_dt + ") Median", str(curr_date) + "\n(P" + str(curr_p.pentad) + ")"] = d
                    i += 1
                    curr_p = next_p
                    curr_date = curr_p.todate()

            elif self.search_ui.RAD_spaltendiff_alter.isChecked():
                date_stamp_start = date(start['y'], start['m'], start['d'])
                date_stamp_end = date(ende['y'], ende['m'], ende['d'])
                df_h = df_art
                txt = 'e+k+w'
                if self.search_ui.CHB_alle_faenge.isChecked():
                    if ages:
                        for age in ages:
                            df_tmp = df_h.loc[df_h['alter'] == age]
                            df_complex.loc[art_dt + " " + txt, "Alter:\n" + age] = len(df_tmp)
                if self.search_ui.CHB_erstfang.isChecked():
                    df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                      ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                    txt = 'e+k'
                    if ages:
                        for age in ages:
                            df_tmp = df_h.loc[df_h['alter'] == age]
                            df_complex.loc[art_dt + " " + txt, "Alter:\n" + age] = len(df_tmp)

            elif self.search_ui.RAD_spaltendiff_sex.isChecked():
                date_stamp_start = date(start['y'], start['m'], start['d'])
                date_stamp_end = date(ende['y'], ende['m'], ende['d'])
                df_h = df_art
                txt = 'e+k+w'
                if self.search_ui.CHB_alle_faenge.isChecked():
                    if sexes:
                        for sex in sexes:
                            df_tmp = df_h.loc[df_h['geschlecht'] == sex]
                            df_complex.loc[art_dt + " " + txt, "Geschlecht:\n" + str(sex)] = len(df_tmp)
                if self.search_ui.CHB_erstfang.isChecked():
                    df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                      ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                    txt = 'e+k'
                    if sexes:
                        for sex in sexes:
                            df_tmp = df_h.loc[df_h['geschlecht'] == sex]
                            df_complex.loc[art_dt + " " + txt, "Geschlecht:\n" + str(sex)] = len(df_tmp)

            elif self.search_ui.RAD_spaltendiff_fangart.isChecked():
                if fangarten:
                    start_val_lok = self.search_ui.PRGB_dav.value()
                    i = 0
                    for fangart in fangarten:
                        val_lok = math.floor(i * frame / len(fangarten))
                        self.search_ui.PRGB_dav.setValue(start_val_lok + val_lok)
                        df_tmp = df_art.loc[df_art['fangart'] == fangart]
                        df_complex.loc[art_dt, "Fangart:\n" + fangart] = len(df_tmp)
                        i += 1

            elif self.search_ui.RAD_spaltendiff_beringer.isChecked():
                anz_ringer = df_ringer_auswahl.shape[0]
                start_val_lok = self.search_ui.PRGB_dav.value()
                if bd.get_debug():
                    print(f"Start_val_lok = {start_val_lok}")
                date_stamp_start = date(start['y'], start['m'], start['d'])
                date_stamp_end = date(ende['y'], ende['m'], ende['d'])
                txt = 'e+k+w'
                if beringer_kuerzel:
                    i = 0
                    for ind, ser in df_ringer_auswahl.iterrows():
                        val_lok = math.floor(i * frame / anz_ringer)
                        self.search_ui.PRGB_dav.setValue(start_val_lok + val_lok)
                        """print(f"val_lok = {val_lok}")
                        print(f"start_val_lok + val_lok = {start_val_lok + val_lok}")
                        print(f"frame = {frame}")"""

                        if self.search_ui.CHB_alle_faenge.isChecked():
                            df_tmp = df_art.loc[df_art['ringer'] == ser['ringer']]
                            df_complex.loc[art_dt + " " + txt, ser['namevoll']] = len(df_tmp)
                        elif self.search_ui.CHB_erstfang.isChecked():
                            df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                              ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                            txt = 'e+k'
                            df_tmp = df_h.loc[df_h['ringer'] == ser['ringer']]
                            df_complex.loc[art_dt + " " + txt, ser['namevoll']] = len(df_tmp)
                        i += 1

            elif self.search_ui.RAD_spaltendiff_keine.isChecked():
                # hier werden die Daten definiert, ab und bis wann die SQL-Abfrage erfolgen soll
                date_stamp_start = date(start['y'], start['m'], start['d'])
                date_stamp_end = date(ende['y'], ende['m'], ende['d'])
                if self.search_ui.CHB_erstfang.isChecked():
                    df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                      ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                    df_complex.loc[art_dt + " (e+k)", str(date_stamp_start) + " - " + str(date_stamp_end)] = len(df_h)
                if self.search_ui.CHB_alle_faenge.isChecked():
                    df_hilfs = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end)]
                    df_complex.loc[art_dt + " total", str(date_stamp_start) + " - " +
                                   str(date_stamp_end)] = len(df_hilfs)
                if self.search_ui.CHB_median.isChecked():
                    df_h = df_art.loc[(df_art["datum"] >= date_stamp_start) & (df_art["datum"] <= date_stamp_end) &
                                      ((df_art["fangart"] == 'e') | (df_art['fangart'] == 'k'))]
                    df_h["datum"] = pd.to_datetime(df_h["datum"])
                    if not df_h.empty:
                        median = math.floor(df_h['datum'].astype('int64').median())
                        result = np.datetime64(median, "ns")
                        ts = pd.to_datetime(str(result))
                        d = ts.strftime('%Y-%m-%d')
                        # df_complex.loc[0, str(date_stamp_start) + " - " + str(date_stamp_end) + "\nMedian(E)"] = d
                    else:
                        d = "---"
                    df_complex.loc[art_dt + " (Median(e+k))", str(date_stamp_start) + " - " + str(date_stamp_end)] = d
            artcnt += 1

        if self.search_ui.CHB_summen.isChecked():
            sums_row = df_complex.sum(axis=1, skipna=True, numeric_only=True)
            df_complex.insert(loc=len(df_complex.columns), column='Summe:', value=sums_row)
            for ind, ser in df_complex.items():
                df_complex.loc["Summe:", ind] = ser.sum()
        return df_complex

    def __show(self):
        self.search_ui.TBL_ergebnis.setSortingEnabled(False)
        if self.search_ui.TREE_arten.topLevelItemCount() == 0:
            rberi_lib.QMessageBoxB('ok', "Bitte gib mindestens eine Art an.",
                                   "Fehlende Information", qss=bd.get_qss()).exec_()
            return
        self.search_ui.TBL_ergebnis.clearContents()

        str_art = "art ='"
        for el in iter_tree_widget(self.search_ui.TREE_arten):
            if len(el.text(1)) > 0:
                str_art += el.text(1) + "' or art ='"
        pos_last_or = str_art.rfind("or")
        str_art = str_art[:pos_last_or]

        str_ringer = "ringer ='"
        for el in iter_tree_widget(self.search_ui.TREE_ringer):
            if len(el.text(1)) > 0:
                str_ringer += el.text(1) + "'or ringer ='"
        pos_last_or_ringer = str_ringer.rfind("or")
        str_ringer = str_ringer[:pos_last_or_ringer]

        von_date = (str(self.search_ui.DTE_von.date().year()) + "-" + str(self.search_ui.DTE_von.date().month()) + "-" +
                    str(self.search_ui.DTE_von.date().day()))
        bis_date = (str(self.search_ui.DTE_bis.date().year()) + "-" + str(self.search_ui.DTE_bis.date().month()) + "-" +
                    str(self.search_ui.DTE_bis.date().day()))
        sql_text = ("SELECT art, fangart, datum, uhrzeit, esf.alter, geschlecht, ringer from esf where "
                    "datum >= '" + von_date +
                    "' and datum <= '" + bis_date +
                    "' and (" + str_art +
                    ")")
        if len(str_ringer) > 8:
            sql_text += " and (" + str_ringer + ")"
        self.search_ui.PRGB_dav.setValue(0)
        self.search_ui.PRGB_dav.setFormat("Auslesen der Datenbank ... %p%")
        try:
            df = pd.read_sql(sql_text, engine)
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Auslesen der Datenbank fehlgeschlagen.', 'Datenbankfehler', str(excp),
                                   qss=bd.get_qss()).exec_()
            return

        self.search_ui.PRGB_dav.setValue(self.search_ui.PRGB_dav.maximum())
        if df.empty:
            rberi_lib.QMessageBoxB('ok', 'Keine Daten im abgegrenzten Zeitraum gefunden.',
                                   'Datenfehler', qss=bd.get_qss()).exec_()
            return

        self.search_ui.TBL_ergebnis.clearContents()
        # beim togglen der 'Summen anzeigen' CHB wird geschaut, ob es einen df_current gibt, der angezeigt werden kann. dieser
        # wird erzeugt/gespeichert wenn man die SUmmen einschaltet. So muss beim Ausschalten nicht die ganze DB-Abfrage erneut
        # stattfinden sondern nur der gespeicherte df wieder in die Tabelle geschrieben werden. Wenn aber neu angezeigt wird, also
        # diese Funktion aufgerufen wird, muss diese Variable wieder resetet werden.
        self.df_current = None
        # ebenso wird die Summe ausgeschaltet, sollte sie eingeschaltet sein. Dafür muss die Verbindung zur Toggle-Funktion
        # aus und danach wieder eingeschaltet werden.
        self.search_ui.CHB_zeilendiff_summen.toggled.disconnect()
        self.search_ui.CHB_zeilendiff_summen.setChecked(False)
        self.search_ui.CHB_zeilendiff_summen.toggled.connect(self.zeilensummen)

        self.search_ui.PRGB_dav.setValue(0)
        self.search_ui.PRGB_dav.setFormat("Daten sammeln & formatieren ... %p%")
        if bd.get_debug():
            print(f"PRGB_dav.maximum = {self.search_ui.PRGB_dav.maximum()}, anzahl topLevelItem ="
                  f"{self.search_ui.TREE_arten.topLevelItemCount()}")
            print(f"ergibt frame = {self.search_ui.PRGB_dav.maximum() / self.search_ui.TREE_arten.topLevelItemCount()}")
        self.df_ergebnis = self.__get_complex_df(df,
                                                 self.search_ui.PRGB_dav.maximum() /
                                                 self.search_ui.TREE_arten.topLevelItemCount())
        self.search_ui.PRGB_dav.setValue(self.search_ui.PRGB_dav.maximum())

        self.search_ui.TBL_ergebnis.setHorizontalHeaderItem(0, QTableWidgetItem("Art"))

        # hier werden die Überschriften der Reihen generiert: (Art + Typ der Daten {Estfang; alle Fänge; Median}
        row_c = 0
        self.search_ui.TBL_ergebnis.setRowCount(self.df_ergebnis.shape[0])

        for idx in self.df_ergebnis.index:
            self.search_ui.TBL_ergebnis.setItem(row_c, 0, QTableWidgetItem(idx))
            row_c += 1

        if not self.df_ergebnis.empty:
            col_count = 0
            self.search_ui.TBL_ergebnis.setColumnCount(len(self.df_ergebnis.columns) + 1)
            for (colname, colval) in self.df_ergebnis.items():
                col_count += 1
                row_count_ = row_c
                self.search_ui.TBL_ergebnis.setHorizontalHeaderItem(col_count, QTableWidgetItem(colname))
                for row_value in colval:
                    try:
                        new_value = int(row_value)
                    except ValueError:
                        new_value = row_value
                    self.search_ui.TBL_ergebnis.setItem(row_c - row_count_, col_count,
                                                        QTableWidgetItem(str(new_value)))
                    row_count_ -= 1

        self.search_ui.PRGB_dav.setValue(self.search_ui.PRGB_dav.maximum())

        if self.search_ui.CHB_all_col_del.isChecked():
            col2del = []

            for col in range(0, self.search_ui.TBL_ergebnis.columnCount()):
                all_zero = 0
                for row_value in range(0, self.search_ui.TBL_ergebnis.rowCount()):
                    if isinstance(self.search_ui.TBL_ergebnis.item(row_value, col), type(None)):
                        continue
                    item_txt = self.search_ui.TBL_ergebnis.item(row_value, col).text()
                    if item_txt != "0" and item_txt != "---":
                        all_zero += 1
                if all_zero == 0:
                    col2del.append(self.search_ui.TBL_ergebnis.horizontalHeaderItem(col).text())
            zaehler = 0
            col_c = self.search_ui.TBL_ergebnis.columnCount()
            self.search_ui.PRGB_dav.setValue(0)
            self.search_ui.PRGB_dav.setFormat("Spaltenbereinigung läuft ... %p%")
            self.search_ui.PRGB_dav.setAlignment(Qt.AlignCenter)
            while zaehler < col_c:
                percentage_per_col = self.search_ui.PRGB_dav.maximum() / col_c
                if isinstance(self.search_ui.TBL_ergebnis.horizontalHeaderItem(zaehler), type(None)):
                    zaehler += 1
                    continue
                if self.search_ui.TBL_ergebnis.horizontalHeaderItem(zaehler).text() in col2del:
                    self.search_ui.PRGB_dav.setValue(int(math.floor(zaehler * percentage_per_col)))
                    self.search_ui.TBL_ergebnis.removeColumn(zaehler)
                    zaehler -= 1
                zaehler += 1
        self.search_ui.PRGB_dav.setFormat("%p%")
        self.search_ui.PRGB_dav.setValue(self.search_ui.PRGB_dav.maximum())
        self.search_ui.PRGB_dav.setAlignment(Qt.AlignRight)
        self.search_ui.TBL_ergebnis.resizeColumnsToContents()
        self.search_ui.TBL_ergebnis.setSortingEnabled(True)

    def zeilensummen(self):
        if not self.search_ui.CHB_zeilendiff_summen.isChecked():
            if isinstance(self.df_current, type(None)) or self.df_current.empty:
                self.__show()
            else:
                self.write_df_to_qtable_result(self.df_current, self.search_ui.TBL_ergebnis)
        else:
            self.df_current = self.get_table_as_df(only_copy=True)
            self.search_ui.TBL_ergebnis.setRowCount(0)
            self.search_ui.TBL_ergebnis.setRowCount(1)
            self.search_ui.TBL_ergebnis.setItem(0, 0, QTableWidgetItem("ZZ Summe"))
            colcnt = 1
            for col, ser in self.df_current.items():
                self.search_ui.TBL_ergebnis.setItem(0, colcnt, QTableWidgetItem(str(ser.sum())))
                colcnt += 1

    def write_df_to_qtable_result(self, df: pd.DataFrame, table: QTableWidget):
        if self:
            pass

        table.setRowCount(df.shape[0])
        table.setColumnCount(df.shape[1] + 1)
        headers = ["Art"]
        for el in df.columns.to_list():
            headers.append(el)
        table.setHorizontalHeaderLabels(headers)
        row = 0
        for ind, ser in df.iterrows():
            table.setItem(row, 0, QTableWidgetItem(str(ind)))
            for col in range(1, table.columnCount()):
                table.setItem(row, col, QTableWidgetItem(str(ser[col - 1])))
            row += 1

    def get_table_as_df(self, **kwargs):
        number_of_rows = self.search_ui.TBL_ergebnis.rowCount()
        number_of_columns = self.search_ui.TBL_ergebnis.columnCount()
        items = []
        for x in range(self.search_ui.TBL_ergebnis.columnCount()):
            items.append(self.search_ui.TBL_ergebnis.horizontalHeaderItem(x).text())
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
            if self.search_ui.TBL_ergebnis.item(i, 0) is None and not copymode:
                self.search_ui.TBL_ergebnis.removeRow(i)
                continue
            for j in range(number_of_columns):
                try:
                    if self.search_ui.TBL_ergebnis.item(i, j) is not None:
                        tmp_df.iloc[i, j] = int(self.search_ui.TBL_ergebnis.item(i, j).text())
                    else:
                        tmp_df.iloc[i, j] = None
                except ValueError:
                    try:
                        if self.search_ui.TBL_ergebnis.item(i, j) is not None:
                            tmp_df.iloc[i, j] = pd.to_datetime(self.search_ui.TBL_ergebnis.item(i, j).text()).dt.date
                        else:
                            tmp_df.iloc[i, j] = None
                    except Exception as excp:
                        if self.search_ui.TBL_ergebnis.item(i, j) is not None:
                            tmp_df.iloc[i, j] = self.search_ui.TBL_ergebnis.item(i, j).text()
                        else:
                            tmp_df.iloc[i, j] = None
                        if bd.get_debug():
                            if bd.get_debug():
                                print(f"Exception: {excp}")

        tmp_df = tmp_df.set_index([tmp_df.columns[0]])

        return tmp_df

    def summen(self):
        if self.search_ui.CHB_summen.isChecked():
            df = self.get_table_as_df()
            if df.empty:
                return
            df.loc['Summe'] = df.sum(numeric_only=False, axis=0)
            df.loc[:, 'Summen'] = df.sum(numeric_only=False, axis=1)
            self.write_df_to_qtable_result(df, self.search_ui.TBL_ergebnis)
        else:
            df = self.get_table_as_df()
            if df.empty:
                return
            df.drop(df.columns[[-1, ]], axis=1, inplace=True)
            df.drop(df.tail(1).index, inplace=True)
            self.write_df_to_qtable_result(df, self.search_ui.TBL_ergebnis)

    def export(self):
        save_path = str(QFileDialog.getExistingDirectory(None, "Select Directory"))
        save_path = save_path.replace("/", "\\")
        filename = datetime.now().strftime("%Y-%m-%d_%H-%M") + "_" + current_u.getuser() + "_DataExport"
        complete_filename = '{0}\\{1}{2}'.format(save_path, filename, '.csv')
        try:
            self.get_table_as_df().to_csv(complete_filename, header=True, index=True)
        except PermissionError as excp:
            rberi_lib.QMessageBoxB('ok', "Keine Berechtigung zum Speichern in diesem Verzeichnis.",
                                   "Berechtigung", excp.strerror, qss=bd.get_qss()).exec_()
        except FileNotFoundError as excp:
            rberi_lib.QMessageBoxB('ok', "Verzeichnis nicht gefunden. Bitte erneut versuchen.",
                                   "Kein Verzeichnis", excp.strerror, qss=bd.get_qss()).exec_()

    def grafik(self):
        def get_selection() -> dict:
            ret_val = {'e': 0,
                       'alle': 0,
                       'median': 0}
            if self.search_ui.CHB_erstfang.isChecked():
                ret_val['e'] = 1
            if self.search_ui.CHB_alle_faenge.isChecked():
                ret_val['alle'] = 1
            if self.search_ui.CHB_median.isChecked():
                ret_val['median'] = 1
            return ret_val

        df = self.get_table_as_df()

        if df.empty:
            rberi_lib.QMessageBoxB('ok', 'Keine Daten zum Anzeigen.', 'Anzeigefehler', qss=bd.get_qss()).exec_()
            return

        if get_selection()['median'] == 1:
            # rberi_lib.QMessageBoxB('ok', 'Irgendwann wird auch das funktionieren. Jedoch aktuell noch nicht.',
            #                       'Anzeigefehler', qss=bd.get_qss()).exec_()
            # return
            pass
        if True:
            df_trans = df.transpose()

            pie_ok = False
            if self.search_ui.RAD_kuchen.isChecked():
                if df_trans.shape[0] == 1 or df_trans.shape[1] == 1:
                    pie_ok = True

            try:
                # ax = df_trans.plot(ax=self.sc.axes, marker='o', markersize=3, title='Diagrammtitel', linewidth=0.5)
                # ax.grid(True, which='both', axis='both', linestyle='dotted', linewidth=0.3)
                # ax.set_xticks([])
                # ax.set_xticks(df_new.index, xtick_labels, minor=True, rotation=45, ha='right', fontsize=7)

                width = 0.25
                multiplier = 0
                x = np.arange(df.shape[1])
                fig, ax = plt.subplots(layout='constrained')

                for label, values in df_trans.items():
                    offset = width * multiplier
                    if (get_selection()['median'] == 1) and (isinstance(values[0], str)):
                        values_dates = []
                        for index, val in values.items():
                            val = datetime.strptime(val, '%Y-%m-%d')
                            values_dates.append(val.strftime('%m-%d'))
                        values_dates_new = mdates.datestr2num(values_dates)
                        if self.search_ui.RAD_balken_vert.isChecked():
                            rects = ax.bar(x + offset, values_dates_new, width, label=label)
                            ax.bar_label(rects, values_dates, padding=3, rotation=90)
                        elif self.search_ui.RAD_linie.isChecked():
                            ax.plot(x, values_dates_new)
                            for d, l, r in zip(x, values, values):
                                ax.annotate(r, xy=(d, l),
                                            xytext=(-3, np.sign(l) * 3), textcoords="offset points",
                                            horizontalalignment="right",
                                            verticalalignment="bottom" if l > 0 else "top",
                                            size=15)
                        elif self.search_ui.RAD_kuchen.isChecked() and pie_ok:
                            ax.pie(values, labels=label)
                        elif self.search_ui.RAD_kuchen.isChecked() and not pie_ok:
                            rberi_lib.QMessageBoxB('ok', 'Kuchendiagramme funktionieren nur, wenn es entweder nur eine '
                                                         'Spalte oder nur eine Reihe gibt. Sonst wirds unübersichtlich.',
                                                   'Kein Kuchen :(',
                                                   [f"Reihen = {df_trans.shape[0]}",
                                                    f"Spalten = {df_trans.shape[1]}"], qss=bd.get_qss()).exec_()
                            return

                        ax.yaxis_date()
                        ax.set_ylim(min(values_dates_new) - 10, max(values_dates_new) + 10)
                        multiplier += 1
                    else:
                        if self.search_ui.RAD_balken_vert.isChecked():
                            rects = ax.bar(x + offset, values, width, label=label)
                            ax.bar_label(rects, padding=3)
                        elif self.search_ui.RAD_linie.isChecked():
                            """values_ = np.asarray(values)
                            i = np.arange(values_.size)
                            valid = np.isfinite(values_)
                            filled = np.interp(i, i[valid], values_[valid])"""
                            ax.plot(x, values)
                            for d, l, r in zip(x, values, values):
                                ax.annotate(r, xy=(d, l),
                                            xytext=(-3, np.sign(l) * 3), textcoords="offset points",
                                            horizontalalignment="right",
                                            verticalalignment="bottom" if l > 0 else "top", size=15)
                        elif self.search_ui.RAD_kuchen.isChecked() and pie_ok:
                            print(values.tolist())
                            print(values.index.tolist())
                            ax.pie(values.tolist(), labels=values.index.tolist(), autopct='%1.1f%%')
                        elif self.search_ui.RAD_kuchen.isChecked() and not pie_ok:
                            rberi_lib.QMessageBoxB('ok', 'Kuchendiagramme funktionieren nur, wenn es entweder nur eine '
                                                         'Spalte oder nur eine Reihe gibt. Sonst wirds unübersichtlich.',
                                                   'Kein Kuchen :(',
                                                   [f"Reihen = {df_trans.shape[0]}", f"Spalten = {df_trans.shape[1]}"],
                                                   qss=bd.get_qss()).exec_()

                        if self.search_ui.CHB_trendlinie.isChecked():
                            z = np.polyfit(x, values.tolist(), 2)
                            p = np.poly1d(z)
                            # add trendline to plot
                            plt.plot(x, p(x), linestyle="--")
                        multiplier += 1

                if not self.search_ui.RAD_kuchen.isChecked():
                    ax.grid(visible=True, which='major', axis='both')
                    ax.set_ylabel('Anzahl', size=15)
                    xtick_vals = tuple(df.columns.tolist())
                    ax.set_title('Anzahl zwischen ' + xtick_vals[0] + ' und ' + xtick_vals[-1], size=25)
                    ax.set_xticks(x + width, xtick_vals, rotation=45)
                    ax.tick_params(axis='both', labelsize=15)

                    anz_label = self.search_ui.TBL_ergebnis.rowCount()
                    labels = df.index.tolist()
                    new_labels = labels
                    if self.search_ui.CHB_trendlinie.isChecked():
                        new_labels = []
                        anz_label = anz_label * 2
                        for label in labels:
                            new_labels.append(label)
                            new_labels.append(label + " (Trend)")

                    fsize = 'x-large'
                    if len(new_labels) > 10:
                        fsize = 'large'
                    elif len(new_labels) > 15:
                        fsize = 'medium'
                    elif len(new_labels) > 20:
                        fsize = 'small'
                    ax.legend(loc='upper left',
                              ncols=anz_label,
                              labels=new_labels,
                              fontsize=fsize, )  # xx-small, x-small, small, medium, large, x-large, xx-large
                else:
                    new_labels = df_trans.index.tolist()
                    fsize = 'x-large'
                    if len(new_labels) > 10:
                        fsize = 'large'
                    elif len(new_labels) > 15:
                        fsize = 'medium'
                    elif len(new_labels) > 20:
                        fsize = 'small'
                    ax.legend(loc='upper left',
                              ncols=df_trans.shape[0],
                              labels=new_labels,
                              fontsize=fsize,
                              title=df.index[0] + ' im Zeitraum ' + self.search_ui.DTE_von.date().toString() + " - " +
                                    self.search_ui.DTE_bis.date().toString(),
                              )

                plt.show()

            except TypeError as t:
                rberi_lib.QMessageBoxB('ok', 'Keine Grafik anzeigbar. Vermutlich wird versucht eine Grafik '
                                             'inklusive Median (Datumswerten) auszugeben, was nicht funktioniert. '
                                             'Siehe Details.', 'Grafikfehler', str(t), qss=bd.get_qss()).exec_()
                return
            except Exception as excp:
                rberi_lib.QMessageBoxB('ok', 'Keine Grafik anzeigbar. Siehe Details.', 'Grafikfehler',
                                       str(excp)).exec()
                return


class _UiDatenblatt2(QDialog):
    def __init__(self, data: dict = None, parent=None):
        QDialog.__init__(self, parent)

        self.ui = Ui_db2()
        self.ui.setupUi(self)
        self.setWindowTitle("Datenblatt Zwei")

        if data is not None:
            self.fill_data(data)
        else:
            self.clear()

        self.ui.BTN_ok.clicked.connect(self.close_ok)
        self.ui.BTN_nok.clicked.connect(self.close_nok)
        self.ui.BTN_walinder.clicked.connect(window.walinder)
        self.ui.INP_kerbe_feder2.editingFinished.connect(lambda: kerbe(self.ui.INP_kerbe_feder2.text(), window.ui.CMB_art,
                                                                       window.ui.INP_fluegellaenge.text(),
                                                                       window.ui.CMB_alter.currentText()))

    def clear(self):
        for el in self.findChildren(type(QLineEdit)):
            el.clear()
        self.ui.CHB_mauserkarte.setChecked(False)

    def close_nok(self):
        self.clear()
        self.reject()
        self.close()

    def close_ok(self):
        if self.proof():
            self.accept()
        else:
            rberi_lib.QMessageBoxB('ok', 'Mindestens ein Wert ist keine Dezimalzahl. Bitte korrigieren.',
                                   'Fehler', qss=bd.get_qss()).exec_()

    def proof(self):
        if (not rberi_lib.check_float(self.ui.INP_feder2.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_feder3.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_kerbe_feder2.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_feder4.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_feder5.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_feder6.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_feder7.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_feder8.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_feder9.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_feder10.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_feder11.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_schnabellaenge.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_schnabelbreite.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_tarsus.text(), zero_or_empty_returns_true=True) or
                not rberi_lib.check_float(self.ui.INP_innenfuss.text(), zero_or_empty_returns_true=True)):
            return False
        return True

    def get_vals(self):
        lib = ({
            "hs2": self.ui.INP_feder2.text(),
            "hs3": self.ui.INP_feder3.text(),
            "kerbe": self.ui.INP_kerbe_feder2.text(),
            "hs4": self.ui.INP_feder4.text(),
            "hs5": self.ui.INP_feder5.text(),
            "hs6": self.ui.INP_feder6.text(),
            "hs7": self.ui.INP_feder7.text(),
            "hs8": self.ui.INP_feder8.text(),
            "hs9": self.ui.INP_feder9.text(),
            "hs10": self.ui.INP_feder10.text(),
            "as1": self.ui.INP_feder11.text(),
            "tarsus": self.ui.INP_tarsus.text(),
            "innenfuss": self.ui.INP_innenfuss.text(),
            "schnabellaenge": self.ui.INP_schnabellaenge.text(),
            "schnabelbreite": self.ui.INP_schnabelbreite.text(),
            "mauserkarte": 1 if self.ui.CHB_mauserkarte.isChecked() else 0,
        })
        if bd.get_debug():
            print(lib)
        return lib

    def fill_data(self, data: dict):
        self.ui.INP_feder2.setText(data['hs2'] if 'hs2' in data else '')
        self.ui.INP_feder3.setText(data['hs3'] if 'hs3' in data else '')
        self.ui.INP_kerbe_feder2.setText(data['kerbe'] if 'kerbe' in data else '')
        self.ui.INP_feder4.setText(data['hs4'] if 'hs4' in data else '')
        self.ui.INP_feder5.setText(data['hs5'] if 'hs5' in data else '')
        self.ui.INP_feder6.setText(data['hs6'] if 'hs6' in data else '')
        self.ui.INP_feder7.setText(data['hs7'] if 'hs7' in data else '')
        self.ui.INP_feder8.setText(data['hs8'] if 'hs8' in data else '')
        self.ui.INP_feder9.setText(data['hs9'] if 'hs9' in data else '')
        self.ui.INP_feder10.setText(data['hs10'] if 'hs10' in data else '')
        self.ui.INP_feder11.setText(data['as1'] if 'as1' in data else '')
        self.ui.INP_tarsus.setText(data['tarsus'] if 'tarsus' in data else '')
        self.ui.INP_innenfuss.setText(data['innenfuss'] if 'innenfuss' in data else '')
        self.ui.INP_schnabelbreite.setText(data['schnabelbreite'] if 'schnabelbreite' in data else '')
        self.ui.INP_schnabellaenge.setText(data['schnabellaenge'] if 'schnabellaenge' in data else '')
        self.ui.CHB_mauserkarte.setChecked(True if ('mauserkarte' in data and data['mauserkarte'] == 1) else False)


class _UiSearchItem(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.ui = Ui_search_ringnb_form()
        self.ui.setupUi(self)

        self.changedItems = []
        self.counter_ma_ok = 0
        self.matrix = {}
        self.set_matrix()
        self.relevante_spalten = [0, 1, 2, 3, 5, 8, 9, 10, 11, 20]
        self.show_all_columns = True
        self.changedStatus = False

        self.ui.BTN_search.clicked.connect(self.search_clicked)
        self.ui.BTN_save.clicked.connect(self.save_clicked)
        self.ui.CMB_art.currentTextChanged.connect(self.art_changed)

        if window.get_current_userlevel() != 3:
            self.ui.BTN_save.setEnabled(False)
            self.ui.BTN_fehlerliste.setVisible(False)
            self.ui.BTN_fehlerliste_wiederfang.setVisible(False)
            self.ui.CHB_rel_col.setVisible(False)
            # self.ui.BTN_export.setVisible(False)
            # self.ui.BTN_import.setVisible(False)
        else:
            self.ui.BTN_save.setEnabled(True)
            self.ui.BTN_fehlerliste.setVisible(True)
            self.ui.BTN_fehlerliste_wiederfang.setVisible(True)
            self.ui.CHB_rel_col.setVisible(True)
            self.ui.BTN_export.setVisible(True)
            self.ui.BTN_import.setVisible(True)

        self.ui.BTN_cancel.clicked.connect(self.cancel_clicked)
        self.ui.label_3.installEventFilter(self)
        self.ui.label_3.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.label_3.customContextMenuRequested.connect(lambda: self.rightClickFunction("start"))
        self.ui.label_5.installEventFilter(self)
        self.ui.label_5.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.label_5.customContextMenuRequested.connect(lambda: self.rightClickFunction("end"))
        self.ui.BTN_fehlerliste.clicked.connect(self.make_fehlerliste)
        self.ui.BTN_fehlerliste_wiederfang.clicked.connect(self.make_wiederfang_fehlerliste)
        self.ui.BTN_export.clicked.connect(self._export)
        self.ui.BTN_import.clicked.connect(self._import)
        self.ui.CHB_rel_col.toggled.connect(self.toggle_col_view)

        self.ui.TBL_results.setColumnHidden(37, True)
        self.fill_arten()

        # self.ui.INP_ringnb.setText("91221496")
        self.ui.DE_start.setDate(QDate(datetime.today().year, datetime.today().month, datetime.today().day))
        self.ui.DE_end.setDate(QDate(datetime.today().year, datetime.today().month, datetime.today().day))

    def rightClickFunction(self, source):
        if source == 'start':
            self.ui.DE_start.setDate(QDate.currentDate())
        elif source == 'end':
            self.ui.DE_end.setDate(QDate.currentDate())

    def art_changed(self):
        if self.ui.CMB_art.currentText() == "":
            self.ui.CMB_art.setCurrentIndex(-1)

    def fill_arten(self):
        sql_t = "SELECT deutsch, esf_kurz FROM arten"
        self.ui.CMB_art.addItem("")
        if not window.df_arten.empty:
            self.ui.CMB_art.addItems(window.df_arten['deutsch'])
        else:
            df_tmp = pd.read_sql(sql_t, engine)
            df_tmp.sort_values(by='deutsch', inplace=True)
            self.ui.CMB_art.addItems(df_tmp['deutsch'])

        self.ui.CMB_art.setCurrentIndex(-1)
        self.ui.DE_start.setDate(date(1960, 1, 1))
        self.ui.DE_end.setDate(QDate.currentDate())

    def get_changedStatus(self):
        return self.changedStatus

    def set_changedStatus(self, s: bool = True):
        self.changedStatus = s

    def reject_changes(self) -> bool:
        if self.get_changedStatus():
            if (rberi_lib.QMessageBoxB('ync', 'Es wurden Änderungen vorgenommen oder zeitintensive Auswertungen abgefragt. '
                                              'Änderungen oder Anzeige verwerfen?', 'Änderungen verwerfen?',
                                       qss=bd.get_qss()).exec_() ==
                    QMessageBox.Yes):
                return True
            else:
                return False
        else:
            return True

    def search_clicked(self):
        # wenn Änderungen gemacht wurden und noch nicht gespeichert, diese auch nicht verworfen werden sollen,
        # wird die Prozedur direkt wieder beendet.
        if not self.reject_changes():
            return

        if len(self.ui.INP_ringnb.text()) <= 0 and self.ui.CMB_art.currentIndex() < 1:
            timed = self.ui.DE_end.date().toPyDate() - self.ui.DE_start.date().toPyDate()
            if timed.days > 30:
                rberi_lib.QMessageBoxB('ok', 'Bitte entweder Ringnummer oder Art oder beides ODER Intervall kleiner '
                                             '30 Tage angeben.', 'Fehler', qss=bd.get_qss()).exec_()
                return

            # für das Füllen des TableViews muss die Verbindung unterbrochen werden, da jedes Mal cellChanged
            # aufgerufen wird - logischerweise. NAch dem Füllen wieder verbinden (siehe 1*)
        if self.ui.TBL_results.receivers(self.ui.TBL_results.cellChanged) > 0:
            self.ui.TBL_results.cellChanged.disconnect(self.tbl_cell_changed)

            # die Liste mit den geänderten Zellen nullen/reseten
        self.clear_list_changedItems()

        rnr_raw = self.ui.INP_ringnb.text()
        if len(rnr_raw) > 0:
            rnr_serie = rnr_raw[:2]
            rnr_nr_raw = rnr_raw[2:]
            rnr_nr = ''
            for z in rnr_nr_raw:
                if z != '0':
                    rnr_nr += z
            rnr_ohne_nullen = rnr_serie + rnr_nr
            anz_nullen = 6 - len(rnr_nr_raw)
            nullen = ''
            for i in range(0, anz_nullen + 1):
                nullen += '0'
            rnr_mit_nullen = rnr_serie + nullen + rnr_nr_raw
            ringnummern_txt_fuer_sql = "(ringnummer = '" + rnr_raw + "' or ringnummer = '" \
                                       + rnr_ohne_nullen + "' or ringnummer = '" + rnr_mit_nullen + "')"
        else:
            ringnummern_txt_fuer_sql = "(ringnummer != '')"

        sql_txt_art = ''
        art_esf = ''

        if self.ui.CMB_art.currentIndex() >= 1:
            sql_t = "SELECT deutsch, esf_kurz FROM arten"
            if not window.df_arten.empty:
                art_esf = window.df_arten.query("deutsch=='" +
                                                self.ui.CMB_art.currentText() + "'")["esf_kurz"].to_string()
                art_esf = art_esf.split()
                art_esf = str(art_esf[1])
            else:
                df_tmp = pd.read_sql(sql_t, engine)
                query_txt = "deutsch=='" + self.ui.CMB_art.currentText() + "'"
                art_esf_df = df_tmp.query(query_txt)["esf_kurz"]
                if art_esf_df.empty:
                    art_esf = ''
                else:
                    print(art_esf_df)
                    art_esf = str(art_esf_df.iloc[0])

            if art_esf == '':
                sql_txt_art = ''
            else:
                sql_txt_art = 'and art = "' + art_esf + '"'

        sql_txt = ("SELECT ringnummer, art, fangart, datum, uhrzeit, ringer, netz, fach, fett, muskel, esf.alter, "
                   "geschlecht, moult1, moult2, moult3, teilfeder, fluegel, gewicht, frei4, verletzung, bemerkung, "
                   "station, zentrale, f9, f7, f6, f5, f4, f3, f2, f1, s1, tarsus, frei2, frei3, frei1, "
                   "mauserkarte, esf.ESF_ID FROM esf WHERE " + ringnummern_txt_fuer_sql + " and datum >= '" +
                   self.ui.DE_start.date().toString(Qt.ISODate) + "' "
                                                                  "and datum <= '" + self.ui.DE_end.date().toString(
                    Qt.ISODate) + "' " + sql_txt_art)

        print(f"{sql_txt}")
        try:
            df_rnr = pd.read_sql(sql_txt, engine)
        except Exception as err:
            rberi_lib.QMessageBoxB('ok', 'Datenbankfehler. Siehe Details.', 'Datenbankfehler', str(err), qss=bd.get_qss()).exec_()
            return

        if df_rnr.empty:
            rberi_lib.QMessageBoxB('ok', f'Kein Eintrag mit der Nummer "{rnr_raw}" oder der Art "{art_esf}" '
                                         f'oder einer Kombination aus beiden Angaben im abgegrenzten Zeitraum. '
                                         f'Bitte erneut versuchen.', 'Ringnummernsuche', qss=bd.get_qss()).exec_()
            return

        write_df_to_qtable(df_rnr, self.ui.TBL_results)
        try:
            make_table_entries_pretty(self.ui.TBL_results, 1, 5)
        except Exception as err:
            rberi_lib.QMessageBoxB('ok', 'Art und Beringer konnten nicht decodiert werden. Siehe Details.', 'Dekodierfehler',
                                   str(err)).exec_()

        self.ui.TBL_results.resizeColumnsToContents()
        self.ui.TBL_results.resizeRowsToContents()
        for i in range(self.ui.TBL_results.rowCount()):
            self.ui.TBL_results.setRowHeight(i, 10)

        # (1*) - hier wieder verbinden.
        self.ui.TBL_results.cellChanged.connect(self.tbl_cell_changed)

    def clear_list_changedItems(self):
        self.changedItems = []

    def set_matrix(self):
        """
        Definiert eine Matrix, die die Spaltennummer mit dem entsprechenden Spaltennamen der Datenbank verbindet. Im zweiten
        Parameter wird gespeichert, ob es sich um einen 't'ext oder um eine 'z'ahl handelt.
        :return:
        """
        self.matrix = {
            0: ['ringnummer', 't'],
            1: ['art', 't'],
            2: ['fangart', 't'],
            3: ['datum', 't'],
            4: ['uhrzeit', 'z'],
            5: ['ringer', 't'],
            6: ['netz', 't'],
            7: ['fach', 't'],
            8: ['fett', 'z'],
            9: ['muskel', 'z'],
            10: ['esf.alter', 't'],
            11: ['geschlecht', 'z'],
            12: ['moult1', 'z'],
            13: ['moult2', 't'],
            14: ['moult3', 'z'],
            15: ['teilfeder', 'z'],
            16: ['fluegel', 'z'],
            17: ['gewicht', 'z'],
            18: ['frei4', 'z'],
            19: ['verletzung', 'z'],
            20: ['bemerkung', 't'],
            21: ['station', 't'],
            22: ['zentrale', 't'],
            23: ['f9', 'z'],
            24: ['f7', 'z'],
            25: ['f6', 'z'],
            26: ['f5', 'z'],
            27: ['f4', 'z'],
            28: ['f3', 'z'],
            29: ['f2', 'z'],
            30: ['f1', 'z'],
            31: ['s1', 'z'],
            32: ['tarsus', 'z'],
            33: ['frei2', 'z'],
            34: ['frei3', 'z'],
            35: ['frei1', 'z'],
            36: ['mauserkarte', 'z'],
            37: ['ESF_ID', 'z'],
        }

    def tbl_cell_changed(self, row, col):
        """
        Sobald eine Zelle geändert wurde (also der Wert sich geändert hat), wird diese Funktion aufgerufen. Die geänderte Zelle
        wird dann in einer internen Liste gespeichert mit einem quadruple folgender Form
        quadruple = (esf_id [primary Key in der DB], Spaltenname [der DB], Text oder Zahl für den sql-Befehl, Wert)
        :param row: Zeile der geänderten Zelle
        :param col: Spalte der geänderten Zelle
        :return: nichts
        """
        if self.ui.TBL_results.rowCount() > 0:
            id_esf = self.ui.TBL_results.item(row, 37).text()
        else:
            return
        col_name = self.matrix[col][0]
        col_typ = self.matrix[col][1]
        value = self.ui.TBL_results.item(row, col).text()
        quadruple = (id_esf, col_name, col_typ, value)

        list_tmp = []

        for value in self.changedItems:
            if value[0] == quadruple[0]:
                if value[1] == quadruple[1]:
                    pass
                else:
                    list_tmp.append(value)
            else:
                list_tmp.append(value)

        list_tmp.append(quadruple)
        self.changedItems = []
        for el in list_tmp:
            self.changedItems.append(el)

    def save_clicked(self):
        a = rberi_lib.QMessageBoxB('ny', 'ACHTUNG! Es sollen Daten in die Datenbank geschrieben werden. '
                                         'Es findet keine Prüfung oder Validierung der Daten statt. Bei falschem '
                                         'Datentyp (zB Text statt Zahl oder umgekehrt) wird der Vorgang abgebrochen. '
                                         'Es wird dann empfohlen die Suche zu Wiederholen um aktuelle Daten zu erhalten. ',
                                   'Speichern ...', [f"Folgende Daten werden geändert: ",
                                                     f"(Datenbank-ID, Spalte, Wert)", f"{self.changedItems}"],
                                   qss=bd.get_qss()).exec_()
        if a == QMessageBox.Yes:
            sql_text = ''
            for vals in self.changedItems:
                if vals[2] == 't':
                    sql_text = 'UPDATE esf SET ' + vals[1] + ' = "' + vals[3] + '" ' + 'WHERE ESF_ID = ' + vals[0]
                elif vals[2] == 'z':
                    val = vals[3].replace(",", ".")
                    sql_text = 'UPDATE esf SET ' + vals[1] + ' = ' + val + ' ' + 'WHERE ESF_ID = ' + vals[0]
                print(sql_text)
                try:
                    cursor = engine.cursor()
                    cursor.execute(sql_text)
                    engine.commit()
                    cursor.close()
                    engine.reset()
                except Exception as excp:
                    rberi_lib.QMessageBoxB('ok', 'Leider ist ein Fehler aufgetreten. Siehe Details.',
                                           'Fehlermeldung', f"{excp}", qss=bd.get_qss()).exec_()
        else:
            return

        if rberi_lib.QMessageBoxB('yn', 'Speicherung erfolgreich. Fenster schließen?', 'Schließen?') == QMessageBox.Yes:
            self.accept()

    def cancel_clicked(self):
        if not self.reject_changes():
            return
        self.reject()

    def setup_dialog_setting(self, was: str):
        # I don't wanna setup_dialog_setting be static
        if self:
            pass

        settings = QDialog()

        CHB_ma_ok = QCheckBox()
        CHB_ma_ok.setText("ohne 'Maße ok' in Bemerkung")
        CHB_ma_ok.setChecked(False)

        RAD_2sigma = QRadioButton()
        RAD_2sigma.setText("2x Sigma")
        RAD_2sigma.setChecked(True)
        RAD_3sigma = QRadioButton()
        RAD_3sigma.setText("3x Sigma")
        RAD_3sigma.setChecked(False)

        chb_mit_masse = QCheckBox()
        chb_mit_masse.setChecked(False)
        chb_mit_masse.setText('mit Gewicht')
        chb_mit_alter = QCheckBox()
        chb_mit_alter.setChecked(True)
        chb_mit_alter.setText("mit Alter")
        chb_mit_m = QCheckBox()
        chb_mit_m.setChecked(False)
        chb_mit_m.setText("mit Mauser")
        chb_mit_kerbe = QCheckBox()
        chb_mit_kerbe.setChecked(True)
        chb_mit_kerbe.setText("mit Kerbe")
        chb_mit_tarsus = QCheckBox()
        chb_mit_tarsus.setChecked(False)
        chb_mit_tarsus.setText("mit Tarsus")

        btn_los = QPushButton()
        btn_los.setText("Los!")
        btn_los.clicked.connect(settings.accept)
        btn_zurueck = QPushButton()
        btn_zurueck.setText("Zurück")
        btn_zurueck.clicked.connect(settings.reject)

        layout = QVBoxLayout()
        if was == 'toleranz':
            layout.addWidget(CHB_ma_ok)
            layout.addWidget(RAD_2sigma)
            layout.addWidget(RAD_3sigma)
            layout.addWidget(chb_mit_masse)
        if was != 'toleranz':
            layout.addWidget(chb_mit_alter)
            layout.addWidget(chb_mit_m)
            layout.addWidget(chb_mit_kerbe)
            layout.addWidget(chb_mit_tarsus)

        layout.addWidget(btn_los)
        layout.addWidget(btn_zurueck)

        settings.setLayout(layout)
        if not settings.exec_() == QDialog.Accepted:
            if was == 'toleranz':
                return False, (False, False, False, False)
            else:
                return False, (False, False, False, False)
        else:
            if was == 'toleranz':
                return True, (CHB_ma_ok.isChecked(), chb_mit_masse.isChecked(), RAD_2sigma.isChecked(), RAD_3sigma.isChecked())
            else:
                return (True, (chb_mit_alter.isChecked(), chb_mit_m.isChecked(), chb_mit_kerbe.isChecked(),
                               chb_mit_tarsus.isChecked()))

    def make_fehlerliste(self, *args) -> None:
        """

        :param
        :return:
        None
        """
        df_art = pd.DataFrame()
        df_esf = pd.DataFrame()
        faktor = 2
        df_fehler_teilfeder = pd.DataFrame()
        df_fehler_fluegel = pd.DataFrame()
        df_fehler_gewicht = pd.DataFrame()
        wo_measurement_ok = False
        w_mass = True

        skip_intro = False
        for arg in args:
            if isinstance(arg, pd.DataFrame):
                df_esf = arg
                wo_measurement_ok = False
                w_mass = True
                skip_intro = True

        if not skip_intro:
            los, (wo_measurement_ok, w_mass, two_sigma, three_sigma) = self.setup_dialog_setting('toleranz')
            if three_sigma:
                faktor = 3

            if not los:
                return
            self.relevante_spalten = [0, 1, 2, 3, 5, 8, 9, 10, 11, 20]

            self.set_changedStatus(True)

            try:
                df_art = pd.read_sql('SELECT deutsch, esf_kurz, f_ex, f_s, w_ex, w_s, g_ex, g_s FROM arten', engine)
                sql_txt = ("SELECT ringnummer, art, fangart, datum, uhrzeit, ringer, netz, fach, fett, muskel, esf.alter, "
                           "geschlecht, moult1, moult2, moult3, teilfeder, fluegel, gewicht, frei4, verletzung, bemerkung, "
                           "station, zentrale, f9, f7, f6, f5, f4, f3, f2, f1, s1, tarsus, frei2, frei3, frei1, "
                           "mauserkarte, esf.ESF_ID FROM esf WHERE datum >= '" +
                           self.ui.DE_start.date().toString(Qt.ISODate) + "' " +
                           "and datum <= '" + self.ui.DE_end.date().toString(Qt.ISODate) + "' ")
                df_esf = pd.read_sql(sql_txt, engine)
            except Exception as excp:
                rberi_lib.QMessageBoxB('ok', 'Keine Datenbankverbindung. ', "Datenbankverbinbung", str(excp),
                                       qss=bd.get_qss()).exec_()
                return

        if df_esf.empty:
            return
        sum_of_entries = df_esf.shape[0]
        progress_i = 0

        for index, value in df_esf.iterrows():
            self.ui.progressBar.setValue(int(progress_i / sum_of_entries * 1000))
            entry = pd.DataFrame()
            if value['art']:
                entry = df_art.query("esf_kurz=='" + value['art'] + "'")

            if entry.empty:
                continue

            teilfeder_mw = entry['f_ex'].iloc[0]
            fluegel_mw = entry['w_ex'].iloc[0]
            gewicht_mw = entry['g_ex'].iloc[0]
            try:
                teilfeder_mw = float(teilfeder_mw)
                fluegel_mw = float(fluegel_mw)
                gewicht_mw = float(gewicht_mw)
            except ValueError as excp:
                rberi_lib.QMessageBoxB('ok', 'Keine Dezimalzahl!', 'Fehler', str(excp), qss=bd.get_qss()).exec_()

            teilfeder_stdab = entry['f_s'].iloc[0]
            fluegel_stdab = entry['w_s'].iloc[0]
            gewicht_stdab = entry['g_s'].iloc[0]
            try:
                teilfeder_stdab = float(teilfeder_stdab)
                fluegel_stdab = float(fluegel_stdab)
                gewicht_stdab = float(gewicht_stdab)
            except ValueError as excp:
                rberi_lib.QMessageBoxB('ok', 'Keine Dezimalzahl!', 'Fehler', str(excp), qss=bd.get_qss()).exec_()

            if ((value['teilfeder'] > 0 and teilfeder_mw > 0 and teilfeder_stdab > 0) and
                    ((value['teilfeder'] > teilfeder_mw + (faktor * teilfeder_stdab)) or
                     (value['teilfeder'] < teilfeder_mw - (faktor * teilfeder_stdab)))):
                if wo_measurement_ok and value['bemerkung'].lower().find("maße ok") >= 0:
                    self.counter_ma_ok += 1
                else:
                    df_fehler_teilfeder = pd.concat([df_fehler_teilfeder, value.to_frame().T])
                if bd.get_debug():
                    print(f"Toleranzfehler bei Teilfeder gefunden: {value['teilfeder']} != 0 und außerhalb von  "
                          f"und {teilfeder_mw - (faktor * teilfeder_stdab)} - {teilfeder_mw + (faktor * teilfeder_stdab)}")

            if ((value['fluegel'] > 0 and fluegel_mw > 0 and fluegel_stdab > 0) and
                    ((value['fluegel'] > fluegel_mw + (faktor * fluegel_stdab)) or
                     (value['fluegel'] < fluegel_mw - (faktor * fluegel_stdab)))):
                if wo_measurement_ok and value['bemerkung'].lower().find("maße ok") >= 0:
                    self.counter_ma_ok += 1
                else:
                    df_fehler_fluegel = pd.concat([df_fehler_fluegel, value.to_frame().T])
                if bd.get_debug():
                    print(f"Toleranzfehler bei Flügel gefunden: {value['fluegel']} != 0 und außerhalb von  "
                          f"und {fluegel_mw - (faktor * fluegel_stdab)} - {fluegel_mw + (faktor * fluegel_stdab)}")

            if w_mass:
                if ((value['gewicht'] > 0 and gewicht_mw > 0 and gewicht_stdab > 0) and
                        ((value['gewicht'] > gewicht_mw + (faktor * gewicht_stdab)) or
                         (value['gewicht'] < gewicht_mw - (faktor * gewicht_stdab)))):
                    if wo_measurement_ok and value['bemerkung'].lower().find("maße ok") >= 0:
                        self.counter_ma_ok += 1
                    else:
                        df_fehler_gewicht = pd.concat([df_fehler_gewicht, value.to_frame().T])
                    if bd.get_debug():
                        print(f"Toleranzfehler bei Gewicht gefunden: {value['gewicht']} != 0 und außerhalb von  "
                              f"und {gewicht_mw - (faktor * gewicht_stdab)} - {gewicht_mw + (faktor * gewicht_stdab)}")
            progress_i += 1

        self.ui.progressBar.setValue(1000)

        if not self.show_all_columns:
            self.toggle_col_view()

        if not df_fehler_teilfeder.empty:
            write_df_to_qtable(df_fehler_teilfeder, self.ui.TBL_results, mark='teilfeder', faktor=faktor)
            self.relevante_spalten.append(15)
        if not df_fehler_fluegel.empty:
            write_df_to_qtable(df_fehler_fluegel, self.ui.TBL_results, op='add', mark='fluegel', faktor=faktor)
            self.relevante_spalten.append(16)
        if w_mass and not df_fehler_gewicht.empty:
            write_df_to_qtable(df_fehler_gewicht, self.ui.TBL_results, op='add', mark='gewicht', faktor=faktor)
            self.relevante_spalten.append(17)
        self.make_TBL_nice_for_fehlerliste()
        if bd.get_debug():
            print(df_fehler_teilfeder)
            print("--- Ende Fehlerliste --- ")

    def make_wiederfang_fehlerliste(self, *args):
        skip_intro = False
        df_esf = pd.DataFrame()
        w_age = True
        w_moult = True
        w_kerbe = True
        w_tarsus = True

        for arg in args:
            if isinstance(arg, pd.DataFrame):
                df_esf = arg
                w_age = True
                w_moult = True
                w_kerbe = True
                w_tarsus = True
                skip_intro = True

        if not skip_intro:
            los, (w_age, w_moult, w_kerbe, w_tarsus) = self.setup_dialog_setting('wiederfang')
            if not los:
                return

            try:
                sql_txt = ("SELECT ringnummer, art, fangart, datum, uhrzeit, ringer, netz, fach, fett, muskel, esf.alter, "
                           "geschlecht, moult1, moult2, moult3, teilfeder, fluegel, gewicht, frei4, verletzung, bemerkung, "
                           "station, zentrale, f9, f7, f6, f5, f4, f3, f2, f1, s1, tarsus, frei2, frei3, frei1, "
                           "mauserkarte, esf.ESF_ID FROM esf WHERE datum >= '" +
                           self.ui.DE_start.date().toString(Qt.ISODate) + "' " +
                           "and datum <= '" + self.ui.DE_end.date().toString(Qt.ISODate) + "' " +
                           "and (fangart = 'w' or fangart = 'k')")
                df_esf = pd.read_sql(sql_txt, engine)
            except Exception as excp:
                rberi_lib.QMessageBoxB('ok', 'Keine Datenbankverbindung. ', "Datenbankverbinbung", str(excp),
                                       qss=bd.get_qss()).exec_()

            if df_esf.empty:
                return

            df_tmp_for_erstfaenge = df_esf.drop_duplicates('ringnummer', keep='first')
            sum_of_entries = df_tmp_for_erstfaenge.shape[0]
            self.set_changedStatus(True)  # teilweise lange ausführzeiten, daher lieber reject quittieren lassen

            progress_i = 0
            self.ui.LBL_progress.setText("Erstfänge im Zeitraum:")
            df_list = []
            for index, values in df_tmp_for_erstfaenge.iterrows():
                self.ui.progressBar.setValue(int(progress_i / sum_of_entries * 1000))
                self.ui.progressBar.update()
                sql_txt2 = ("SELECT ringnummer, art, fangart, datum, uhrzeit, ringer, netz, fach, fett, muskel, esf.alter, "
                            "geschlecht, moult1, moult2, moult3, teilfeder, fluegel, gewicht, frei4, verletzung, bemerkung, "
                            "station, zentrale, f9, f7, f6, f5, f4, f3, f2, f1, s1, tarsus, frei2, frei3, frei1, "
                            "mauserkarte, esf.ESF_ID FROM esf WHERE ringnummer = '" + values['ringnummer'] + "' ")
                df_tmp = pd.read_sql(sql_txt2, engine)
                # df_esf = df_esf._append(df_tmp, ignore_index=True)
                df_list.append(df_tmp)
                progress_i += 1
            df_esf = df_esf[0:0]
            df_esf = pd.concat(df_list)

        df_esf.sort_values(by='ringnummer', inplace=True)
        self.ui.LBL_progress.setText("Fortschritt:")
        list_of_rnr = []
        matrix2mark = {}
        df_to_add_to_table = pd.DataFrame()
        sum_of_entries = df_esf.shape[0]
        progress_i = 0

        # first key is difference between alter_e and iter_alter
        matrix_alter_juv_bei_e = {
            0: [1, 2, 3, '1', '2', '3'],
            1: [4, 5, '4', '5'],
            2: [4, 6, '4', '6'],
            3: [4, 7, '4', '7'],
            4: [4, 8, '4', '8'],
            5: [4, 9, '4', '9'],
            6: [4, 'A', '4', 'A'],
            7: [4, 'B', '4', 'B'],
        }
        matrix_alter_ad_bei_e = {
            0: [4, '4'],
            1: [4, 6, '4', '6'],
            2: [4, 7, '4', '7'],
            3: [4, 8, '4', '8'],
            4: [4, 9, '4', '9'],
            5: [4, 'A', '4', 'A'],
            6: [4, 'B', '4', 'B'],
        }
        self.ui.LBL_progress.setText("Fehlererkennung:")
        for index, values in df_esf.iterrows():
            self.ui.progressBar.setValue(int(progress_i / sum_of_entries * 1000))
            if values['ringnummer'] not in list_of_rnr:
                list_of_rnr.append(values['ringnummer'])
                df_rnr = df_esf.query("ringnummer=='" + values['ringnummer'] + "'")
                if df_rnr.empty:
                    continue
                # DONE  0) wir brauchen ein Dataframe df_rnr mit nur EINER Ringnummer und dem Erstfang und allen Wiederfängen.
                df_rnr = df_rnr.sort_values(['datum', 'uhrzeit'])
                # DONE  1) sortieren des dataframes nach datum (und dann uhrzeit)
                art = df_rnr.drop_duplicates('art')
                # wenn jetzt mehr als ein Eintrag (shape > 1), dann gibt es unterschiedliche arten!
                if art.shape[0] > 1:
                    entry = df_rnr.query('fangart == "e"')
                    if entry.empty:
                        continue
                    art_e = entry['art'].iloc[0]
                    key = df_rnr.query('fangart == "e"')['ESF_ID'].iloc[0]
                    if key not in matrix2mark.keys():
                        matrix2mark[key] = []
                        df_to_add_to_table = pd.concat([df_to_add_to_table, df_rnr.loc[df_rnr['fangart'] == "e"]])
                    matrix2mark[key].append(1)
                    if 1 not in self.relevante_spalten:
                        self.relevante_spalten.append(1)
                    for index2, art in df_rnr.iterrows():
                        if art['fangart'] != 'e' and art['art'] != art_e:
                            key = art['ESF_ID']
                            if key not in matrix2mark.keys():
                                matrix2mark[key] = []
                                df_to_add_to_table = pd.concat([df_to_add_to_table, art.to_frame().T])
                            matrix2mark[key].append(1)
                            if 1 not in self.relevante_spalten:
                                self.relevante_spalten.append(1)

                # print(matrix2mark)
                # print(df_to_add_to_table)
                # print("Art erledigt")

                # DONE  3) erstmal alle Arten vergleichen; falls da was ungleich ist, beim Erstfang zur Marikerung merken und
                # DONE      beim Wiederfang ebenso
                #       3a) eigentlich müssen alle EInträge entsprechend markiert werden oder? Logik ist aber für die anderen
                #           noch nutzbar (und kompliziert :) Daher machen wir das zum Schluss

                if w_age:
                    erstfang = df_rnr.query('fangart == "e"')
                    # Erstfang nicht vorhanden kann vorkommen bei Fremdfang!!!
                    if erstfang.empty:
                        continue
                    alter_e = erstfang['alter'].iloc[0]

                    dateString = str(erstfang['datum'].iloc[0])
                    dateFormatter = "%Y-%m-%d"
                    jahr_e = datetime.strptime(dateString, dateFormatter).year

                    if alter_e in [1, 2, 3, '1', '2', '3']:
                        matrix2use = matrix_alter_juv_bei_e
                        max_age = 7
                    else:
                        matrix2use = matrix_alter_ad_bei_e
                        max_age = 6

                    found_error = False
                    for ind, art in df_rnr.iterrows():
                        if art['fangart'] == 'e':
                            continue
                        dateString = str(art['datum'])
                        dateFormatter = "%Y-%m-%d"
                        year_diff = datetime.strptime(dateString, dateFormatter).year - jahr_e

                        if art['alter'] not in matrix2use[year_diff] or year_diff > max_age:
                            found_error = True
                            key = art['ESF_ID']
                            if key not in matrix2mark.keys():
                                matrix2mark[key] = []
                                df_to_add_to_table = pd.concat([df_to_add_to_table, art.to_frame().T])
                            matrix2mark[key].append(10)
                            if 10 not in self.relevante_spalten:
                                self.relevante_spalten.append(10)
                            # append(10): die zehnte Spalte in der Tabelle zeigt das Alter

                    if found_error:
                        key = df_rnr.query('fangart == "e"')['ESF_ID'].iloc[0]
                        if key not in matrix2mark.keys():
                            df_to_add_to_table = pd.concat([df_to_add_to_table, df_rnr.loc[df_rnr['fangart'] == "e"]])
                            matrix2mark[key] = []
                        matrix2mark[key].append(10)
                        if 10 not in self.relevante_spalten:
                            self.relevante_spalten.append(10)
                        # append(10): die zehnte Spalte in der Tabelle zeigt das Alter

                    # print(matrix2mark)
                    # print(df_to_add_to_table)
                    # print("Alter erledigt")

                    # DONE  4) Alter: Jahr vom Erstfang anschauen und dann für alle (vorhandenen) Jahre schauen ob es passt (
                    # DONE      Achtung, unklar ignorieren) und ggf.
                    # DONE      markieren (erstfang-mark nicht vergessen)

                geschlecht = df_rnr.drop_duplicates('geschlecht')
                if geschlecht.shape[0] > 2:
                    for index2, art in df_rnr.iterrows():
                        if art['geschlecht'] in [1, '1', 2, '2']:
                            key = art['ESF_ID']
                            if key not in matrix2mark.keys():
                                df_to_add_to_table = pd.concat([df_to_add_to_table, art.to_frame().T])
                                matrix2mark[key] = []
                            matrix2mark[key].append(11)
                            if 11 not in self.relevante_spalten:
                                self.relevante_spalten.append(11)

                # print(matrix2mark)
                # print(df_to_add_to_table)
                # print("Art erledigt")

                # DONE  5) Geschlecht: bei unterscheidung (und ungleich 0): alle markieren.

                if w_moult:
                    m1_compare = df_rnr['moult1'].iloc[0]
                    m2_compare = df_rnr['moult2'].iloc[0]
                    dat_compare = df_rnr['datum'].iloc[0]
                    dateString = str(dat_compare)
                    dateFormatter = "%Y-%m-%d"
                    dat_compare = datetime.strptime(dateString, dateFormatter)

                    id_compare = df_rnr['ESF_ID'].iloc[0]
                    df_compare = df_rnr.iloc[0]

                    for ind, val in df_rnr.iterrows():
                        dateString = str(val['datum'])
                        dateFormatter = "%Y-%m-%d"
                        dat_current = datetime.strptime(dateString, dateFormatter)
                        if abs(dat_current - dat_compare).days <= 2:
                            if m1_compare != val['moult1']:
                                key = val['ESF_ID']
                                if key not in matrix2mark.keys():
                                    df_to_add_to_table = pd.concat([df_to_add_to_table, val.to_frame().T])
                                    matrix2mark[key] = []
                                matrix2mark[key].append(12)
                                if 12 not in self.relevante_spalten:
                                    self.relevante_spalten.append(12)
                                key = id_compare
                                if key not in matrix2mark.keys():
                                    df_to_add_to_table = pd.concat([df_to_add_to_table, df_compare])
                                    matrix2mark[key] = []
                                matrix2mark[key].append(12)
                            if m2_compare != val['moult2']:
                                key = val['ESF_ID']
                                if key not in matrix2mark.keys():
                                    df_to_add_to_table = pd.concat([df_to_add_to_table, val.to_frame().T])
                                    matrix2mark[key] = []
                                matrix2mark[key].append(13)
                                if 12 not in self.relevante_spalten:
                                    self.relevante_spalten.append(13)
                                key = id_compare
                                if key not in matrix2mark.keys():
                                    df_to_add_to_table = pd.concat([df_to_add_to_table, df_compare])
                                    matrix2mark[key] = []
                                matrix2mark[key].append(13)
                        m1_compare = val['moult1']
                        m2_compare = val['moult2']
                        dat_compare = val['datum']
                        dateString = str(dat_compare)
                        dateFormatter = "%Y-%m-%d"
                        dat_compare = datetime.strptime(dateString, dateFormatter)
                        id_compare = val['ESF_ID']
                        df_compare = val.to_frame().T

                        if val['alter'] in [0, 1, 2, 3, '0', '1', '2', '3']:
                            pass  # erst mit Volker/Thomas sprechen

                # DONE  6) moult1: wenn weniger als 2 Tage auseinander und ungleich => markieren
                # DONE  7) moult2: wenn weniger als 5 Tage auseinander und ungleich => markieren
                #       8) moult3: nur auf 0/3 bei jungen/alten kontrollieren

                if w_kerbe:
                    df_kerbe = pd.DataFrame()
                    kerbe_sum = 0
                    kerbe_anz = 0
                    for ind, eintrag in df_rnr.iterrows():
                        if eintrag['frei4']:
                            eintrag['frei4'] = round(float(eintrag['frei4']), 1)
                        else:
                            continue
                        if eintrag['frei4'] > 0:
                            kerbe_sum += eintrag['frei4']
                            kerbe_anz += 1
                        df_kerbe = pd.concat([df_kerbe, eintrag.to_frame().T])

                    if kerbe_anz > 0:
                        kerbe_mw = kerbe_sum / kerbe_anz
                    else:
                        continue
                    df_kerbe = df_kerbe.drop_duplicates('frei4', keep='first')
                    if df_kerbe.shape[0] > 1:
                        for ind, art in df_kerbe.iterrows():
                            if float(art['frei4']) < 0.5:
                                continue
                            if float(art['frei4']) < kerbe_mw - 0.5 or float(art['frei4']) > kerbe_mw + 0.5:
                                key = art['ESF_ID']
                                if key not in matrix2mark.keys():
                                    df_to_add_to_table = pd.concat([df_to_add_to_table, art.to_frame().T])
                                    matrix2mark[key] = []
                                matrix2mark[key].append(18)
                                if 18 not in self.relevante_spalten:
                                    self.relevante_spalten.append(18)

                if w_tarsus:
                    df_tarsus = pd.DataFrame()
                    tarsus_sum = 0
                    tarsus_anz = 0
                    for ind, eintrag in df_rnr.iterrows():
                        if eintrag['tarsus']:
                            eintrag['tarsus'] = round(float(eintrag['tarsus']), 1)
                        else:
                            continue
                        if eintrag['tarsus'] > 0:
                            tarsus_sum += eintrag['tarsus']
                            tarsus_anz += 1
                        df_tarsus = pd.concat([df_tarsus, eintrag.to_frame().T])

                    if tarsus_anz > 0:
                        tarsus_mw = tarsus_sum / tarsus_anz
                    else:
                        continue
                    df_tarsus = df_tarsus.drop_duplicates('tarsus', keep='first')
                    if df_tarsus.shape[0] > 1:
                        for ind, art in df_tarsus.iterrows():
                            if float(art['tarsus']) < 0.5:
                                continue
                            if float(art['tarsus']) < tarsus_mw - 0.5 or float(art['tarsus']) > tarsus_mw + 0.5:
                                key = art['ESF_ID']
                                if key not in matrix2mark.keys():
                                    df_to_add_to_table = pd.concat([df_to_add_to_table, art.to_frame().T])
                                    matrix2mark[key] = []
                                matrix2mark[key].append(32)
                                if 32 not in self.relevante_spalten:
                                    self.relevante_spalten.append(32)

                # DONE  9) frei4 kontrollieren (Kerbe)
                # DONE  10) tarsus kontrollieren
                # DONE  11) df_rnr übegeben mit Matrix=dict der Markierungen (Zeilen und Spalten) ==> keyword = markMatrix

            progress_i += 1
        self.ui.LBL_progress.setText("Fortschritt:")
        self.ui.progressBar.setValue(1000)

        if bd.get_debug():
            print(matrix2mark)
            print(df_to_add_to_table)

        write_df_to_qtable(df_to_add_to_table, self.ui.TBL_results, matrix2mark)
        self.ui.TBL_results.sortByColumn(2, Qt.AscendingOrder)
        self.ui.TBL_results.sortByColumn(0, Qt.AscendingOrder)
        if not self.ui.CHB_rel_col.isChecked():
            self.ui.CHB_rel_col.toggle()
        else:
            for col_i in range(self.ui.TBL_results.columnCount()):
                if col_i not in self.relevante_spalten:
                    self.ui.TBL_results.hideColumn(col_i)
        self.show_all_columns = False

    def toggle_col_view(self):
        if self.show_all_columns:
            for col_i in range(self.ui.TBL_results.columnCount()):
                if col_i not in self.relevante_spalten:
                    self.ui.TBL_results.hideColumn(col_i)
            self.show_all_columns = False
        else:
            for col_i in range(self.ui.TBL_results.columnCount()):
                self.ui.TBL_results.showColumn(col_i)
            self.show_all_columns = True

    def make_TBL_nice_for_fehlerliste(self):
        self.ui.TBL_results.sortByColumn(0, Qt.AscendingOrder)
        list_esf_id = {}
        list_of_rows_to_be_removed = []
        for row_i in range(self.ui.TBL_results.rowCount()):
            if isinstance(self.ui.TBL_results.item(row_i, 37), type(None)):
                continue
            if self.ui.TBL_results.item(row_i, 37).text() not in list_esf_id.keys():
                list_esf_id[self.ui.TBL_results.item(row_i, 37).text()] = row_i
            else:
                row_value_to_add_in = list_esf_id[self.ui.TBL_results.item(row_i, 37).text()]
                for col_i in range(self.ui.TBL_results.columnCount()):
                    if self.ui.TBL_results.item(row_i, col_i).background() == QColor("yellow"):
                        self.ui.TBL_results.item(row_value_to_add_in, col_i).setBackground(QColor("yellow"))
                        self.ui.TBL_results.item(row_value_to_add_in, col_i).setForeground(QColor("red"))
                list_of_rows_to_be_removed.append(row_i)

        list_of_rows_to_be_removed.sort(reverse=True)
        for i in list_of_rows_to_be_removed:
            self.ui.TBL_results.removeRow(i)

        if not self.ui.CHB_rel_col.isChecked():
            self.ui.CHB_rel_col.toggle()
        else:
            for col_i in range(self.ui.TBL_results.columnCount()):
                if col_i not in self.relevante_spalten:
                    self.ui.TBL_results.hideColumn(col_i)
        self.show_all_columns = False

    def _import(self):
        self.ui.TBL_results.setSortingEnabled(False)
        path, ok = QFileDialog.getOpenFileName(self, 'Open CSV', os.getenv('HOME'), 'CSV(*.csv)')
        if ok:
            if self.get_changedStatus():
                if rberi_lib.QMessageBoxB('yn', 'Es sind noch Änderungen vorhanden oder es werden Ergebnisse mit langer '
                                                'Berechnungszeit angezeigt. Wirklich verwerfen?', 'Anzeige verwerfen',
                                          qss=bd.get_qss()).exec_() \
                        == QMessageBox.Yes:
                    self.ui.TBL_results.clear()
                else:
                    return
            with open(path) as csvfile:
                reader = csv.reader(csvfile, dialect='excel', lineterminator='\n')
                header = next(reader)
                self.ui.TBL_results.setColumnCount(len(header))
                self.ui.TBL_results.setHorizontalHeaderLabels(header)
                for row, values in enumerate(reader):
                    self.ui.TBL_results.insertRow(row)
                    for column, value in enumerate(values):
                        self.ui.TBL_results.setItem(row, column, QtWidgets.QTableWidgetItem(value))

            a = rberi_lib.QMessageBoxB('ync', 'Handelt es sich um eine Wiederfangfehlerliste, bestätige bitte mit Yes. Handelt '
                                              'es sich um eine Toleranzfehlerliste, bestätige bitte mit No. Wenn Du nicht weißt,'
                                              ' um welche Liste es sich handelt, breche bitte mit Cancel ab und schau Dir die '
                                              'Liste an und wiederhole den Import.', 'Listentyp', qss=bd.get_qss()).exec_()
            if a == QMessageBox.Yes:
                self.make_wiederfang_fehlerliste(write_qtable_to_df(self.ui.TBL_results))
            elif a == QMessageBox.No:
                self.make_fehlerliste(write_qtable_to_df(self.ui.TBL_results))
            else:
                pass
        self.ui.TBL_results.setSortingEnabled(True)

    def _export(self):
        path, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save CSV', os.getenv('HOME'), 'CSV(*.csv)')
        if ok:
            columns = range(self.ui.TBL_results.columnCount())
            header = [self.ui.TBL_results.horizontalHeaderItem(column).text() for column in columns]
            with open(path, 'w') as csvfile:
                writer = csv.writer(csvfile, dialect='excel', lineterminator='\n')
                writer.writerow(header)
                for row in range(self.ui.TBL_results.rowCount()):
                    writer.writerow(self.ui.TBL_results.item(row, column).text() for column in columns)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, user_internal, parent=None):
        super().__init__(parent)

        self.viewPDF = None
        self.current_user = None
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("Geier")

        self.set_user(user_internal)

        self.cancel = 0
        self.df_ringer = pd.DataFrame({})
        self.df_arten = pd.DataFrame({})
        self.ringnumber_generated = 0
        self.ringnummern_laenge = bd.get_ringnummern_laenge()
        self.berechtigung_beringer_speichern = 'nok'  # wird später bei der Anmeldung abgefragt und im Zweifel geändert
        self.alt_pressed = False
        self.edit_status = False
        self.stunde = None
        self.save_allowed = False
        self.eingabe_str = None
        self.art = None
        self.txt = None
        self.thread = None
        self.ui_search = None
        self.img_view = None
        self.mouse_over_pic = False
        self.scene = QGraphicsScene()
        self.pic = None
        self.pos_in_pic_list = -1
        self.pic_list = []
        self._zoom = 0
        self.search_ui = None
        self.img = None
        self.walinder_result = None
        self.walinder_data = None
        self.walinder_dialog = None
        self.verhaeltnis_aufgerufen = False
        self.teilfeder = -1
        self.fluegellaenge = -1
        self.masse = -1
        self.zoom_seitenbreite = bd.get_zoom_seitenbreite()
        self.no_click = None
        self.backup_window = None
        self.beringer_in_tab = False

        self.db2 = {}
        self.oot = {}  # das ist ein Dictionary, welches die Eingaben für Flügellänge/Teilfeder/Masse speichert,
        # wenn sie außerhalb der Toleranz sind. Damit lässt sich dann prüfen, ob das Maß wirklich
        # nochmal geändert wurde. Falls nicht, soll eine Abfrage erfolgen und ein Vermerk gespeichert
        # werden.

        self.cmb_list1 = ([self.ui.CMB_netz, self.ui.CMB_fach])
        self.cmb_list2 = ([self.ui.CMB_fett, self.ui.CMB_muskel, self.ui.CMB_alter, self.ui.CMB_sex,
                           self.ui.CMB_mauser1, self.ui.CMB_mauser2, self.ui.CMB_mauser3])
        self.cmb_list3 = ([self.ui.CMB_art, self.ui.CMB_fangart, self.ui.CMB_beringer, self.ui.CMB_zentrale,
                           self.ui.CMB_station])

        self.ui.widgetEingabe.setVisible(False)
        self.ui.CMB_art.setEnabled(False)
        self.ui.CMB_fangart.setEnabled(False)
        self.ui.INP_ringnummer.setEnabled(False)
        self.ui.BTN_neuer_datensatz.setVisible(False)
        self.ui.BTN_bearb_beenden.setVisible(False)

        # lädt die Benutzereinstellungen
        self.benutzereinstellungen(True)

        self.__connect()
        self.__set_validators()
        self._qss = bd.get_qss()
        self.__set_stylesheet(self._qss)

        try:
            self.handle_user_level()
        except Exception as excp:
            raise excp

        # klappt nicht mit dem dunklen Schema (da dann weiß auf weiß bei der alternierenden Zeile)
        self.ui.TBL_wiederfaenge.setAlternatingRowColors(False)

        self.ui.TBL_wiederfaenge.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        for i in range(self.ui.TBL_wiederfaenge.columnCount() - 2):
            self.ui.TBL_wiederfaenge.horizontalHeader().setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)

        try:
            # Usb(0x067B, 0x2305, 0)
            self.printer = Usb(bd.get_drucker_vendor_id(), bd.get_drucker_typ_id(), 0)
        except Exception as err:
            self.printer = None
            rberi_lib.QMessageBoxB("ok", 'Kein Drucker gefunden. Siehe Details.', 'Druckerfehler', str(err),
                                   qss=bd.get_qss()).exec_()

    def __connect(self):
        # alle Menu-Einträge werden hier verbunden mit den internen Funktionen.
        self.ui.actionArten.triggered.connect(self.show_artverwaltung)
        self.ui.actionBeenden.triggered.connect(lambda: self.programm_beenden(txt="über Datei -> Beenden oder Strg+Q"))
        self.ui.actionNeuen_Benutzer_anlegen.triggered.connect(self.add_new_user)
        self.ui.actionPasswort_aendern.triggered.connect(change_pw)
        self.ui.actionAbmelden.triggered.connect(self.abmelden)
        self.ui.actionBeringer.triggered.connect(self.call_beringerverwaltung)
        self.ui.actionHinzufuegen.triggered.connect(self.hinzufuegen)
        self.ui.actionEinstellungen.triggered.connect(self.menu_settings_triggered)
        self.ui.actionBenutzereinstellungen.triggered.connect(self.benutzereinstellungen)
        self.ui.actionRingserien.triggered.connect(self.ringserienverwaltung)
        self.ui.actionSuchen.triggered.connect(self.search)
        self.ui.actionEintrag_suchen.triggered.connect(self.search_item_ringnb)
        self.ui.actionWalinder.triggered.connect(self.walinder)
        self.ui.actionAktueller_Status.triggered.connect(self.aktueller_status)
        self.ui.action_ueber_geier.triggered.connect(GeierStates.ueber_geier)
        self.ui.actionFeedback.triggered.connect(lambda: self.feedback('feedback'))
        self.ui.actionKontakt.triggered.connect(lambda: self.feedback('kontakt'))
        self.ui.actionThemen.triggered.connect(self.change_theme)
        self.ui.actionGrosse_Schrift.triggered.connect(self.grosse_schrift)
        self.ui.actionKleine_Schrift.triggered.connect(self.kleine_schrift)
        self.ui.actionTages_Back_Up.triggered.connect(self.backup)

        # shortcuts
        # mit dem Shortcut Ctrl+Q kann man das Programm beenden (es wird die entsrepcehnde Funtion die mit dem
        # Menu "Beenden" verbunden ist, aufgerufen, sodass dort die Überprüfung stattfinden kann, ob überhaupt
        # quittiert werden darf)
        self.ui.actionBeenden.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        self.ui.BTN_speichern_zeitgleich.setShortcut(QtGui.QKeySequence("Ctrl+S"))
        self.ui.BTN_schliessen.setShortcut(QtGui.QKeySequence("Ctrl+C"))
        self.ui.actionHinzufuegen.setShortcut(QtGui.QKeySequence("Alt+E"))
        self.shortcut1 = QShortcut(QtGui.QKeySequence("Ctrl+B"), self.ui.CMB_beringer)
        self.shortcut1.activated.connect(self.ui.CMB_beringer.setFocus)

        # Alle Aktionen für Button-Clicks
        self.ui.BTN_bearb_beenden.clicked.connect(self.edit_beenden)
        self.ui.BTN_schliessen.clicked.connect(self.schliessen)
        self.ui.BTN_neuer_datensatz.clicked.connect(self.new_dataset)
        self.ui.BTN_speichern_zeitgleich.clicked.connect(self.save_same_time)
        self.ui.BTN_ringer_nicht_gefunden.clicked.connect(self.ringer_not_found)
        self.ui.BTN_pic.clicked.connect(self.picture_show_clicked)
        self.ui.BTN_datenblatt_zwei.clicked.connect(self.datenblatt_zwei)
        self.ui.BTN_next_img.clicked.connect(self.next_pic_clicked)
        self.ui.BTN_prev_img.clicked.connect(self.prev_pic_clicked)
        self.ui.BTN_snapshot.clicked.connect(self.snapshot)
        self.ui.BTN_kamera_testen.clicked.connect(self.kameratest)

        # ComboBoxen
        # Alle Aktionen die mit den ComboBoxen und der Liste verknüpft sind
        # damit beim Initialisieren nicht ständig doppelt abgefragt wird und v.a. die Ringnummer nicht
        # generiert wird, verknüpfen wir das hier erst, wenn fertig.
        self.ui.CMB_art.currentIndexChanged.connect(self.art_index_changed)
        self.ui.CMB_art.currentTextChanged.connect(self.art_text_changed)

        self.ui.CMB_beringer.currentIndexChanged.connect(self.beringer_changed)
        self.ui.CMB_fangart.currentIndexChanged.connect(self.fangart_changed)
        self.ui.CMB_netz.setEditable(True)
        self.ui.CMB_netz.setCompleter(None)
        self.ui.CMB_netz.editTextChanged.connect(self.changed)
        self.ui.CMB_fach.setEditable(True)
        self.ui.CMB_fach.setCompleter(None)
        self.ui.CMB_fach.editTextChanged.connect(self.changed)
        self.ui.CMB_fett.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_muskel.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_alter.currentIndexChanged.connect(self.check_age)
        self.ui.CMB_sex.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_mauser1.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_mauser2.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_mauser2.currentTextChanged.connect(self.m2changed)
        self.ui.CMB_mauser3.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_fangart.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_verletzungscode.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_zentrale.currentIndexChanged.connect(self.zentrale_changed)

        # Listen:
        self.ui.LST_letzte_beringer.itemDoubleClicked.connect(self.beringer_aus_liste)

        # LineEdits' (Ringnummer, Teilfeder, Flügellänge, Masse)
        self.ui.INP_ringnummer.editingFinished.connect(self.ringnumber_edit_finished)
        self.ui.INP_ringnummer.installEventFilter(self)

        self.ui.INP_teilfeder.returnPressed.connect(self.focusNextChild)
        self.ui.INP_teilfeder.editingFinished.connect(lambda: self.teilfeder_editing_finished('teilfeder'))
        self.ui.INP_teilfeder.textEdited.connect(lambda: self.measurement_field_edited('teilfeder'))
        # self.ui.INP_teilfeder.installEventFilter(self)
        self.ui.INP_fluegellaenge.returnPressed.connect(self.focusNextChild)
        self.ui.INP_fluegellaenge.editingFinished.connect(lambda: self.teilfeder_editing_finished('fluegel'))
        self.ui.INP_fluegellaenge.textEdited.connect(lambda: self.measurement_field_edited('fluegellaenge'))
        # self.ui.INP_fluegellaenge.installEventFilter(self)
        self.ui.INP_masse.returnPressed.connect(self.focusNextChild)
        self.ui.INP_masse.editingFinished.connect(lambda: self.teilfeder_editing_finished('masse'))
        self.ui.INP_masse.textEdited.connect(lambda: self.measurement_field_edited('masse'))
        # self.ui.INP_masse.installEventFilter(self)

        self.ui.INP_teilfeder_2.editingFinished.connect(self.kerbe_edit_finished)
        # self.ui.INP_masse.editingFinished.connect(self.focus_next)
        self.ui.INP_teilfeder_2.textEdited.connect(lambda: self.measurement_field_edited('kerbe'))

        self.ui.INP_innenfuss.textEdited.connect(lambda: self.measurement_field_edited('innenfuss'))

        self.ui.CMB_art.installEventFilter(self)
        self.ui.CMB_fangart.installEventFilter(self)
        self.ui.CMB_netz.installEventFilter(self)
        self.ui.CMB_fach.installEventFilter(self)
        self.ui.CMB_fett.installEventFilter(self)
        self.ui.CMB_fett.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.CMB_fett.customContextMenuRequested.connect(lambda: self.rightClickFunction("fett"))

        self.ui.CMB_muskel.installEventFilter(self)
        self.ui.CMB_muskel.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.CMB_muskel.customContextMenuRequested.connect(lambda: self.rightClickFunction("muskel"))

        self.ui.CMB_alter.installEventFilter(self)
        self.ui.CMB_alter.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.CMB_alter.customContextMenuRequested.connect(lambda: self.rightClickFunction("alter"))

        self.ui.CMB_sex.installEventFilter(self)
        self.ui.CMB_sex.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.CMB_sex.customContextMenuRequested.connect(lambda: self.rightClickFunction("geschlecht"))

        self.ui.CMB_mauser1.installEventFilter(self)
        self.ui.CMB_mauser1.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.CMB_mauser1.customContextMenuRequested.connect(lambda: self.rightClickFunction("mauser1"))

        self.ui.CMB_mauser2.installEventFilter(self)
        self.ui.CMB_mauser2.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.CMB_mauser2.customContextMenuRequested.connect(lambda: self.rightClickFunction("mauser2"))

        self.ui.CMB_mauser3.installEventFilter(self)
        self.ui.CMB_mauser3.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.CMB_mauser3.customContextMenuRequested.connect(lambda: self.rightClickFunction("mauser3"))

        self.ui.CMB_verletzungscode.installEventFilter(self)
        self.ui.CMB_verletzungscode.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.CMB_verletzungscode.customContextMenuRequested.connect(lambda: self.rightClickFunction("verletzung"))

        self.ui.CMB_beringer.installEventFilter(self)
        self.ui.CMB_zentrale.installEventFilter(self)
        self.ui.CMB_station.installEventFilter(self)
        self.ui.PTE_bemerkung.installEventFilter(self)
        self.ui.CMB_camera_source.addItems(['0', '1', '2', '3', '4'])
        self.ui.CMB_camera_source.setCurrentIndex(0)

        self.ui.INP_teilfeder.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.INP_teilfeder.customContextMenuRequested.connect(lambda: self.rightClickFunction("teilfederlaenge"))
        self.ui.INP_fluegellaenge.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.INP_fluegellaenge.customContextMenuRequested.connect(lambda: self.rightClickFunction("fluegellaenge"))

        # self.ui.LBL_bild.enterEvent = lambda event: self.mouse_over_lbl(True)
        # self.ui.LBL_bild.leaveEvent = lambda event: self.mouse_over_lbl(False)
        # self.ui.GRA_view.enterEvent = lambda event: self.mouse_over_lbl(True)
        # self.ui.GRA_view.leaveEvent = lambda event: self.mouse_over_lbl(False)
        self.ui.GRA_view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.ui.GRA_view.setOptimizationFlags(QGraphicsView.DontAdjustForAntialiasing)

    def __set_validators(self):
        validator = QtGui.QRegularExpressionValidator()
        validator.setRegularExpression(QRegularExpression("[0-9]{0,4}|[0-9]{0,4}[.,]{1}[05]{1}"))
        # ^[1-9]{0,4}$|^(?=\d+[.,][05]$).{3,6}
        self.ui.INP_teilfeder.setValidator(validator)
        self.ui.INP_fluegellaenge.setValidator(validator)
        validator2 = QtGui.QRegularExpressionValidator()
        validator2.setRegularExpression(QRegularExpression("[0-9]{0,2}[.,]{0,1}[0,5]{0,1}"))
        self.ui.INP_teilfeder_2.setValidator(validator2)
        validator3 = QtGui.QRegularExpressionValidator()
        validator3.setRegularExpression(QRegularExpression("[0-9]{0,4}[.,]{0,1}[0-9]{0,1}"))
        # ^[1-9]{0,4}$|^(?=\d+[.,]\d$).{3,6}
        self.ui.INP_masse.setValidator(validator3)

    def __set_stylesheet(self, qss):
        # qss = "./qss/Adaptic/Adaptic.qss"
        # qss = "./qss/SpyBot/SpyBot.qss"
        # qss = "./qss/MacOS.qss"
        # qss = "./qss/Darkeum/Darkeum.qss"
        # qss = "./qss/Diffnes/Diffnes.qss"
        # qss = "./qss/Fibers/Fibers.qss"
        # qss = "./qss/Gravira/Gravira.qss"
        # qss = "./qss/Incrypt/Incrypt.qss"
        # qss = "./qss/Integrid/Integrid.qss" #label müsste schwarz
        # qss = "./qss/Irrorater/Irrorater.qss"
        # qss = "./qss/Remover/Remover.qss"
        # qss = "./qss/Integrid/Integrid.qss"
        # qss = "./qss/Adaptic/Adaptic.qss"
        # "./qss/Darkorange/darkorange.qss"
        # qss = "./qss/Combinear/Combinear.qss"  # ==> bestes Dark Theme
        app.setStyle("plastique")
        try:
            with open(qss, "r") as fh:
                self.setStyleSheet(fh.read())
                # self.menuBar().setStyleSheet(fh.read())
                # self.statusBar().setStyleSheet(fh.read())
                # self.centralWidget().setStyleSheet(fh.read())
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Das Stylesheet konnte nicht geladen werden.', 'Stylesheet-Fehler', str(excp),
                                   qss=bd.get_qss()).exec_()
            return

    def __get_stylesheet_file(self):
        return self._qss

    def __set_stylesheet_file(self, filename: str):
        self._qss = filename

    def __set_widget_stylesheet(self, widget: QWidget):
        try:
            with open(self.__get_stylesheet_file(), "r") as fh:
                widget.setStyleSheet(fh.read())
        except Exception as exp:
            rberi_lib.QMessageBoxB('ok', "Das Stylesheet konnte nicht geladen werden.", "Stylesheet-Fehler", str(exp),
                                       qss=bd.get_qss()).exec_()

    def change_theme(self):
        def open_file_picker():
            filename, ok = QFileDialog.getOpenFileName(
                self,
                "Auswahl StyleSheet",
                "./",
                "StyleSheets (*.qss)"
            )
            if filename:
                # self.selected_theme = Path(filename)
                try:
                    with open(filename, "r") as fh:
                        themePicker.setStyleSheet(fh.read())
                except Exception as excp:
                    rberi_lib.QMessageBoxB('ok', 'Konnte das StyleSheet nicht laden. Siehe Details.', 'Fehler beim Laden',
                                           str(excp), qss=bd.get_qss()).exec_()
                    return

        def speichern():
            # neues qss setzen (self.__set_file_stylesheet ... oder so) :)
            self.__set_widget_stylesheet(self)

        themePicker = QDialog()
        themePicker.setWindowTitle("Thema auswählen ...")

        label_aktuelles_theme = QLabel('Aktuelles Thema: "' + self.__get_stylesheet_file() + '"')
        button_select_theme = QPushButton('Thema wählen ... ')
        button_save = QPushButton('Übernehmen')
        button_cancel = QPushButton('Abbrechen/Schließen')

        test_combo = QComboBox()
        test_combo.addItems(['ComboBox', 'ist ', 'editierbar'])
        test_combo.setEditable(True)
        test_combo1 = QComboBox()
        test_combo1.addItems(['ComboBox', 'ist', 'nicht', 'editierbar'])
        test_combo1.setEditable(False)
        test_combo2 = QComboBox()
        test_combo2.addItems(['ComboBox', 'ist', 'deaktiviert'])
        test_combo2.setEnabled(False)

        test_lineedit = QLineEdit()
        test_lineedit.setInputMask('LineEdit mit Inputmaske')

        test_lineedit1 = QLineEdit()
        test_lineedit.setInputMask('LineEdit mit Inputmaske, deaktiviert')
        test_lineedit.setEnabled(False)

        test_chb = QCheckBox('CheckBox klick mich!')
        test_chb1 = QCheckBox('CheckBox deaktiviert')

        test_rdb = QRadioButton('RadioButton 1')
        test_rdb1 = QRadioButton('RadioButton 2')
        test_rdb2 = QRadioButton('RadioButton 3 deaktiviert')
        test_rdb2.setEnabled(False)

        test_tbl = QTableWidget()
        test_tbl.setColumnCount(3)
        test_tbl.setRowCount(3)
        test_tbl.setHorizontalHeaderLabels(['Spalte 1', 'Spalte 2', 'Spalte 3'])
        test_tbl.setHorizontalHeader(QtWidgets.QHeaderView(Qt.Orientation.Horizontal))

        for row in range(test_tbl.rowCount()):
            for col in range(test_tbl.columnCount()):
                test_tbl.setItem(row, col, QTableWidgetItem('R' + str(row) + 'C' + str(col)))

        test_tbl.resizeColumnsToContents()

        spacerItem = QtWidgets.QSpacerItem(10, 30, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        spacerItem1 = QtWidgets.QSpacerItem(10, 50, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)

        layout = QGridLayout()
        layout.addWidget(label_aktuelles_theme, 1, 0)
        layout.addWidget(button_select_theme, 1, 1)
        layout.addItem(spacerItem, 2, 0)
        layout.addWidget(test_combo, 3, 0)
        layout.addWidget(test_combo1, 3, 1)
        layout.addWidget(test_combo2, 3, 2)
        layout.addWidget(test_lineedit, 4, 0)
        layout.addWidget(test_lineedit1, 4, 1)
        layout.addWidget(test_chb, 5, 0)
        layout.addWidget(test_chb1, 5, 1)
        layout.addWidget(test_rdb, 6, 0)
        layout.addWidget(test_rdb1, 6, 1)
        layout.addWidget(test_rdb2, 6, 2)
        layout.addWidget(test_tbl, 7, 0)
        layout.addItem(spacerItem1, 8, 0)
        layout.addWidget(button_save, 9, 0)
        layout.addWidget(button_cancel, 9, 1)

        themePicker.setLayout(layout)

        button_select_theme.clicked.connect(open_file_picker)
        button_save.clicked.connect(speichern)
        button_cancel.clicked.connect(themePicker.reject)

        self.__set_widget_stylesheet(themePicker)
        themePicker.exec_()

    def kleine_schrift(self):
        self.__set_stylesheet("./qss/Darkorange/darkorange_klein.qss")

    def grosse_schrift(self):
        self.__set_stylesheet("./qss/Darkorange/darkorange.qss")

    # ############################################################################################################################
    # ALLES RUND UM LOOK-AND-FEEL (key-press, events, mouse-over, mouse-action, rightclick, etc.
    # ############################################################################################################################

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        if len(self.pic_list) > 0:
            self.fitInView(self.ui.GRA_view)
        QMainWindow.resizeEvent(self, event)

    def wheelEventQ(self, event):
        state = {
            'angleDelta': event.angleDelta(),
            'buttons': event.buttons(),
            # 'delta': event.delta(),
            'globalPos': event.globalPos(),
            'globalPosF': event.globalPosF(),
            'globalPosition': event.globalPosition(),
            'globalX': event.globalX(),
            'globalY': event.globalY(),
            'inverted': event.inverted(),
            # 'orientation': event.orientation(),
            'phase': event.phase(),
            'pixelDelta': event.pixelDelta(),
            'pos': event.pos(),
            'posF': event.posF(),
            'position': event.position(),
            'source': event.source(),
            'x': event.x(),
            'y': event.y(),
        }

        if self.mouse_over_pic:
            if bd.get_debug():
                print(f"Maus ist über LBL und Mausrad wird gedreht! ... {state}")

            if self.pic is not None and len(self.scene.items()) > 0:
                if event.angleDelta().y() > 0:
                    faktor = 1.1
                    self._zoom += 1
                else:
                    faktor = 0.9
                    self._zoom -= 1
                if self._zoom > 0:
                    self.ui.GRA_view.scale(faktor, faktor)

                elif self._zoom < 0:
                    self.fitInView(self.ui.GRA_view)
                else:
                    self._zoom = 0
        event.ignore()

        return super().wheelEventQ(event)

    def eventFilter(self, source: QObject, event: QEvent):
        if event.type() == QEvent.FocusIn:
            if source.objectName() == 'INP_teilfeder':
                self.teilfeder = self.ui.INP_teilfeder.text()
            elif source.objectName() == 'INP_fluegellaenge':
                self.fluegellaenge = self.ui.INP_fluegellaenge.text()
            elif source.objectName() == 'INP_masse':
                self.masse = self.ui.INP_masse.text()

        elif event.type() == QEvent.FocusOut:
            if source.objectName() == 'CMB_fach':
                if 0 < len(self.ui.CMB_fach.currentText()) < 2:
                    rberi_lib.QMessageBoxB('ok', f'Das Netz "{self.ui.CMB_netz.currentText()} '
                                                 f'{self.ui.CMB_fach.currentText()}" '
                                                 f'existiert nicht. Automatische Korrektur bitte überprüfen und im Zweifel '
                                                 f'anpassen. ', 'Eingabefehler', qss=bd.get_qss()).exec_()
                    netz = self.ui.CMB_netz.currentText()
                    fach = self.ui.CMB_fach.currentText()
                    self.ui.CMB_netz.setCurrentText("0" + netz[0])
                    self.ui.CMB_fach.setCurrentText(netz[1] + fach.upper())
            if source.objectName() == 'CMB_art' and len(self.ui.CMB_art.currentText()) > 0:
                if self.ui.timeEdit.time().hour() != QTime.currentTime().hour():
                    answer = rberi_lib.QMessageBoxB('ny', 'Zeit aktualisieren für diesen Datensatz?', 'Zeitanpassung',
                                                    qss=bd.get_qss()).exec_()
                    if answer == QMessageBox.Yes:
                        self.ui.timeEdit.setTime(QTime.currentTime())
                if self.ui.dateEdit.date().toPyDate() != datetime.today().date():
                    answer = rberi_lib.QMessageBoxB('yn', 'Datum aktualisieren für diesen Datensatz?', 'Datumsanpassung',
                                                    qss=bd.get_qss()).exec_()
                    if answer == QMessageBox.Yes:
                        self.ui.dateEdit.setDate(datetime.today())
                if not self.is_rohrsaenger():
                    self.ui.INP_teilfeder_2.setEnabled(False)
                    self.ui.INP_innenfuss.setEnabled(False)
                else:
                    self.ui.INP_teilfeder_2.setEnabled(True)
                    self.ui.INP_innenfuss.setEnabled(True)

        elif event.type() == QEvent.KeyPress:
            if event.modifiers() & Qt.AltModifier:
                if event.key() == QtCore.Qt.Key.Key_Down:
                    return super().eventFilter(source, event)
            elif event.key() == QtCore.Qt.Key.Key_Down:
                if isinstance(source, QComboBox) or isinstance(source, QLineEdit):
                    self.focusNextChild()
                    return True
                    # hier darf nicht der super rein, weil der sonst auch zuschlägt ;)
                    # return super().eventFilter(source, event)
                if isinstance(source, QPlainTextEdit):
                    #  print(f"position des cursors in Bemerkung = {source.textCursor().position()}")
                    if len(source.toPlainText()) == 0 or source.textCursor().position() >= len(source.toPlainText()):
                        self.focusNextChild()
                        return True
            elif event.key() == QtCore.Qt.Key.Key_Up:
                if isinstance(source, QComboBox) or isinstance(source, QLineEdit):
                    if source.objectName() != "CMB_art":
                        self.focusPreviousChild()
                    return True
                if isinstance(source, QPlainTextEdit):
                    # print(f"position des cursors in Bemerkung = {source.textCursor().position()}")
                    if len(source.toPlainText()) == 0 or source.textCursor().position() == 0:
                        self.focusPreviousChild()
                        return True
            elif event.key() == QtCore.Qt.Key.Key_Delete or event.key() == QtCore.Qt.Key.Key_Backspace:
                if source in self.cmb_list1 or source in self.cmb_list2:
                    source.setCurrentIndex(-1)
                    return super().eventFilter(source, event)
            elif event.modifiers() & Qt.ControlModifier:
                if event.key() == Qt.Key_C:
                    self.schliessen()
                    return True
            elif event.key() == Qt.Key_Return and source == self.ui.CMB_art:
                self.focusNextChild()
                return True

        return super().eventFilter(source, event)

    def teilfeder_editing_finished(self, source):
        if source == 'teilfeder':
            if self.ui.INP_teilfeder.text() != self.teilfeder:
                self.proof_gauss('teilfeder')
            if (self.ui.INP_teilfeder.text().find(".") < 0 and self.ui.INP_teilfeder.text().find(",") < 0 and
                    len(self.ui.INP_teilfeder.text())):
                self.ui.INP_teilfeder.setText(self.ui.INP_teilfeder.text() + ".0")
        elif source == 'fluegel':
            if self.ui.INP_fluegellaenge.text() != self.fluegellaenge:
                self.proof_gauss('fluegel')
            if (self.ui.INP_fluegellaenge.text().find(".") < 0 < len(self.ui.INP_fluegellaenge.text()) and
                    self.ui.INP_fluegellaenge.text().find(",") < 0):
                self.ui.INP_fluegellaenge.setText(self.ui.INP_fluegellaenge.text() + ".0")
        elif source == 'masse':
            if self.ui.INP_masse.text() != self.masse:
                self.proof_gauss('gewicht')

    def is_rohrsaenger(self):
        if self.ui.CMB_art.currentText() == "Sumpfrohrsänger" or self.ui.CMB_art.currentText() == "Teichrohrsänger":
            return True
        return False

    def measurement_field_edited(self, source: str):
        if source == "teilfeder":
            txt = self.ui.INP_teilfeder.text()
            if txt.find(",5") > 0 or txt.find(".5") > 0 or txt.find(",0") > 0 or txt.find(".0") > 0:
                self.ui.INP_fluegellaenge.setFocus()
        elif source == "fluegellaenge":
            txt = self.ui.INP_fluegellaenge.text()
            if txt.find(",5") > 0 or txt.find(".5") > 0 or txt.find(",0") > 0 or txt.find(".0") > 0:
                if self.is_rohrsaenger():
                    self.ui.INP_teilfeder_2.setFocus()
                else:
                    self.ui.INP_masse.setFocus()
        elif source == "masse":
            txt = self.ui.INP_masse.text()
            if (txt.find(",") > 0 or txt.find(".") > 0) and (txt[-1] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']):
                self.ui.CMB_verletzungscode.setFocus()
        elif source == 'kerbe':
            txt = self.ui.INP_teilfeder_2.text()
            if txt.find(",5") > 0 or txt.find(".5") > 0 or txt.find(",0") > 0 or txt.find(".0") > 0:
                self.ui.INP_innenfuss.setFocus()
        elif source == 'innenfuss':
            txt = self.ui.INP_innenfuss.text()
            if (txt.find(",") > 0 or txt.find(".") > 0) and (txt[-1] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']):
                self.ui.INP_masse.setFocus()

    def keyPressEvent(self, event: QEvent):
        if event.key() == QtCore.Qt.Key.Key_Down:
            if (self.ui.INP_teilfeder.hasFocus() or self.ui.INP_fluegellaenge.hasFocus() or self.ui.INP_masse.hasFocus() or
                    self.ui.INP_teilfeder_2.hasFocus() or self.ui.INP_innenfuss.hasFocus()):
                self.focusNextChild()
                return
        elif event.key() == QtCore.Qt.Key.Key_Up:
            if (self.ui.INP_teilfeder.hasFocus() or self.ui.INP_fluegellaenge.hasFocus() or self.ui.INP_masse.hasFocus() or
                    self.ui.INP_teilfeder_2.hasFocus() or self.ui.INP_innenfuss.hasFocus()):
                self.focusPreviousChild()
                return
        if event.key() == QtCore.Qt.Key.Key_Escape:
            if not self.get_edit_status():
                self.schliessen()
                return

        super(MainWindow, self).keyPressEvent(event)

    def mouse_over_lbl(self, state):
        self.mouse_over_pic = state
        if not self.ui.GRA_view.sceneRect():
            return
        if len(self.ui.GRA_view.items()) <= 0:
            return

        if state:
            self.fitInView(self.ui.GRA_view)
        else:
            self.fitInView(self.ui.GRA_view)
            # self.ui.GRA_view.scale(0.1, 0.1)

    def rightClickFunction(self, source: str):
        info_kurztext = ":"
        if source == 'fett':
            info_kurztext = "Fettbestimmung:"
        elif source == 'muskel':
            info_kurztext = "Muskelbestimmung:"
        elif source == 'alter':
            info_kurztext = "Altersbestimmung:"
        elif source == 'geschlecht':
            info_kurztext = 'Geschlechtsbestimmung:'
        elif source == 'mauser1':
            info_kurztext = 'Kleingefiedermauser:'
        elif source == 'mauser2':
            info_kurztext = 'Kleingefiederfortschritt:'
        elif source == 'mauser3':
            info_kurztext = 'Großgefiedermauser:'
        elif source == 'teilfederlaenge':
            info_kurztext = 'Teilfederlänge:'
        elif source == 'fluegellaenge':
            info_kurztext = 'Flügellänge:'
        elif source == "verletzung":
            info_kurztext = 'Verletzungscode:'

        show_pic = QtWidgets.QDialog()
        show_pic.setWindowTitle("Info über " + info_kurztext)

        show_pic.setLayout(QVBoxLayout())
        bild_lbl = QtWidgets.QLabel()
        filepath = bd.get_hilfepfad() + source + '.jpg'
        if os.path.isfile(filepath):
            bild_lbl.setPixmap(QPixmap(filepath))
            bild_lbl.setScaledContents(True)
            show_pic.layout().addWidget(bild_lbl)
            show_pic.resize(bild_lbl.width(), bild_lbl.height())
            show_pic.exec_()
        else:
            rberi_lib.QMessageBoxB('ok', 'Bild "' + str(source) + '" nicht gefunden.',
                                   'File nicht gefunden ...', qss=bd.get_qss()).exec_()
            return
        if self:
            pass

    def disconnect_all(self):
        self.ui.CMB_fach.editTextChanged.disconnect(self.changed)
        self.ui.CMB_netz.editTextChanged.disconnect(self.changed)
        self.ui.CMB_fett.currentIndexChanged.disconnect(self.changed_index)
        self.ui.CMB_muskel.currentIndexChanged.disconnect(self.changed_index)
        # self.ui.CMB_alter.currentIndexChanged.disconnect(self.changed_index)
        self.ui.CMB_alter.currentIndexChanged.disconnect(self.check_age)
        self.ui.CMB_sex.currentIndexChanged.disconnect(self.changed_index)
        self.ui.CMB_mauser1.currentIndexChanged.disconnect(self.changed_index)
        self.ui.CMB_mauser2.currentIndexChanged.disconnect(self.changed_index)
        self.ui.CMB_mauser3.currentIndexChanged.disconnect(self.changed_index)

    def connect_all(self):
        self.ui.CMB_fach.editTextChanged.connect(self.changed)
        self.ui.CMB_netz.editTextChanged.connect(self.changed)
        self.ui.CMB_fett.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_muskel.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_alter.currentIndexChanged.connect(self.check_age)
        self.ui.CMB_sex.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_mauser1.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_mauser2.currentIndexChanged.connect(self.changed_index)
        self.ui.CMB_mauser3.currentIndexChanged.connect(self.changed_index)

    ##############################################################################################################################
    # ALLE FUNKTIONEN DIE EIN NEUES FENSTER ÖFFNEN
    ##############################################################################################################################

    def search(self):
        self.ui_search = _UiSearch()
        self.__set_widget_stylesheet(self.ui_search)
        self.ui_search.show()

    def ringserienverwaltung(self):
        rsv = Ui_RingSerienVerwaltung(engine)
        rsv.setWindowTitle("Ringserienverwaltung")
        self.__set_widget_stylesheet(rsv)
        # rsv.ui.TBL_ringserien.status_changed.connect(rsv.ui.BTN_spezial.setEnabled)

        if ringserienverwaltung.check_integrity_ringseries(engine):
            self.ui.statusbar.showMessage('Integrity OK', 5000)
            rsv.exec_()
        else:
            print('Integrity NOK -  WARNING! WARNING!')
            rberi_lib.QMessageBoxB('ok', 'Integrity-Check NICHT erfolgreich durchlaufen!! Bitte einen Admin '
                                         'kontaktieren. Die Datenbank muss angepasst werden. Dies kann aber nicht über '
                                         'das Programm erfolgen.', 'Info', qss=bd.get_qss()).exec_()
            self.programm_beenden('Integrity-Test negativ!!! HÖCHSTE ALARMSTUFE!!!! ACHTUNG!! ACHTUNG!!')

    def datenblatt_zwei(self):
        if len(self.ui.INP_teilfeder.text()) > 0:
            self.db2['hs3'] = self.ui.INP_teilfeder.text()
        if len(self.ui.INP_teilfeder_2.text()) > 0:
            self.db2['kerbe'] = self.ui.INP_teilfeder_2.text()
        if len(self.ui.INP_innenfuss.text()) > 0:
            self.db2['innenfuss'] = self.ui.INP_innenfuss.text()

        if self.db2:
            sb2 = _UiDatenblatt2(self.db2)
        else:
            sb2 = _UiDatenblatt2()
        self.__set_widget_stylesheet(sb2)
        if sb2.exec_() == QDialog.Accepted:
            self.db2 = sb2.get_vals()
        else:
            sb2.close()

    def kerbe_edit_finished(self):
        kerbe(self.ui.INP_teilfeder_2.text(), self.ui.CMB_art, self.ui.INP_fluegellaenge.text(), self.ui.CMB_alter.currentText())
        # self.ui.BTN_speichern_zeitgleich.setFocus(True)

    def menu_settings_triggered(self):
        ui_einstellungen = Ui_Settings()
        self.__set_widget_stylesheet(ui_einstellungen)
        if ui_einstellungen.exec_() == QDialog.Accepted:
            return True
        return False

    def benutzereinstellungen(self, onlyload=False):
        def fileOpenDialog():
            filedialog = QFileDialog(self)
            filedialog.setFileMode(QFileDialog.ExistingFile)
            filedialog.setNameFilter("Stylesheet (*.qss)")
            filedialog.setViewMode(QFileDialog.List)
            if filedialog.exec_():
                user_settings.ui.LE_stylesheet.setText(filedialog.selectedFiles()[0])

        # -----------------------------------------------------------------------------------------------------------------------

        user_settings = QDialog()
        user_settings.ui = Ui_Dialog_usersettings()
        user_settings.ui.setupUi(user_settings)
        if not onlyload:
            self.__set_widget_stylesheet(user_settings)

        # user_settings.ui.LE_stylesheet.setText("not implemented yet")
        # user_settings.ui.LE_stylesheet.setEnabled(False)

        user_settings.ui.BTN_speichern.clicked.connect(user_settings.accept)
        user_settings.ui.BTN_cancel.clicked.connect(user_settings.reject)
        user_settings.ui.TBTN_qss_select.clicked.connect(fileOpenDialog)
        try:
            engine.ping()
        except Exception as err:
            rberi_lib.QMessageBoxB('ok', 'Keine Datenbankverbindung.', 'Datenbankfehler', str(err), qss=bd.get_qss()).exec_()
            return
        df_set = pd.read_sql("SELECT * FROM benutzer WHERE username = '" + self.get_current_user() + "'", engine)
        if df_set.empty:
            rberi_lib.QMessageBoxB('ok', 'Interner Fehler. Es wurden keine Benutzerdaten gefunden.', 'Interner Fehler.',
                                   ['SQL_TXT = ', '"SELECT * FROM benutzer WHERE username = self.get_current_user()',
                                    'self.get_current_user = ', self.get_current_user()], qss=bd.get_qss()).exec_()
            return
        schnellauswahl = str(df_set['schnellauswahl'].iloc[0])
        if schnellauswahl == "Y":
            user_settings.ui.RDB_schnellauswahl_ein.setChecked(True)
            self.ui.CHB_schnellauswahl.setChecked(True)
        else:
            user_settings.ui.RDB_schnellauswahl_aus.setChecked(True)
            self.ui.CHB_schnellauswahl.setChecked(False)

        beringer_in_tab = str(df_set['beringer_in_tab'].iloc[0])
        if beringer_in_tab == "Y":
            user_settings.ui.RDB_beringer_tab_ja.setChecked(True)
            self.beringer_in_tab = True
        else:
            user_settings.ui.RDB_beringer_tab_nein.setChecked(True)
            self.beringer_in_tab = False

        schriftgroesse = str(df_set['schriftgroesse'].iloc[0])
        if schriftgroesse == "k":
            user_settings.ui.RDB_schrift_klein.setChecked(True)
            # TODO
            # hier muss noch rein, dass das kleine oder das grosse schrift - qss geladen wird
        else:
            # TODO
            # hier muss noch rein, dass das kleine oder das grosse schrift - qss geladen wird
            user_settings.ui.RDB_schrift_gross.setChecked(True)

        stylesheet = str(df_set['stylesheet'].iloc[0])
        if bd.set_qss(stylesheet):
            self.__set_stylesheet(bd.get_qss())
            user_settings.ui.LE_stylesheet.setText(stylesheet)
        else:
            user_settings.ui.LE_stylesheet.setText("")

        if onlyload:
            return

        if user_settings.exec_() == QDialog.Accepted:
            if user_settings.ui.RDB_schnellauswahl_ein.isChecked() and schnellauswahl == "N":
                schnellauswahl_neu = "Y"
                self.ui.CHB_schnellauswahl.setChecked(True)
            elif user_settings.ui.RDB_schnellauswahl_aus.isChecked() and schnellauswahl == "Y":
                schnellauswahl_neu = "N"
                self.ui.CHB_schnellauswahl.setChecked(False)
            else:
                schnellauswahl_neu = schnellauswahl

            if user_settings.ui.RDB_beringer_tab_ja.isChecked() and beringer_in_tab == "N":
                beringer_in_tab_neu = "Y"
                self.beringer_in_tab = True
            elif user_settings.ui.RDB_beringer_tab_nein.isChecked() and beringer_in_tab == "Y":
                beringer_in_tab_neu = "N"
                self.beringer_in_tab = False
            else:
                beringer_in_tab_neu = beringer_in_tab

            if user_settings.ui.RDB_schrift_klein.isChecked() and schriftgroesse == "g":
                # hier muss eigentlich noch geprüft werden, ob es ein "kleinschriftiges" stylesheet gibt...
                # TODO
                # TODO
                # TODO
                schriftgroesse_neu = "k"
            elif user_settings.ui.RDB_schrift_gross.isChecked() and schriftgroesse == "k":
                schriftgroesse_neu = "g"
            else:
                schriftgroesse_neu = schriftgroesse

            if bd.set_qss(user_settings.ui.LE_stylesheet.text()):
                stylesheet_new = user_settings.ui.LE_stylesheet.text()
            else:
                stylesheet_new = stylesheet

            stylesheet_new.replace("\\", "/")

            try:
                cursor = engine.cursor()
                sql_t = ("UPDATE benutzer SET beringer_in_tab = '" + beringer_in_tab_neu + "', schriftgroesse = '"
                         + schriftgroesse_neu + "', schnellauswahl = '" + schnellauswahl_neu + "', stylesheet = '"
                         + stylesheet_new + "' WHERE username = '" + self.get_current_user() + "'")
                cursor.execute(sql_t)
                engine.commit()
                cursor.close()
            except Exception as err:
                rberi_lib.QMessageBoxB('ok', 'Konnte die Änderungen nicht speichern.', 'Datenbankfehler', str(err),
                                       qss=bd.get_qss()).exec_()
                return

    def call_beringerverwaltung(self):
        if get_connection_status(engine):
            self.df_ringer = pd.read_sql("SELECT * FROM ringer", engine)
            df_ringer = self.df_ringer
            beringerverwaltung_ui = Dialog_beringerverwaltung(self.berechtigung_beringer_speichern, df_ringer)
            self.__set_widget_stylesheet(beringerverwaltung_ui)
            if beringerverwaltung_ui.exec_() == QtWidgets.QMessageBox.Accepted:
                # speichern:
                eintrag = beringerverwaltung_ui.get_row_to_save()  # Bibiliothek
                eintrag_vorhanden = pd.read_sql("SELECT * FROM ringer where nachname='"
                                                + eintrag['nachname'] + "' and vorname='"
                                                + eintrag['vorname'] + "'", engine)
                if len(eintrag_vorhanden) >= 1 and eintrag['only-year'] == 0:
                    # Beringer bereits vorhanden ==> überschreiben?
                    msgb = QtWidgets.QMessageBox()
                    msgb.setWindowTitle("Speichern ...")
                    msgb.setText("Eintrag ist bereits vorhanden! Wirklich speichern/überschreiben?")
                    msgb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msgb.setDefaultButton(QMessageBox.No)
                    if msgb.exec_() != QMessageBox.Yes:
                        return
                    try:
                        if not eintrag['plz']:
                            plz_txt = "''"
                        else:
                            plz_txt = str(eintrag['plz'])
                        SQL_txt = ("UPDATE ringer SET strasse='" + eintrag['strasse'] + "', plz =" + plz_txt +
                                   ", ort ='" + eintrag['stadt'] + "', land ='" + eintrag['land'] + "', telefon ='" +
                                   str(eintrag['telefon']) + "', telefax = '" + str(eintrag['fax']) + "', email ='" +
                                   eintrag['email'] + "', anmerkung ='" + eintrag['anmerkung'] +
                                   "', zeige_wiederfaenge =" + str(eintrag['wiederfang']) + " WHERE vorname ='" +
                                   eintrag['vorname'] + "' AND nachname = '" + eintrag['nachname'] + "'")
                        if bd.get_debug():
                            print(SQL_txt)
                        cursor = engine.cursor()
                        cursor.execute(SQL_txt)
                        engine.commit()
                        cursor.close()
                        logging(window.get_current_user(), datetime.now(), "verwaltung",
                                "Beringerverwaltung: '" + eintrag['nachname'] + ", " + eintrag['vorname'] +
                                "' wurde geändert.")
                    except Exception as exc:
                        rberi_lib.QMessageBoxB('ok', "Fehler beim Speichern des Datensatzes für '" + eintrag['nachname'] +
                                               ", " + eintrag['vorname'] + "'. Siehe Details für die genaue Fehlerbeschreibung. "
                                                                           "Bitte kontaktiert den Support!",
                                               "Speichern fehlgeschlagen", str(exc), qss=bd.get_qss()).exec_()

                elif len(eintrag_vorhanden) >= 1 and eintrag['only-year'] == 1:
                    try:
                        SQL_txt = ("UPDATE ringer SET jahr=" + datetime.now().date().strftime("%Y") +
                                   " WHERE vorname ='" + eintrag['vorname'] + "' AND nachname = '" +
                                   eintrag['nachname'] + "'")
                        # print(SQL_txt)
                        cursor = engine.cursor()
                        cursor.execute(SQL_txt)
                        engine.commit()
                        cursor.close()
                        rberi_lib.QMessageBoxB('ok', "Aktivierung von '" + eintrag['vorname'] + " " + eintrag['nachname'] +
                                               "' für das Jahr " + datetime.now().date().strftime("%Y") + " erfolgreich!",
                                               "Erfolg", qss=bd.get_qss()).exec_()
                        self.fill_ringer_current_year()
                        combo_txt = eintrag['nachname'] + ", " + eintrag['vorname']
                        # self.ui.CMB_beringer.setCurrentText(combo_txt)
                        self.ui.CMB_beringer.setCurrentIndex(self.ui.CMB_beringer.findText(combo_txt))
                        logging(window.get_current_user(), datetime.now(), "verwaltung",
                                "Beringerverwaltung: '" + eintrag['nachname'] + ", " + eintrag['vorname'] +
                                "' wurde für das Jahr " + datetime.now().date().strftime("%Y") + " freigeschaltet.")
                    except Exception as exc:
                        rberi_lib.QMessageBoxB('ok', "Fehler beim Speichern des Datensatzes für '" +
                                               eintrag['nachname'] + ", " + eintrag['vorname'] +
                                               "'. Siehe Details für die genaue Fehlerbeschreibung. Bitte kontaktiert den \
                                            Support!", 'Fehler beim Speichern', str(exc), qss=bd.get_qss()).exec_()
                else:  # neuer Eintrag
                    try:
                        ringer_alt = ""
                        jahr = datetime.now().year
                        ringer_neu = self.generate_new_ringer(eintrag['vorname'], eintrag['nachname'])
                        if ringer_neu == "ungueltig":
                            rberi_lib.QMessageBoxB('ok', "Es konnte keine automatische Kürzelgenerierung erfolgen. Bitte "
                                                         "kontaktiere den Support. ", "Interner Fehler", qss=bd.get_qss()).exec_()
                            return
                        station = "REIT"
                        cursor = engine.cursor()
                        cursor.execute("INSERT INTO ringer (ringer_alt, jahr, ringer_new, station, vorname, strasse, "
                                       "plz, ort, land, telefon, telefax, email, anmerkung, zeige_wiederfaenge, "
                                       "nachname) "
                                       "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                       (ringer_alt, jahr, ringer_neu, station, eintrag['vorname'],
                                        eintrag['strasse'], str(eintrag['plz']), eintrag['stadt'], eintrag['land'],
                                        eintrag['telefon'], eintrag['fax'], eintrag['email'], eintrag['anmerkung'],
                                        eintrag['wiederfang'], eintrag['nachname']))
                        engine.commit()
                        cursor.close()
                        logging(window.get_current_user(), datetime.now(), "verwaltung",
                                "Beringerverwaltung: '" + eintrag['nachname'] + ", " + eintrag['vorname'] +
                                "' wurde hinzugefügt.")
                    except Exception as exc:
                        rberi_lib.QMessageBoxB('ok', "Fehler beim Speichern des Datensatzes für '" +
                                               eintrag['nachname'] + ", " + eintrag['vorname'] +
                                               "'. Siehe Details für die genaue Fehlerbeschreibung. Bitte kontaktiert den \
                                           Support!", 'Fehler beim Speichern', str(exc), qss=bd.get_qss()).exec_()

    def add_new_user(self):
        if self:
            pass
        level = df_benutzer["level"].tolist()
        level.sort()
        newuser_ui = Ui_Dialogs(level)
        newuser_ui.setupUi()
        self.__set_widget_stylesheet(newuser_ui)
        rueck = newuser_ui.exec_()
        if rueck == QDialog.Accepted:
            if bd.get_debug():
                print("Benutzername kann angelegt werden!")
            new_username = newuser_ui.INP_username.text()
            new_pw = newuser_ui.INP_pw.text()
            new_lvl = newuser_ui.CMB_lvl.currentText()
            token_ = f.encrypt(new_pw.encode())
            if new_username not in df_benutzer.username.tolist():
                cursor = engine.cursor()
                cursor.execute("INSERT INTO benutzer (username, password, level) VALUES (%s, %s, %s)",
                               (new_username, token_, new_lvl))
                engine.commit()
                cursor.close()
            else:
                rberi_lib.QMessageBoxB('ok', "Username bereits vorhanden!", "Fehler",
                                       "Welche weiteren Informationen erwartest Du hier? Der Username ist "
                                       "halt schon vergeben. Ende Basta Aus!", qss=bd.get_qss()).exec_()
                return

    def show_artverwaltung(self):
        if self:
            pass
        if bd.get_debug():
            print("Artverwaltung im Menue wurde aufgerufen... ")
        artv_ui = artverwalt.ArtverwaltungWindow(engine)
        self.__set_widget_stylesheet(artv_ui)
        artv_ui.show()
        artv_ui.loggingNeeded.connect(logging)

    def walinder(self):
        """
        Öffnet Dialog für den Walinder.
        :return:
        """

        def proof():
            schnabellaenge = self.walinder_dialog.ui.INP_schnabellaenge.text().replace(",", ".")
            tarsusbreite = self.walinder_dialog.ui.INP_tarsusbreite.text().replace(",", ".")
            schnabelbreite = self.walinder_dialog.ui.INP_schnabelbreite.text().replace(",", ".")
            if len(schnabellaenge) <= 0 or len(tarsusbreite) <= 0 or len(schnabelbreite) <= 0:
                return
            try:
                schnabellaenge = round(float(schnabellaenge), 2)
                tarsusbreite = round(float(tarsusbreite), 2)
                schnabelbreite = round(float(schnabelbreite), 2)
            except ValueError as ve:
                rberi_lib.QMessageBoxB('ok', 'Einer der Werte ist keine Dezimalzahl!', 'Dezimalzahlfehler', str(ve),
                                       qss=bd.get_qss()).exec_()
                return

            if schnabellaenge > 0 and tarsusbreite > 0 and schnabelbreite > 0:
                result = schnabellaenge - (tarsusbreite * schnabelbreite)
                self.walinder_data = (f"Schnabellänge = {schnabellaenge} mm, Tarsusbreite = {tarsusbreite} mm, "
                                      f"Schnabelbreite = {schnabelbreite} mm. Ergebnis = {result:.2f}")

                if 8.0 >= result >= 4.5:
                    self.walinder_result = 'Sumpfrohrsänger'
                elif 8.5 <= result <= 12.5:
                    self.walinder_result = 'Teichrohrsänger'
                else:
                    self.walinder_result = 'UNIDENTIFIED'

                self.walinder_dialog.ui.LBL_Ergebnis.setText(self.walinder_result)
                self.walinder_dialog.ui.LBL_result_value.setText(f"{result:.1f}")

        def take_all():
            if self.ui.CMB_art.currentText() != self.walinder_result and self.walinder_resut != 'UNIDENTIFIED':
                self.ui.CMB_art.setCurrentText(self.walinder_result)
                self.db2['schnabellaenge'] = self.walinder_dialog.ui.INP_schnabellaenge.text()
                self.db2['schnabelbreite'] = self.walinder_dialog.ui.INP_schnabelbreite.text()
                # self.db2['tarsusbreite'] = self.walinder_dialog.ui.INP_tarsusbreite.text()
                # noch nicht im DB2 enthalten.

            self.ui.PTE_bemerkung.setPlainText(self.walinder_data)
            self.walinder_dialog.accept()

        def take_species():
            if self.ui.CMB_art.currentText() != self.walinder_result and self.walinder_result != 'UNIDENTIFIED':
                self.ui.CMB_art.currentText(self.walinder_result)
            self.walinder_dialog.accept()

        if self.ui.CMB_art.currentText() != 'Teichrohrsänger' and self.ui.CMB_art.currentText() != "Sumpfrohrsänger":
            rberi_lib.QMessageBoxB('ok', 'Walinder kann nur bei Sumpf- oder Teichrohrsänger angewendet werden.',
                                   'Walinder', qss=bd.get_qss()).exec_()
            return

        self.walinder_dialog = QDialog()
        self.walinder_dialog.ui = UiWalinder()
        self.walinder_dialog.ui.setupUi(self.walinder_dialog)
        self.walinder_dialog.setWindowTitle("Walinder")
        self.walinder_dialog.ui.INP_tarsusbreite.editingFinished.connect(proof)
        self.walinder_dialog.ui.INP_schnabelbreite.editingFinished.connect(proof)
        self.walinder_dialog.ui.INP_schnabellaenge.editingFinished.connect(proof)
        self.walinder_dialog.ui.BTN_calc.clicked.connect(proof)
        self.walinder_dialog.ui.BTN_take_all.clicked.connect(take_all)
        self.walinder_dialog.ui.BTN_take_species.clicked.connect(take_species)
        self.walinder_dialog.ui.BTN_cancel.clicked.connect(self.walinder_dialog.reject)
        self.walinder_dialog.ui.LBL_current_species.setText(self.ui.CMB_art.currentText())
        self.__set_widget_stylesheet(self.walinder_dialog)
        self.walinder_dialog.exec_()

    def search_item_ringnb(self):
        self.search_ui = _UiSearchItem()
        self.__set_widget_stylesheet(self.search_ui)
        if self.search_ui.exec_() == QDialog.Accepted:
            pass
        else:
            pass

    def backup(self):
        self.backup_window = Backup_GUI()
        filename = self.__get_stylesheet_file()
        if filename:
            with open(filename, "r") as fh:
                self.backup_window.setStyleSheet(fh.read())
        result = self.backup_window.exec_()
        self.backup_window.done(result)

    # ############################################################################################################################
    # ALLES RUND UMS BILD
    # ############################################################################################################################
    def fitInView(self, view: QGraphicsView):
        if self.pic is None:
            return
        if self.pic.pixmap() is None:
            return
        if not isinstance(self.pic, QGraphicsPixmapItem):
            return
        if not isinstance(self.pic.pixmap(), QPixmap):
            return
        try:
            rect = QtCore.QRectF(self.pic.pixmap().rect())
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Es trat ein Fehler mit der Bilddarstellung auf. Bitte den Entwickler informieren und '
                                         'den genauen Fehlertext (siehe Details) mitteilen. Danke für die Mitarbeit!',
                                   'Bildfehler', str(excp), qss=bd.get_qss()).exec_()
            return

        if not rect.isNull():
            view.setSceneRect(rect)
            unity = view.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
            view.scale(1 / unity.width(), 1 / unity.height())
            """if bd.get_debug():
                print(f"view.width = {view.width()}, view.height = {view.height()}")"""
            viewrect = view.viewport().rect()
            """if bd.get_debug():
                print(f"Viewport.rect(): w = {viewrect.width()}, h = {viewrect.height()}")"""
            scenerect = view.transform().mapRect(rect)
            """if bd.get_debug():
                print(f"scenerect.rect(): w = {scenerect.width()}, h = {scenerect.height()}")
                print("Jetzt wird gezoomt .... ")"""
            if self.zoom_seitenbreite:
                factor = viewrect.width() / scenerect.width()
            else:
                factor = min(viewrect.width() / scenerect.width(), viewrect.height() / scenerect.height())
            """if bd.get_debug():
                print(f"factor = {factor}")"""
            view.scale(factor, factor)
            """if firstload:
                view.scale(0.100, 0.100)"""
            """if bd.get_debug():
                print(f"Zoom/Scale beendet ... ")
                print(f"view.width = {view.width()}, view.height = {view.height()}")
                print(f"Viewport.rect(): w = {viewrect.width()}, h = {viewrect.height()}")
                print(f"scenerect.rect(): w = {scenerect.width()}, h = {scenerect.height()}")"""
            view.centerOn(1, 1)
            self._zoom = 0

    def load_img(self, filepath: str = ''):
        if filepath == '':
            return

        self.img = QImage(filepath)
        self.pic = QGraphicsPixmapItem()
        self.pic.setPixmap(QPixmap.fromImage(self.img))
        self.scene.clear()
        self.scene.addItem(self.pic)
        # openGLviewport = QOpenGLWidget()
        # self.ui.GRA_view.setViewport(openGLviewport)
        self.ui.GRA_view.setScene(self.scene)
        self.ui.GRA_view.setRenderHints(QPainter.RenderHint.LosslessImageRendering |
                                        QPainter.RenderHint.HighQualityAntialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        # self.ui.GRA_view.setSceneRect(150, 150, 100, 100)
        self.fitInView(self.ui.GRA_view)
        # self.ui.GRA_view.repaint()
        self._zoom = 0

    def set_list_of_picture_paths_of_dir(self) -> (str, list):
        """

        :return:
        TUPLE (str, list) : Erste Zeichenkette enthält Fehlertext, zweite Zeichenkette enthält Liste mit Filenamen
        """

        if self.ui.CMB_art.currentIndex() == -1:
            return "Keine Art gewählt, daher kein Bilderverzeichnis durchsuchbar.", []

        self.ui.BTN_next_img.setEnabled(False)
        self.ui.BTN_prev_img.setEnabled(False)

        bilder_dir = bd.get_BilderPfad()

        self.pic_list = []
        bilder_dir = os.path.join(bilder_dir, self.ui.CMB_art.currentText())
        for dir_path, dir_names, filenames in os.walk(str(bilder_dir)):
            if not dir_path:
                return "Es wurde kein Verzeichnis mit Bildern gefunden.", []
            for each_file in filenames:
                self.pic_list.append(os.path.join(dir_path, each_file))
        if len(self.pic_list) <= 0:
            return f"Keine Bilder für '{self.ui.CMB_art.currentText()}' gefunden.", []
        if bd.get_debug():
            print(self.pic_list)
        return "", self.pic_list

    def get_first_picture_of_dir(self) -> str:
        if len(self.pic_list) > 0:
            if len(self.pic_list) == 1:
                self.ui.BTN_next_img.setEnabled(False)
            else:
                self.ui.BTN_next_img.setEnabled(True)
            return self.pic_list[0]
        else:
            self.pos_in_pic_list = -1
            self.ui.BTN_next_img.setEnabled(False)
            self.ui.BTN_prev_img.setEnabled(False)
            return ""

    def next_pic_clicked(self):
        if len(self.pic_list) > self.pos_in_pic_list + 1:
            self.load_img(self.pic_list[self.pos_in_pic_list + 1])
            self.pos_in_pic_list += 1
            self.ui.BTN_prev_img.setEnabled(True)
        else:
            self.ui.BTN_next_img.setEnabled(False)

    def prev_pic_clicked(self):
        if self.pos_in_pic_list > 0:
            self.load_img(self.pic_list[self.pos_in_pic_list - 1])
            self.pos_in_pic_list -= 1
            self.ui.BTN_next_img.setEnabled(True)
        else:
            self.ui.BTN_prev_img.setEnabled(False)

    def picture_show_clicked(self):
        if self.ui.CMB_art.currentIndex() == -1:
            return
        if self.pic_list:
            filepath = self.pic_list[self.pos_in_pic_list]
            self.img_view = ImageViewer()
            self.img_view.load_file(filepath)
            self.img_view.show()
        else:
            self.ui.BTN_pic.setEnabled(False)

    # ############################################################################################################################
    # KERNFUNKTIONEN (hinzufügen + speichern, edit-finished etc.)
    # ############################################################################################################################

    def save_same_time(self):
        fangart = self.ui.CMB_fangart.currentText()
        if fangart == "e":
            self.save_procedure_raw(fangart)
        elif fangart == "w":
            art_gleich = [True, "", ""]
            # if not self.check_for_needed_entries():
            #     return
            ringnr = self.ui.INP_ringnummer.text()
            if len(ringnr) <= 0:
                ok = self.check_for_needed_entries()
                rberi_lib.QMessageBoxB('ok', 'Fehlende Einträge! Siehe Details.', 'Fehler', ok, qss=bd.get_qss()).exec_()
                return
            if self.ui.TBL_wiederfaenge.rowCount() > 0:
                art_gleich = self.check_same_art(self.ui.CMB_art.currentText(), self.ui.TBL_wiederfaenge.item(0, 0).text())
            if not art_gleich[0]:
                msgb = QMessageBox()
                msgb.setWindowTitle("Artabweichung!")
                msgb.setText("Die Arten weichen voneinander ab. Siehe Details. Wirklich speichern?")
                msgb.setDetailedText("Es wurde als Art eingegeben:    " + art_gleich[1] +
                                     "\n\nArt beim Erstfang gespeichert:  " + art_gleich[2])
                msgb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msgb.setDefaultButton(QMessageBox.No)
                if msgb.exec_() != QMessageBox.Yes:
                    return
            """else:
                catched_this_year = pd.read_sql("SELECT * FROM ESF where ringnummer ='" +
                                                self.ui.INP_ringnummer.text() + "' and " +
                                                "jahr = " + datetime.now().date().strftime("%Y"), engine)
                if catched_this_year.empty:
                    x = rberi_lib.QMessageBoxB("yn", "Fangart wird auf Kontrollfang 'k' geändert. Fortfahren?",
                                               "Wieder-/Kontrollfang",
                                               "Da der Vogel dieses Jahr noch nicht gefangen wurde, ist der korrekte "
                                               "Status 'k' = Kontrollfang.")
                    if x.exec_() != QMessageBox.Yes:
                        return
                    self.ui.CMB_fangart.setCurrentText("k")
                    fangart = 'k'"""
            self.save_procedure_raw(fangart)
        elif fangart == "d":
            ringnr = self.ui.INP_ringnummer.text()
            ring_nr_such = ringnr
            """if len(ringnr) < bd.get_ringnummern_laenge():
                ring_serie = ringnr[:2]
                ring_nr = ringnr[2:]
                if len(ring_nr) == 1:
                    ring_nr_such = ring_serie + "00000" + ring_nr
                elif len(ring_nr) == 2:
                    ring_nr_such = ring_serie + "0000" + ring_nr
                elif len(ring_nr) == 3:
                    ring_nr_such = ring_serie + "000" + ring_nr
                elif len(ring_nr) == 4:
                    ring_nr_such = ring_serie + "00" + ring_nr
                elif len(ring_nr) == 5:
                    ring_nr_such = ring_serie + "0" + ring_nr"""
            df_nr = pd.read_sql("SELECT ringnummer from esf where ringnummer = '" + ring_nr_such + "' OR " +
                                "ringnummer = '" + ringnr + "'", engine)
            if not df_nr.empty:
                # self.fill_wiederfang_liste(self.ui.INP_ringnummer.text())
                msgb = QMessageBox()
                msgb.setWindowTitle("Ring defekt ...")
                msgb.setText("Ringnummer wurde bereits vergeben! Sicher als defekt markieren?")
                msgb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msgb.setDefaultButton(QMessageBox.No)
                if msgb.exec_() != QMessageBox.Yes:
                    return
            else:
                rings, ringn, ringn_int = self.get_ringnr_separated(self.ui.INP_ringnummer.text())
                lastnum = -1
                try:
                    lastnum = ringserienverwaltung.get_last_given_nmb(engine, ringserie=rings)
                    if lastnum == -1:
                        rberi_lib.QMessageBoxB('ok', 'Die letzte vergebene Ringnummer konnte nicht ermittelt werden.'
                                                     'Der Eintrag wird nicht gespeichert.',
                                               'Fehlermeldung', qss=bd.get_qss()).exec_()
                        return
                except Exception as excp:
                    print(f"Exception: {excp}")

                if (ringn_int >= 0) and (lastnum == ringn_int - 1):
                    action = ringserienverwaltung.increment_last_nr(engine, ringserie=rings)
                    if action[0] == -1:
                        rberi_lib.QMessageBoxB('ok', 'Die Ringnummer konnte nicht gespeichert werden.',
                                               'Ringnummernfehler', qss=bd.get_qss()).exec_()
                        return
                elif ringn_int < 0:
                    rberi_lib.QMessageBoxB("ok", "Ringnummer besteht nicht aus 2 alphanumerischen und bis zu 6"
                                                 " numerischen Zeichen. Bitte korrigieren. ", "Ringnummernfehler",
                                           [rings, ringn, ringn_int], qss=bd.get_qss()).exec_()
                    return
                elif lastnum < ringn_int - 1:
                    rberi_lib.QMessageBoxB("ok", f"Die letzte gespeicherte Ringnummer ({lastnum}) der Serie "
                                                 f"({rings}) ist mehr als 1 kleiner als die aktuelle Nummer "
                                                 f"({ringn_int}). Dies kann nicht sein, daher wird der Eintrag nicht "
                                                 f"gespeichert. Bitte die dazwischenliegenden Ringnummern bearbeiten "
                                                 f"bzw. ebenfalls als 'defekt' markieren/speichern.",
                                           "Ringnummernfehler",
                                           ["letzte gespeicherte Nummer der Serie '" + rings + "':",
                                            lastnum, "aktuelle Ringnummer: ", ringn, "aktuelle Ringnummer als Zahl:",
                                            ringn_int], qss=bd.get_qss()).exec_()
                    return

            ok = self.check_for_needed_entries()

            if ok[0] == "ok":
                name = self.ui.CMB_beringer.currentText()
                vorname = name[name.find(",") + 1:].strip()
                nachname = name[:name.find(",")]
                df_ringer = pd.read_sql("SELECT ringer_new from ringer where vorname = '" + vorname +
                                        "' and nachname = '" + nachname + "'", engine)
                ringer = df_ringer.iloc[0, 0]
                cursor = engine.cursor()
                try:
                    cursor.execute("Insert into esf (station, ringnummer, fangart, zentrale, datum, uhrzeit, "
                               "bemerkung, ringer, jahr) Values ('" + self.ui.CMB_station.currentText() + "', '" +
                               ring_nr_such + "', 'd', '" +
                               self.get_zentrale(self.ui.CMB_zentrale.currentText()) + "', '" +
                               self.ui.dateEdit.date().toString(Qt.ISODate) + "', " +
                               str(self.ui.timeEdit.time().hour()) + ", '" +
                               self.ui.PTE_bemerkung.toPlainText() + "', '" + str(ringer) + "', '" + str(date.today().year) +
                                                                                                         "')")
                except Exception as exp:
                    rberi_lib.QMessageBoxB('ok', 'Fehler bei der Anlage des defekten Ringes. Bitte Fehlermeldung anschauen und '
                                                 'ggf. nochmal probieren. Sonst Entwickler kontaktieren.', 'Interner Fehler',
                                           str(exp), qss=bd.get_qss()).exec()
                    cursor.close()
                    return
                engine.commit()
                cursor.close()
                self.clearEingabe()
            else:
                rberi_lib.QMessageBoxB('ok', "Es sind nicht alle notwendigen Daten eingetragen. Siehe Details.",
                                       'Fehlende Eingabe', ok, qss=bd.get_qss()).exec_()
                return
        elif fangart == "k":
            self.save_procedure_raw(fangart)
            return
        elif fangart == "f":
            # self.ui.CMB_fangart.setCurrentText("k")
            self.save_procedure_raw('f')
            self.handle_fremdfang('save')
        else:
            rberi_lib.QMessageBoxB('ok', 'Fehlende Eingaben! Siehe Details!', 'Fehlende Eingaben',
                                   self.check_for_needed_entries(), qss=bd.get_qss()).exec_()

        # if not isinstance(self.stunde, QTime):
        #    self.stunde = QTime.currentTime()

        # self.ui.timeEdit.setTime(self.stunde)

        self.handle_fremdfang('save')  # nur zur Sicherheit, dass die Zentrale wieder gesperrt wird
        self.ui.CMB_art.setFocus()

    def save_procedure_raw(self, fangart: str = 'xxx'):  # SE062459
        """

        :param fangart:
            Ist es ein Fremdfang, muss anders geprüft werden!
        :return:
        """
        check = self.check_for_needed_entries(fangart)
        if check[0] == "ok":
            if fangart == 'f':
                self.ui.CMB_fangart.setCurrentText('k')
                fangart = 'k'

            art = self.ui.CMB_art.currentText()
            df_art = pd.read_sql("SELECT esf_kurz FROM arten WHERE deutsch ='" + art + "'", engine)
            teilfeder = self.ui.INP_teilfeder.text()
            if len(teilfeder) > 0:
                teilfeder = teilfeder.replace(",", ".")
                try:
                    float(teilfeder)
                except ValueError:
                    rberi_lib.QMessageBoxB('ok', 'Teilfeder ist keine Dezimalzahl.', 'Wertfehler', qss=bd.get_qss()).exec_()
                    self.ui.INP_teilfeder.setFocus(True)
                    return
            else:
                teilfeder = "Null"
            fluegel = self.ui.INP_fluegellaenge.text()
            if len(fluegel) > 0:
                fluegel = fluegel.replace(",", ".")
                try:
                    float(fluegel)
                except ValueError:
                    rberi_lib.QMessageBoxB('ok', 'Flügellänge ist keine Dezimalzahl!', 'Wertfehler', qss=bd.get_qss()).exec_()
                    self.ui.INP_fluegellaenge.setFocus(True)
                    return
            else:
                fluegel = "Null"
            masse = self.ui.INP_masse.text()
            if len(masse) > 0:
                masse = masse.replace(",", ".")
                try:
                    float(masse)
                except ValueError:
                    rberi_lib.QMessageBoxB('ok', 'Masse ist keine Dezimalzahl!', 'Wertfehler', qss=bd.get_qss()).exec_()
                    self.ui.INP_masse.setFocus(True)
                    return
            else:
                masse = "Null"

            _kerbe = self.ui.INP_teilfeder_2.text()
            if len(_kerbe) > 0:
                _kerbe = _kerbe.replace(",", ".")
                try:
                    float(_kerbe)
                except ValueError:
                    rberi_lib.QMessageBoxB('ok', 'Kerbe ist keine Dezimalzahl!', 'Wertfehler', qss=bd.get_qss()).exec_()
                    self.ui.INP_teilfeder_2.setFocus(True)
                    return
            else:
                _kerbe = 0

            if ((self.ui.CMB_fangart.currentText() == "e") and
                    (self.ui.INP_ringnummer.text() != self.format_ringnr(str(self.ringnumber_generated)))):
                rberi_lib.QMessageBoxB("ok", "Ringnummer stimmt nicht mit der generierten Ringnummer überein!",
                                       "Eingabefehler", ["Es handelt sich um einen Erstfang. Bei einem "
                                                         "Erstfang wird die Ringnummer automatisch generiert. "
                                                         "Sollten Abweichungen entstanden sein, müssen diese erst "
                                                         "korrigiert werden. Die generierte Nummer "
                                                         "lautet: \n",
                                                         self.format_ringnr(str(self.ringnumber_generated))],
                                       qss=bd.get_qss()).exec_()
                return

            name = self.ui.CMB_beringer.currentText()
            vorname = name[name.find(",") + 1:].strip()
            nachname = name[:name.find(",")]

            try:
                df_ringer = pd.read_sql("SELECT ringer_new from ringer where vorname = '" + vorname +
                                        "' and nachname = '" + nachname + "'", engine)
                ringer = df_ringer['ringer_new'].iloc[0]
            except Exception as err:
                rberi_lib.QMessageBoxB("ok", f"Der Beringer '{nachname}, {vorname}' konnte nicht gefunden werden! Bitte den "
                                             f"Beringer nochmal aus der Dropdownliste auswählen. Falls dies auch nicht "
                                             f"funktioniert, bitte vorerst einen anderen Beringer wählen und beim nächsten "
                                             f"Datensatz erneut probieren. Sollte das Problem weiterhin bestehen, "
                                             f"bitte über das Menu ein Feedback abgeben und den Fehler beschreiben, "
                                             f"vor allem mit dem Namen des Beringers. Dann auch den Fehlertext aus den "
                                             f"Details hineinkopieren. Danke! Siehe "
                                             f"Details.", "Interner Fehler", str(err)).exec_()
                return

            if len(self.ui.CMB_netz.currentText()) == 0:
                netz = ""
            else:
                netz = self.ui.CMB_netz.currentText()
            if len(self.ui.CMB_fach.currentText()) == 0:
                fach = ""
            else:
                fach = self.ui.CMB_fach.currentText()
            if len(self.ui.CMB_fett.currentText()) == 0:
                fett = "Null"
            else:
                fett = self.ui.CMB_fett.currentText()
            if len(self.ui.CMB_muskel.currentText()) == 0:
                muskel = "Null"
            else:
                muskel = self.ui.CMB_muskel.currentText()
            if len(self.ui.CMB_alter.currentText()) == 0:
                alter = ""
            else:
                alter = self.ui.CMB_alter.currentText()
            if len(self.ui.CMB_sex.currentText()) == 0:
                sex = "Null"
            else:
                sex = self.ui.CMB_sex.currentText()
            if len(self.ui.CMB_mauser1.currentText()) == 0:
                m1 = "Null"
            else:
                m1 = self.ui.CMB_mauser1.currentText()
            if len(self.ui.CMB_mauser2.currentText()) == 0:
                m2 = ""
            else:
                m2 = self.ui.CMB_mauser2.currentText()
            if len(self.ui.CMB_mauser3.currentText()) == 0:
                m3 = "Null"
            else:
                m3 = self.ui.CMB_mauser3.currentText()
            if len(self.ui.CMB_verletzungscode.currentText()) == 0:
                verletzung = 'Null'
            else:
                verletzung = self.ui.CMB_verletzungscode.currentText().split(';')[0]

            sql_text = "INSERT INTO esf (station, ringnummer, fangart, zentrale, art, datum, uhrzeit, netz, fach, "
            sql_text += "`alter`, geschlecht, moult1, moult2, moult3, teilfeder, fluegel, gewicht, fett, muskel, "
            sql_text += "bemerkung, ringer, verletzung, tarsus, f9,f7,f6,f5,f4,f3,f2,f1,s1, mauserkarte, beringer2, " \
                        "ex_esf, "
            sql_text += "ex_erbe, ringfund, frei1, frei2, frei3, frei4, dat_erstanlage, zeit_erstanlage, "
            sql_text += "dat_aenderung, zeit_aenderung, jahr, brutfleck) "
            sql_text += "VALUES "
            sql_text += "('" + self.ui.CMB_station.currentText() + "', "

            nmb = self.ui.INP_ringnummer.text()
            new_nmb = nmb
            if (len(nmb) < bd.get_ringnummern_laenge()) and (bd.get_ringnummern_laenge() != 0):
                differenz = bd.get_ringnummern_laenge() - len(nmb)
                new_nmb = nmb[0:2] + differenz * '0' + nmb[2:]
                if bd.get_debug():
                    print(f'Speicherprozess! Alte nummer = "{nmb}"; Neue nummer = "{new_nmb}"')
            new_nmb = new_nmb.upper()
            sql_text += "'" + new_nmb + "', "
            print_txt = new_nmb + "; "
            sql_text += "'" + self.ui.CMB_fangart.currentText() + "', "
            print_txt = print_txt + self.ui.CMB_fangart.currentText() + "; "
            sql_text += "'" + self.get_zentrale(self.ui.CMB_zentrale.currentText()) + "', "
            sql_text += "'" + df_art.iloc[0, 0] + "', "
            print_txt = print_txt + df_art.iloc[0, 0] + "; "
            sql_text += "'" + self.ui.dateEdit.date().toString(Qt.ISODate) + "', "
            sql_text += "" + str(self.ui.timeEdit.time().hour()) + ", "
            print_txt = (print_txt + self.ui.dateEdit.date().toString(Qt.ISODate) + " " + str(self.ui.timeEdit.time().hour()) +
                         ":00; ")
            sql_text += "'" + netz + "', "

            sql_text += "'" + fach + "', "
            sql_text += "'" + alter + "', "
            sql_text += "" + sex + ", "
            sql_text += "" + m1 + ", "
            sql_text += "'" + m2 + "', "
            sql_text += "" + m3 + ", "
            sql_text += "" + teilfeder + ", "
            sql_text += "" + fluegel + ", "
            sql_text += "" + masse + ", "
            sql_text += "" + fett + ", "
            sql_text += "" + muskel + ", "
            sql_text += "'" + self.ui.PTE_bemerkung.toPlainText() + "', "
            sql_text += "'" + ringer + "', "
            sql_text += "" + verletzung + ", "

            # hier wird der Druckstring erzeugt. wenn der Eintrag "Null" ist oder die Länge des Eintrags 0, wird ein - gedruckt
            snippets2print = []
            snippets2print.extend([netz, fach, alter, sex, m1, m2, m3, teilfeder, fluegel, masse, fett, muskel,
                                   self.ui.PTE_bemerkung.toPlainText(), ringer, verletzung])
            for el in snippets2print:
                if el == "Null" or len(el) == 0:
                    print_txt = print_txt + "-;"
                else:
                    print_txt = print_txt + el + ";"

            if self.db2:
                self.db2 = self.make_dict_pretty(self.db2)
                sql_text += self.db2['tarsus'] + ", "
                sql_text += self.db2['hs2'] + ", "
                sql_text += self.db2['hs4'] + ", "
                sql_text += self.db2['hs5'] + ", "
                sql_text += self.db2['hs6'] + ", "
                sql_text += self.db2['hs7'] + ", "
                sql_text += self.db2['hs8'] + ", "
                sql_text += self.db2['hs9'] + ", "
                sql_text += self.db2['hs10'] + ", "
                sql_text += self.db2['as1'] + ", "
                sql_text += str(self.db2['mauserkarte']) + ", "
                sql_text += "'', '', '', (Null), "
                sql_text += self.db2['innenfuss'] + ", "
                sql_text += self.db2['schnabellaenge'] + ", "
                sql_text += self.db2['schnabelbreite'] + ", "
                sql_text += self.db2['kerbe'] + ", "
                sql_text += "(Null), (Null), (Null), (Null), "
                print_txt = (print_txt + "; " + self.db2['tarsus'] + "; " + self.db2['hs2'] + "; " + self.db2['hs4'] + "; " +
                             self.db2['hs5'] + "; " + self.db2['hs6'] + "; " + self.db2['hs7'] + "; " + self.db2['hs8'] + "; "
                             + self.db2['hs9'] + "; " + self.db2['hs10'] + "; " + self.db2['as1'] + "; " + self.db2[
                                 'mauserkarte'] + "; " + self.db2['tarsus'] + "; innenfuss=" + self.db2['innenfuss'] +
                             "; schnabellaenge=" +
                             self.db2['schnabellaenge'] + "; schnabelbreite=" + self.db2['schnabelbreite'] + "; kerbe=" +
                             self.db2['kerbe'])
            else:
                sql_text += "0,0,0,0,0,0,0,0,0,0,0,'','','', (Null), 0,0,0,"
                sql_text += str(_kerbe) + ", (Null), (Null), (Null), (Null), "
                if _kerbe != 0:
                    print_txt = print_txt + "; kerbe=" + str(_kerbe)
            sql_text += str(datetime.today().year) + ", "
            sql_text += "'Y'" if self.ui.CHB_bruffleck.isChecked() else "'N'"
            sql_text += ")"
            if bd.get_debug():
                print(f"{sql_text}")

            if fangart == 'e':
                rings, ringn, ringn_int = self.get_ringnr_separated(self.ui.INP_ringnummer.text())
                lastnum = -1
                ringtyp = ringserienverwaltung.get_ringtypref(engine, self.ui.CMB_art.currentText())
                if ringtyp < 0:
                    rberi_lib.QMessageBoxB('ok', 'Der Ringtyp konnte nicht gefunden werden. Das darf eigentlich nicht sein. '
                                                 'Bitte einen Fehler absetzen (feedback) mit dem detaillierten Text.',
                                           'Interner Fehler',
                                           [f'ringserienverwaltung.get_ringtypref: Fehlercode = {ringtyp}'],
                                           qss=bd.get_qss()).exec_()
                    return
                try:
                    lastnum = ringserienverwaltung.get_last_given_nmb(engine, ringtyp, rings)
                except Exception as err:
                    rberi_lib.QMessageBoxB("ok", "Die letzte vergebene Ringnummer konnte nicht ermittelt werden. Siehe Details.",
                                           "Ringnummernfehler.", [str(err),
                                                                  f'Ringtyp = {ringtyp}, Ringserie = {rings}, lastnum = '
                                                                  f'{lastnum}'], qss=bd.get_qss()).exec_()
                    return

                """try:
                    engine.reset()
                    lastnum = int(pd.read_sql("Select letztevergebenenummer FROM " + bd.get_tbl_name_ringserie() + " " +
                                              "WHERE ringserie = '" + rings + "' AND status = 1",
                                              engine).iat[0, 0])
                    lastnum_df = pd.read_sql("Select letztevergebenenummer FROM " + bd.get_tbl_name_ringserie() + " " +
                                              "WHERE ringserie = '" + rings + "' AND status = 1", engine)
                    print(lastnum)
                except Exception as excp:
                    rberi_lib.QMessageBoxB('ok',
                                           f'rings = {rings}, ringn = {ringn}, ringn_int = {ringn_int}, '
                                           f'lastnum = {lastnum}\n\nBitte Entwickler kontaktieren!',
                                           'Fehler!', f'Exception = {excp}', qss=bd.get_qss()).exec_()
                    return False"""

                if (ringn_int >= 0) and (lastnum == ringn_int - 1):
                    new_nmb, msg_text = ringserienverwaltung.increment_last_nr(engine, ringtypref=ringtyp, ringserie=rings)
                    if new_nmb == -1:
                        rberi_lib.QMessageBoxB('ok', f'{msg_text}', 'Warnung!', qss=bd.get_qss()).exec_()
                        return False
                elif ringn_int < 0:
                    rberi_lib.QMessageBoxB("ok", "Ringnummer besteht nicht aus 2 alphanumerischen und bis zu 6 "
                                                 "numerischen Zeichen. Bitte Konsistenz prüfen! Eintrag wurde NICHT "
                                                 "gespeichert!", "Ringnummernfehler",
                                           [rings, ringn, ringn_int], qss=bd.get_qss()).exec_()
                    return False
                elif lastnum < ringn_int - 1:
                    rberi_lib.QMessageBoxB("ok", "Die letzte gespeicherte Ringnummer der Serie ist mehr als "
                                                 "1 kleiner als die aktuelle Nummer. Falls dies nicht korrekt ist, "
                                                 "bitte mit der Bearbeitung sofort aufhören und die Ringserien pflegen!"
                                                 " [Siehe Details]", "Ringnummernfehler",
                                           ["letzte gespeicherte Nummer der Serie '" + rings + "':",
                                            lastnum, "aktuelle Ringnummer: ", ringn, "aktuelle Ringnummer als Zahl:",
                                            ringn_int], qss=bd.get_qss()).exec_()
                    return False

            try:
                cursor = engine.cursor()
                cursor.execute(sql_text)
                engine.commit()
                cursor.close()
            except Exception as err:
                rberi_lib.QMessageBoxB('ok', 'Datensatz konnte nicht gespeichert werden. Schwerer Ausnahmefehler! Siehe '
                                             'Details!', 'Ausnahmefehler', str(err)).exec_()
                return

            if self.printer is None:
                try:
                    self.printer = Usb(bd.get_drucker_vendor_id(), bd.get_drucker_typ_id(), 0)
                except Exception as err:
                    self.ui.statusbar.showMessage("Drucker nicht gefunden ...", 5000)
            if self.printer is not None:
                if bd.get_debug():
                    print(bd.get_drucker_typ_id())
                    print(bd.get_drucker_vendor_id())
                    print("typ = ", type(bd.get_drucker_typ_id()))

                txt2print = []
                for i in range(0, (len(print_txt) // 82) + 1):
                    if (i + 1) * 82 > len(print_txt):
                        endpos = len(print_txt)
                    else:
                        endpos = (i + 1) * 82
                    txt2print.append(print_txt[i * 82:endpos])

                try:
                    for el in txt2print:
                        self.printer.textln("   " + el)
                except Exception as err:
                    self.ui.statusbar.showMessage("Drucken fehlgeschlagen ... Exception: " + str(err), 10000)
            else:
                self.ui.statusbar.showMessage("Drucker nicht gefunden ... ", 5000)

            self.ringnumber_generated = 0
            self.clearEingabe()
            return True

        else:
            rberi_lib.QMessageBoxB('ok', "Es sind nicht alle notwendigen Daten eingetragen. Siehe Details.",
                                   "Fehlende Eingabe", check, qss=bd.get_qss()).exec_()
            return False

    def ringnumber_edit_finished(self):
        self.ui.INP_ringnummer.editingFinished.disconnect(self.ringnumber_edit_finished)
        curr_rnr = self.ui.INP_ringnummer.text()
        curr_fangart = self.ui.CMB_fangart.currentText()
        if curr_fangart in ['w', 'k']:
            try:
                self.fill_wiederfang_liste(curr_rnr)
            except Exception as excp:
                rberi_lib.QMessageBoxB('ok', f'Die Wiederfangliste zur Ringnummer {curr_rnr} konnte nicht geladen werden.',
                                       'Wiederfanglistenladefehler', str(excp), qss=bd.get_qss()).exec_()
        elif (curr_fangart == "" or isinstance(curr_fangart, type(None))) and len(curr_rnr) > 0:
            self.ui.CMB_fangart.setCurrentText('w')
        self.ui.CMB_netz.setFocus(True)
        self.ui.INP_ringnummer.editingFinished.connect(self.ringnumber_edit_finished)

    def get_edit_status(self):
        return self.edit_status

    def set_edit_status(self, b=True):
        self.edit_status = b

    def fill_wiederfang_liste(self, rnr):
        if len(rnr) <= 2:
            return
        rnr_serie = rnr[:2]
        rnr_nr = 0
        try:
            rnr_nr = int(rnr[2:])
        except ValueError:
            if len(rnr) > 0:
                a = rberi_lib.QMessageBoxB('ok', f"Hinterer Teil der Ringnummer {rnr[2:]} ist nicht numerisch. Sollte es "
                                                 f"sich wirklich um eine korrekte Ringnummer handeln, bitte über Fremdfang "
                                                 f"abhandeln oder die Ringnummer korrigieren.",
                                           "Wertfehler", qss=bd.get_qss()).exec_()
                self.ui.INP_ringnummer.setFocus(True)
                return

        df_wiederfaenge = pd.read_sql("SELECT * from ESF where ringnummer ='" + rnr + "'", engine)

        if df_wiederfaenge.empty:
            rnr_nullen = ""
            if rnr_nr < 100000:
                rnr_nullen = "0"
            elif rnr_nr < 10000:
                rnr_nullen = "00"
            elif rnr_nr < 1000:
                rnr_nullen = "000"
            elif rnr_nr < 100:
                rnr_nullen = "0000"
            elif rnr_nr < 10:
                rnr_nullen = "00000"
            ring_such_text = str(rnr_serie) + rnr_nullen + str(rnr_nr)
            df_wiederfaenge = pd.read_sql("SELECT * from ESF where ringnummer ='" + ring_such_text + "'", engine)

        catched_this_year = df_wiederfaenge.query("jahr == " + datetime.now().date().strftime("%Y"))
        if catched_this_year.empty:
            self.ui.CMB_fangart.setCurrentText("k")

        if not df_wiederfaenge.empty:
            self.ui.TBL_wiederfaenge.setSortingEnabled(False)
            self.ui.TBL_wiederfaenge.setRowCount(df_wiederfaenge.shape[0])
            for i in range(df_wiederfaenge.shape[0]):
                self.ui.TBL_wiederfaenge.setItem(i, 0, QTableWidgetItem(self.df_arten.query("esf_kurz == '" + str(
                    df_wiederfaenge['art'][i]) + "'")['deutsch'].iloc[0]))
                self.ui.TBL_wiederfaenge.setItem(i, 1, QTableWidgetItem(df_wiederfaenge['ringnummer'][i]))
                self.ui.TBL_wiederfaenge.setItem(i, 2, QTableWidgetItem(df_wiederfaenge['fangart'][i]))
                self.ui.TBL_wiederfaenge.setItem(i, 3, QTableWidgetItem(str(df_wiederfaenge['datum'][i])))
                uhrzeit_str = str(df_wiederfaenge['uhrzeit'][i]) + ":00"
                self.ui.TBL_wiederfaenge.setItem(i, 4, QTableWidgetItem(uhrzeit_str))
                self.ui.TBL_wiederfaenge.setItem(i, 5, QTableWidgetItem(df_wiederfaenge['netz'][i]))
                kuerzel = str(df_wiederfaenge['ringer'][i])
                nachname = self.df_ringer.query("ringer_new == '" + kuerzel + "'")['nachname'].iloc[0]
                vorname = self.df_ringer.query("ringer_new == '" + kuerzel + "'")['vorname'].iloc[0]
                name = nachname + ", " + vorname
                # self.ui.TBL_wiederfaenge.setItem(i, 6, QTableWidgetItem(df_wiederfaenge['ringer'][i]))
                self.ui.TBL_wiederfaenge.setItem(i, 6, QTableWidgetItem(name))
                self.ui.TBL_wiederfaenge.setItem(i, 7, QTableWidgetItem(str(df_wiederfaenge['fett'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 8, QTableWidgetItem(str(df_wiederfaenge['muskel'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 9, QTableWidgetItem(str(df_wiederfaenge['alter'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 10, QTableWidgetItem(str(df_wiederfaenge['geschlecht'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 11, QTableWidgetItem(str(df_wiederfaenge['gewicht'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 12, QTableWidgetItem(str(df_wiederfaenge['teilfeder'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 13, QTableWidgetItem(str(df_wiederfaenge['fluegel'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 14, QTableWidgetItem(str(df_wiederfaenge['moult1'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 15, QTableWidgetItem(str(df_wiederfaenge['moult2'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 16, QTableWidgetItem(str(df_wiederfaenge['moult3'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 17, QTableWidgetItem(df_wiederfaenge['bemerkung'][i]))
                self.ui.TBL_wiederfaenge.setItem(i, 18, QTableWidgetItem(str(df_wiederfaenge['frei1'][i])))
                self.ui.TBL_wiederfaenge.setItem(i, 19, QTableWidgetItem(str(df_wiederfaenge['frei4'][i])))
                self.ui.TBL_wiederfaenge.setRowHeight(i, 7)
            self.ui.TBL_wiederfaenge.setSortingEnabled(True)
        else:
            rberi_lib.QMessageBoxB('ok', 'Es konnte kein Ring in der Datenbank gefunden werden. Handelt es sich ggf. um einen '
                                         'Fremdfang? Dann bitte über "f" bei Fangart das Fremdfanghandling initiieren.',
                                   'Kein Eintrag', qss=bd.get_qss()).exec_()

    def set_save_allowed(self, flag=False):
        self.save_allowed = flag

    def update_ringnumber(self) -> bool:
        """
        Zuerst wird geschaut, ob es einen Unterschied zwischen weiblichen und männlichen Vögeln gibt,
        was den benötigten Ringtyp angeht. Dann wird der entsprechende nächste Ring über das Modul ringserienverwaltung
        geholt. Weiter wird der Abstand zur Schnur/Paketende ermittelt und ggf eine entsprechende Warnung ausgegeben.
        Wurde die nächste zu vergebende Ringnummer korrekt ermittelt, wird diese in das Eingabefeld für die Ringnummer
        eingetragen sowie die interne Variable self.ringnumber_generated damit befüllt.
        :return:
        True : wenn alles nach Plan läuft\n
        False : bei Fehler
        """
        if self.ui.CMB_art.currentIndex() < 0:
            return False
        art_d = self.ui.CMB_art.currentText()

        ringtyp_df = pd.read_sql("SELECT ringtypMaleRef, ringtypFemaleRef from arten where deutsch = '" + art_d + "'",
                                 engine)
        ringtyp_m = int(ringtyp_df['ringtypMaleRef'].iloc[0])
        ringtyp_f = 'None'
        try:
            if not isinstance(ringtyp_df['ringtypFemaleRef'].iloc[0], type(None)):
                ringtyp_f = int(ringtyp_df['ringtypFemaleRef'].iloc[0])
            else:
                ringtyp_f = 'None'
        except TypeError as err:
            rberi_lib.QMessageBoxB('ok', 'Es konnte keine Ringserie für einen weiblichen Vogel gefunden werden.',
                                   'Ringnummernfehler', str(err), qss=bd.get_qss()).exec_()
            return False

        if ringtyp_f != 'None':
            answer = rberi_lib.QMessageBoxB('cyn',
                                            'Bei der Art "' + art_d + '" haben Weibchen andere Ringgrößen als '
                                                                      'Männchen. Handelt es sich um ein Weibchen?',
                                            'Geschlecht definieren ...', 'In diesem Fall wird zwingend '
                                                                         'das Geschlecht benötigt. Die Unterscheidung '
                                                                         'liegt unter anderem '
                                                                         'in der Größe, so dass die Flügellänge '
                                                                         'und/oder die Teilfederlänge '
                                                                         'vermutlich zur Abgrenzung ausreicht. Bitte '
                                                                         'bestimme zuerst das '
                                                                         'Geschlecht bevor es weitergeht...',
                                            qss=bd.get_qss()).exec_()
            if answer == QMessageBox.Yes:
                next_nmb, diff_to_end, ringserie = ringserienverwaltung.get_next_nr(engine, ringtyp_f)
                ringtyp = ringtyp_f
            elif answer == QMessageBox.No:
                next_nmb, diff_to_end, ringserie = ringserienverwaltung.get_next_nr(engine, ringtyp_m)
                ringtyp = ringtyp_m
            else:
                return False
        else:
            next_nmb, diff_to_end, ringserie = ringserienverwaltung.get_next_nr(engine, ringtyp_m)
            ringtyp = ringtyp_m

        if next_nmb < 0 or diff_to_end < 0:
            rberi_lib.QMessageBoxB('ok', 'Es trat ein Fehler auf. Bitte Stationsleitung informieren. Siehe Details.',
                                   'Ringnummernfehler', ringserie, qss=bd.get_qss()).exec_()
            return False

        self.ui.INP_ringnummer.setText(str(ringserie) + str(next_nmb))
        self.ringnumber_generated = str(ringserie) + str(next_nmb)

        if diff_to_end == self.get_warnung_paketende():
            next_package_nmb, next_package_infos = ringserienverwaltung.get_next_paket_infos(engine, ringtyp)
            rberi_lib.QMessageBoxB('ok', f'Noch {diff_to_end} Ringe bis zum Paketende. Nächste Paketnummer '
                                         f'ist die {next_package_nmb} mit den Ringnummern {next_package_infos[1]} '
                                         f'{next_package_infos[2]}-{next_package_infos[3]}.',
                                   'Warnung Schnur-Ende', qss=bd.get_qss()).exec_()
        if diff_to_end == 1:
            next_package_nmb, next_package_infos = ringserienverwaltung.get_next_paket_infos(engine, ringtyp)
            rberi_lib.QMessageBoxB('ok', f'Letzter Ring der Schnur verbraucht!! Nächste '
                                         f'Paketnummer '
                                         f'ist die {next_package_nmb} mit den Ringnummern {next_package_infos[1]} '
                                         f'{next_package_infos[2]}-{next_package_infos[3]}.',
                                   'Warnung Schnur-Ende', qss=bd.get_qss()).exec_()
        return True

    def get_warnung_paketende(self) -> int:
        """

        :return:
        int : Konstante/Benutzerparameter, bei welchem Abstand zum Paketende gewarnt werden soll.\n
              -1 bei Fehler
        """
        try:
            print(f"self.get_current_user = {self.get_current_user()}")
            df_paketende = pd.read_sql("SELECT warnung_paketende FROM benutzer WHERE username = '" +
                                       self.get_current_user() + "'", engine)
            value_paketende = df_paketende['warnung_paketende'].iloc[0]
            value_paketende = int(value_paketende)
            return value_paketende
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Warnung für Abstand zum Paketende konnte nicht ermittelt werden.',
                                   'Fehler!', str(excp), qss=bd.get_qss()).exec_()
            return -1

    def art_text_changed(self, t):
        if self.ui.CHB_schnellauswahl.isChecked():
            if t in ['te', 'Te', 'TE']:
                self.ui.CMB_art.setCurrentText('Teichrohrsänger')
                self.ui.CMB_fangart.setFocus(True)
            if t in ['su', 'Su', 'SU']:
                self.ui.CMB_art.setCurrentText('Sumpfrohrsänger')
                self.ui.CMB_fangart.setFocus(True)
            if t in ['zi', 'Zi', 'ZI']:
                self.ui.CMB_art.setCurrentText('Zilpzalp')
                self.ui.CMB_fangart.setFocus(True)
            if t in ['fi', 'Fi', 'FI']:
                self.ui.CMB_art.setCurrentText('Fitis')
                self.ui.CMB_fangart.setFocus(True)
            if t in ['Bl', 'bl', 'BL']:
                self.ui.CMB_art.setCurrentText('Blaumeise')
                self.ui.CMB_fangart.setFocus(True)
            if t in ['Ko', 'ko', 'KO']:
                self.ui.CMB_art.setCurrentText('Kohlmeise')
                self.ui.CMB_fangart.setFocus(True)

    def art_index_changed(self) -> None:
        """
        Sobald der Index der Art Auswahl Kombobox sich geändert hat (wenn also eine Art eingetragen wurde und die
        Kombobox verlassen wurde), soll geschaut werden ob ein Bild angezeigt werden kann ...
        :return:
        """
        if self.ui.CMB_art.currentIndex() >= 0:
            self.pos_in_pic_list = 0  # FALLS Dateien im Ordner existieren, fangen wir wieder bei Pos. 0 an.

            art_deutsch = self.ui.CMB_art.currentText()
            art_df_row = self.df_arten.query("deutsch == '" + art_deutsch + "'")
            art_lat = art_df_row.at[art_df_row.index[0], 'lateinisch']
            art_eng = art_df_row.at[art_df_row.index[0], 'englisch']

            self.ui.LBL_vogelnamen.setText(art_lat + ", " + art_eng)
            self.ui.LBL_vogelnamen.setStyleSheet("font: 10pt; font-style: italic;")
            fehlertext, list_of_pics = self.set_list_of_picture_paths_of_dir()

            if len(fehlertext) > 0:
                self.ui.statusbar.showMessage(fehlertext, 10000)
                self.ui.BTN_pic.setEnabled(False)
                self.scene.clear()
            else:
                self.ui.statusbar.showMessage(f"Anzahl Bilder: {len(list_of_pics)}", 5000)
                self.ui.BTN_pic.setEnabled(True)
                self.load_img(self.get_first_picture_of_dir())

            if len(self.ui.INP_ringnummer.text()) > 0 and self.ui.CMB_fangart.currentText() == "e":
                self.ui.INP_ringnummer.setText("")
                self.ui.CMB_fangart.setCurrentIndex(-1)
                self.ui.CMB_fangart.setCurrentIndex(self.ui.CMB_fangart.findText("e"))
        else:
            self.ui.LBL_vogelnamen.setText("")
            self.ui.BTN_pic.setEnabled(False)
            self.scene.clear()

    def fangart_changed(self):
        fangart = self.ui.CMB_fangart.currentText()
        self.ui.INP_ringnummer.setEnabled(True)
        if fangart == 'e':
            self.update_ringnumber()
            # self.ui.INP_ringnummer.setFocus(True)
            self.ui.INP_ringnummer.setStyleSheet("color: lightgrey;")
            self.ui.INP_ringnummer.setEnabled(False)
            return
        elif fangart == 'w':
            self.ui.INP_ringnummer.clear()
        elif fangart == 'k':
            pass
            # self.ui.INP_ringnummer.clear()
        elif fangart == 'd':
            self.ui.INP_ringnummer.clear()
        elif fangart == 'f':
            self.ui.INP_ringnummer.clear()
            self.handle_fremdfang('fangart')

    def zentrale_changed(self):
        if self.ui.CMB_fangart.currentText() == 'f':
            self.ui.INP_ringnummer.setFocus(True)

    def handle_fremdfang(self, aufruf_von: str = 'fangart'):
        """
        1) die Zentrale muss freigegeben werden und Infofenster, dass nun die Zentrale geändert werden kann +
            Info, dass wenn keine Zentrale gefunden wird, KEINE eingetragen wird.
        2) beim Speichern muss die Zentrale dann wieder zurückgesetzt werden auf die Standardzentrale laut Einstellungen

        :return:
        """
        if aufruf_von == 'fangart':
            self.ui.CMB_zentrale.setEnabled(True)
            rberi_lib.QMessageBoxB('ok', 'Für einen Fremdfang bitte die Zentrale änden. Sollte '
                                         'sich kein passender Eintrag finden, bitte Element "UNBEKANNT" wählen. '
                                         'Danach mit der Bearbeitung wie gewohnt fortfahren.',
                                   'Beringungszentrale ändern ...', qss=bd.get_qss()).exec_()
            self.ui.CMB_zentrale.setFocus(True)
            self.ui.CMB_zentrale.showPopup()
        elif aufruf_von == 'save':
            self.set_zentrale()
            self.ui.CMB_zentrale.setEnabled(False)

    def ringer_not_found(self):
        self.ui.actionBeringer.trigger()

    def beringer_aus_liste(self, wi):
        if bd.get_debug():
            print(self.ui.CMB_beringer.count())
            print(f"wi = {wi.text()}")
        for i in range(self.ui.CMB_beringer.count()):
            if bd.get_debug():
                print(f"CMB_beringer.itemText({i}) = {self.ui.CMB_beringer.itemText(i)}")
            if self.ui.CMB_beringer.itemText(i) == wi.text():
                self.ui.CMB_beringer.setCurrentIndex(i)
        self.ui.CMB_beringer.setCurrentText(wi.text())

    def beringer_changed(self):
        cur_ringer = self.ui.CMB_beringer.currentText()
        if len(cur_ringer) < 2:
            return
        for i in range(0, self.ui.LST_letzte_beringer.count()):
            if cur_ringer == self.ui.LST_letzte_beringer.item(i).text():
                return
        if self.ui.LST_letzte_beringer.count() > 4:
            for i in range(4, 0, -1):
                if bd.get_debug():
                    print(i)
                self.ui.LST_letzte_beringer.item(i).setText(self.ui.LST_letzte_beringer.item(i - 1).text())
                if bd.get_debug():
                    print("item(i) = " + self.ui.LST_letzte_beringer.item(i).text())
                # self.ui.LST_letzte_beringer.item(0).setText(cur_ringer)
            self.ui.LST_letzte_beringer.item(0).setText(cur_ringer)
        elif self.ui.LST_letzte_beringer.count() == 0:
            self.ui.LST_letzte_beringer.addItem(cur_ringer)
        else:
            self.ui.LST_letzte_beringer.addItem(
                self.ui.LST_letzte_beringer.item(self.ui.LST_letzte_beringer.count() - 1).text())
            for i in range(self.ui.LST_letzte_beringer.count() - 2, 0, -1):
                self.ui.LST_letzte_beringer.item(i).setText(self.ui.LST_letzte_beringer.item(i - 1).text())
            self.ui.LST_letzte_beringer.item(0).setText(cur_ringer)
        self.ui.CMB_fett.setFocus(True)

    def check_for_needed_entries(self, fangart: str = 'xxx'):
        """

        :param fangart:
            Wenn die fangart "f" für Fremdfang ist, muss die Ringserie nicht geprüft werden.
        :return:
        """
        missing_values = []
        self.save_allowed = False
        if (self.ui.CMB_art.currentIndex() < 0) and (self.ui.CMB_fangart.currentText() != "d"):
            missing_values.append("Art darf nicht leer sein.")
        if self.ui.CMB_beringer.currentIndex() < 0:
            missing_values.append("Beringer darf nicht leer sein.")
        ring_nr = self.ui.INP_ringnummer.text()
        self.ui.INP_ringnummer.setText(self.format_ringnr(ring_nr))
        ringserie = self.ui.INP_ringnummer.text()[:2]
        # ringnr = self.ui.INP_ringnummer.text()[2:]
        df_serie = pd.read_sql("SELECT ringserie from ringserie where ringserie = '" + ringserie + "'", engine)
        if fangart != "f":
            if len(df_serie) == 0:
                missing_values.append("Ringserie unbekannt.")
            # if len(ringnr) != 6:
            #    missing_values.append("Ringnummer muss aus sechs Ziffern bestehen.")

        if not self.check_oot():
            missing_values.append("Toleranzfehler nicht bestätigt.")

        if len(missing_values) == 0:
            missing_values.append("ok")
        return missing_values

    def format_ringnr(self, rn=""):
        """
        Auskommentiert wurde die Anpassung der Ringnummer auf die festgelegte Ringnummernlänge. Bisher wurde die
        Ringnummer immer auf 8 Stellen mit = aufgefüllt, auch wenn die fortlaufende Nummer nur 4 Stellen hatte.
        Beispiel: steht auf der Ringnummer VA4005 (6 Zeichen) wurde in der Datenbank die Ringnummer auf VA004005
        (8 Zeichen) erweitert. Diese 8 Zeichen sind in der Datei hinterlegt, in der die Standards definiert sind:
        basic_definitions.py

        :param rn: Ringnummer als String
        :return: -
        """
        if self:
            pass
        ring_nr_such = rn
        """if len(str(rn)) < bd.get_ringnummern_laenge():
            ring_serie = rn[:2]
            ring_nr = rn[2:]
            if len(ring_nr) == 1:
                ring_nr_such = ring_serie + "00000" + ring_nr
            elif len(ring_nr) == 2:
                ring_nr_such = ring_serie + "0000" + ring_nr
            elif len(ring_nr) == 3:
                ring_nr_such = ring_serie + "000" + ring_nr
            elif len(ring_nr) == 4:
                ring_nr_such = ring_serie + "00" + ring_nr
            elif len(ring_nr) == 5:
                ring_nr_such = ring_serie + "0" + ring_nr
        else:
            ring_nr_such = rn"""
        return ring_nr_such

    def get_zentrale(self, name="Vogelwarte Helgoland"):
        if self:
            pass
        df_zentrale = pd.read_sql("SELECT Name, ZentraleKuerzel from zentralen", engine)
        kuerzel = df_zentrale[df_zentrale["Name"] == name]["ZentraleKuerzel"].values[0]
        if kuerzel and (kuerzel != ""):
            return kuerzel
        else:
            return "Fehler"
        # string3 = df3[df3["name"]=="Amsel"]["eng"].values[0]

    def set_zentrale(self) -> bool:
        """
            Setzt die Zentrale im Eingabefenster auf den Standardwert laut defaults/Einstellungen. \n
        :return:
            True: es hat alles geklappt \n
            False: etwas hat nicht geklappt \n
        """
        zentrale_id = self.get_defaults()['Zentrale'].iloc[0]

        try:
            df_zentrale = pd.read_sql(
                "SELECT Name, ZentraleKuerzel from zentralen WHERE zentraleID = " + str(zentrale_id),
                engine)
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Zentrale konnte nicht gesetzt werden.', "Fehler",
                                   f"Exception: {excp}", qss=bd.get_qss()).exec_()
            return False
        self.ui.CMB_zentrale.setCurrentText(str(df_zentrale['Name'].iloc[0]))

    def get_ringnr_separated(self, rnr) -> (str, str, int):
        if self:
            pass
        if len(rnr) > 0:
            rings = rnr[:2]
            ringn = rnr[2:]
            ringn_int = -1
            try:
                ringn_int = int(ringn)
            except ValueError as excp:
                rberi_lib.QMessageBoxB('ok', "'" + ringn + "' ist keine Ganzzahl.", "Fehler", str(excp))
            return str(rings), str(ringn), ringn_int
        else:
            return '', '', -1

    def check_age(self):
        age = self.ui.CMB_alter.currentText()
        if age in ['1', '3']:
            self.ui.CMB_mauser2.setEnabled(True)
        else:
            self.ui.CMB_mauser2.setCurrentIndex(-1)
            self.ui.CMB_mauser2.setEnabled(False)

        fangart = self.ui.CMB_fangart.currentText()
        if fangart == 'e':
            if age in ['', '0', '1', '2', '3', '4', 0, 1, 2, 3, 4]:
                self.ui.CMB_sex.setFocus(True)
                return
            elif age in ['5', 5]:
                a = rberi_lib.QMessageBoxB('yn', 'Die Altersbestimmung "5" = 2. KJ (also im vorigen Jahr geboren) ist '
                                                 'nur in '
                                                 'begrenztem Zeitraum möglich: machen die Vorjährigen (also 2. KJ) nur eine '
                                                 'Jugendteilmauser in ihrem ersten Sommer durch, so bleiben die Mausergrenzen '
                                                 'stehen, bis sie im darauffolgenden Sommer (also "jetzt") eine erste adulte '
                                                 'Vollmauser machen. Fängt man sie vor der Vollmauser, ist 5 = 2. KJ '
                                                 'anhand der Mausergrenzen und den abgenutztem Großgefieder bestimmbar.\n\n'
                                                 'Soll das Alter 5 wirklich eingestellt werden?', 'Altersbestimmung',
                                           qss=bd.get_qss()).exec_()
                if a == QMessageBox.No:
                    self.ui.CMB_alter.setCurrentIndex(-1)
                    self.ui.CMB_alter.setFocus(True)
                    return
            else:
                a = rberi_lib.QMessageBoxB('yn', 'Die Alterbestimmung anhand des Gefieders für Individuen älter als 2. KJ, '
                                                 'also ab Code 6 aufwärts, ist nur bei einigen sehr wenigen Arten sicher '
                                                 'möglich. Bei den meisten Singvögeln und bei allem Vögeln im MRI-Programm ist '
                                                 'diese Altersbestimmung nicht anhand des Gefieders möglich. Daher wird '
                                                 'dringend empfohlen, das Alter auf 4 zu setzen. Alter ändern?',
                                           'Altersbestimmung', qss=bd.get_qss()).exec_()
                if a == QMessageBox.Yes:
                    self.ui.CMB_alter.setCurrentText('4')
                    self.ui.CMB_sex.setFocus(True)
                    return
        elif self.ui.CMB_fangart.currentText() in ['w', 'k']:
            if age in ['0', '1', '2', '3', '4', 0, 1, 2, 3, 4]:
                self.ui.CMB_sex.setFocus(True)
                return
            try:
                erstfang = pd.read_sql("SELECT * FROM esf WHERE ringnummer = '" + self.ui.INP_ringnummer.text() + "' AND "
                                                                                                                  "fangart = 'e'",
                                       engine)
                if erstfang.empty:
                    rberi_lib.QMessageBoxB('ok', 'Kein Erstfang zu dieser Ringnummer gefunden. ', 'Ringnummernfehler',
                                           qss=bd.get_qss()).exec_()
                    return
            except Exception as excp:
                rberi_lib.QMessageBoxB('ok', 'Datenbankfehler! Bitte neu starten/verbinden.', 'Datenbankfehler',
                                       str(excp), qss=bd.get_qss()).exec_()
                return
            alter_e = erstfang['alter'].iloc[0]
            jahr_e = erstfang['datum'].iloc[0].year
            jahr_w = date.today().year
            matrix_erstfang_juv = {
                0: '3',
                1: '5',
                2: '7',
                3: '9',
                4: 'B',
                5: 'D',
                6: 'F',
                7: 'H',
            }
            matrix_erstfang_ad_4 = {
                0: '4',
                1: '6',
                2: '8',
                3: 'A',
                4: 'C',
                5: 'E',
                6: 'G',
            }
            matrix_erstfang_ad_5 = {
                0: '5',
                1: '7',
                2: '9',
                3: 'B',
                4: 'D',
                5: 'F',
                6: 'H',
            }
            matrix_erstfang_ad_6 = {
                0: '6',
                1: '8',
                2: 'A',
                3: 'C',
                4: 'E',
                5: 'G',
            }
            matrix_erstfang_ad_7 = {
                0: '7',
                1: '9',
                2: 'B',
                3: 'D',
                4: 'F',
                5: 'H',
            }
            matrix_erstfang_ad_8 = {
                0: '8',
                1: 'A',
                2: 'C',
                3: 'E',
                4: 'G',
            }
            matrix_erstfang_ad_9 = {
                0: '9',
                1: 'B',
                2: 'D',
                3: 'F',
                4: 'H',
            }
            matrix_erstfang_ad_A = {
                0: 'A',
                1: 'C',
                2: 'E',
                3: 'G',
            }
            matrix_erstfang_ad_B = {
                0: 'B',
                1: 'D',
                2: 'F',
                3: 'H',
            }
            matrix_erstfang_ad_C = {
                0: 'C',
                1: 'E',
                2: 'G',
            }
            matrix_erstfang_ad_D = {
                0: 'D',
                1: 'F',
                2: 'H',
            }
            matrix_erstfang_ad_E = {
                0: 'E',
                1: 'G',
            }
            matrix_erstfang_ad_F = {
                0: 'F',
                1: 'H',
            }
            matrix_erstfang_ad_G = {
                0: 'G'
            }
            matrix_erstfang_ad_H = {
                0: 'H'
            }
            year_diff = int(jahr_w - jahr_e)
            if alter_e in [1, 3, '1', '3']:
                if year_diff in matrix_erstfang_juv.keys():
                    correct_age = matrix_erstfang_juv[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in [4, '4']:
                if year_diff in matrix_erstfang_ad_4.keys():
                    correct_age = matrix_erstfang_ad_4[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in [5, '5']:
                if year_diff in matrix_erstfang_ad_5.keys():
                    correct_age = matrix_erstfang_ad_5[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in [6, '6']:
                if year_diff in matrix_erstfang_ad_6.keys():
                    correct_age = matrix_erstfang_ad_6[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in [7, '7']:
                if year_diff in matrix_erstfang_ad_7.keys():
                    correct_age = matrix_erstfang_ad_7[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in [8, '8']:
                if year_diff in matrix_erstfang_ad_8.keys():
                    correct_age = matrix_erstfang_ad_8[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in [9, '9']:
                if year_diff in matrix_erstfang_ad_9.keys():
                    correct_age = matrix_erstfang_ad_9[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in ['A']:
                if year_diff in matrix_erstfang_ad_A.keys():
                    correct_age = matrix_erstfang_ad_A[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in ['B']:
                if year_diff in matrix_erstfang_ad_B.keys():
                    correct_age = matrix_erstfang_ad_B[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in ['C']:
                if year_diff in matrix_erstfang_ad_C.keys():
                    correct_age = matrix_erstfang_ad_C[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in ['D']:
                if year_diff in matrix_erstfang_ad_D.keys():
                    correct_age = matrix_erstfang_ad_D[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in ['E']:
                if year_diff in matrix_erstfang_ad_E.keys():
                    correct_age = matrix_erstfang_ad_E[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in ['F']:
                if year_diff in matrix_erstfang_ad_F.keys():
                    correct_age = matrix_erstfang_ad_F[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in ['G']:
                if year_diff in matrix_erstfang_ad_G.keys():
                    correct_age = matrix_erstfang_ad_G[year_diff]
                else:
                    correct_age = '4'
            elif alter_e in ['G']:
                if year_diff in matrix_erstfang_ad_H.keys():
                    correct_age = matrix_erstfang_ad_H[year_diff]
                else:
                    correct_age = '4'
            else:
                correct_age = '2'

            change_of_age_allowed = bd.get_age_adult_allowed()
            if not change_of_age_allowed:
                rberi_lib.QMessageBoxB('ok',
                                       f'Die Altersbestimmung anhand des Gefieders jenseits des 2. KJ ist nahezu unmöglich. Um '
                                       f'viele'
                                       f'Fehleingaben zu vermeiden, hat man sich entschlossen, nur 4 und in begründeten '
                                       f'Ausnahmefällen 5 als Alter zuzulassen. Das korrekte Alter aufgrund des Wiederfangs wäre '
                                       f'"{correct_age}" gewesen. Sei ehrlich, wäre es korrekt gewesen? ',
                                       'Altersbestimmung', qss=bd.get_qss()).exec_()
                self.ui.CMB_alter.setCurrentText('4')
                self.ui.CMB_sex.setFocus(True)
                return
            else:
                if correct_age == self.ui.CMB_alter.currentText():
                    self.ui.CMB_sex.setFocus(True)
                    return
                a = rberi_lib.QMessageBoxB('yn',
                                           f'Das korrekte Alter aufgrund des Erstfangdatums  wäre '
                                           f'"{correct_age}". Soll das Alter geändert werden?',
                                           'Altersbestimmung Wiederfang', qss=bd.get_qss()).exec_()
                if a == QMessageBox.Yes:
                    self.ui.CMB_alter.setCurrentText(correct_age)
                    self.ui.CMB_sex.setFocus(True)

    def new_dataset(self):
        if self.get_edit_status():
            rberi_lib.QMessageBoxB('ok', "Aktuell wird ein Datensatz bearbeitet. Speichere diesen oder beende die "
                                         "Bearbeitung.", "Eingabe verwerfen?", qss=bd.get_qss()).exec_()
            return

        self.ui.CMB_art.setEnabled(True)
        self.ui.CMB_fangart.setCurrentIndex(-1)
        self.ui.CMB_art.setFocus()
        self.ui.INP_ringnummer.setEnabled(True)
        self.ui.CMB_fangart.setEnabled(True)
        self.ui.timeEdit.setTime(QTime.currentTime())
        self.stunde = QTime.currentTime()
        self.handle_fremdfang('save')
        self.set_edit_status(False)

    def edit_beenden(self):
        """print_font = {
            "height": 8,
        }
        # with Printer(printer_name='OKI DATA CORP ML6300FB-SC', linegap=0, auto_page=False) as printer:
        with Printer(printer_name='OKI ML6300FB-SC K1', linegap=0) as printer:
            printer.text("          Line1 Das ist ein Test!", font_config=print_font)
            printer.text("          Line2 ... besser?", font_config=print_font)

        printers = win32print.EnumPrinters(2, None, 2)
        print_name = 'None'
        for p in printers:
            if "OKI" in p['pPrinterName']:
                print_name = p['pPrinterName']

        if print_name != 'None':
            printHANDLE = win32print.OpenPrinter(print_name)

        raw_data = bytes("          This is a test", "utf-8")

        try:
            pJOB = win32print.StartDocPrinter(printHANDLE, 1, ("test of raw data", None, "RAW"))
            try:
                win32print.StartPagePrinter(printHANDLE)
                win32print.WritePrinter(printHANDLE, raw_data)
                win32print.EndPagePrinter(printHANDLE)
            finally:
                win32print.EndDocPrinter(printHANDLE)
        finally:
            win32print.ClosePrinter(printHANDLE)"""

        if (self.get_edit_status()) and (self.ui.CMB_art.currentIndex() != -1 or self.ui.INP_ringnummer.text() != ""):
            msgb = QMessageBox()
            msgb.setWindowTitle("Achtung ... ")
            msgb.setText("Es wird gerade ein Datensatz bearbeitet. Bearbeitung wirklich abbrechen?")
            msgb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgb.setDefaultButton(QMessageBox.No)
            if msgb.exec_() != QMessageBox.Yes:
                return
        self.clearEingabe('bearbeiten_beenden')
        self.handle_fremdfang('save')

    def schliessen(self):
        if (self.get_edit_status()) and (self.ui.CMB_art.currentIndex() != -1 or self.ui.INP_ringnummer.text() != ""):
            msgb = QMessageBox()
            msgb.setWindowTitle("Achtung ... ")
            msgb.setText("Es wird gerade ein Datensatz bearbeitet. Wirklich schließen?")
            msgb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgb.setDefaultButton(QMessageBox.No)
            if msgb.exec_() != QMessageBox.Yes:
                return
        self.clearEingabe('schliessen')
        self.handle_fremdfang('save')

    def clearEingabe(self, umfang=''):
        self.ui.CMB_art.setCurrentIndex(-1)
        self.ui.CMB_fangart.setCurrentIndex(-1)
        self.ui.CMB_netz.setCurrentIndex(-1)
        self.ui.CMB_fach.setCurrentIndex(-1)
        self.ui.CMB_fett.setCurrentIndex(-1)
        self.ui.CMB_muskel.setCurrentIndex(-1)
        self.ui.CMB_alter.setCurrentIndex(-1)
        self.ui.CMB_sex.setCurrentIndex(-1)
        self.ui.CMB_mauser1.setCurrentIndex(-1)
        self.ui.CMB_mauser2.setCurrentIndex(-1)
        self.ui.CMB_mauser3.setCurrentIndex(-1)
        self.ui.INP_fluegellaenge.setText("")
        self.ui.INP_masse.setText("")
        self.ui.INP_teilfeder_2.setText("")
        self.ui.INP_ringnummer.setText("")
        self.ui.INP_teilfeder.setText("")
        self.ui.INP_innenfuss.setText("")
        self.ui.PTE_bemerkung.clear()
        self.ui.CHB_bruffleck.setChecked(False)
        # self.ui.PTE_bemerkung.setEnabled(False)
        self.ui.TBL_wiederfaenge.setRowCount(0)
        # self.ui.LBL_bild.clear()
        self.scene.clear()
        self.ui.CMB_verletzungscode.setCurrentIndex(-1)
        self.db2 = {}
        self.oot = {}
        self.verhaeltnis_aufgerufen = False
        self.teilfeder = -1
        self.set_edit_status(False)

        self.ui.CMB_art.setFocus()
        self.stunde = QTime.currentTime()
        self.set_save_allowed(False)

        if umfang == 'schliessen':
            self.ui.CMB_beringer.setCurrentIndex(-1)
            # self.ui.LST_letzte_beringer.clear()
            self.ui.CMB_station.setCurrentIndex(-1)
            self.ui.CMB_zentrale.setCurrentIndex(-1)
            self.ui.CMB_art.setEnabled(False)
            self.ui.INP_ringnummer.setEnabled(False)
            self.ui.actionHinzufuegen.setEnabled(True)
            self.set_edit_status(False)
            self.ui.widgetEingabe.setVisible(False)
        elif umfang == 'bearbeiten_beenden':
            # Hier soll die letzten eingegebene Art gezeigt werden...

            self.ui.CMB_art.setEnabled(False)
            self.ui.INP_ringnummer.setEnabled(False)
            self.ui.CMB_fangart.setEnabled(False)
            self.set_edit_status(False)
            self.ui.BTN_neuer_datensatz.setFocus(True)

    def get_defaults(self) -> pd.DataFrame:
        """

        :return:
        Panda DataFrame.
            Spalte 1: Station (ID) - als Fremdschlüssel, Verweis auf stationen.stationenID
            Spalte 2: Zentrale (ID) - als Fremdschlüssel, Verweis auf zentralen.zentraleID
            Spalte 3: Bilderverzeichnis (string)
            Spalte 4: ringer_in_tab - Soll der Beringer in der TAB-Reihenfolge berücksichtigt werden (also nach Netzfach Fokus
                        erhalten, oder eben nicht)
        """
        if self:
            pass
        if get_connection_status(engine):
            return pd.read_sql("SELECT * FROM defaults", engine)

    def changed(self, txt: str):
        if bd.get_debug():
            print(self.ui.CMB_fach.currentText())
            print(self.ui.CMB_fach.currentIndex())
        if len(txt) < 2:
            return
        if self.ui.CMB_netz.findText(txt) >= 0 and self.ui.CMB_netz.hasFocus():
            self.ui.CMB_fach.setFocus()
            return
        elif self.ui.CMB_netz.findText(txt) < 0 and self.ui.CMB_netz.hasFocus():
            # self.ui.CMB_netz.lineEdit().selectAll()
            self.ui.CMB_netz.lineEdit().clear()
            return
        else:
            if self.ui.CMB_fach.hasFocus():
                if self.ui.CMB_fach.findText(txt) >= 0:
                    if self.beringer_in_tab:
                        self.ui.CMB_beringer.setFocus()
                    else:
                        self.ui.CMB_fett.setFocus()
                else:
                    txt = txt.upper()
                    if self.ui.CMB_fach.findText(txt) >= 0:
                        self.ui.CMB_fach.setCurrentText(txt)
                        if self.beringer_in_tab:
                            self.ui.CMB_beringer.setFocus()
                        else:
                            self.ui.CMB_fett.setFocus()
                        return
                    else:
                        self.ui.CMB_fach.lineEdit().clear()

        # if (len(txt) == 2) and not self.ui.CMB_fett.hasFocus():
        #    self.focusNextChild()

    def m2changed(self, t):
        if t == "/":
            self.ui.CMB_mauser2.setCurrentText('U')
        elif t == "*":
            self.ui.CMB_mauser2.setCurrentText('M')
        elif t == "-":
            self.ui.CMB_mauser2.setCurrentText('N')
        elif t == "+":
            self.ui.CMB_mauser2.setCurrentText('J')
        self.ui.CMB_mauser3.setFocus(True)

    def changed_index(self):
        if self.ui.CMB_alter.currentText() not in ('1', '3'):
            self.ui.CMB_mauser2.setCurrentIndex(-1)
            self.ui.CMB_mauser2.setEnabled(False)
        else:
            self.ui.CMB_mauser2.setEnabled(True)
        self.focusNextChild()

    def hinzufuegen(self):
        if not get_connection_status(engine):
            rberi_lib.QMessageBoxB('ok', 'Keine Verbindung zur Datenbank! Bitte erneut verbinden.', 'Datenbankfehler',
                                   qss=bd.get_qss()).exec_()
            return

        self.disconnect_all()
        self.ui.widgetEingabe.setVisible(True)
        self.set_edit_status()
        self.stunde = QTime.currentTime()

        self.ui.CMB_art.setEnabled(True)
        self.ui.CMB_fangart.setEnabled(True)
        self.ui.INP_ringnummer.setEnabled(True)
        self.ui.actionHinzufuegen.setEnabled(False)

        self.ui.dateEdit.setDate(QDate.currentDate())
        self.ui.timeEdit.setTime(QTime.currentTime())

        df = pd.read_sql("SELECT * FROM arten", engine)
        self.df_arten = df.sort_values(by='deutsch')
        # damit es hier nicht zur Erstfang-Generierung der Ringnummer kommt. Denn das Füllen der Combobox
        # triggert das Signal currentIndexChanged:
        self.ui.CMB_art.currentIndexChanged.disconnect(self.art_index_changed)
        if self.ui.CMB_art.count() <= 0:
            self.ui.CMB_art.addItems(self.df_arten['deutsch'])
            self.ui.CMB_art.setCurrentIndex(-1)
        # und wieder connect, damit alles dann funktioniert.
        self.ui.CMB_art.currentIndexChanged.connect(self.art_index_changed)

        if self.ui.CMB_fangart.count() <= 0:
            self.ui.CMB_fangart.addItems(['', 'e', 'w', 'k', 'd', 'f'])

        df = pd.read_sql("SELECT * FROM netze", engine)
        df_netze = df.sort_values(by='Netz')

        if self.ui.CMB_netz.count() <= 0:
            self.ui.CMB_netz.addItems(df_netze['Netz'])
        self.ui.CMB_netz.setCurrentIndex(-1)

        df = pd.read_sql("SELECT * FROM netfaecher", engine)
        df_faecher = df.sort_values(by='Fach')
        if self.ui.CMB_fach.count() <= 0:
            self.ui.CMB_fach.addItems(df_faecher['Fach'])
        self.ui.CMB_fach.setCurrentIndex(-1)

        if self.ui.CMB_fett.count() <= 0:
            self.ui.CMB_fett.addItems(['', '0', '1', '2', '3', '4', '5', '6', '7', '8'])
        self.ui.CMB_fett.setCurrentIndex(-1)
        if self.ui.CMB_muskel.count() <= 0:
            self.ui.CMB_muskel.addItems(['', '0', '1', '2', '3'])
        self.ui.CMB_muskel.setCurrentIndex(-1)
        if self.ui.CMB_alter.count() <= 0:
            self.ui.CMB_alter.addItems(['', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F',
                                        'G', 'H'])
        self.ui.CMB_alter.setCurrentIndex(-1)
        if self.ui.CMB_sex.count() <= 0:
            self.ui.CMB_sex.addItems(['', '0', '1', '2'])
        self.ui.CMB_sex.setCurrentIndex(-1)
        if self.ui.CMB_mauser1.count() <= 0:
            self.ui.CMB_mauser1.addItems(['', '0', '1', '2'])
        self.ui.CMB_mauser1.setCurrentIndex(-1)
        if self.ui.CMB_mauser2.count() <= 0:
            self.ui.CMB_mauser2.addItems(['', 'J', 'U', 'M', 'N', '/', '*', '-', '+'])
        self.ui.CMB_mauser2.setCurrentIndex(-1)

        if self.ui.CMB_mauser3.count() <= 0:
            self.ui.CMB_mauser3.addItems(['', '0', '1', '2', '3'])

            """item1 = QtGui.QStandardItem()
            item1.setData("1 - unvermausert/alt", Qt.DisplayRole)
            item1.setData("1", Qt.UserRole)
            # item1->setData(tr("Red"), Qt::DisplayRole);
            # item1->setData("1", Qt::UserRole); # note: doesn't have to be a string.
            item2 = QtGui.QStandardItem()
            item2.setData("2 - aktive Handschwingenmauser", Qt.DisplayRole)
            item2.setData("2", Qt.UserRole)

            model = QtGui.QStandardItemModel()
            model.setItem(0, 0, item1)
            model.setItem(1, 0, item2)

            self.ui.CMB_mauser3.setModel(model)"""

            # self.ui.CMB_mauser3.setItemData(1, "1")
            # self.ui.CMB_mauser3.setItemText(1, "unvermausert")

            """self.ui.CMB_mauser3.addItem(['', '0', '1', '2', '3'], ['-', 'unklar', 'alt/unvermausert',
                                                                   'aktive Handschwingenmauser', 'neu/vermausert'])"""

        self.ui.CMB_mauser3.setCurrentIndex(-1)
        if self.ui.CMB_verletzungscode.count() <= 0:
            df_verletzung = pd.read_sql('SELECT * FROM verletzung', engine)
            list_verletzung = ['']
            for index, item in df_verletzung.iterrows():
                txt = str(item[1]) + "; " + str(item[2]) + "; " + str(item[3])
                list_verletzung.append(txt)
            self.ui.CMB_verletzungscode.addItems(list_verletzung)
            ownview = self.ui.CMB_verletzungscode.view()
            ownview.setFixedWidth(500)
        df = pd.read_sql("SELECT * FROM stationen", engine)
        df_stationen = df.sort_values(by='Name')
        if self.ui.CMB_station.count() <= 0:
            self.ui.CMB_station.addItems(df_stationen['Name'])
        if bd.get_debug():
            print(self.get_defaults()['Station'])
        self.ui.CMB_station.setCurrentText(df_stationen.at[df_stationen[df_stationen['stationenID'] ==
                                                                        self.get_defaults().loc[0].at[
                                                                            'Station']].index.item(), 'Name'])
        # df.loc[5].at['B']
        # df[df['A'] == 5].index.item() ==> Index der gesuchten Zeile

        df = pd.read_sql("SELECT * FROM zentralen", engine)
        df_zentralen = df.sort_values(by='Name')
        if self.ui.CMB_zentrale.count() <= 0:
            self.ui.CMB_zentrale.addItems(df_zentralen['Name'])
            AllItems = [self.ui.CMB_zentrale.itemText(i) for i in range(self.ui.CMB_zentrale.count())]
            fm = QFontMetrics(self.ui.CMB_zentrale.property('font'))
            pixelsWide = self.ui.CMB_zentrale.width()
            for el in AllItems:
                if fm.width(el) > pixelsWide:
                    pixelsWide = fm.width(el)
            ownview = self.ui.CMB_zentrale.view()
            ownview.setFixedWidth(pixelsWide)
        self.ui.CMB_zentrale.setCurrentText(df_zentralen.at[df_zentralen[
            df_zentralen['zentraleID'] == self.get_defaults().loc[0].at['Zentrale']].index.item(), 'Name'])

        if self.ui.CMB_beringer.count() <= 0:
            self.fill_ringer_current_year()

        # ganz am Ende:
        self.ui.CMB_art.setFocus()
        self.connect_all()

    def make_dict_pretty(self, d: dict):
        if self:
            pass
        for key, value in d.items():
            if value == '' or value is None:
                d[key] = 'Null'
            elif isinstance(value, str) and value.find(",") > 0:
                d[key] = value.replace(",", ".")

        if "tarsus" not in d:
            d['tarsus'] = ''
        if "hs2" not in d:
            d['hs2'] = ''
        if "hs4" not in d:
            d['hs4'] = ''
        if "hs5" not in d:
            d['hs5'] = ''
        if "hs6" not in d:
            d['hs6'] = ''
        if "hs7" not in d:
            d['hs7'] = ''
        if "hs8" not in d:
            d['hs8'] = ''
        if "hs9" not in d:
            d['hs9'] = ''
        if "hs10" not in d:
            d['hs10'] = ''
        if "as1" not in d:
            d['as1'] = ''
        if "mauserkarte" not in d:
            d['mauserkarte'] = 0
        if "innenfuss" not in d:
            d['innenfuss'] = ''
        if "schnabellaenge" not in d:
            d['schnabellaenge'] = ''
        if "schnabelbreite" not in d:
            d['schnabelbreite'] = ''
        if "kerbe" not in d:
            d['kerbe'] = ''
        return d

    def fill_ringer_current_year(self):
        self.ui.CMB_beringer.clear()
        self.df_ringer = pd.read_sql("SELECT nachname, vorname, ringer_new, jahr FROM ringer", engine)
        df_ringer_year = self.df_ringer.query("jahr == " + datetime.now().date().strftime("%Y"))
        # df = pd.read_sql("SELECT * FROM RINGER where jahr=" + datetime.now().date().strftime("%Y"), engine)
        df_ringer = df_ringer_year.sort_values(by='nachname')

        for ringer in df_ringer.iterrows():
            list_item = ringer[1]['nachname'] + ", " + ringer[1]['vorname']
            self.ui.CMB_beringer.addItem(list_item)
        self.ui.CMB_beringer.setCurrentIndex(-1)

        gestern = datetime.now() - timedelta(1)
        gestern = gestern.strftime("%Y-%m-%d")
        df_gestern = pd.read_sql("select distinct ringer from esf where datum >= '" + gestern + "'", engine)
        counter = 0
        self.ui.LST_letzte_beringer.clear()
        for ind, name in df_gestern.itertuples():
            counter += 1
            nachname = pd.read_sql("select nachname from ringer where ringer_new = '" + name + "'", engine).iat[0, 0]
            vorname = pd.read_sql("select vorname from ringer where ringer_new = '" + name + "'", engine).iat[0, 0]
            list_item = nachname + ", " + vorname
            self.ui.LST_letzte_beringer.addItem(list_item)
            if counter >= 5:
                return

    def generate_new_ringer(self, vorname, nachname):
        kuerzel_vorhanden = self.df_ringer['ringer_new'].tolist()
        kuerzel_neu = nachname[0].upper() + vorname[0].upper()
        i = 0
        while kuerzel_neu in kuerzel_vorhanden and i < 10:
            i += 1
            if len(kuerzel_neu) % 2 == 0:  # kuerzel ist geradestellig - also zusätzlichen buchstaben vom nachnamen
                kuerzel_neu = nachname[0:i + 1].upper() + vorname[0:i].upper()
            else:
                kuerzel_neu = nachname[0:i].upper() + vorname[0:i + 1].upper()
        if i >= 10:
            kuerzel_neu = "ungueltig"
        if bd.get_debug():
            print(kuerzel_neu)
        return kuerzel_neu

    def check_same_art(self, art1, art2) -> list:
        df_arten = self.df_arten
        df_arten = df_arten.sort_index()
        index1 = -1
        index2 = -1
        for (ind, colname) in enumerate(df_arten):
            if art1 in df_arten[colname].values:  # erzeugt eine Liste der Spaltenwerte
                index1 = df_arten[colname].values.tolist().index(art1)
            if art2 in df_arten[colname].values:
                index2 = df_arten[colname].values.tolist().index(art2)
        if index1 == index2:
            return_list = [True, df_arten.loc[index1, 'deutsch'], df_arten.loc[index1, 'lateinisch'],
                           df_arten.loc[index1, 'englisch'], df_arten.loc[index1, 'esf_kurz']]
            if bd.get_debug():
                print(return_list)
            return return_list
        else:
            return_list = [False, df_arten.loc[index1, 'deutsch'], df_arten.loc[index2, 'deutsch'],
                           df_arten.loc[index1, 'esf_kurz'], df_arten.loc[index2, 'esf_kurz']]
            if bd.get_debug():
                print(return_list)
            return return_list

    def abmelden(self):
        if self.get_edit_status():
            a = rberi_lib.QMessageBoxB("ync", "Es liegen nicht gespeicherte Eingaben vor. Alle nicht "
                                              "gespeicherten Daten gehen verloren. Wirklich abmelden?",
                                       "Abmeldung", qss=bd.get_qss()).exec_()
            if a != QMessageBox.Yes:
                return

        self.set_edit_status(False)
        logout("Abmelden über Menü aufgerufen")
        login_form = Loginpage(df_benutzer, current_u)
        result = login_form.exec_()
        if bd.get_debug():
            print(result)
        if result == QtWidgets.QDialog.Accepted:
            self.handle_user_level()
        else:
            logout("Erneute Anmeldung hat nicht geklappt.")
            # sys.exit()

    def handle_user_level(self):
        """
        Nach der Anmeldung werden hier die Menu-Einträge deaktiviert oder aktiviert, je nach Userlevel.
        Wenn zusätzliche Berechtigungen vergeben werden sollen, so muss die Tabelle 'berechtigungen' ergänzt werden
        und hier an der Stelle (1) die False-Anweisung sowie an Stelle (2) die entsprechende Abfrage + True-Anweisung
        :return:
        """
        user_level = self.get_current_userlevel()

        self.ui.actionNeuen_Benutzer_anlegen.setEnabled(False)
        self.ui.CMB_zentrale.setEnabled(False)
        self.ui.actionEinstellungen.setEnabled(False)
        self.ui.actionArten.setEnabled(False)
        self.ui.actionRingserien.setEnabled(False)
        self.ui.actionPasswort_aendern.setEnabled(False)
        # STELLE (1)

        berechtigungen = pd.read_sql("SELECT * FROM beringung.berechtigungen WHERE level = " + str(user_level), engine)
        if not berechtigungen.empty:
            if berechtigungen['new_user'].iloc[0] == 'Y':
                self.ui.actionNeuen_Benutzer_anlegen.setEnabled(True)
            if berechtigungen['zentrale'].iloc[0] == 'Y':
                self.ui.CMB_zentrale.setEnabled(True)
            if berechtigungen['einstellungen'].iloc[0] == 'Y':
                self.ui.actionEinstellungen.setEnabled(True)
            if berechtigungen['arten'].iloc[0] == 'Y':
                self.ui.actionArten.setEnabled(True)
            if berechtigungen['ringserie'].iloc[0] == 'Y':
                self.ui.actionRingserien.setEnabled(True)
            if berechtigungen['beringer_speichern'].iloc[0] == 'Y':
                self.berechtigung_beringer_speichern = 'ok'
            if berechtigungen['pw_aendern'].iloc[0] == 'Y':
                self.ui.actionPasswort_aendern.setEnabled(True)
            # STELLE (2)

    def closeevent(self):
        if bd.get_debug():
            print("closeEvent in MainWindow() aufgerufen")
        logout("Programm über Fenster-X oder Alt-F4 geschlossen")
        super().__init__(parent=None)

    def programm_beenden(self, txt=None):
        if not self.get_edit_status():
            if bd.get_debug():
                print("programm_beenden aufgerufen")
            logout(txt)
            app.exit(0)
        else:
            if rberi_lib.QMessageBoxB("ny", "Es wird gerade ein Datensatz bearbeitet. Sicher verlassen?",
                                      "Sicherheitsabfrage", None, qss=bd.get_qss()).exec_() != QMessageBox.Yes:
                return
            else:
                logout(txt)
                app.exit(0)

    def set_user(self, _user):
        self.current_user = _user

    def get_current_user(self) -> str:
        return self.current_user.getuser()

    def get_current_userlevel(self):
        if self:
            pass
        return self.current_user.getlevel()

    def check_oot(self) -> bool:
        """
        Prüft ob Toleranzfehler korrigiert wurden. Falls nicht oder falls der korrigierte Wert auch außerhalb der
        Toleranz ist, wird abgefragt, ob die Werte ok sind. Falls mit 'JA' bestätigt, wird 'Maße OK' in die Bemerkung
        hinzugefügt und TRUE zurückgegeben. Wenn nicht wird False zurückgegeben.
        :return:
        TRUE - wenn Maß bestätigt wird ODER wenn das Dict (mit den gespeicherten Eingaben) leer ist
        FALSE - wenn Maß nicht bestätigt wird
        """
        if not self.oot:
            return True
        for key, value in self.oot.items():
            # print(key, "->", value)
            # key = Teilfederlänge
            if key == "Teilfederlänge" and len(self.ui.INP_teilfeder.text()) <= 0:
                continue
            elif key == "Flügellänge" and len(self.ui.INP_fluegellaenge.text()) <= 0:
                continue
            if len(value) == 1:
                a = rberi_lib.QMessageBoxB('yn', f'{key} ist außerhalb der Toleranz und wurde nicht geändert. '
                                                 f'Mit "Ja/Yes" wird "Maße OK" im Bemerkungsfeld hinzugefügt. ',
                                           'Toleranzabfrage', qss=bd.get_qss()).exec_()
                if a == QMessageBox.Yes:
                    if len(self.ui.PTE_bemerkung.toPlainText()) > 0:
                        self.ui.PTE_bemerkung.appendPlainText('\nMaße OK')
                    else:
                        self.ui.PTE_bemerkung.setPlainText('Maße OK')
                    return True
                else:
                    return False
            elif len(value) > 1:
                a = rberi_lib.QMessageBoxB('yn', f'{key} ist auch nach Änderung außerhalb der Toleranz. '
                                                 f'Mit "Ja/Yes" wird "Maße OK" im Bemerkungsfeld hinzugefügt. ',
                                           'Toleranzabfrage', qss=bd.get_qss()).exec_()
                if a == QMessageBox.Yes:
                    if len(self.ui.PTE_bemerkung.toPlainText()) > 0:
                        self.ui.PTE_bemerkung.appendPlainText('\nMaße OK')
                    else:
                        self.ui.PTE_bemerkung.setPlainText('Maße OK')
                    return True
                else:
                    return False
        return True

    def proof_gauss(self, source: str) -> bool:
        """

        :param source: Automatismus bei 'teilfeder', 'fluegel' und 'gewicht'.
        :return:
        None
        """

        def proof_ok(mittel, _faktor_min, _faktor_max, _abweichung, _eingabe) -> int:
            if (mittel - _faktor_min * _abweichung) <= _eingabe <= (mittel + _faktor_max * _abweichung):
                return 0
            elif (mittel - _faktor_min * _abweichung) > _eingabe:
                return -1
            else:
                return 1

        _object = None
        einheit = 'mm'
        if source == 'teilfeder':
            _object = self.ui.INP_teilfeder
            self.txt = 'Teilfederlänge'
            self.eingabe_str = self.ui.INP_teilfeder.text()
            vals = {"mw": "f_ex", "stdab": "f_s", "faktor_min": "f_d_neg", "faktor_max": "f_d_pos",
                    "quot": "quo_f3_flg_ex", "quot_s": "quo_f3_flg_s", "quot_d_min": "quo_f3_flg_d_neg",
                    "quot_d_max": "quo_f3_flg_d_pos", "show_g": "show_g_msg", "show_q": "show_q_msg"}
        elif source == 'fluegel':
            _object = self.ui.INP_fluegellaenge
            self.txt = 'Flügellänge'
            self.eingabe_str = self.ui.INP_fluegellaenge.text()
            vals = {"mw": "w_ex", "stdab": "w_s", "faktor_min": "w_d_neg", "faktor_max": "w_d_pos",
                    "quot": "quo_f3_flg_ex", "quot_s": "quo_f3_flg_s", "quot_d_min": "quo_f3_flg_d_neg",
                    "quot_d_max": "quo_f3_flg_d_pos", "show_g": "show_g_msg", "show_q": "show_q_msg"}
        elif source == 'gewicht':
            _object = self.ui.INP_masse
            self.txt = 'Masse'
            einheit = 'g'
            self.eingabe_str = self.ui.INP_masse.text()
            vals = {"mw": "g_ex", "stdab": "g_s", "faktor_min": "g_d_neg", "faktor_max": "g_d_pos",
                    "quot": "quo_f3_flg_ex", "quot_s": "quo_f3_flg_s", "quot_d_min": "quo_f3_flg_d_neg",
                    "quot_d_max": "quo_f3_flg_d_pos", "show_g": "show_g_msg", "show_q": "show_q_msg"}
        else:
            return True

        art_df = pd.read_sql('SELECT esf_kurz FROM arten WHERE deutsch = "' + self.ui.CMB_art.currentText() + '"',
                             engine)
        if art_df.empty:
            return True

        self.art = art_df['esf_kurz'].iloc[0]
        if rberi_lib.check_float(self.eingabe_str):
            self.eingabe_str = self.eingabe_str.replace(",", ".")
            eingabe = float(self.eingabe_str)
        else:
            return True

        try:
            df_vals = pd.read_sql('SELECT ' + vals['mw'] + ', ' + vals['stdab'] + ', ' + vals['faktor_min'] + ', ' +
                                  vals['faktor_max'] + ', ' + vals['quot'] + ', ' + vals['quot_s'] + ', ' +
                                  vals['quot_d_min'] + ', ' + vals['quot_d_max'] + ', ' + vals['show_g'] + ', ' +
                                  vals['show_q'] + ' ' + 'FROM arten WHERE esf_kurz = "' + self.art + '"', engine)
        except Exception as excp:
            rberi_lib.QMessageBoxB('ok', 'Mittelwert und Standardabweichung konnten nicht '
                                         'ermittelt werden. Bitte Datenbankverbindung prüfen.', 'Fehler',
                                   str(excp), qss=bd.get_qss()).exec_()
            return True

        # wenn für diese Art keine Gewichtsabweichungen angezeigt werden sollen, wird hier die Bearbeitung
        # beendet.
        show_g_msg_txt = df_vals[vals['show_g']].iloc[0]
        if source == 'gewicht' and show_g_msg_txt == 0:
            return True

        avg_df = df_vals[vals['mw']].iloc[0]
        if avg_df <= 0:
            return True
        std_ab = df_vals[vals['stdab']].iloc[0]
        if std_ab <= 0:
            return True
        faktor_min = df_vals[vals['faktor_min']].iloc[0]
        if faktor_min <= 0:
            faktor_min = 2
        faktor_max = df_vals[vals['faktor_max']].iloc[0]
        if faktor_max <= 0:
            faktor_max = 2
        quot = df_vals[vals['quot']].iloc[0]
        quot_s = df_vals[vals['quot_s']].iloc[0]
        quot_faktor_min = df_vals[vals['quot_d_min']].iloc[0]
        quot_faktor_max = df_vals[vals['quot_d_max']].iloc[0]
        show_q_msg = df_vals[vals['show_q']].iloc[0]

        result_proof = proof_ok(avg_df, faktor_min, faktor_max, std_ab, eingabe)
        if not result_proof == 0:
            if result_proof < 0:
                abweichung = f"{avg_df - (faktor_min * std_ab) - eingabe: .1f}{einheit}"
            else:
                abweichung = f"{eingabe - (avg_df + (faktor_max * std_ab)):.1f}{einheit}"

            result_txt = [f'{self.txt} ist außerhalb der Toleranz. Bitte prüfen.',
                          [f'Eingabe = {eingabe}{einheit}', f'Mittelwert = {avg_df:.2f}{einheit}',
                           f'Standardabweichung = {std_ab:.2f}{einheit}',
                           f'Zulässiger Bereich: (-{faktor_min:.1f}x bis {faktor_max:.1f}x Stdabw.) = '
                           f'[{avg_df - (faktor_min * std_ab):.2f} - {avg_df + (faktor_max * std_ab):.2f}]{einheit}',
                           f'Aktuelle Abweichung zum Mittel = {abs(avg_df - eingabe):.2f}{einheit} und damit '
                           f'um {abweichung} außerhalb des Bereichs.']
                          ]
            rberi_lib.QMessageBoxB('ok', result_txt[0], 'Toleranzfehler', result_txt[1], qss=bd.get_qss()).exec_()

            # mit self.oot lässt sich beim Speichern prüfen, ob ein Wert außerhalb der Toleranz geändert wurde ...
            # daher wird hier jeder Wert eingefügt, der geprüft wurde (also jedes mal nach Änderung des Textes des
            # entsprechenden Eingabefelds)
            if source == 'teilfeder':
                if 'Teilfederlänge' in self.oot:
                    self.oot['Teilfederlänge'].append(eingabe)
                else:
                    self.oot['Teilfederlänge'] = [eingabe]
            elif source == 'fluegel':
                if 'Flügellänge' in self.oot:
                    self.oot['Flügellänge'].append(eingabe)
                else:
                    self.oot['Flügellänge'] = [eingabe]
            elif source == 'gewicht':
                if 'Masse' in self.oot:
                    self.oot['Masse'].append(eingabe)
                else:
                    self.oot['Masse'] = [eingabe]

            _object.setFocus()
            _object.selectAll()
            internal_marker = True
            # _object.setSelection(0, len(_object.text()))    BUGGY!
        else:
            if source == 'teilfeder':
                self.oot['Teilfederlänge'] = []
            elif source == 'fluegel':
                self.oot['Flügellänge'] = []
            elif source == 'gewicht':
                self.oot['Masse'] = []
            internal_marker = False

        if (rberi_lib.check_float(self.ui.INP_teilfeder.text()) and
                rberi_lib.check_float(self.ui.INP_fluegellaenge.text()) and
                show_q_msg == 1 and not self.verhaeltnis_aufgerufen):
            self.verhaeltnis_aufgerufen = True
            tf = self.ui.INP_teilfeder.text().replace(",", ".")
            fl = self.ui.INP_fluegellaenge.text().replace(",", ".")
            eingabe_quot = float(tf) / float(fl)
            result_proof = proof_ok(quot, quot_faktor_min, quot_faktor_max, quot_s, eingabe_quot)
            if result_proof == 0:
                pass
            else:
                if result_proof < 0:
                    abw = f'{quot - (quot_faktor_min * quot_s) - eingabe_quot:.2f}'
                else:
                    abw = f'{eingabe_quot - (quot + (quot_faktor_max * quot_s)):.2f}'
                rberi_lib.QMessageBoxB('ok', 'Verhältnis Teilfeder : Flügel außerhalb der Toleranz. Bitte prüfen.',
                                       'Toleranzfehler',
                                       [f'Eingegebener Quotient = {eingabe_quot:.2f}',
                                        f'Mittelwert Quotient = {quot:.2f}',
                                        f'Zulässiger Bereich (-{quot_faktor_min}x Sigma <= Quotient <= '
                                        f'{quot_faktor_max}x Sigma) = [{(quot - quot_faktor_min * quot_s):.2f}, '
                                        f'{(quot + quot_faktor_max * quot_s):.2f}]',
                                        f'Aktuelle Abweichung zum Mittel: {abs(quot - eingabe_quot):.1f} und damit '
                                        f'um {abw} außerhalb des Bereichs.'
                                        ]
                                       , qss=bd.get_qss()).exec_()
                _object.setFocus(True)
                _object.selectAll()
                internal_marker = True

        return internal_marker

    def feedback(self, source: str):
        diag = Kontakt_Menu_GUI(source)
        self.__set_widget_stylesheet(diag)
        diag.exec_()

    def add_bemerkung(self):
        self.ui.PTE_bemerkung.setEnabled(True)
        self.ui.PTE_bemerkung.setFocus(True)

    def aktueller_status(self):
        txt_db = 'besteht NICHT!'
        if get_connection_status(engine):
            txt_db = 'besteht'
        txt_user = self.get_current_user()
        txt_level = self.get_current_userlevel()
        rberi_lib.QMessageBoxB('ok', f'Verbindung zur Datenbank: {txt_db}\nAktueller Benutzer: {txt_user}\n'
                                     f'Berechtigungslevel (1: Eingabestatus, 2: Pflegestatus, 3: Adminstatus) = '
                                     f'{txt_level}\n', 'Aktueller Status', qss=bd.get_qss()).exec_()

    def snapshot(self):
        fehlertxt = ""
        if self.ui.CMB_art.currentIndex() < 0:
            fehlertxt += "Art"
        beringer = self.ui.CMB_beringer.currentText()
        if len(beringer) <= 0:
            if len(fehlertxt) > 0:
                fehlertxt += ", Beringer"
            else:
                fehlertxt += "Beringer"
        ringnummer = self.ui.INP_ringnummer.text()
        if len(ringnummer) <= 0:
            if len(fehlertxt) > 0:
                fehlertxt += ", Ringnummer"
            else:
                fehlertxt += "Ringnummer"

        if len(fehlertxt) > 0:
            rberi_lib.QMessageBoxB('ok', f'Folgende Daten fehlen: {fehlertxt}',
                                   'Daten fehlen', qss=bd.get_qss()).exec_()
            return

        zeitstempel = datetime.now().strftime("%Y%m%d-%H%M%S")
        art = self.ui.CMB_art.currentText()
        art = art.replace("ä", "ae")
        art = art.replace("ö", "oe")
        art = art.replace("ü", "ue")
        art = art.replace("ß", "ss")
        beringer_list = beringer.split(",")
        beringer_text = ""
        for namepart in beringer_list:
            beringer_text += namepart.strip().replace(" ", "")
        _filename = art + "_" + ringnummer + "_" + beringer_text + "_" + zeitstempel + ".png"
        _path = self.get_defaults()['Bilderverzeichnis'].tolist()[0] + "/" + self.ui.CMB_art.currentText()
        if not os.path.isdir(_path):
            try:
                os.makedirs(_path)
            except Exception as err:
                rberi_lib.QMessageBoxB('ok', 'Neues Verzeichnis konnte nicht angelegt werden. Siehe Details.', 'Fehler',
                                       str(err)).exec_()
                return

        _filename = self.get_defaults()['Bilderverzeichnis'].tolist()[0] + "/" + self.ui.CMB_art.currentText() + "/" + _filename
        if bd.get_debug():
            print(f"Art = {art}")
            print(f"Beringer = {beringer_text}")
            print(f"Zeitstempel = {zeitstempel}")
            print(f"_filename: {_filename}")

        # diese zeile wieder löschen und oben entkommentieren.
        """_filename = (self.get_defaults()['Bilderverzeichnis'].tolist()[0] + "/Test/" + datetime.now().strftime("%Y%m%d-%H%M%S")
                     + ".png")"""

        cam_port = int(self.ui.CMB_camera_source.currentText())
        self.ui.statusbar.showMessage("Open Camera ... ", 3000)
        cam = cv2.VideoCapture(cam_port, cv2.CAP_DSHOW)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        if not cam.isOpened():
            self.ui.statusbar.showMessage(f"Kann die Kamera nicht öffnen.", 3000)
            rberi_lib.QMessageBoxB('ok', 'Kann die Kamera nicht öffnen.', 'Kamerafehler', qss=bd.get_qss()).exec_()
            return
        self.ui.statusbar.showMessage(f"Camera opened ... ", 3000)

        cv2.namedWindow('Belegfoto', cv2.WINDOW_KEEPRATIO)
        cv2.setWindowTitle('Belegfoto', 'Belegfoto (Leertaste = Bild aufnehmen; Fenster schliesst sich. '
                                        'ODER "q" zum Beenden ohne Bild)')
        cv2.resizeWindow('Belegfoto', 1280, 720)

        no_pic_needed = False
        while True:
            key = cv2.waitKey(25)
            result, image = cam.read()
            """if not result:
                self.ui.statusbar.showMessage(f"Kein Videostream der Kamera gefunden.", 3000)
                no_pic_needed = True
                break"""
            cv2.imshow('Belegfoto', image)

            """if bd.get_debug() and cv2.waitKey(1) == ord('r'):
                print('Resolution: ' + str(image.shape[0]) + ' x ' + str(image.shape[1]))"""
            if key == 32:  # space is hit
                cam.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)
                k = 0
                while k < 3:
                    result, image = cam.read()
                    time.sleep(0.1)
                    k += 1
                break
            if key == ord('q'):
                no_pic_needed = True
                break

        if isinstance(image, np.ndarray) and image.size > 0 and not no_pic_needed:
            cv2_im = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(cv2_im)
            try:
                img_pil.save(_filename)
                self.ui.PTE_bemerkung.appendPlainText("Belegfoto: " + _filename)
            except Exception as err:
                rberi_lib.QMessageBoxB('ok', 'Speichern des Belegfotos fehlgeschlagen. Siehe Details.', 'Fehlermeldung',
                                       str(err), qss=bd.get_qss()).exec_()

        try:
            cam.release()
            cv2.destroyWindow("Belegfoto")
        except Exception as excp:
            self.ui.statusbar.showMessage(f"Belegfoto-Fenster nicht mehr gefunden ... kein Handlungsbedarf! Excp: {excp}",
                                          3000)

    def kameratest(self):
        def klick(event, x, y, flags, param):

            if event == cv2.EVENT_LBUTTONDOWN:
                self.no_click = False
                if bd.get_debug():
                    print("LEFTCLICK! in Kameratest")

        self.no_click = True
        cam_port = int(self.ui.CMB_camera_source.currentText())
        cam = cv2.VideoCapture(cam_port)
        if not cam.isOpened():
            a = rberi_lib.QMessageBoxB('yn', f"Kann die Kamera auf Slot {cam_port} nicht öffnen. Soll der nächste Slot "
                                             f"getestet werden?", 'Kamerafehler', qss=bd.get_qss()).exec_()
            if a == QMessageBox.Yes:
                if self.ui.CMB_camera_source.currentIndex() < self.ui.CMB_camera_source.maxCount() - 2:
                    self.ui.CMB_camera_source.setCurrentIndex(self.ui.CMB_camera_source.currentIndex())
                    self.kameratest()
                else:
                    rberi_lib.QMessageBoxB('ok', 'Keine weiteren Slots gefunden.', 'Kamerafehler', qss=bd.get_qss()).exec_()
            else:
                return

        result, image = cam.read()
        if not result:
            rberi_lib.QMessageBoxB('ok', f"Kein Videostream der Kamera gefunden. Stelle sicher, dass die Kamera im "
                                         f"Videomodus ist.", 'Kamerafehler', qss=bd.get_qss()).exec_()
            return

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


def kerbe(kerbe_val, art_obj, fluegel, alter):
    # 1 = Palustris (Sumpfi)
    # 2 = Scirspaceus (Teichi)
    # 0 = unklar
    dict_juv = {
        60: {9.5: 2, 10: 2},
        61: {10: 2, 10.5: 2, 11: 2},
        62: {9.5: 2, 10: 2, 10.5: 2, 11: 2},
        63: {9: 2, 9.5: 2, 10: 2, 10.5: 2, 11: 2, 11.5: 2, 12: 2},
        64: {8.5: 1, 9: 2, 9.5: 2, 10: 2, 10.5: 2, 11: 2, 11.5: 2, 12: 2, 12.5: 2},
        65: {9.5: 2, 10: 2, 10.5: 2, 11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2},
        66: {8.5: 1, 9: 0, 9.5: 2, 10: 2, 10.5: 2, 11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2},
        67: {8: 1, 8.5: 1, 9: 1, 9.5: 0, 10: 2, 10.5: 2, 11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2},
        68: {7.5: 1, 8: 1, 8.5: 1, 9: 1, 9.5: 1, 10: 0, 10.5: 2, 11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2, 13.5: 2},
        69: {7.5: 1, 8: 1, 8.5: 1, 9: 1, 9.5: 1, 10: 0, 10.5: 0, 11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2, 13.5: 2},
        70: {7.5: 1, 8: 1, 8.5: 1, 9: 1, 9.5: 1, 10: 0, 10.5: 0, 11: 0, 11.5: 2, 12: 2, 12.5: 2, 13: 2, 13.5: 2},
        71: {7.5: 1, 8: 1, 8.5: 1, 9: 1, 9.5: 1, 10: 1, 10.5: 1, 11: 1, 11.5: 2, 12: 2, 12.5: 2, 13: 2, 13.5: 2},
        72: {7.5: 1, 8: 1, 8.5: 1, 9: 1, 9.5: 1, 10: 1, 10.5: 1, 11: 1, 11.5: 2, 12: 2, 12.5: 2, 13: 2, 13.5: 2},
        73: {8: 1, 8.5: 1, 9: 1, 9.5: 1, 10: 1, 10.5: 1, 11: 1, 12.5: 2},
        74: {10: 1, 10.5: 1, 11: 1},
    }
    dict_ad = {
        61: {11: 2},
        62: {11: 2, 12: 2, 13: 2},
        63: {10.5: 2, 11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2},
        64: {11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2},
        65: {11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2, 13.5: 2, 14: 2, 15: 2},
        66: {9: 2, 10: 2, 10.5: 2, 11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2, 13.5: 2, 14: 2},
        67: {9.5: 1, 10: 1, 10.5: 2, 11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2, 13.5: 2, 14: 2},
        68: {8.5: 1, 9: 1, 9.5: 1, 10: 1, 10.5: 0, 11: 2, 11.5: 2, 12: 2, 12.5: 2, 13: 2, 13.5: 2, 14: 2},
        69: {9: 1, 9.5: 1, 10: 1, 10.5: 1, 11: 0, 11.5: 2, 12: 2, 12.5: 2, 13: 2, 13.5: 2, 14: 2},
        70: {9: 1, 9.5: 1, 10: 1, 10.5: 1, 11: 1, 12: 2, 12.5: 2, 13: 2, 13.5: 2, 14: 2},
        71: {9: 1, 9.5: 1, 10: 1, 10.5: 1, 11: 1, 12: 2, 12.5: 2, 13: 2, 13.5: 2, 14: 2},
        72: {9: 1, 9.5: 1, 10: 1, 10.5: 1, 11: 1, 11.5: 1, 12: 1, 12.5: 2, 13: 2, 13.5: 2, 14: 2, 14.5: 2},
        73: {9.5: 1, 10: 1, 10.5: 1, 11: 1},
        74: {10.5: 1, 11: 1},
        75: {12: 1},
        76: {12: 1},
    }
    kerbe_val = rberi_lib.return_float(kerbe_val)
    kerbe_val = round(kerbe_val, 1)
    if str(kerbe_val)[-1] != '0':
        kerbe_val = round(float(str(kerbe_val)[:-2] + ".5"), 1)
    else:
        kerbe_val = int(kerbe_val)

    if kerbe_val <= 0:
        return
    if art_obj.currentText() == "Teichrohrsänger":
        art_eingabe = 2
    elif art_obj.currentText() == 'Sumpfrohrsänger':
        art_eingabe = 1
    else:
        return
    fluegel = rberi_lib.return_float(fluegel)
    if fluegel <= 0:
        return

    fluegel = round(fluegel, 1)
    if str(fluegel)[-1] != '0':
        fluegel = int(fluegel)
        fluegel += 1
    else:
        fluegel = int(fluegel)

    art_winkler = art_eingabe
    if alter == '3':  # Jungvogel
        if fluegel in dict_juv.keys() and kerbe_val in dict_juv[fluegel].keys():
            art_winkler = dict_juv[fluegel][kerbe_val]
    elif alter not in ['0', '1', '2']:  # Altvogel
        if fluegel in dict_ad.keys() and kerbe_val in dict_ad[fluegel].keys():
            art_winkler = dict_ad[fluegel][kerbe_val]
    else:
        return

    if art_winkler != art_eingabe:
        if art_winkler == 1:
            a = rberi_lib.QMessageBoxB('ync', 'Laut der Übersicht Winkler handelt es sich um einen '
                                              'Sumpfrohrsänger. Soll die Art geändert werden?',
                                       'Sumpf/Teich?', qss=bd.get_qss()).exec_()
            if a == QMessageBox.Yes:
                art_obj.setCurrentText('Sumpfrohrsänger')
                window.set_list_of_picture_paths_of_dir()
                window.load_img(window.get_first_picture_of_dir())

        elif art_winkler == 2:
            a = rberi_lib.QMessageBoxB('ync', 'Laut der Übersicht Winkler handelt es sich um einen '
                                              'Teichrohrsänger. Soll die Art geändert werden?',
                                       'Sumpf/Teich?', qss=bd.get_qss()).exec_()
            if a == QMessageBox.Yes:
                art_obj.setCurrentText('Teichrohrsänger')
                window.set_list_of_picture_paths_of_dir()
                window.load_img(window.get_first_picture_of_dir())

        elif art_winkler == 0:
            rberi_lib.QMessageBoxB('ok', 'Laut der Übersicht Winkler liegt der Vogel im '
                                         'unbestimmten Bereich. Bitte schaut Euch die Handschwingenunterschiede '
                                         'der beiden Arten an. Sollte auch dies nicht zur eindeutigen '
                                         'Bestimmung ausreichen, könnt ihr noch Walinder bemühen.',
                                   'Sumpf/Teich?', qss=bd.get_qss()).exec_()


def make_table_entries_pretty(table: QTableWidget, col_art, col_ringer):
    if not isinstance(table, QTableWidget):  # PyQt5.QtWidgets.QTableWiget
        return

    try:
        df_art = pd.read_sql("SELECT deutsch, esf_kurz FROM arten", engine)
        df_ringer = pd.read_sql("SELECT nachname, vorname, ringer_new FROM ringer", engine)
    except Exception as err:
        rberi_lib.QMessageBoxB("ok", "Datenbankfehler!", "Datenbankfehler", str(err), qss=bd.get_qss()).exec_()
        return

    for i in range(0, table.rowCount()):
        esf_ = table.item(i, col_art).text()
        new_art = df_art.query("esf_kurz == '" + esf_ + "'")['deutsch'].iloc[0]
        ringer_ = table.item(i, col_ringer).text()
        new_name_df = df_ringer.query("ringer_new == '" + ringer_ + "'")
        new_name = new_name_df['nachname'].iloc[0] + ", " + new_name_df['vorname'].iloc[0]
        table.setItem(i, col_art, QTableWidgetItem(new_art))
        table.setItem(i, col_ringer, QTableWidgetItem(new_name))


def write_df_to_qtable(df_to_integrate: pd.DataFrame, table: QTableWidget, *args, **kwargs):
    table.setSortingEnabled(False)
    operation = 'new'
    col_to_mark = None
    row_offset = 0
    m2m = {}
    faktor = 2

    df_arten = pd.read_sql("SELECT * from arten", engine)
    df_ringer = pd.read_sql("SELECT * from ringer", engine)

    for arg in args:
        if isinstance(arg, dict):
            m2m = arg

    for kw in kwargs:
        if kw == 'op' and kwargs[kw] == 'add':
            operation = 'add'
        elif kw == 'mark' and m2m == {}:
            if kwargs[kw] == 'teilfeder':
                col_to_mark = 15
            elif kwargs[kw] == 'fluegel':
                col_to_mark = 16
            elif kwargs[kw] == 'gewicht':
                col_to_mark = 17
            elif kwargs[kw] == 'art':
                col_to_mark = 1
            elif kwargs[kw] == 'alter':
                col_to_mark = 10
            elif kwargs[kw] == 'geschlecht':
                col_to_mark = 11
            elif kwargs[kw] == 'moult1':
                col_to_mark = 12
            elif kwargs[kw] == 'moult2':
                col_to_mark = 13
            elif kwargs[kw] == 'moult3':
                col_to_mark = 14
            elif kwargs[kw] == 'tarsus':
                col_to_mark = 32
            elif kwargs[kw] == 'kerbe':
                col_to_mark = 18
        elif kw == 'faktor':
            faktor = kwargs[kw]

    if bd.get_debug():
        print(f'table_rowcount_old = {table.rowCount()}')
    if operation == 'new':
        headers = list(df_to_integrate)
        headers = list(map(str.capitalize, headers))
        table.clear()
        table.setSortingEnabled(False)
        table.setRowCount(df_to_integrate.shape[0])
        table.setColumnCount(df_to_integrate.shape[1])
        table.setHorizontalHeaderLabels(headers)
    elif operation == 'add':
        if df_to_integrate.shape[1] != table.columnCount():
            if bd.get_debug():
                print("Cannot add Dataframe to Table. Columncount not matching.")
            return
        row_offset = table.rowCount()
        table.setRowCount(table.rowCount() + df_to_integrate.shape[0])

    if bd.get_debug():
        print(f'row_offset = {row_offset}')
        print(f'table_rowcount_new = {table.rowCount()}')
        print(f'df_shape rows : {df_to_integrate.shape[0]}')

    df_array = df_to_integrate.values

    for row in range(df_to_integrate.shape[0]):
        art_esw = df_arten.query("esf_kurz == '" + df_array[row, 1] + "'")['deutsch'].iloc[0]
        ringer = (df_ringer.query("ringer_new == '" + df_array[row, 5] + "'")['nachname'].iloc[0] + ", " +
                  df_ringer.query("ringer_new == '" + df_array[row, 5] + "'")['vorname'].iloc[0])
        teilfeder_mw = df_arten.query("esf_kurz == '" + df_array[row, 1] + "'")['f_ex'].iloc[0]
        try:
            teilfeder_mw_float = float(teilfeder_mw)
        except ValueError:
            teilfeder_mw_float = 0
        teilfeder_stdab = df_arten.query("esf_kurz == '" + df_array[row, 1] + "'")['f_s'].iloc[0]
        try:
            teilfeder_stdab_float = float(teilfeder_stdab)
        except ValueError:
            teilfeder_stdab_float = 0
        wing_mw = df_arten.query("esf_kurz == '" + df_array[row, 1] + "'")['w_ex'].iloc[0]
        try:
            wing_mw_float = float(wing_mw)
        except ValueError:
            wing_mw_float = 0
        wing_stdab = df_arten.query("esf_kurz == '" + df_array[row, 1] + "'")['w_s'].iloc[0]
        try:
            wing_stdab_float = float(wing_stdab)
        except ValueError:
            wing_stdab_float = 0
        masse_mw = df_arten.query("esf_kurz == '" + df_array[row, 1] + "'")['g_ex'].iloc[0]
        masse_stdab = df_arten.query("esf_kurz == '" + df_array[row, 1] + "'")['g_s'].iloc[0]
        try:
            masse_mw_float = float(masse_mw)
            masse_stdab_float = float(masse_stdab)
        except ValueError:
            masse_mw_float = 0
            masse_stdab_float = 0

        for col in range(df_to_integrate.shape[1]):
            item2add = QTableWidgetItem(str(df_array[row, col]))
            match col:
                case 1:
                    item2add.setToolTip(art_esw)
                case 5:
                    item2add.setToolTip(ringer)
                case 15:
                    item2add.setToolTip(str("{:.1f}".format(teilfeder_mw_float - faktor * teilfeder_stdab_float)) + " --- " +
                                        str("{:.1f}".format(teilfeder_mw_float)) + " --- " +
                                        str("{:.1f}".format(teilfeder_mw_float + faktor * teilfeder_stdab_float)))
                case 16:
                    item2add.setToolTip(str("{:.1f}".format(wing_mw_float - faktor * wing_stdab_float)) + " --- " +
                                        str("{:.1f}".format(wing_mw_float)) + " --- " +
                                        str("{:.1f}".format(wing_mw_float + faktor * wing_stdab_float)))
                case 17:
                    item2add.setToolTip(str("{:.1f}".format(masse_mw_float - faktor * masse_stdab_float)) + " --- " +
                                        str("{:.1f}".format(masse_mw_float)) + " --- " +
                                        str("{:.1f}".format(masse_mw_float + faktor * masse_stdab_float)))

            table.setItem(row + row_offset, col, item2add)
            if col_to_mark and col == col_to_mark:
                # item2add.setData(Qt.BackgroundRole, QColor('yellow'))
                # item2add.setData(Qt.ForegroundRole, QColor('red'))
                # item2add.setBackground(QtGui.QColor(255, 215, 0))
                # table.item(row + row_offset, col).setBackground(QColor('red'))
                color = QColor(Qt.GlobalColor.yellow)
                table.item(row + row_offset, col).setBackground(color)
                font = QtGui.QFont()
                font.setBold(True)
                font.setItalic(True)
                font.setUnderline(True)
                table.item(row + row_offset, col).setFont(font)
                # item2add.setBackground(QColor("yellow"))
                # item2add.setForeground(QColor("red"))

    if m2m != {}:
        for row in range(row_offset, table.rowCount()):
            try:
                esfid = int(table.item(row, 37).text())
            except ValueError:
                rberi_lib.QMessageBoxB('ok', 'Die ESF-ID wurde nicht gefunden. Ganz schlecht. Entwickler kontaktieren!',
                                       'BÖSER FEHLER', qss=bd.get_qss()).exec_()
                return

            if esfid in m2m.keys():
                for col_to_mark in m2m[esfid]:
                    table.item(row, col_to_mark).setBackground(QColor('yellow'))
                    table.item(row, col_to_mark).setForeground(QColor("red"))
                    font = QtGui.QFont()
                    font.setBold(True)
                    font.setItalic(True)
                    font.setUnderline(True)
                    table.item(row, col_to_mark).setFont(font)
            elif str(esfid) in m2m.keys():
                for col_to_mark in m2m[str(esfid)]:
                    table.item(row, col_to_mark).setBackground(QColor('yellow'))
                    table.item(row, col_to_mark).setForeground(QColor("red"))
                    font = QtGui.QFont()
                    font.setBold(True)
                    font.setItalic(True)
                    font.setUnderline(True)
                    table.item(row, col_to_mark).setFont(font)

    table.resizeColumnsToContents()
    table.setSortingEnabled(True)


def write_qtable_to_df(table):
    col_count = table.columnCount()
    row_count = table.rowCount()
    headers = [str(table.horizontalHeaderItem(i).text()) for i in range(col_count)]

    # df indexing is slow, so use lists
    df_list = []
    for row in range(row_count):
        df_list2 = []
        for col in range(col_count):
            table_item = table.item(row, col)
            df_list2.append('' if table_item is None else str(table_item.text()))
        df_list.append(df_list2)

    df = pd.DataFrame(df_list, columns=headers)
    return df


def change_pw():
    def save_clicked():
        username = combo_user.currentText()
        if combo_user.currentIndex() < 0:
            rberi_lib.QMessageBoxB('ok', 'User auswählen!', "Kein User ...", qss=bd.get_qss()).exec_()
            ui.reject()

        pw_old = input_pw_old.text()
        pw_new = input_pw_new.text()
        pw_wdh = input_pw_wdh.text()
        lvl = combo_level.currentText()

        password = pd.read_sql("SELECT password FROM benutzer WHERE username = '" + combo_user.currentText() + "'",
                               engine).iloc[0]
        f_ = Fernet(bd.get_key())
        token_ = f_.decrypt(password[0])
        pw_old_saved = token_.decode()
        token_new_pw = f_.encrypt(pw_new.encode())

        if pw_old_saved != pw_old:
            rberi_lib.QMessageBoxB('ok', 'Falsches (altes) Passwort!', "Passwort inkorrekt", qss=bd.get_qss()).exec_()
            ui.reject()

        if pw_new != pw_wdh:
            rberi_lib.QMessageBoxB('ok', 'Neues Passwort und dessen Wiederholung nicht identisch.',
                                   "Passwort inkorrekt", qss=bd.get_qss()).exec_()
            ui.reject()

        cursor = engine.cursor()
        cursor.execute("UPDATE benutzer SET password = %s, level = %s WHERE username = %s", (token_new_pw, lvl, username))
        engine.commit()
        cursor.close()
        ui.accept()
        return

    def user_changed():
        u_level = pd.read_sql("SELECT level FROM benutzer WHERE username = '" + combo_user.currentText() + "'",
                              engine).iloc[0]
        combo_level.setCurrentText(str(u_level[0]))

    level = df_benutzer["level"].tolist()
    level.sort()
    level_ = []
    for el in level:
        if str(el) not in level_:
            level_.append(str(el))
    level = level_

    ui = QDialog()
    combo_user = QComboBox()
    combo_user.addItems(df_benutzer['username'].tolist())
    combo_level = QComboBox()
    combo_level.addItems(level)
    input_pw_new = QLineEdit()
    input_pw_new.setEchoMode(QLineEdit.Password)
    input_pw_wdh = QLineEdit()
    input_pw_wdh.setEchoMode(QLineEdit.Password)
    input_pw_old = QLineEdit()
    input_pw_old.setEchoMode(QLineEdit.Password)
    btn_save = QPushButton("Speichern")
    btn_cancel = QPushButton("Abbrechen")

    layout = QGridLayout(ui)
    layout.addWidget(QLabel("Benutzer:"), 0, 0)
    layout.addWidget(combo_user, 0, 1)
    layout.addWidget(QLabel("Passwort alt:"), 1, 0)
    layout.addWidget(input_pw_old, 1, 1)
    layout.addWidget(QLabel("Passwort neu:"), 2, 0)
    layout.addWidget(input_pw_new, 2, 1)
    layout.addWidget(QLabel("Passwort-Wdh:"), 3, 0)
    layout.addWidget(input_pw_wdh, 3, 1)
    layout.addWidget(QLabel("Userlevel:"), 4, 0)
    layout.addWidget(combo_level, 4, 1)
    layout.addWidget(btn_cancel, 5, 0)
    layout.addWidget(btn_save, 5, 1)

    user_changed()
    btn_save.clicked.connect(save_clicked)
    combo_user.currentIndexChanged.connect(user_changed)
    btn_cancel.clicked.connect(ui.reject)

    ui.exec_()


def iter_tree_widget(root):
    iterator = QTreeWidgetItemIterator(root)
    while True:
        item = iterator.value()
        if item is not None:
            yield item
            iterator += 1
        else:
            break


def drive_from_mask(mask):
    n_drive = 0
    while 1:
        if mask & (2 ** n_drive):
            return n_drive
        else:
            n_drive += 1


def logout(bemerkung=""):
    logging(window.get_current_user(), datetime.now(), "logout", bemerkung)


def logging(user_bmi, zeitstempel, action, bemerkung):
    pd.read_sql("SELECT * FROM login_logging", engine)
    cursor_new = engine.cursor()
    cursor_new.execute("INSERT INTO login_logging (username, timestamp, action, text) VALUES (%s, %s, %s, %s)",
                       (user_bmi, zeitstempel, action, bemerkung))
    engine.commit()
    cursor_new.close()


def get_connection_status(connection):
    try:
        connection.ping()
    except Exception as excp:
        print(f"Exception: {excp}")
        return False
    return True


def db_connection(_host, _user, password, _port, _database):
    try:
        return mariadb.connect(user=_user, password=password, host=_host, port=_port, database=_database)
    except mariadb.Error as excp:
        rberi_lib.QMessageBoxB("ok",
                               "Es konnte keine Verbindung zur Datenbank aufgebaut werden. Daher wird nun das "
                               "Einstellungsfenster geöffnet um die Datenbankverbindung zu konfigurieren. Versuche es danach "
                               "erneut.",
                               "Datenbankfehler",
                               ["Exception:", str(excp)], qss=bd.get_qss()).exec_()
        settings = Ui_Settings(nocon=True)
        settings.exec_()
        sys.exit(0)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    try:
        bd = BD('./basic_definitions.ini')
        f = Fernet(bd.get_key())
        token = f.decrypt(bd.get_p())
        pw = token.decode()
        host = bd.get_host()
        user = bd.get_user()
        port = bd.get_port()
        database = bd.get_database()

        if pw != '':
            engine = db_connection(host, user, pw, port, database)
            # cursor = engine.cursor()
            # lieber vor jedem Bedarf erzeugen und danach direkt wieder schließen.
            df_benutzer = pd.read_sql("SELECT * FROM benutzer", engine)
            current_u = CurrentUser()
            form = Loginpage(df_benutzer, current_u)

            # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5()) --> dafür muss wieder qdarkstyle importiert werden

            if not bd.get_mit_anmeldung():
                form.auto_login('admin')
                window = MainWindow(current_u)

                # window = ImageViewer()
                window.showMaximized()
                sys.exit(app.exec_())
            else:
                if form.exec_() == QtWidgets.QDialog.Accepted:
                    print(f"current_u = {current_u.getuser()}")
                    window = MainWindow(current_u)
                    window.showMaximized()
                    sys.exit(app.exec_())

    except Exception as e:
        logout(f"schwerwiegender Fehler: {e}")
