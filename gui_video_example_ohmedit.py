from dlclive import DLCLive, Processor
import numpy as np
import serial, cv2, sys, os, json, pickle
from pypylon import pylon, genicam
import time
from datetime import datetime, date 

from multiprocessing import Process
from threading import Thread

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from qt_material import apply_stylesheet


class Gui_updater(QThread):
    update_image = pyqtSignal(np.ndarray)
    def __init__(self):
        super().__init__()
        self._gui_run_flag = True
        self.vid = pylon.InstantCamera()
        with open('settings.json', 'r') as json_settings:
            settings = json.load(json_settings)
        self.settings = settings['camera']
        

    def grab_single_image(self):
        self.setup()
        grab = self.vid.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
        if grab.GrabSucceeded():
            frame = grab.GetArray()
            self.process_frame(frame)
        self.vid.Close()

    def run(self):
        self.setup()
        while self._gui_run_flag:
            grab = self.vid.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
            if grab.GrabSucceeded():
                frame = grab.GetArray()
                self.process_frame(frame)
        self.vid.Close()
    
    def setup(self):
        w, h, ox, oy = self.settings.values()
        tl = pylon.TlFactory.GetInstance();self.vid.Attach(tl.CreateFirstDevice());self.vid.Open()
        self.vid.Width.SetValue(w);self.vid.Height.SetValue(h);self.vid.OffsetX.SetValue(ox);self.vid.OffsetX.SetValue(oy)
        
        # self.vid.UserSetSelector.SetValue(pylon.UserSetSelector_AutoFunctions)

        self.vid.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    def process_frame(self, frame):
        qframe = QImage(frame, frame.shape[1], frame.shape[0], QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qframe)
        self.update_image.emit(pixmap)

    def stop(self):
        self._gui_run_flag=False
        self.wait()

class hslider(QWidget):
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
        self.sl.valueChanged.connect(self.slider_updates_text)

        self.layout.addWidget(self.lbl);self.layout.addWidget(self.txt);self.layout.addWidget(self.sl)
        self.setLayout(self.layout)


    def slider_updates_text(self):
        self.txt.setText(f'{self.sl.sliderPosition()}')

    def text_updates_slider(self):
        self.sl.setSliderPosition(float(self.txt.text()))

class vslider(QWidget):
    def __init__(self, sname, smin:int, smax:int, sstep:float, startval, orientation = Qt.Orientation.Horizontal):
        super().__init__()  

        self.name = sname
        self.layout = QVBoxLayout()
        self.start = startval;self.step = sstep;self.min = smin; self.max = smax

        self.lbl = QLabel(alignment = Qt.AlignmentFlag.AlignCenter, text = f'{self.name}')
        self.lbl.setFixedHeight(20)


        self.txt = QLineEdit(alignment = Qt.AlignmentFlag.AlignCenter, text = f'{self.start}')
        self.txt.setValidator(QIntValidator((smin-1), (smax+1)))
        self.txt.setFixedWidth(50)
        self.txt.editingFinished.connect(self.text_updates_slider)


        self.sl = QSlider(orientation)
        self.sl.setMinimum(smin);self.sl.setMaximum(smax);self.sl.setTickInterval(sstep);self.sl.setTickPosition(QSlider.TickPosition(3));self.sl.setValue(self.start)
        self.sl.setFixedHeight(50)
        self.sl.valueChanged.connect(self.slider_updates_text)

        self.layout.addWidget(self.lbl);self.layout.addWidget(self.txt);self.layout.addWidget(self.sl)
        self.setLayout(self.layout)

    def slider_updates_text(self):
        self.txt.setText(f'{self.sl.sliderPosition()}')

    def text_updates_slider(self):
        self.sl.setSliderPosition(int(self.txt.text()))    

class QGB(QGridLayout):
    def __init__(self):
        super().__init__()
        self.groups = ["video setup", "experiment setup", "controls setup", "execute exp"]

        #these are all the push changes buttons that need to be callable, therefore defined here GROUPED
        #video setup
        self.push_vschanges = QPushButton(text = f'Push \'{self.groups[0]}\' Changes?')
        #experiment setup 
        self.change_filepath = QPushButton(text = 'click here to select filepath')
        self.path_label = QLabel(text = 'please select filepath (none selected)')
        self.push_eschanges = QPushButton(text = f'Push \'{self.groups[1]}\' Changes?')
        #controls setup
        self.push_cschanges = QPushButton(text = f'Push \'{self.groups[2]}\' Changes?')
        #experiment execution
        self.start = QPushButton(text = 'Start Experiment')
        self.stop = QPushButton(text = 'Stop Experiment')

        #vertical spacer box for any vertical spacing, with height 25
        self.vspacer = QWidget();self.vspacer.setFixedHeight(25)

        self.gboxes = [self.gbox(i) for i in range(4)]


    def vs_layout(self):
        vs_layout = QVBoxLayout()
        
        Xdim_vid = hslider('X dim:', 0, 784, 784/20, 455)
        Ydim_vid = hslider('Y dim:', 0, 582, 582/20, 455)

        Xpos_vid = hslider('X pan:', -100, 100, 10, 0)
        Ypos_vid = hslider('Y pan:', -100, 100, 10, 0)

        vs_layout.addWidget(Xdim_vid);vs_layout.addWidget(Ydim_vid);vs_layout.addWidget(self.vspacer);vs_layout.addWidget(Xpos_vid);vs_layout.addWidget(Ypos_vid);vs_layout.addWidget(self.push_vschanges)
        return vs_layout
    
    def es_layout(self):
        es_layout = QVBoxLayout()

        es_layout.addWidget(self.change_filepath);es_layout.addWidget(self.path_label);es_layout.addWidget(self.push_eschanges)
        return es_layout

    def cs_layout(self):
        cs_layout = QVBoxLayout()

        shock_setup = vslider('Shock Magnitude (mA/10, or 10^-4 A):', 1, 40, 1, 5)

        rotation_setup = vslider('Rotation Speed (rpm):', 1, 25, 1, 5)

        cs_layout.addWidget(shock_setup);cs_layout.addWidget(rotation_setup);cs_layout.addWidget(self.push_eschanges)
        return cs_layout
     
    def ee_layout(self):
        ee_layout = QVBoxLayout()

        ee_layout.addWidget(self.start);ee_layout.addWidget(self.stop)
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

class Maze_Controller(QWidget):
    def __init__(self):
        super().__init__()
        if not os.path.exists('./settings.json'):
            print('Missing settings file ... Loading defaults')
            with open('default_settings.json', 'r') as default_settings:
                self.settings = json.load(default_settings)
            #loads the settings from the default file and saves them to a new settings file since there is none
            with open('settings.json', 'w') as outfile:
                json.dump(self.settings, outfile)
        else:
            print('Found settings file')
            with open('settings.json', 'r') as json_settings:
                self.settings = json.load(json_settings)
        # self.vid = pylon.InstantCamera();self.setup()
        # self.conv = pylon.ImageFormatConverter()

        # self.windowTitle('MazeController')
        self.showFullScreen()
        self.exit= QAction("Exit Application",shortcut=QKeySequence("Esc"),triggered=self.close)
        self.addAction(self.exit)
        apply_stylesheet(app, theme='dark_cyan.xml')

        
        self.tabs = QTabWidget()

        self.tab_names = ['livestream', 'buttons']

        livestream_layout = QVBoxLayout()
        livestream_widget = QWidget()
        livestream_lbl =  QLabel()
        livestream_lbl.setFixedWidth(self.settings['camera']['width']);livestream_lbl.setFixedHeight(self.settings['camera']['height'])
        self.data_table = QTableWidget();self.data_table.setRowCount(3);self.data_table.setColumnCount(3);self.data_table.setHorizontalHeaderLabels(['X', 'Y', 'prob.']);self.data_table.setVerticalHeaderLabels(['nose', 'center', 'tail'])
        self.data_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        livestream_layout.addWidget(livestream_lbl, Qt.AlignmentFlag.AlignCenter);livestream_layout.addWidget(self.data_table, Qt.AlignmentFlag.AlignCenter)
        livestream = QWidget();livestream.setLayout(livestream_layout)
        
        self.grid = QGB()
        buttons =  QWidget();buttons.setLayout(self.grid)
        
        # self.tabs.addTab(self.livestream, 'livestream')
        
        self.tab_dict = {'livestream':livestream, 'buttons':buttons}

        for i in self.tab_names:
            self.tabs.addTab(self.tab_dict[i], i)
            
        self.main_layout = QHBoxLayout();self.main_layout.addWidget(self.tabs)
        self.setLayout(self.main_layout)

        self.wdir = os.path.dirname(os.path.realpath(__file__))
        self.grid.change_filepath.clicked.connect(self.pathprompt)


    def button_setup(self):
        self.grid.push_vschanges.clicked.connect()
        self.grid.push_eschanges.clicked.connect()
        self.grid.push_vschanges.clicked.connect()
        self.grid.start.clicked.connect()
        self.grid.stop.clicked.connect()
        self.grid.change_filepath.clicked.connect()

    def main_processing(self):
        #get Qthreadpool to keep gui up to date
        self.gui_thread = Gui_updater()
        self.gui_thread.update_image.connect(self.gui_update)
        self.gui_thread.start()

    def shutdown_routine(self):
        print("Shutdown Routine Activated")
        #add all shutdown commands here
        self.gui_thread.stop()
        self.close()
        return
    
    @pyqtSlot(np.ndarray)
    def gui_update(self, Qframe):
        Qframe = cv2.cvtColor(Qframe, cv2.COLOR_BGR2RGB)
        Qframe = QImage(Qframe, Qframe.shape[1], Qframe.shape[0], Qframe.strides[0],QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(Qframe)
        self.display_camera.setPixmap(pixmap)

    def pathprompt(self):
        options = QFileDialog.Option.ShowDirsOnly
        dlg = QFileDialog();dlg.setOptions(options);dlg.setFileMode(QFileDialog.FileMode.Directory)
        file = dlg.getOpenFileName(caption='select the working directory for your project');fname = file[0]
        self.wdir = fname
        msg = f'the working directory is: \"{str(fname)}\"'
        self.grid.path_label.setText(msg)
    
    def calculation(self, dlc):
        time.sleep(1)
        return



if __name__ == '__main__':
    app = QApplication(sys.argv)
    Maze = Maze_Controller()
    Maze.show()
    app.exec()
