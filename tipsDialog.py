# -*- coding: utf-8 -*-
import random
from random import randrange

from PyQt5.QtWidgets import QDialog, QMessageBox
from Beringungsoberflaeche.tips import Ui_Dialog


class TipsDialog(QDialog):
    def __init__(self, list_of_tips: list, qss):
        super().__init__()
        self.ui = Ui_Dialog()
        with open(qss, "r") as fh:
            self.setStyleSheet(fh.read())
        self.ui.setupUi(self)
        self.ui.LBL_tip.setStyleSheet("""
                                    font-size: 14px;
                                """)
        self.tips = list_of_tips
        if len(self.tips) == 0:
            self.ui.LBL_tip.setText("Keine Tipps zum Anzeigen.")
            self.ui.BTN_next.setEnabled(False)

        self.no_tips_anymore = False

        # connections:
        self.ui.BTN_close.clicked.connect(self.close_dialog)
        self.ui.CHB_notips.toggled.connect(self.notips)
        self.ui.BTN_next.clicked.connect(self.next_tip)

        self.next_tip()

    def next_tip(self):
        if len(self.tips) > 0:
            self.ui.LBL_tip.setText(self.tips.pop(randrange(len(self.tips))))
        else:
            self.ui.LBL_tip.setText("Keine weiteren Tipps zum Anzeigen.")

    def notips(self):
        if self.ui.CHB_notips.isChecked():
            self.no_tips_anymore = True
        else:
            self.no_tips_anymore = False

    def close_dialog(self):
        if self.no_tips_anymore:
            self.reject()
        else:
            self.accept()
        # super().close()
