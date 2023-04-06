import numpy as np;import pandas as pd
import serial, cv2, sys, os, json, pickle
import time
from time import sleep

from multiprocessing import Process
from threading import Thread

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from qt_material import apply_stylesheet


class dataset():
    '''
    if you have your x and y values as separate arrays, then pass the 2 arrays in order (x, y) using args
    when instantiating the class [dataset(x_arr, y_arr]. otherwise, you can pass a (2, n) size array
    that includes both [dataset(data_arr)]
    
    '''
    def __init__(self, *data:np.ndarray):
        # if data.shape[0] == 2:
        #     self.x, self.y = data
        # else:
        self.x, self.y = data[0], data[1]

    def return_x(self):
        return self.x
    
    def return_y(self):
        return self.y
    

array = np.random.rand(1000).reshape((2, 500))
data = dataset(array)