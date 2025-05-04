import sys

from PyQt5.QtWidgets import (QLabel, QMessageBox, QScrollArea, QWidget, QSizePolicy, QApplication)
from PyQt5.QtGui import (QGuiApplication, QImageReader, QPalette, QPixmap)
from PyQt5.QtCore import Qt


ABOUT = """<p>The <b>Image Viewer</b> example shows how to combine QLabel
and QScrollArea to display an image. QLabel is typically used
for displaying a text, but it can also display an image.
QScrollArea provides a scrolling view around another widget.
If the child widget exceeds the size of the frame, QScrollArea
automatically provides scroll bars. </p><p>The example
demonstrates how QLabel's ability to scale its contents
(QLabel.scaledContents), and QScrollArea's ability to
automatically resize its contents
(QScrollArea.widgetResizable), can be used to implement
zooming and scaling features. </p><p>In addition the example
shows how to use QPainter to print an image.</p>
"""


class _QScrollArea(QScrollArea):
    def __init__(self, parent=QWidget):
        super().__init__(parent)
        self._scale_factor = 1.0
        self._image_label = QLabel()
        self._image_label.setBackgroundRole(QPalette.Base)
        self._image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setWidget(self._image_label)

    def wheelEvent(self, event):
        if (event.modifiers() & Qt.ControlModifier):
            if event.angleDelta().y() > 0:
                self._zoom_in()
            else:
                self._zoom_out()
        else:
            super().wheelEvent(event)

    def adjustLabel(self):
        self._image_label.adjustSize()
        self._image_label.setScaledContents(True)

    def _zoom_in(self):
        self._scale_image(1.15)

    def _zoom_out(self):
        self._scale_image(0.85)

    def _set_image(self, new_image):
        self._image = new_image
        self._image_label.setPixmap(QPixmap.fromImage(self._image))
        self.adjustLabel()

    def _normal_size(self):
        self._image_label.adjustSize()
        self._scale_factor = 1.0

    def _scale_image(self, factor):
        self._scale_factor *= factor
        print(f"factor in _scale_image wird übergeben und ist = {factor}")
        print(f"self._scale_factor += factor = {self._scale_factor}")
        new_size = self._scale_factor * self._image_label.pixmap().size()
        print(f"newsize = {new_size}")
        self._image_label.resize(new_size)
        self._adjust_scrollbar(self.horizontalScrollBar(), factor)
        self._adjust_scrollbar(self.verticalScrollBar(), factor)

    def _adjust_scrollbar(self, scrollBar, factor):
        pos = int(factor * scrollBar.value() + ((factor - 1) * scrollBar.pageStep() / 2))
        scrollBar.setValue(pos)


class ImageViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setGeometry(100, 100, 800, 600)
        self.setObjectName("ImageViewer")
        self.setWindowTitle("Details")
        self.pic_w = 0
        self._scroll_area = _QScrollArea(self)
        self._scroll_area.setBackgroundRole(QPalette.Dark)
        self.resize(QGuiApplication.primaryScreen().availableSize() * 3 / 5)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self._scroll_area.resize(self.width(), self.height())
        if self.pic_w >0:
            self._scroll_area._normal_size()
            self._scroll_area._scale_image((self.width()-20)/self.pic_w)

    def load_file(self, fileName):
        reader = QImageReader(fileName)
        reader.setAutoTransform(True)
        new_image = reader.read()
        self._scroll_area._set_image(new_image)
        self.pic_w = new_image.width()
        self._scroll_area._scale_image((self.width()-20)/self.pic_w)
        return True

    def _about(self):
        QMessageBox.about(self, "About Image Viewer", ABOUT)


"""app = QApplication(sys.argv)
window = ImageViewer()
window.show()
window.load_file("C:\\Users\\wicht\\PycharmProjects\\DB_connection\\Bilder\\Amsel\\Amsel01_Barth.png")
sys.exit(app.exec_())"""



