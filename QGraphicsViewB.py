# -*- coding: utf-8 -*-
from PyQt5 import QtCore
from PyQt5.QtWidgets import QGraphicsView
import keyboard


class QGraphicsViewB(QGraphicsView):
    def __init__(self, parent=None, **kwargs):
        super().__init__(parent)
        self._zoom = 0

    def wheelEvent(self, event):
        if len(self.items()) > 0 and keyboard.is_pressed('Ctrl'):
            # print('keyboard_is_pressed (CTRL) funktioniert!')
            if event.angleDelta().y() > 0:
                faktor = 1.1
                self._zoom += 1
            elif event.angleDelta().y() < 0:
                faktor = 0.9
                self._zoom -= 1
            self.scale(faktor, faktor)
        return super().wheelEvent(event)


