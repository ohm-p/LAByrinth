from dlclive import DLCLive, Processor
import numpy as np
import serial, cv2, sys, os, json, pickle
import time
from datetime import datetime, date 

from multiprocessing import Process
from threading import Thread

from PyQt6.QtWidgets import *
from PyQt6.QtGui import QImage, QPixmap, QAction, QKeySequence
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from qt_material import apply_stylesheet

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

class Gui_updater(QThread):
    update_image = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self._gui_run_flag = True
    

    def grab_single_image(self):


    def run(self):
        raw_video = cv2.VideoCapture(0)
        while self._gui_run_flag:
            retrieved, frame = raw_video.read()
            if retrieved:
                Qframe = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                #Qframe = QImage(Qframe, Qframe.shape[1], Qframe.shape[0], Qframe.strides[0],QImage.Format.Format_RGB888)
                #pixmap = QPixmap.fromImage(Qframe)
                self.update_image.emit(frame)
        raw_video.release()

    def stop(self):
        self._gui_run_flag=False
        self.wait()


class Maze_Controller(QWidget):
    def __init__(self):
        super().__init__()
        #check for settings file
        if not os.path.exists('./settings.json'):
            print('Missing settings file ... Loading defaults')
            #write file for default settings
            # Rotational values
            # 4-100 rounds/minute type 0x01
            # clockwise or counterclockwise 0x00 or 0x01 type 0x01
            # Stop or Start 0x00 or 0x01 type 0x02

            #Shocking values
            #.1-4 *10 mA Type 0x03
            #stop and start, 0x00 or 0x01 Type 0x04

            #0xaa, 0xbb, Type(0x01-0x04), Value(varies), Check sum (d2+d3+d4)&0xff, 0xcc, 0xdd

                #add a way to store shapes in json file
            # }
            with open('default_settings.json', 'r') as default_settings:
                self.settings = json.load(default_settings)
            #loads the settings from the default file and saves them to a new settings file since there is none
            with open('settings.json', 'w') as outfile:
                json.dump(self.settings, outfile)
        else:
            print('Found setttings file')
            with open('settings.json', 'r') as json_settings:
                self.settings = json.load(json_settings)

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
        self.button = QPushButton('Start')

        #setup orgin points and sliders
        origin = QLabel("Origin: ")
        

        main_layout = QGridLayout()
        main_layout.addWidget(self.display_camera, 0,0,2,2, Qt.AlignmentFlag.AlignCenter)
        #main_layout.addWidget(self.instances_table,0,1,2,0)
        
        layout1 = QVBoxLayout()
        layout1.addWidget(self.instances_table)
        layout1.addWidget(self.button)
        main_layout.addLayout(layout1, 0,3,6,1)



        self.setLayout(main_layout)
        self.main_processing()


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
    
    def calculation(self, dlc):
        time.sleep(1)
        return




if __name__ == '__main__':
    app = QApplication(sys.argv)
    Maze = Maze_Controller()
    Maze.show()
    app.exec()
