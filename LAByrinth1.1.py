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

class processor(QObject):
    frm = pyqtSignal(np.ndarray)
    
    def __init__(self, model_path):
        super().__init__()
        if os.path.exists(model_path):
            self.model_path = model_path
        else:
            sys.exit('error selecting the correct model.')

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
        self._run_flag = False
        path = "C:\\Users\\ohmkp\\OneDrive\\Desktop\\vids\\"
        self.dt = datetime.strftime(datetime.now(), "d%y.%m.%d_t%H.%M")
        fourcc = cv2.VideoWriter_fourcc(*'XVID');fps = 30.0;frameSize = (1290, 720)
        vid_path = path +  self.dt + "_recording.avi"
        self.out = cv2.VideoWriter(vid_path, fourcc, fps, frameSize)
        self.setup()

        self.commands = [[0x01, 1], #1: rotation setup: default counter clockwise, 4-100rpm
        [0x02, 0x01], #2: rotate, 0x01 to start
        [0x02, 0x00], #3: rotate, 0x00 to stop
        [0x03, 5], #4: shock current, (1-40)/10 mA (enter an integer)
        [0x04, 0x01], #5: shock, 0x01 to start
        [0x04, 0x00]] #6: shock, 0x00 to stop

        ###DLC setup
        self.dlc_processor = Processor()
        self.dlc_live = DLCLive(self.model_path)
        self.marker_dims = (7,7)

        self.ser = serial.Serial();self.ser.port= 'COM5';self.ser.baudrate = 115200   
        


    def grab_single(self):
        self.setup()
        grab = self.vid.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
        if grab.GrabSucceeded():
            frame = grab.Array
            mod_frame = self.process(frame)
            self.frm.emit(mod_frame)
        else:
            sys.exit('cam failed to cap frame')
        grab.Release()
        self.vid.Close()
        
    def grab_stream(self):
        self.setup()
        self._run_flag = True
        while self._run_flag:
            grab = self.vid.RetrieveResult(1000, pylon.TimeoutHandling_ThrowException)
            if grab.GrabSucceeded():
                frame = grab.Array
                mod_frame = self.process(frame)
                self.frm.emit(mod_frame)
            else:
                sys.exit('cam failed to cap frame')
                break
        grab.Release()
        self.vid.Close()

    def change_settings(self, new_settings):
        self.settings = new_settings
        self.h, self.w, self.x_off, self.y_off, self.x_cen, self.y_cen = self.settings['camera'].values()
        self.setup()

    def setup(self):
        h, w, x_off, y_off, x_cen, y_cen = self.settings['camera'].values()
        self.vid = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice());self.vid.Open()
        self.vid.Width.SetValue(w);self.vid.Height.SetValue(h)
        self.vid.OffsetX.SetValue(x_off);self.vid.OffsetY.SetValue(y_off)
        self.vid.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

    def process(self, frame):
        pose = self.dlc_live.get_pose(frame) 
        mod_frame = frame.copy()
        for i in range(3):
            coords = (int(pose[i, 0]), int(pose[i, 1]))
            cv2.ellipse(mod_frame, (coords, self.marker_dims, 0), self.colors[i], -1)


        return mod_frame
    
    def process(self, frame):
        pose = self.dlc_live.get_pose(frame) 
        mod_frame = frame.copy()
        for i in range(3):
            coords = (int(pose[i, 0]), int(pose[i, 1]))
            cv2.ellipse(mod_frame, (coords, self.marker_dims, 0), self.colors[i], -1)
        if(self.in_sector(pose[0,0], pose[0,1])
            and self.in_sector(pose[1,0], pose[1,1])
            and self.in_sector(pose[2,0], pose[2,1])):
                #the subject is in the sector, so shock is delivered (turned on if off)
                if not self.shock_on:
                    self.ser.write(self.command(5))
                    self.shock_on = True
                    #notes the time that the shock started, for later use
                    self.start_timer = time()               
        else:
                #shock is not delivered since the subject is not in the sector (turned off if on)
                if self.shock_on:
                    self.ser.write(self.command(6))
                    self.shock_on = False
                    #notes the time that the shock ended, subtracts from start and adds to the array
                    self.final_time = time() - self.start_timer
                    self.times_inzone = np.append(self.times_inzone, self.final_time)                  
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
#######################################################################################################


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

class Maze_Controller(QWidget,QObject):
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

        self.setWindowTitle('MazeController')
        self.showFullScreen()
        self.exit= QAction("Exit Application",shortcut=QKeySequence("Esc"),triggered=self.shutdown_routine)
        self.addAction(self.exit)
        apply_stylesheet(app, theme='dark_cyan.xml')
        self.tabs = QTabWidget()
        self.tab_names = ['livestream', 'buttons']
        livestream_layout = QVBoxLayout()
        livestream_widget = QWidget()
        self.livestream_lbl =  QLabel()
        self.livestream_lbl.setFixedWidth(self.settings['camera']['width']);self.livestream_lbl.setFixedHeight(self.settings['camera']['height'])
        self.data_table = QTableWidget();self.data_table.setRowCount(3);self.data_table.setColumnCount(3);self.data_table.setHorizontalHeaderLabels(['X', 'Y', 'prob.']);self.data_table.setVerticalHeaderLabels(['nose', 'center', 'tail'])
        self.data_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        livestream_layout.addWidget(self.livestream_lbl, Qt.AlignmentFlag.AlignCenter);livestream_layout.addWidget(self.data_table, Qt.AlignmentFlag.AlignCenter)
        livestream = QWidget();livestream.setLayout(livestream_layout)
        self.grid = QGB()
        buttons =  QWidget();buttons.setLayout(self.grid)
        self.tab_dict = {'livestream':livestream, 'buttons':buttons}
        for i in self.tab_names:
            self.tabs.addTab(self.tab_dict[i], i)
        self.main_layout = QHBoxLayout();self.main_layout.addWidget(self.tabs)
        self.setLayout(self.main_layout)
    
        # self.tabs.addTab(self.livestream, 'livestream')

        self.wdir = os.path.dirname(os.path.realpath(__file__))
        self.grid.change_filepath.clicked.connect(self.pathprompt)
    
        model_path = self.model_pathprompt()
        self.processor = processor(model_path = model_path)
        self.preview_thread = QThread()
        self.stream_thread = QThread()


    def button_setup(self):
        self.grid.push_vschanges.clicked.connect()
        self.grid.push_eschanges.clicked.connect()
        self.grid.push_vschanges.clicked.connect()
        self.grid.start.clicked.connect(self.main_processing)
        self.grid.stop.clicked.connect(self.shutdown_routine)
        self.grid.change_filepath.clicked.connect(self.pathprompt)

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
        #get Qthreadpool to keep gui up to date       
        self.processor.moveToThread(self.stream_thread)
        self.stream_thread.started.connect(self.processor.grab_stream)
        self.stream_thread.start()

    def preview(self):
        self.processor.moveToThread(self.preview_thread)
        self.preview_thread.started.connect(self.processor.grab_single  )
        self.preview_thread.start()

    def shutdown_routine(self):
        #add all shutdown commands here
        self.processor.vid.Close()
        self.processor.out.release()
        self.stream_thread.exit();self.preview_thread.exit()
        self.close()

        print("Shutdown Routine Activated")
        return

    @pyqtSlot(np.ndarray)
    def display_frame(self, frame):
        Qframe = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        Qframe = QImage(Qframe, Qframe.shape[1], Qframe.shape[0], Qframe.strides[0],QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(Qframe)
        self.livestream_lbl.setPixmap(pixmap)




if __name__ == '__main__':
    app = QApplication(sys.argv)
    Maze = Maze_Controller()
    Maze.show()
    app.exec()
    
