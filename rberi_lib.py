# -*- coding: utf-8 -*-
from datetime import date, timedelta
from typing import Literal

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QTextCursor
from PyQt5.QtWidgets import QMessageBox, QWidget, QTableWidget, QStyledItemDelegate, QTextEdit


class ReadOnlyDelegate(QStyledItemDelegate):
    def createEditor(self, *args, **kwargs):
        return


class OwnTable(QTableWidget):
    """
    Eigene Tabelle für die RIngserienpflege bei der das Editieren nicht möglich ist, aber bestimmte
    Mausklicks:
    Rechtsklick auf Spalte Status ermöglicht eine Umschaltung von 0 zu 3 und von 3 zu 0

    """
    status_changed = pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        QTableWidget.__init__(self, *args, **kwargs)
        self.setItemDelegate(ReadOnlyDelegate(self))
        self.kombi = 0
        self.row_clicked = 0
        self.col_clicked = 0

    def punch(self):
        self.status_changed.emit(True)

    def free_to_fire(self) -> bool:
        prio_items = self.findItems('-1', Qt.MatchExactly)
        if len(prio_items) == 0:
            return True
        else:
            return False

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            it = self.itemAt(event.pos())
            if not isinstance(it, type(None)):
                if it.column() == 6 and it.text() != '1' and it.text() != '2':
                    if self.horizontalHeaderItem(it.column()).text() == "Status":
                        if it.text() == '0':
                            it.setText('3')
                        elif it.text() == '3' or it.text() == '-1':
                            it.setText('0')
                    self.punch()
                    self.kombi += 1
                    self.row_clicked = it.row()
                    self.col_clicked = it.column()
                else:
                    self.kombi = 0
                    self.row_clicked = 0
                    self.col_clicked = 0
        if event.button() == Qt.MouseEventCreatedDoubleClick:
            it = self.itemAt(event.pos())
            if not isinstance(it, type(None)):
                if it.column() == 4 and it.row() == self.row_clicked and self.free_to_fire() and self.kombi > 0:
                    self.item(it.row(), self.col_clicked).setText('-1')
                else:
                    self.kombi = 0
                    self.row_clicked = 0
                    self.col_clicked = 0
        QTableWidget.mousePressEvent(self, event)


class QMessageBoxB(QMessageBox):
    def __init__(self,
                 typ: Literal['ok', 'yn', 'ny', 'ync', 'nyc', 'cyn', 'cny'] = 'ok',
                 text: str | None = "",
                 title: str | None = "Information",
                 det_t: str | list | None = None,
                 *args,
                 **kwargs):
        super().__init__()
        self.setText(text)
        self.setWindowTitle(title)

        if isinstance(det_t, str):
            self.setDetailedText(det_t)
        elif isinstance(det_t, list):
            txt = ""
            for el in det_t:
                try:
                    txt += str(el).strip()
                    txt += "\n"
                except Exception as excp:
                    raise excp
            self.setDetailedText(txt)
        elif isinstance(det_t, type(None)):
            pass
        else:
            txt = f"{det_t}"
        if typ == "ok":
            self.setStandardButtons(QMessageBox.Ok)
        elif typ == "yn":
            self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            self.setDefaultButton(QMessageBox.Yes)
        elif typ == "ny":
            self.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            self.setDefaultButton(QMessageBox.No)
        elif typ == "ync":
            self.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            self.setDefaultButton(QMessageBox.Yes)
        elif typ == "nyc":
            self.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            self.setDefaultButton(QMessageBox.No)
        elif (typ == "cyn") or (typ == "cny"):
            self.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            self.setDefaultButton(QMessageBox.Cancel)

        if kwargs:
            for kw in kwargs:
                if kw == 'icontyp':
                    if kwargs[kw] == 'Warning':
                        self.setIcon(QMessageBox.Warning)
                    elif kwargs[kw] == 'Question':
                        self.setIcon(QMessageBox.Question)
                    elif kwargs[kw] == 'Information':
                        self.setIcon(QMessageBox.Information)
                    elif kwargs[kw] == 'Critical':
                        self.setIcon(QMessageBox.Critical)
                    else:
                        self.setIcon(QMessageBox.NoIcon)
                if kw == 'qss':
                    try:
                        with open(kwargs[kw], "r") as fh:
                            self.setStyleSheet(fh.read())
                    except Exception:
                        pass


class UI_MainW(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("Grafik")
        MainWindow.resize(500, 400)
        if self:
            pass


class GrafikHolder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = UI_MainW()
        self.ui.setupUi(self)


def monday_of_calenderweek(year, week):
    first = date(year, 1, 1)
    base = 1 if first.isocalendar()[1] == 1 else 8
    return first + timedelta(days=base - first.isocalendar()[2] + 7 * (week - 1))


def saturday_of_calenderweek(year, week):
    first = date(year, 1, 1)
    base = 1 if first.isocalendar()[1] == 1 else 6
    return first + timedelta(days=base - first.isocalendar()[2] + 7 * (week - 1))


def check_float(element: str, zero_or_empty_returns_true: bool = False):
    element = element.replace(",", ".")
    partition = element.partition(".")

    if zero_or_empty_returns_true:
        if element is None or element == '':
            check_add = True
        else:
            check_add = False
    else:
        check_add = False

    if element.isdigit() or check_add:
        return True
    elif (
            (partition[0].isdigit() and partition[1] == "." and partition[2].isdigit())
            or (partition[0] == "" and partition[1] == "." and partition[2].isdigit())
            or (partition[0].isdigit() and partition[1] == "." and partition[2] == "")
    ):
        return True
    else:
        return False


def return_float(el: str):
    if check_float(el, zero_or_empty_returns_true=True):
        el_new = el.replace(",", ".")
        if el is None or el == '':
            return 0.0
        try:
            return float(el_new)
        except ValueError:
            raise ValueError(f"{el_new} ist kein Float.")
    else:
        return 0.0


class Stadium(QWidget):
    def __init__(self, pixmap, parent=None):
        QWidget.__init__(self, parent=parent)
        self.pixmap = pixmap
        self.pos = None
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.pixmap)
        painter.setPen(QPen(Qt.red, 15, Qt.SolidLine))
        if self.pos:
            painter.drawEllipse(self.pos, 15, 15)

    def mouseMoveEvent(self, event):
        self.pos = event.pos()
        self.update()


class QTextEditFeedback(QTextEdit):
    def __init__(self, maxTextLength: int = 5000, parent=None):
        QTextEdit.__init__(self, parent=parent)
        self.maxTextLength = maxTextLength
        self.setTabChangesFocus(True)
        self.textChanged.connect(self.__textChanged)
        self.diff = maxTextLength

    def __textChanged(self):
        self.diff = self.maxTextLength - len(self.toPlainText())
        if self.diff >= 0:
            return
        new_txt = self.toPlainText()
        new_txt = new_txt[:self.maxTextLength]
        self.setText(new_txt)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def set_max_text_length(self, val: int = 5000):
        self.maxTextLength = val

    def get_max_text_length(self):
        return self.maxTextLength

    def get_diff(self):
        return self.diff


