from dlclive import DLCLive, Processor
import numpy as np
import serial, cv2, sys, os, json, pickle
from pypylon import pylon, genicam
import time
from time import sleep

from multiprocessing import Process
from threading import Thread

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from qt_material import apply_stylesheet

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
    pose_arr = pyqtSignal(np.ndarray)
    times_up = pyqtSignal()
    
    def __init__(self, model_path, settings, main_thread):
        super().__init__()
        self.main_thread = main_thread
        if os.path.exists(model_path):
            self.model_path = model_path
        else:
            sys.exit('error selecting the correct model.')
        
        self.settings = settings
        self._run_flag = False
        self.setup();print('camera successfully initiated')
        grab = self.vid.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
        if grab.GrabSucceeded():
            self.W = grab.Width
            self.H = grab.Height
        else:
            sys.exit('init grab failed, please make sure the camera is connected')
        # path = "C:\\Users\\ohmkp\\OneDrive\\Desktop\\vids\\"
        path = "C:\\tracking_system\\_OHM\\vids\\"
        self.dt = time.strftime(r"d%y.%m.%d_t%H.%M")
        fourcc = cv2.VideoWriter_fourcc(*'XVID');fps = int(30.0);frameSize = (self.H, self.W)
        print(frameSize)
        vid_path = path +  self.dt + "_recording.avi"
        self.poses_path = path + self.dt + "_poses.npy"
        self.times_path = path + self.dt + "_times.txt"
        # self.out = cv2.VideoWriter(vid_path, fourcc, fps, frameSize)
        self.out = cv2.VideoWriter(vid_path, cv2.VideoWriter_fourcc(*'MJPG'), fps, frameSize)
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
        self.dlc_processor = Processor()
        self.dlc_live = DLCLive(self.model_path)
        self.marker_dims = (7,7)

        self.ser = serial.Serial();self.ser.port= 'COM5';self.ser.baudrate = 115200   
        self.ser.open()
        self.colors = [(0,255,171), (171,0,255), (212, 255,0)]
        self.center = (self.settings.pull(('video', 'x_center',)), self.settings.pull(('video', 'y_center',)))
        self.angle_center = self.settings.pull(('controls', 'sector_center'))
        self.settings.sig.connect(self.update_settings)
        self.trial_duration = None
        
    @pyqtSlot(dict)
    def update_settings(self, new_settings):
        self.settings.settings = new_settings


    def grab_single(self):
        self.setup()
        grab = self.vid.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
        if grab.GrabSucceeded():
            self.W = grab.Width
            self.H = grab.Height
            frame = grab.Array
            mod_frame = self.idle_process(frame)
            self.frm.emit(mod_frame)
        else:
            sys.exit('cam failed to cap frame')
        grab.Release()
        self.vid.Close()
        self.thread().quit()
        
    def grab_stream(self):
        self.setup()
        self._run_flag = True
        while self._run_flag:
            grab = self.vid.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
            if grab.GrabSucceeded():
                frame = grab.Array
                mod_frame = self.stream_process_retention(frame)
                self.frm.emit(mod_frame)
            else:
                sys.exit('cam failed to cap frame')
                break
            self.check_time()
        grab.Release()
        self.vid.Close()
        self.thread().quit()

    def model_startup(self):
        self.setup()
        grab = self.vid.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
        if grab.GrabSucceeded():
            frame = grab.Array
            pose = self.dlc_live.init_inference(frame)
            mod_frame = np.dstack((frame, frame, frame))
            for i in range(3):
                coords = (int(pose[i, 0]), int(pose[i, 1]))
                cv2.ellipse(mod_frame, (coords, self.marker_dims, 0), self.colors[i], -1)
            self.frm.emit(mod_frame)
        else:
            sys.exit('cam failed to cap frame')
        grab.Release()
        self.vid.Close()
        self.thread().quit()

    def change_settings(self, new_settings):
        self.settings.settings = new_settings
        self.h, self.w, self.x_off, self.y_off, self.x_cen, self.y_cen = self.settings.pull(('video',)).values()
        self.setup()

    def setup(self):
        self.h, self.w, self.x_off, self.y_off, self.x_cen, self.y_cen = self.settings.pull(('video',)).values()
        self.res = np.array((self.w, self.h))
        self.vid = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice());self.vid.Open()
        self.vid.Width.SetValue(self.w);self.vid.Height.SetValue(self.h)
        self.vid.OffsetX.SetValue(self.x_off);self.vid.OffsetY.SetValue(self.y_off)
        self.vid.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    def idle_process(self, frame):
        pose = self.dlc_live.get_pose(frame) 
        mod_frame = np.dstack((frame, frame, frame))
        for i in range(3):
            coords = (int(pose[i, 0]), int(pose[i, 1]))
            cv2.ellipse(mod_frame, (coords, self.marker_dims, 0), self.colors[i], -1)
        cv2.ellipse(mod_frame, (self.center, (13,13), 0), (0,0,0), -1)
        self.pose_arr.emit(pose)
        print(pose.shape)
        return mod_frame      

    def stream_process_retention(self, frame):
        pose = self.dlc_live.get_pose(frame) 
        triple_frame = np.dstack((frame, frame, frame));mod_frame = triple_frame.copy()
        self.out.write
        for i in range(3):
            coords = (int(pose[i, 0]), int(pose[i, 1]))
            cv2.ellipse(mod_frame, (coords, self.marker_dims, 0), self.colors[i], -1)
        cv2.ellipse(mod_frame, (self.center, (13,13), 0), (0,0,0), -1)
        if(self.in_sector(pose[0,0], pose[0,1])
            and self.in_sector(pose[1,0], pose[1,1])
            and self.in_sector(pose[2,0], pose[2,1])):
                #the subject is in the sector, so shock is delivered (turned on if off)
                cv2.ellipse(mod_frame, ((15, 15), (10, 10), 0), (255, 0, 0), -1)
                if not self.shock_on:
                    self.start_shock = time.perf_counter()
                    self.shock_on = True
                                
        else:
                #shock is not delivered since the subject is not in the sector (turned off if on)
                if self.shock_on:
                    self.end_shock = time.perf_counter()
                    self.end_time = time.strftime("%H.%M.%S")
                    self.shock_on = False
                    #notes the time that the shock ended, subtracts from start and adds to the array
                    diff = self.end_shock - self.start_shock
                    self.times.append([self.end_time, diff])
        self.out.write(triple_frame)
        self.poses.append(pose)
        self.pose_arr.emit(pose)
        return mod_frame  

    def stream_process(self, frame):
        self.trial_start_time = time.perf_counter()
        pose = self.dlc_live.get_pose(frame) 
        triple_frame = np.dstack((frame, frame, frame));mod_frame = triple_frame.copy()
        self.out.write
        for i in range(3):
            coords = (int(pose[i, 0]), int(pose[i, 1]))
            cv2.ellipse(mod_frame, (coords, self.marker_dims, 0), self.colors[i], -1)
        cv2.ellipse(mod_frame, (self.center, (13,13), 0), (0,0,0), -1)
        if(self.in_sector(pose[0,0], pose[0,1])
            and self.in_sector(pose[1,0], pose[1,1])
            and self.in_sector(pose[2,0], pose[2,1])):
                #the subject is in the sector, so shock is delivered (turned on if off)
                cv2.ellipse(mod_frame, ((15, 15), (10, 10), 0), (255, 0, 0), -1)
                if not self.shock_on:
                    self.ser.write(self.command(5))
                    self.start_shock = time.perf_counter()
                    self.start_time = time.perf_counter() - self.trial_start_time
                    self.shock_on = True
                                
        else:
                #shock is not delivered since the subject is not in the sector (turned off if on)
                if self.shock_on:
                    self.ser.write(self.command(6))
                    self.end_shock = time.perf_counter()
                    self.shock_on = False
                    #notes the time that the shock ended, subtracts from start and adds to the array
                    diff = self.end_shock - self.start_shock
                    self.times.append([self.start_time, diff])
        self.out.write(triple_frame)
        self.poses.append(pose)
        self.pose_arr.emit(pose)
        return mod_frame        

    def in_sector(self, x, y):
        vec_1 = np.array([x, y])
        vec_2 = np.array((self.x_cen, self.y_cen))
        diff = vec_2 - vec_1;theta = np.degrees(np.arctan2(diff[1], diff[0]))
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
        self.commands[3][1] = shock
        self.commands[0][1] = rotation
        self.write_command(4)
        self.write_command(1)

    def write_command(self, i:int):
        self.ser.write(self.command(i))

    def reset_thread(self):
        prev_thread = self.thread()
        prev_thread.started.disconnect()
        self.moveToThread(self.main_thread)
        prev_thread.quit()

    def check_time(self):
        running_time = time.perf_counter() - self.trial_start_time
        if not running_time < (self.trial_duration)*60:
            self.times_up.emit()
        
    

class textbox(QWidget):
    def __init__(self, wname, startval, orientation = Qt.Orientation.Horizontal):
        super().__init__()

        self.name = wname
        self.layout = QHBoxLayout
        self.lbl = QLabel(alignment = Qt.AlignmentFlag.AlignLeft, text = f'{self.name}')
        self.lbl.setFixedWidth(150)

        self.txt = QLineEdit(alignment = Qt.AlignmentFlag.AlignCenter, text = f'{startval}')
        self.txt.setValidator(QDoubleValidator(bottom = float(0), decimals = 1, top = 60))
        self.txt.setFixedWidth(150)

        self.layout.addWidget(self.lbl);self.layout.addWidget(self.txt)
        self.setLayout(self.layout)


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

        self.Xpos_vid = hslider('X pan:', 0, int(582 - h), 10, x_off)
        self.Ypos_vid = hslider('Y pan:', 0, int(582 - w), 10, y_off)

        
        self.Xcenter_vid = hslider('X of center pt:', 0, 784, 1, x_cen)
        self.Ycenter_vid = hslider('Y of center pt:', 0, 582, 1, y_cen)

        vs_layout.addWidget(self.Xdim_vid);vs_layout.addWidget(self.Ydim_vid);vs_layout.addWidget(self.vspacer);vs_layout.addWidget(self.Xpos_vid);vs_layout.addWidget(self.Ypos_vid);vs_layout.addWidget(self.vspacer);vs_layout.addWidget(self.Xcenter_vid);vs_layout.addWidget(self.Ycenter_vid);vs_layout.addWidget(self.push_vschanges)
        return vs_layout
    
    def es_layout(self):
        es_layout = QVBoxLayout()
        self.trial_duration_widget = textbox('Enter the duration of the trial (in minutes):', startval = float(30))
        es_layout.addWidget(self.change_filepath);es_layout.addWidget(self.path_label);es_layout.addWidget(self.push_eschanges);es_layout.addWidget(self.trial_duration_widget)
        return es_layout

    def cs_layout(self):
        cs_layout = QVBoxLayout()
        r, s, c = self.settings.pull(('controls',)).values()

        self.shock_setup = vslider('Shock Magnitude (mA/10, or 10^-4 A):', 1, 40, 1, s)

        self.rotation_setup = vslider('Rotation Speed (rpm):', 1, 25, 1, r)

        self.sector_center = vslider('Center of the sector (+/- 30deg):', 0, 360, 1, c)

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
        # self.tabs.addTab(self.livestream, 'livestream')

        self.wdir = os.path.dirname(os.path.realpath(__file__))
        self.grid.change_filepath.clicked.connect(self.pathprompt)
    
        model_path = self.model_pathprompt()
        self.processor = processor(model_path = model_path, settings = self.settings, main_thread = self.main_thread)
        self.create_threads();self.button_setup()
        self.disable_startandpreview_buttons()
        self.settings.sig.connect(self.update_settings)
        self.setLayout(self.main_layout)
        self.model_startup()


    @pyqtSlot(dict)
    def update_settings(self, new_settings):
        self.settings.settings = new_settings

    def create_threads(self):
        self.preview_thread = QThread() #this is likely the most active thread, as the preview will be done multiple times 
        self.stream_thread = QThread() #this thread is gonna be used once as well, and it usually the last thread used
        self.model_startup_thread = QThread() #this one is only used once        self.preview_thread.finished.connect(self.preview_thread.quit);self.stream_thread.finished.connect(self.stream_thread.quit);self.model_startup_thread.finished.connect(self.model_startup_thread.quit)

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
        self.grid.trial_duration_widget.txt.editingFinished.connect(self.update_trial_duration)
        self.processor.frm.connect(self.display_frame)
        self.processor.times_up.connect(self.shutdown_routine)

    def pathprompt(self):
        options = QFileDialog.Option.ShowDirsOnly
        dlg = QFileDialog();dlg.setOptions(options);dlg.setFileMode(QFileDialog.FileMode.Directory)
        file = dlg.getOpenFileName(caption='select the working directory for your project');fname = file[0]
        self.wdir = fname
        msg = f'the working directory is: \"{str(fname)}\"'
        self.grid.path_label.setText(msg)

    def model_pathprompt(self):
        model_options = QFileDialog.Option.ShowDirsOnly
        model_dlg = QFileDialog();model_dlg.setOptions(model_options);model_dlg.setFileMode(QFileDialog.FileMode.Directory)
        model_path = model_dlg.getExistingDirectory(caption='select the directory of the exported model that you will be using')
        return model_path

    def main_processing(self):
        #commands and pushing new settings
        self.push_controlssetup_changes()
        self.processor.write_command(2)
        #actual thread execution       
        self.processor.moveToThread(self.stream_thread)
        self.stream_thread.started.connect(self.processor.grab_stream)
        self.stream_thread.finished.connect(self.thread_done)
        self.stream_thread.start()
 
    def preview(self):
        self.processor.moveToThread(self.preview_thread)
        self.preview_thread.started.connect(self.processor.grab_single)
        self.preview_thread.finished.connect(self.thread_done)
        self.preview_thread.start()
    
    def model_startup(self):
        #as encountered in a previous iteration, a special function called 'init_inference' must be called to instanitate the tensorflow ('tf') object -- idk
        self.processor.moveToThread(self.model_startup_thread)
        self.model_startup_thread.started.connect(self.processor.model_startup)
        self.model_startup_thread.finished.connect(self.thread_done)
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
            print('processor successfully reset to self.main_thread')
        else:
            sys.exit('failed to successfully reset processor object to main thread')
        thread.finished.disconnect();thread.started.disconnect()
        print('connections of thread reset')
    
    def thread_done(self):
        thread = self.processor.thread()
        thread.started.disconnect();thread.finished.disconnect()
        thread.started.connect(self.processor.reset_thread)
        thread.start()

        print('thread successfully reset')


    def shutdown_routine(self):
        #add all shutdown commands here
        self.processor._run_flag = False
        self.processor.write_command(3);self.processor.write_command(6)
        self.stream_thread.quit();self.preview_thread.quit();self.model_startup_thread.quit()
        self.processor.vid.Close()
        self.processor.out.release();print('video successfully saved')
        self.settings.save_settings_func()
        np.save(self.processor.poses_path, self.processor.poses)
        np.savetxt(self.processor.times_path, self.processor.times, delimiter = ', ', fmt = '%s')
        print('data successfully saved')
        # self.close()
        sys.exit('shutdown routine activated')    
    

    @pyqtSlot(np.ndarray)
    def display_frame(self, frame):
        Qframe = QImage(frame, frame.shape[1], frame.shape[0], frame.strides[0],QImage.Format.Format_RGB888)
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
        b = self.grid.rotation_setup.sl.value()
        a = self.grid.shock_setup.sl.value()
        c = self.grid.sector_center.sl.value()
        self.processor.shockandrotation_setup(a, b)
        print(a, b)
        self.settings.push_c((b, a, c))
        print('successfully pushed controls setup changes')

    def reenable_startandpreview_buttons(self):
        self.grid.start.setEnabled(True)
        self.grid.preview.setEnabled(True)

    def disable_startandpreview_buttons(self):
        self.grid.start.setEnabled(False)
        self.grid.preview.setEnabled(False)

    def update_trial_duration(self):
        self.processor.trial_duration = self.grid.trial_duration_widget.txt.text()
        print('trial duration successfully updated.')

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
    
