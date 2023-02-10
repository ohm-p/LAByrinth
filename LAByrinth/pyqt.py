from PyQt6.QtCore import QDateTime, Qt, QTimer
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
        QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget, QMainWindow)
from PyQt6.QtGui import QImage, QPixmap
import sys
from pypylon import pylon, genicam
import cv2
import numpy as np


class QGB(QGridLayout):
    def __init__(self):
        super().__init__()
        self.groups = ["video setup", "experiment setup", "controls setup", "execute exp"]
        self.gboxes = []

        for i in self.groups:
            box =  QGroupBox(i)
            layout =  QVBoxLayout()
            box.setLayout(layout)
            self.gboxes.append(box)
        # self.setup_buttons()

        for i in range(2):
            for j in range(2):
                ind = i + j
                self.addWidget(self.gboxes[ind], i, j)

        def gbox(self, ind):
            name = self.groups[ind]
            box = QGroupBox(i)
            ##insert other func here
            return box
        
        def vs_layout(self):
            vs_layout = QVBoxLayout()
            
            Xdim_vid = QSlider(Qt.Orientation.Horizontal);Xdim_vid.setMaximum(784);Xdim_vid.setMinimum(0)
            Xdim_vid.setTickInterval(8);Xdim_vid.setTickPosition(QSlider.tickPosition(3))
            Ydim_vid = QSlider(Qt.Orientation.Horizontal);Ydim_vid.setMaximum(582);Ydim_vid.setMinimum(0)
            Ydim_vid.setTickInterval(6);Ydim_vid.setTickPosition(QSlider.tickPosition(3))

            Xpos_vid = 
            return vs_layout
        def es_layout(self):
            es_layout = QVBoxLayout()
            return es_layout
        def cs_layout(self):
            cs_layout = QVBoxLayout()
            return cs_layout 
        def ee_layout(self):
            ee_layout = QVBoxLayout()
            return ee_layout





class MazeGUI(QWidget):
    def __init__(self):
        super().__init__()
        # self.vid = pylon.InstantCamera();self.setup()
        # self.conv = pylon.ImageFormatConverter()

        # self.windowTitle('MazeController')
        self.setGeometry(0,0,500,500)
        
        self.tabs = QTabWidget()

        self.tab_names = ['livestream', 'buttons']

        livestream_lbl =  QLabel();
        livestream_layout = QHBoxLayout();livestream_layout.addWidget(livestream_lbl)
        livestream = QWidget();livestream.setLayout(livestream_layout)
        
        buttons =  QWidget();buttons.setLayout(QGB())
        
        # self.tabs.addTab(self.livestream, 'livestream')
        
        self.tab_dict = {'livestream':livestream, 'buttons':buttons}

        for i in self.tab_names:
            self.tabs.addTab(self.tab_dict[i], i)
            
        self.main_layout = QHBoxLayout();self.main_layout.addWidget(self.tabs)
        self.setLayout(self.main_layout)


    def setup(self):
        tl = pylon.TlFactory.GetInstance();self.vid.Attach(tl.CreateFirstDevice());self.vid.Open()
        self.vid.Width.SetValue(455);self.vid.Height.SetValue(455);self.vid.OffsetX.SetValue(77)
        
        # self.vid.UserSetSelector.SetValue(pylon.UserSetSelector_AutoFunctions)

        self.vid.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    def main(self):
        grab = self.vid.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
        while True:
            if grab.GrabSucceeded():
                frm = grab.GetArray()
            else:
                sys.exit('cam failed')
                break

            s, s = frm.shape
            img = QImage(frm.data, s, s, QImage.Format.Format_Mono)
            cv2.imshow('live video', frm)
            


QApplication.setStyle(QStyleFactory.create('fusion'))
app =  QApplication(sys.argv)


win = MazeGUI()
# win.main()
win.show()

app.exec()


