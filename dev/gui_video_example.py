# from dlclive import DLCLive, Processor
import numpy as np
import serial, cv2, sys, os, json, qt_material, imageio
import time
from datetime import datetime, date 

from multiprocessing import Process
from threading import Thread

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from qt_material import apply_stylesheet



def spacer():
# class preview(QObject):
#     preview_img = pyqtSignal(np.ndarray)

#     def __init__(self):
#         super().__init__()

#     def run(self):
#         vid = cv2.VideoCapture(0)
#         retrieved, frame = vid.read()
#         if retrieved:
#             self.update_image.emit(frame)
#         vid.release()
    

# class livestream(QObject):
#     live_img = pyqtSignal(np.ndarray)


#     def __init__(self):
#         super().__init__()
#         path = "C:\\Users\\ohmkp\\OneDrive\\Desktop\\vids\\"
#         self.dt = datetime.strftime(datetime.now(), "d%y.%m.%d_t%H.%M")
#         fourcc = cv2.VideoWriter_fourcc(*'MP4V');fps = 30;frameSize = (1290, 720)
#         # self.out = cv2.VideoWriter()
#         self.vid_path = path +  self.dt + "_recording.mp4"
#         self._gui_run_flag = False

#     def run(self):
#         self._gui_run_flag = True
#         vid = cv2.VideoCapture(0)
#         while self._gui_run_flag:
#             retrieved, frame = vid.read()
#             if retrieved:
#                 self.update_image.emit(frame)
#             #     rgb_frame = np.column_stack((frame, frame, frame)) 
#             # imageio.imwrite(self.vid_path, rgb_frame, format = 'FFMPEG')
#         vid.release()

#     def stop(self):
#         self._gui_run_flag=False
#         self.wait()

    pass


class processor(QObject):
    frm = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self._run_flag = False
        path = "C:\\Users\\ohmkp\\OneDrive\\Desktop\\vids\\"
        self.dt = datetime.strftime(datetime.now(), "d%y.%m.%d_t%H.%M")
        fourcc = cv2.VideoWriter_fourcc(*'XVID');fps = 30.0;frameSize = (1290, 720)
        vid_path = path +  self.dt + "_recording.avi"
        self.out = cv2.VideoWriter(vid_path, fourcc, fps, frameSize)
        self.vid = cv2.VideoCapture(0);self.vid.release()


    def grab_single(self):
        if not self.vid.isOpened():
            self.vid.open(0)
        ret, frame = self.vid.read()
        if ret:
            self.frm.emit(frame)
        else:
            sys.exit('the camera failed to capture a frame')
        self.vid.release()
        
    def grab_stream(self):
        self._run_flag = True
        if not self.vid.isOpened():
            self.vid.open(0)
        while self._run_flag:
            ret, frame = self.vid.read()
            if ret:
                self.frm.emit(frame)
                self.out.write(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                sys.exit('the camera failed to capture a frame')
        self.vid.release()
        self.out.release()



class Maze_Controller(QWidget, QObject):
    def __init__(self):
        super().__init__()
        #check for settings file
        # if not os.path.exists('./settings.json'):
        #     print('Missing settings file ... Loading defaults')
        #     #write file for default settings
        #     # Rotational values
        #     # 4-100 rounds/minute type 0x01
        #     # clockwise or counterclockwise 0x00 or 0x01 type 0x01
        #     # Stop or Start 0x00 or 0x01 type 0x02

        #     #Shocking values
        #     #.1-4 *10 mA Type 0x03
        #     #stop and start, 0x00 or 0x01 Type 0x04

        #     #0xaa, 0xbb, Type(0x01-0x04), Value(varies), Check sum (d2+d3+d4)&0xff, 0xcc, 0xdd

        #         #add a way to store shapes in json file
        #     # }
        #     with open('default_settings.json', 'r') as default_settings:
        #         self.settings = json.load(default_settings)
        #     #loads the settings from the default file and saves them to a new settings file since there is none
        #     with open('settings.json', 'w') as outfile:
        #         json.dump(self.settings, outfile)
        # else:
        #     print('found settings file')
        #     with open('settings.json', 'r') as json_settings:
        #         self.settings = json.load(json_settings)

        # Force the style to be the same on all OSs:
        app.setStyle("Fusion")
        #self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowTitle("Maze Controller")
        self.showFullScreen()

        # Now use a qt_material to switch to dark colors:
        apply_stylesheet(app, theme='dark_cyan.xml')

        #set shorcut for closing window to Esc sends code directly to shutdown_routine
        self.exit= QAction("Exit Application",shortcut=QKeySequence("Esc"),triggered=self.shutdown_routine)
        self.addAction(self.exit)

        #create label for the QPixmap to map to
        self.display_camera = QLabel()

        #create table of instances
        self.instances_table = QTableWidget()
        self.instances_table.setRowCount(1)
        self.instances_table.setColumnCount(3)
        self.instances_table.setHorizontalHeaderLabels(['Shock Type', 'Start Angle', 'Total Angle'])
        self.start_button = QPushButton('Start');self.start_button.clicked.connect(self.main_processing)
        self.stop_button = QPushButton('Stop');self.stop_button.clicked.connect(self.shutdown_routine)
        self.preview_button = QPushButton('Preview');self.preview_button.clicked.connect(self.preview)

        #setup orgin points and sliders
        origin = QLabel("Origin: ")
        

        main_layout = QGridLayout()
        main_layout.addWidget(self.display_camera, 0,0,2,2, Qt.AlignmentFlag.AlignCenter)
        #main_layout.addWidget(self.instances_table,0,1,2,0)
        
        layout1 = QVBoxLayout()
        layout1.addWidget(self.instances_table)
        layout1.addWidget(self.start_button);layout1.addWidget(self.stop_button);layout1.addWidget(self.preview_button)
        main_layout.addLayout(layout1, 0,3,6,1)


        self.setLayout(main_layout)
        self.processor = processor()
        self.preview_thread = QThread()
        self.stream_thread = QThread()
        self.processor.frm.connect(self.display_frame)
        
        # self.main_processing()



    def main_processing(self):
        #get Qthreadpool to keep gui up to date       
        # self.thread.started.connect(self.gui_update)
        self.processor.moveToThread(self.stream_thread)
        self.stream_thread.started.connect(self.processor.grab_stream)
        self.stream_thread.start()

    def preview(self):
        # self.thread.started.connect(self.gui_preview)
        self.processor.moveToThread(self.preview_thread)
        self.preview_thread.started.connect(self.processor.grab_single  )
        self.preview_thread.start()

    def shutdown_routine(self):

        #add all shutdown commands here
        self.processor.vid.release()
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
        self.display_camera.setPixmap(pixmap)

    
    def calculation(self, dlc):
        time.sleep(1)
        return




if __name__ == '__main__':
    app = QApplication(sys.argv)
    Maze = Maze_Controller()
    Maze.show()
    app.exec()