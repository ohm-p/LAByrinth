# from dlclive import DLCLive, Processor
import numpy as np
import serial, cv2, sys, os, json, pickle
# from pypylon import pylon, genicam
import time
from datetime import datetime, date 

from multiprocessing import Process
from threading import Thread

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from qt_material import apply_stylesheet

class settings():
    sig = pyqtSignal()
    def __init__(self):
        if not os.path.exists('./settings.json'):
            print('Missing settings file ... Loading defaults')
            with open('defaults.json', 'r') as default_settings:
                self.settings = json.load(default_settings)
            #loads the settings from the default file and saves them to a new settings file since there is none
            with open('settings.json', 'w') as outfile:
                json.dump(self.settings, outfile)
        else:
            print('Found settings file')
            with open('settings.json', 'r') as json_settings:
                self.settings = json.load(json_settings)
        self._open_flag_ = False

    def pull(self, inds:tuple):
        if len(inds) == 1:
            i, = inds
            return self.settings[i]
        elif len(inds) == 2:
            i, j, = inds
            return self.settings[i][j]
        else:
            print('you attempted to pull settings that don\'t exist')
            return self.settings

    def push_c(self, values:tuple):
        if np.size(values) == len(self.settings['video']):
            self.settings['video'] = dict([(list(self.settings['video'].keys())[i], values[i]) for i in range(len(self.settings['video']))])
        else:
            sys.exit('attempted passing settings of incorrect size')

    def push_v(self, values:tuple):
        if np.size(values) == len(self.settings['controls']):
            self.settings['controls'] = dict([(list(self.settings['controls'].keys())[i], values[i]) for i in range(len(self.settings['controls']))])
        else:
            sys.exit('attempted passing settings of incorrect size')

    def save_settings_func(self):
        if not self._open_flag_:
            if os.path.exists('./settings.json'):
                with open('settings.json', 'w') as outfile:
                    json.dump(self.settings, outfile)
                    print('changed current settings file')
            else:
                with open('settings.json', 'w') as outfile:
                    json.dump(self.settings, outfile)
                    print('no \'settings.json\' exists. new file created and settings saved')
            self._open_flag_ = True
        else:
            sys.exit('trying to write to the same \'settings.json\' file in multiple statements')
        

class processor(QObject):
    frm = pyqtSignal(np.ndarray)
    
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self._run_flag = False
        path = "C:\\Users\\ohmkp\\OneDrive\\Desktop\\vids\\"
        # path = "C:\\tracking_system\\_OHM\\vids\\"
        self.dt = datetime.strftime(datetime.now(), "d%y.%m.%d_t%H.%M")
        # fourcc = cv2.VideoWriter_fourcc(*'mp4v');fps = 30.0;frameSize = (1290, 720)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v');fps = 30.0;frameSize = (455, 455)
        vid_path = path +  self.dt + "_recording.mp4"
        self.out = cv2.VideoWriter(vid_path, fourcc, fps, frameSize)
        self.setup();self.vid.release();print('camera successfully initiated')

        self.commands = [[0x01, None], #1: rotation setup: default counter clockwise, 4-100rpm
        [0x02, 0x01], #2: rotate, 0x01 to start
        [0x02, 0x00], #3: rotate, 0x00 to stop
        [0x03, None], #4: shock current, (1-40)/10 mA (enter an integer)
        [0x04, 0x01], #5: shock, 0x01 to start
        [0x04, 0x00]] #6: shock, 0x00 to stop

        ###DLC setup
        # self.dlc_processor = Processor()
        # self.dlc_live = DLCLive(self.model_path)
        self.marker_dims = (7,7)

        self.colors = [(0,255,171), (171,0,255), (212, 255,0)]
        self.center = (self.settings.pull(('video', 'x_center',)), self.settings.pull(('video', 'y_center',)))
        

    def grab_single(self):
        self.setup()
        ret, frame = self.vid.read()
        print('preview successful')
        if ret:
            mod_frame = self.mobile_process(frame)
            self.frm.emit(mod_frame)
        else:
            sys.exit('cam failed to cap frame')
        print('successfully grabbed single')
        self.vid.release()
        
    def grab_stream(self):
        self.setup()
        self._run_flag = True
        while self._run_flag:
            ret, frame = self.vid.read()  
            if ret:
                print("___")
                mod_frame = self.mobile_process(frame)
                self.frm.emit(mod_frame)
                self.out.write(frame)
            else:
                sys.exit('cam failed to cap frame')
        print('successfully grabbed stream')
        self.vid.release()

    def change_settings(self, new_settings):
        self.settings.settings = new_settings
        self.h, self.w, self.x_off, self.y_off, self.x_cen, self.y_cen = self.settings.pull(('video',)).values()
        self.setup()

    def setup(self):
        self.h, self.w, self.x_off, self.y_off, self.x_cen, self.y_cen = self.settings.pull(('video',)).values()
        self.vid = cv2.VideoCapture(0)
        self.vid.set(cv2.CAP_PROP_FRAME_WIDTH, self.w)
        if not self.vid.isOpened():
            self.vid.open(0)
    
    
    def mobile_process(self, frame):
        mod_frame = frame.copy()
        mod_frame = cv2.resize(mod_frame, (self.h, self.w))
        cv2.ellipse(mod_frame, (self.center, (13,13), 0), (0,0,0), -1)
        return mod_frame        

    def in_sector(self, x, y):
        # time.sleep(0)
        vec_1 = np.array([x, y])
        vec_2 = self.mag/2
        diff = vec_1 - vec_2;ratio = diff[1]/diff[0]
        theta = np.degrees(np.arctan(ratio))
        # true if calculated theta is in the 60 degree sector from -30 to 30 degrees
        if (theta < 30 and theta > -30):
            #boolean output for the shock function
            return True
        
    # simplified command function, see previous version for legacy (eliminated 5 other commands and simplified process)
    def command(self, inp):
         d2, d3 = self.commands[inp - 1]
         d0 = 0xaa
         d1 = 0xbb
         d4 = 0x00
         d5 = (d2 + d3 + d4) & 0xff
         d6 = 0xcc
         d7 = 0xdd 
         
         #creates a list that will be converted to a byte array
         l = [d0, d1, d2, d3, d4, d5, d6, d7]
         
         return bytearray(l)
    
    def shockandrotation_setup(self, shock, rotation):
        self.commands[0][1] = shock
        self.commands[3][1] = rotation

        shock_setup_command = self.command(4)
        rotation_setup_command = self.command(1)

    

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
        self.sl.setMinimum(smin);self.sl.setMaximum(smax);self.sl.setTickInterval(int(sstep));self.sl.setTickPosition(QSlider.TickPosition(3));self.sl.setValue(self.start)
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
    def __init__(self, settings):
        super().__init__()
        self.settings = settings
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
        self.preview  = QPushButton(text = 'click to preview')
        self.stop = QPushButton(text = 'Stop Experiment')
        self.savesettings = QPushButton(text = 'save current settings to \'settings.json\'')

        #vertical spacer box for any vertical spacing, with height 25
        self.vspacer = QWidget();self.vspacer.setFixedHeight(25)

        self.gboxes = [self.gbox(i) for i in range(4)]

 #######################################################################################################


    def vs_layout(self):
        vs_layout = QVBoxLayout()
        h, w, x_off, y_off, x_cen, y_cen = self.settings.pull(('video',)).values()

        self.Xdim_vid = hslider('X dim:', 0, 711, 1000/20, h)
        self.Ydim_vid = hslider('Y dim:', 0, 582, 1000/20, w)

        self.Xpos_vid = hslider('X pan:', -100, 100, 10, x_off)
        self.Ypos_vid = hslider('Y pan:', -100, 100, 10, y_off)

        
        self.Xcenter_vid = hslider('X of center pt:', 0, 784, 1, x_cen)
        self.Ycenter_vid = hslider('Y of center pt:', 0, 582, 1, y_cen)

        vs_layout.addWidget(self.Xdim_vid);vs_layout.addWidget(self.Ydim_vid);vs_layout.addWidget(self.vspacer);vs_layout.addWidget(self.Xpos_vid);vs_layout.addWidget(self.Ypos_vid);vs_layout.addWidget(self.vspacer);vs_layout.addWidget(self.Xcenter_vid);vs_layout.addWidget(self.Ycenter_vid);vs_layout.addWidget(self.push_vschanges)
        return vs_layout
    
    def es_layout(self):
        es_layout = QVBoxLayout()

        es_layout.addWidget(self.change_filepath);es_layout.addWidget(self.path_label);es_layout.addWidget(self.push_eschanges)
        return es_layout

    def cs_layout(self):
        cs_layout = QVBoxLayout()

        self.shock_setup = vslider('Shock Magnitude (mA/10, or 10^-4 A):', 1, 40, 1, 5)

        self.rotation_setup = vslider('Rotation Speed (rpm):', 1, 25, 1, 5)

        cs_layout.addWidget(self.shock_setup);cs_layout.addWidget(self.rotation_setup);cs_layout.addWidget(self.push_eschanges)
        return cs_layout
     
    def ee_layout(self):
        ee_layout = QVBoxLayout()

        ee_layout.addWidget(self.start);ee_layout.addWidget(self.preview);ee_layout.addWidget(self.stop);ee_layout.addWidget(self.savesettings)
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
    


class Maze_Controller(QWidget,QObject):
    def __init__(self):
        super().__init__()

    # self.vid = pylon.InstantCamera();self.setup()
    # self.conv = pylon.ImageFormatConverter()
        self.settings = settings()

        self.setWindowTitle('MazeController')
        self.showFullScreen()
        self.exit= QAction("Exit Application",shortcut=QKeySequence("Esc"),triggered=self.shutdown_routine)
        self.addAction(self.exit)
        apply_stylesheet(app, theme='dark_cyan.xml')
        self.tabs = QTabWidget()
        self.tab_names = ['livestream', 'buttons']
        livestream_layout = QVBoxLayout()
        livestream_widget = QWidget()
        self.livestream_lbl =  QLabel();self.livestream_lbl.setMinimumHeight(200)
        # self.livestream_lbl.setFixedWidth(self.settings.pull(('video','width',)));self.livestream_lbl.setFixedHeight(self.settings.pull(('video','height',)))
        self.data_table = QTableWidget();self.data_table.setRowCount(3);self.data_table.setColumnCount(3);self.data_table.setHorizontalHeaderLabels(['X', 'Y', 'prob.']);self.data_table.setVerticalHeaderLabels(['nose', 'center', 'tail'])
        self.data_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        livestream_layout.addWidget(self.livestream_lbl, Qt.AlignmentFlag.AlignCenter);livestream_layout.addWidget(self.data_table, Qt.AlignmentFlag.AlignCenter)
        livestream_widget.setLayout(livestream_layout)
        self.grid = QGB(settings = self.settings)
        buttons =  QWidget();buttons.setLayout(self.grid)
        self.tab_dict = {'livestream':livestream_widget, 'buttons':buttons}
        for i in self.tab_names:
            self.tabs.addTab(self.tab_dict[i], i)
        self.main_layout = QHBoxLayout();self.main_layout.addWidget(self.tabs)
        self.setLayout(self.main_layout)
        self.processor = processor(self.settings)
        self.processor.frm.connect(self.display_frame)
    
        # self.tabs.addTab(self.livestream, 'livestream')

        self.preview_thread = QThread()
        self.stream_thread = QThread()
        self.button_setup()
        # self.main_processing()
        


    def button_setup(self):
        self.grid.push_vschanges.clicked.connect(self.push_videosetup_changes)
        self.grid.push_cschanges.clicked.connect(self.push_controlssetup_changes)
        # self.grid.push_eschanges.clicked.connect(self.pathprompt)
        self.grid.start.clicked.connect(self.main_processing)
        self.grid.preview.clicked.connect(self.preview)
        self.grid.savesettings.clicked.connect(self.settings.save_settings_func)
        self.grid.stop.clicked.connect(self.shutdown_routine)
        # self.grid.change_filepath.clicked.connect(self.pathprompt)

    def main_processing(self):
        #get Qthreadpool to keep gui up to date       
        self.processor.moveToThread(self.stream_thread)
        self.stream_thread.started.connect(self.processor.grab_stream)
        self.stream_thread.start()
        # self.push_controlssetup_changes()
        # self.processor.command(2)


    def preview(self):
        self.processor.moveToThread(self.preview_thread)
        self.preview_thread.started.connect(self.processor.grab_single)
        self.preview_thread.start()

    def shutdown_routine(self):
        #add all shutdown commands here
        self.processor.vid.release()
        self.processor.out.release()
        self.stream_thread.exit();self.preview_thread.exit()
        # self.close()
        sys.exit('shutdown routine activated')    
    

    @pyqtSlot(np.ndarray)
    def display_frame(self, frame):
        Qframe = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        Qframe = QImage(Qframe, Qframe.shape[1], Qframe.shape[0], Qframe.strides[0],QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(Qframe)
        self.livestream_lbl.setPixmap(pixmap)

    def push_videosetup_changes(self):
        a = self.grid.Xdim_vid.sl.value()
        b = self.grid.Ydim_vid.sl.value()
        c = self.grid.Xpos_vid.sl.value()
        d = self.grid.Ypos_vid.sl.value()
        e = self.grid.Xcenter_vid.sl.value()
        f = self.grid.Ycenter_vid.sl.value()
        self.settings.push_v((a, b, c, d, e, f))

    def push_controlssetup_changes(self):
        a = self.grid.shock_setup.sl.value()
        b = self.grid.rotation_setup.sl.value()
        print(a, b)
        self.processor.shockandrotation_setup(a, b)
        self.settings.push_c((a, b))
        print((a, b).size)


    @pyqtSlot()
    def save_settings(self):
        if os.path.exists('./settings.json'):
            with open('settings.json', 'w') as outfile:
                json.dump(self.settings.settings, outfile)
                print('changed current settings file')
        else:
            with open('settings.json', 'w') as outfile:
                json.dump(self.settings.settings, outfile)
                print('no \'settings.json\' exists. new file created and settings saved')





if __name__ == '__main__':
    app = QApplication(sys.argv)
    Maze = Maze_Controller()
    Maze.show()
    app.exec()
    
