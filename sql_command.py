# -*- coding: utf-8 -*-
import datetime
import sqlalchemy as sa
import pandas as pd
from PyQt5.QtCore import QDate, Qt, QAbstractTableModel, QVariant

import rberi_lib
from PyQt5.QtWidgets import QDialog, QFileDialog, QButtonGroup, QTableWidgetItem, QWidget, QTableView, QHeaderView
from Beringungsoberflaeche.SQL_GUI import Ui_Form


class SQL_command(QWidget):
    def __init__(self, db_eng: sa.Engine, debug: bool = False, current_user: str = "reit", parent=None, **kwargs):
        super().__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.TBL_result.setStyleSheet("""
            font-size: 11px;
        """)

        self.engine = db_eng
        self.debug = debug
        self.user = current_user

        self.esf_fields = pd.DataFrame()
        try:
            self.esf_fields = pd.read_sql("DESCRIBE esf", self.engine)
        except Exception as err:
            rberi_lib.QMessageBoxB("yn", "Datenbankfehler. Siehe Details.", "Datenbankfehler", str(err)).exec_()
            return

        self.ui.LST_table_content.addItems(self.esf_fields['Field'])

        # Connections:
        self.ui.BTN_export.clicked.connect(self.export)
        self.ui.BTN_close.clicked.connect(self.close)
        self.ui.LE_sql_command.returnPressed.connect(self.sql)

    def export(self):
        save_path = str(QFileDialog.getExistingDirectory(None, "Select Directory"))
        save_path = save_path.replace("/", "\\")
        filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M") + "_" + self.user + "_SQL_Befehl"
        complete_filename = '{0}\\{1}{2}'.format(save_path, filename, '.csv')
        try:
            self.get_table_as_df().to_csv(complete_filename, header=True, index=True)
        except PermissionError as excp:
            rberi_lib.QMessageBoxB('ok', "Keine Berechtigung zum Speichern in diesem Verzeichnis.",
                                   "Berechtigung", excp.strerror).exec_()
        except FileNotFoundError as excp:
            rberi_lib.QMessageBoxB('ok', "Verzeichnis nicht gefunden. Bitte erneut versuchen.",
                                   "Kein Verzeichnis", excp.strerror).exec_()

    def get_table_as_df(self, **kwargs):
        number_of_rows = self.ui.TBL_result.rowCount()
        number_of_columns = self.ui.TBL_result.columnCount()
        items = []
        for x in range(self.ui.TBL_result.columnCount()):
            if self.ui.TBL_result.horizontalHeaderItem(x) is not None:
                items.append(self.ui.TBL_result.horizontalHeaderItem(x).text())
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
            if self.ui.TBL_result.item(i, 0) is None and not copymode:
                self.ui.TBL_result.removeRow(i)
                continue
            for j in range(number_of_columns):
                try:
                    if self.ui.TBL_result.item(i, j) is not None:
                        tmp_df.iloc[i, j] = int(self.ui.TBL_result.item(i, j).text())
                    else:
                        tmp_df.iloc[i, j] = None
                except ValueError:
                    try:
                        if self.ui.TBL_result.item(i, j) is not None:
                            tmp_df.iloc[i, j] = pd.to_datetime(self.ui.TBL_result.item(i, j).text()).dt.date
                        else:
                            tmp_df.iloc[i, j] = None
                    except Exception as excp:
                        if self.ui.TBL_result.item(i, j) is not None:
                            tmp_df.iloc[i, j] = self.ui.TBL_result.item(i, j).text()
                        else:
                            tmp_df.iloc[i, j] = None
                        if self.debug:
                            print(f"Exception: {excp}")

        tmp_df = tmp_df.set_index([tmp_df.columns[0]])
        return tmp_df

    def sql(self):
        self.ui.TBL_result.setSortingEnabled(False)
        erstes_wort = self.ui.LE_sql_command.text().split()[0]
        if not "select" in erstes_wort.lower():
            rberi_lib.QMessageBoxB('ok', "Aktuell wird nur der SELECT Befehl zugelassen...", "Select fehlt.", "Hättest wohl "
                                                                                                              "gerne, "
                                                                                                              "was? Nix da!").exec_()
            return

        try:
            df = pd.read_sql(self.ui.LE_sql_command.text(), self.engine)
        except Exception as err:
            self.ui.LBL_status.setText("Status-Message: " + str(err))
            return
        self.ui.LBL_status.setText("Status-Message: Abfrage ok!")

        self.ui.TBL_result.setRowCount(df.shape[0])
        self.ui.TBL_result.setColumnCount(df.shape[1])
        j = 0
        for i in df.columns.tolist():
            self.ui.TBL_result.setHorizontalHeaderItem(j, QTableWidgetItem(i))
            j += 1

        for row, content in df.iterrows():
            i = 0
            for col, cont in content.items():
                _item = QTableWidgetItem()
                _item.setData(Qt.DisplayRole, cont)
                self.ui.TBL_result.setItem(row, i, _item)
                i += 1

        self.ui.TBL_result.resizeColumnsToContents()
        self.ui.TBL_result.setSortingEnabled(True)



