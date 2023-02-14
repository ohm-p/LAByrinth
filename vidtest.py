from PyQt6.QtCore import QDateTime, Qt, QTimer, QRegularExpression, QThread, pyqtSignal, pyqtSlot, QObject
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget, QMainWindow)
from PyQt6.QtGui import QImage, QPixmap, QIntValidator
from PyQt6 import QtCore, QtGui, QtWidgets
import sys
from pypylon import pylon, genicam
import cv2
import numpy as np
from time import sleep


class stream(QMainWindow):
    def __init__(self):
        super().__init__()
        #GUI STUFF
        self.name = 'live video stream'
        self.setGeometry(0,0,1000,1000)
        self.win = QWidget()
        self.layout = QVBoxLayout()
        self.frame = QLabel()
        self.layout.addWidget(self.frame)
        self.win.setLayout(self.layout)
        self.setCentralWidget(self.win)

        #CAMERA STUFF
        self.vid = pylon.InstantCamera();self.setup()
        self.conv = pylon.ImageFormatConverter()

        #THREADING
        self.thread = QThread()
        self.worker = self.run()
        self.worker.moveToThread(self.thread)

    def main(self):        
        self.thread.start()

    @pyqtSlot()
    class run(QObject):
        def __init__(self):
            super().__init__()
        
        def run(self):
            while True:
                grab = self.vid.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
                if grab.GrabSucceeded():
                    frm = grab.GetArray()
                else:
                    sys.exit('cam failed')
                    break
                # h, w = frame.shape
                img = QPixmap(QPixmap.loadFromData(frm))
                self.frame.setPixmap(img)


    def setup(self):
        tl = pylon.TlFactory.GetInstance();self.vid.Attach(tl.CreateFirstDevice());self.vid.Open()
        self.vid.Width.SetValue(455);self.vid.Height.SetValue(455);self.vid.OffsetX.SetValue(77)
        self.vid.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)


app =  QApplication(sys.argv)


win = stream()
win.main()

app.exec()