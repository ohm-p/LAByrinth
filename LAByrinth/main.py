# from dlclive import DLCLive, Processor
import numpy as np
import serial, cv2, sys, os, json, pickle
# from pypylon import pylon, genicam
import time
from time import sleep

from multiprocessing import Process
from threading import Thread

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from qt_material import apply_stylesheet

from utils import *
from settings import *
from widgets import *



if __name__ == '__main__':
    app = QApplication(sys.argv)
    Maze = Maze_Controller()
    Maze.show()
    app.exec()
    
