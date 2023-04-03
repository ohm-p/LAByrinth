import numpy as np
import serial, cv2, sys, os, json, pickle
import time
from time import sleep

from multiprocessing import Process
from threading import Thread

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from qt_material import apply_stylesheet
import random

class settings(QObject):
    sig = pyqtSignal(dict)
    def __init__(self):
        super().__init__()
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

    def push_v(self, values:tuple):
        if np.size(values) == len(self.settings['video'].values()):
            self.settings['video'] = dict([(list(self.settings['video'].keys())[i], values[i]) for i in range(len(self.settings['video']))])
        else:
            sys.exit('attempted passing settings of incorrect size')
        self.sig.emit(self.settings)

    def push_c(self, values:tuple):
        if np.size(values) == len(self.settings['controls']):
            self.settings['controls'] = dict([(list(self.settings['controls'].keys())[i], values[i]) for i in range(len(self.settings['controls']))])
        else:
            sys.exit('attempted passing settings of incorrect size')
        self.sig.emit(self.settings)

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
    fin = pyqtSignal()
    pose_arr = pyqtSignal(np.ndarray)
    
    def __init__(self, settings):
        super().__init__()
        self.main_thread = QThread.currentThread()
        self.settings = settings
        self._run_flag = False
        self.setup();print('camera successfully initiated')
        # path = "C:\\Users\\ohmkp\\OneDrive\\Desktop\\vids\\"
        path = "C:\\tracking_system\\_OHM\\vids\\"
        self.dt = time.strftime(r"d%y.%m.%d_t%H.%M")
        fourcc = cv2.VideoWriter_fourcc(*'MJPG');fps = 30.0;frameSize = (int(self.vid.get(3)), int(self.vid.get(4)))
        vid_path = path +  self.dt + "_recording.avi"
        self.poses_path = path + self.dt + "_poses.txt"
        self.times_path = path + self.dt + "_times.txt"
        self.out = cv2.VideoWriter(vid_path, fourcc, fps, frameSize)
        self.shock_on = False
        self.times = []
        self.poses = []

        self.commands = [[0x01, None], #1: rotation setup: default counter clockwise, 4-100rpm
        [0x02, 0x01], #2: rotate, 0x01 to start
        [0x02, 0x00], #3: rotate, 0x00 to stop
        [0x03, None], #4: shock current, (1-40)/10 mA (enter an integer)
        [0x04, 0x01], #5: shock, 0x01 to start
        [0x04, 0x00]] #6: shock, 0x00 to stop



        ###DLC setup
        self.marker_dims = (7,7)

        self.colors = [(0,255,171), (171,0,255), (212, 255,0)]
        self.center = (self.settings.pull(('video', 'x_center',)), self.settings.pull(('video', 'y_center',)))
        self.angle_center = self.settings.pull(('controls', 'sector_center'))
        self.settings.sig.connect(self.update_settings)

        self.init_pose()
        
    @pyqtSlot(dict)
    def update_settings(self, new_settings):
        self.settings.settings = new_settings


    def model_startup(self):
        self.grab_single()

    def grab_single(self):
        self.setup()
        ret, frame = self.vid.read()
        print('preview successful')
        if ret:
            mod_frame = self.idle_process(frame)
            self.frm.emit(mod_frame)
        else:
            sys.exit('cam failed to cap frame')
        self.vid.release()
        sleep(1);self.fin.emit()
        
    def grab_stream(self):
        self.setup()
        self._run_flag = True
        while self._run_flag:
            ret, frame = self.vid.read()
            if ret:
                mod_frame = self.mobile_process(frame)
                self.frm.emit(mod_frame)
            else:
                sys.exit('cam failed to cap frame')
        self.vid.release()
        sleep(1);self.fin.emit()

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

    def idle_process(self, frame):
        mod_frame = frame.copy()
        cv2.ellipse(mod_frame, (self.center, (13,13), 0), (0,0,0), -1)
        return mod_frame      


    def mobile_process(self, frame):
        mod_frame = frame.copy()
        cv2.ellipse(mod_frame, (self.center, (13,13), 0), (0,0,0), -1)
        self.out.write(frame)
        self.pose_arr.emit(self.init_pose())
        for i in range(3):
            coords = (int(self.pose[i, 0]), int(self.pose[i, 1]))
            cv2.ellipse(mod_frame, (coords, self.marker_dims, 0), self.colors[i], -1)
        return mod_frame        

    def in_sector(self, x, y):
        vec_1 = np.array([x, y])
        vec_2 = self.res/2
        diff = vec_1 - vec_2;ratio = diff[1]/diff[0]
        theta = np.degrees(np.arctan(ratio))
        # true if calculated theta is in the 60 degree sector from centered around the value pulled from settings
        upper = self.angle_center + 30; lower = self.angle_center - 30
        if (theta < upper and theta > lower):
            #boolean output for the shock function
            return True
        
    # simplified command function, see previous version for legacy (eliminated 5 other commands and simplified process)
    def command(self, inp):
         d2, d3 = self.commands[int(inp) - 1]
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

    def reset_thread(self):
       self.moveToThread(self.main_thread)

    def init_pose(self):
        lis = []
        for i in range(3):
            current = [int(random.randint(0, 500)), int(random.randint(0, 500)), random.random()]
            lis.append(current)
        self.pose = np.array(lis)   
        return(self.pose)
 

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
        self.sl.setSliderPosition(int(self.txt.text()))

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
        self.preview = QPushButton(text = 'click to preview')
        self.stop = QPushButton(text = 'Stop Experiment')
        self.savesettings = QPushButton(text = 'save current settings to \'settings.json\'')

        #vertical spacer box for any vertical spacing, with height 25
        self.vspacer = QWidget();self.vspacer.setFixedHeight(25)

        self.gboxes = [self.gbox(i) for i in range(4)]

        self.settings.sig.connect(self.update_settings)

    @pyqtSlot(dict)
    def update_settings(self, new_settings):
        self.settings.settings = new_settings


    def vs_layout(self):
        vs_layout = QVBoxLayout()
        h, w, x_off, y_off, x_cen, y_cen = self.settings.pull(('video',)).values()

        self.Xdim_vid = hslider('X dim:', 0, 582, 1000/20, h)
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

        self.sector_center = vslider('Center of the sector (+/- 30deg):', 0, 360, 1, 0)

        cs_layout.addWidget(self.shock_setup);cs_layout.addWidget(self.rotation_setup);cs_layout.addWidget(self.sector_center);cs_layout.addWidget(self.push_cschanges)
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
        self.main_thread = QThread.currentThread()
        self.settings = settings()

        self.setWindowTitle('MazeController')
        self.showFullScreen()
        self.exit= QAction("Exit Application",shortcut=QKeySequence("Esc"),triggered=self.shutdown_routine)
        self.addAction(self.exit)
        apply_stylesheet(app, theme='dark_cyan.xml')
        self.tabs = QTabWidget()
        livestream_layout = QVBoxLayout()
        livestream_widget = QWidget()
        self.livestream_lbl =  QLabel()
        self.livestream_lbl.setFixedWidth(self.settings.pull(('video','width',)));self.livestream_lbl.setFixedHeight(self.settings.pull(('video','height',)))
        self.data_table = QTableWidget();self.data_table.setRowCount(3);self.data_table.setColumnCount(3);self.data_table.setHorizontalHeaderLabels(['X', 'Y', 'prob.']);self.data_table.setVerticalHeaderLabels(['nose', 'center', 'tail'])
        self.data_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        livestream_layout.addWidget(self.livestream_lbl, Qt.AlignmentFlag.AlignCenter);livestream_layout.addWidget(self.data_table, Qt.AlignmentFlag.AlignCenter)
        livestream_widget.setLayout(livestream_layout)
        self.grid = QGB(settings = self.settings)
        buttons =  QWidget();buttons.setLayout(self.grid)
        self.tab_dict = {'livestream':livestream_widget, 'buttons':buttons}
        for k, v in self.tab_dict.items():
            self.tabs.addTab(v, k)
        self.main_layout = QHBoxLayout();self.main_layout.addWidget(self.tabs)
        self.setLayout(self.main_layout)
    
        # self.tabs.addTab(self.livestream, 'livestream')

        self.wdir = os.path.dirname(os.path.realpath(__file__))
        self.grid.change_filepath.clicked.connect(self.pathprompt)
    
        self.processor = processor(settings = self.settings)
        self.processor.frm.connect(self.display_frame)
        self.processor.fin.connect(self.thread_fin);self.processor.fin.connect(self.reenable_startandpreview_buttons)
        self.preview_thread = QThread();self.stream_thread = QThread();self.model_startup_thread = QThread()
        self.button_setup()
        self.disable_startandpreview_buttons()
        self.model_startup()
        self.settings.sig.connect(self.update_settings)

    @pyqtSlot(dict)
    def update_settings(self, new_settings):
        self.settings.settings = new_settings

    def button_setup(self):
        self.grid.push_vschanges.clicked.connect(self.push_videosetup_changes)
        self.grid.push_cschanges.clicked.connect(self.push_controlssetup_changes)
        self.grid.push_eschanges.clicked.connect(self.pathprompt)
        self.grid.savesettings.clicked.connect(self.settings.save_settings_func)
        self.grid.start.clicked.connect(self.main_processing)
        self.grid.preview.clicked.connect(self.preview)
        self.grid.stop.clicked.connect(self.shutdown_routine)
        self.grid.change_filepath.clicked.connect(self.pathprompt)
        self.grid.start.clicked.connect(self.disable_startandpreview_buttons);self.grid.preview.clicked.connect(self.disable_startandpreview_buttons)
        self.processor.pose_arr.connect(self.update_pose_table)

    def pathprompt(self):
        options = QFileDialog.Option.ShowDirsOnly
        dlg = QFileDialog();dlg.setOptions(options);dlg.setFileMode(QFileDialog.FileMode.Directory)
        file = dlg.getOpenFileName(caption='select the working directory for your project');fname = file[0]
        self.wdir = fname
        msg = f'the working directory is: \"{str(fname)}\"'
        self.grid.path_label.setText(msg)

    def main_processing(self):
        # self.stream_thread.finished.disconnect();self.stream_thread.started.disconnect()
        self.push_controlssetup_changes()
        self.processor.moveToThread(self.stream_thread)
        self.stream_thread.started.connect(self.processor.grab_stream)
        self.stream_thread.start()
 
    def preview(self):
        # self.preview_thread.finished.disconnect();self.preview_thread.started.disconnect()
        self.processor.moveToThread(self.preview_thread)
        self.preview_thread.started.connect(self.processor.grab_single)
        self.preview_thread.start()
    
    def model_startup(self):
        # self.isSignalConnected(self.getsignal)
        # model_startup_thread.finished.
        # self.model_startup_thread.finished.disconnect();self.model_startup_thread.started.disconnect()
        #as encountered in a previous iteration, a special function called 'init_inference' must be called to instanitate the tensorflow ('tf') object -- idk
        self.processor.moveToThread(self.model_startup_thread)
        self.model_startup_thread.started.connect(self.processor.model_startup)
        self.model_startup_thread.start()

    def thread_fin(self):
        thread = self.processor.thread()
        if thread != self.main_thread:
            thread.quit()
            thread.started.disconnect()
            # thread.finished.disconnect()
            thread.started.connect(self.processor.reset_thread)
            thread.finished.connect(thread.quit)
            thread.start()
            sleep(1)
        else:
            print('\'processor\' object is already in the main thread')

        if self.processor.thread() == self.main_thread:
            print('processor location successfully reset to self.main_thread')
        thread.finished.disconnect();thread.started.disconnect()
        print('connections of thread reset')


    def shutdown_routine(self):
        self.stream_thread.quit();self.preview_thread.quit();self.model_startup_thread.quit()
        self.processor.vid.release()
        self.processor.out.release()
        self.settings.save_settings_func()

        # self.close()
        sys.exit('shutdown routine activated')    
    

    @pyqtSlot(np.ndarray)
    def display_frame(self, frame):
        Qframe = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        Qframe = QImage(Qframe, Qframe.shape[1], Qframe.shape[0], Qframe.strides[0],QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(Qframe)
        self.livestream_lbl.setPixmap(pixmap)

    @pyqtSlot(np.ndarray)
    def update_pose_table(self, pose):
        if pose.shape == (3, 3):
            for i in range(3):
                for j in range(3):
                    new_item = QTableWidgetItem(str(pose[i][j]))
                    self.data_table.setItem(i, j, new_item)
        else:
            self.shutdown_routine()
            # sys.exit('a pose of incorrect dimensions was passed: expected dimensions were (3x3)')

    def push_videosetup_changes(self):
        a = self.grid.Xdim_vid.sl.value()
        b = self.grid.Ydim_vid.sl.value()
        c = self.grid.Xpos_vid.sl.value()
        d = self.grid.Ypos_vid.sl.value()
        e = self.grid.Xcenter_vid.sl.value()
        f = self.grid.Ycenter_vid.sl.value()
        self.settings.push_v((a, b, c, d, e, f))
        print('successfully pushed video setup changes')

    def push_controlssetup_changes(self):
        a = self.grid.shock_setup.sl.value()
        b = self.grid.rotation_setup.sl.value()
        c = self.grid.sector_center.sl.value()
        self.processor.shockandrotation_setup(a, b)
        self.settings.push_c((a, b, c))
        print('successfully pushed controls setup changes')


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

    def reenable_startandpreview_buttons(self):
        self.grid.start.setEnabled(True)
        self.grid.preview.setEnabled(True)

    def disable_startandpreview_buttons(self):
        self.grid.start.setEnabled(False)
        self.grid.preview.setEnabled(False)





if __name__ == '__main__':
    app = QApplication(sys.argv)
    Maze = Maze_Controller()
    Maze.show()
    app.exec()
    
