from PyQt6.QtCore import QDateTime, Qt, QTimer, QRegularExpression
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

class slider(QWidget):
    def __init__(self, sname, smin:int, smax:int, sstep:float, startval, orientation = Qt.Orientation.Horizontal):
        super().__init__()  

        self.name = sname
        self.layout = QHBoxLayout()
        self.start = startval

        self.lbl = QLabel(alignment = Qt.AlignmentFlag.AlignLeft, text = f'{self.name}')
        self.lbl.setFixedWidth(50)


        self.txt = QLineEdit(alignment = Qt.AlignmentFlag.AlignCenter, text = f'{self.start}')
        self.txt.setValidator(QIntValidator((smin-1), (smax+1)))
        self.txt.setFixedWidth(50)
        self.txt.editingFinished.connect(self.text_updates_slider)


        self.sl = QSlider(orientation)
        self.sl.setMinimum(smin);self.sl.setMaximum(smax);self.sl.setTickInterval(sstep);self.sl.setTickPosition(QSlider.TickPosition(3));self.sl.setValue(self.start)
        self.sl.setFixedWidth(200)
        self.sl.sliderReleased.connect(self.slider_updates_text)


        self.layout.addWidget(self.lbl);self.layout.addWidget(self.txt);self.layout.addWidget(self.sl)
        self.setLayout(self.layout)

    def slider_updates_text(self):
        self.txt.setText(f'{self.sl.sliderPosition()}')

    def text_updates_slider(self):
        self.sl.setSliderPosition(float(self.txt.text()))
    


class QGB(QGridLayout):
    def __init__(self):
        super().__init__()
        self.groups = ["video setup", "experiment setup", "controls setup", "execute exp"]
        self.gboxes = [self.gbox(i) for i in range(4)]

    def vs_layout(self):
        vs_layout = QVBoxLayout()
        
        Xdim_vid = slider('X dim:', 0, 784, 784/20, 455)
        Ydim_vid = slider('Y dim:', 0, 582, 582/20, 455)

        Xpos_vid = slider('X pan:', -100, 100, 10, 0)
        Ypos_vid = slider('Y pan:', -100, 100, 10, 0)

        vs_layout.addWidget(Xdim_vid);vs_layout.addWidget(Ydim_vid);vs_layout.addWidget(QWidget());vs_layout.addWidget(Xpos_vid);vs_layout.addWidget(Ypos_vid)
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
    
    def gbox(self, ind):
        name = self.groups[ind]
        box = QGroupBox(name)
        if ind == 0:
            box.setLayout(self.vs_layout())
            self.addWidget(box, 0, 0)
        elif ind == 1:
            box.setLayout(self.es_layout())
            self.addWidget(box, 1, 0)
        elif ind == 2:
            box.setLayout(self.cs_layout())
            self.addWidget(box, 0, 1)
        elif ind == 3:
            box.setLayout(self.ee_layout())
            self.addWidget(box, 1, 1)
        else:
            sys.exit('you messed up the setup')
        ##insert other func here
        return box






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


