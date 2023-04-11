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
    def __init__(self, data:np.ndarray, framerate:int):

        self.x, self.y = data
        self.df = pd.DataFrame(data = {'x_pos' : self.x, 'y_pos' : self.y})
        self.fr = framerate
        self.deltas()


    def return_x(self):
        return self.x
    
    def return_y(self):
        return self.y
    
    def deltas(self):
        self.df['x_pos_copy'] = self.df['x_pos']
        self.df['y_pos_copy'] = self.df['y_pos']
        self.df['delta_x'] = self.df.x_pos_copy.diff();self.df ['delta_x'] = self.df.delta_x.shift(periods = -1, fill_value = 0)
        self.df['delta_y'] = self.df.y_pos_copy.diff();self.df ['delta_y'] = self.df.delta_y.shift(periods = -1, fill_value = 0)
        self.df.drop(labels = ['x_pos_copy', 'y_pos_copy'], axis = 1,inplace = True)
        self.df['v_y'] = self.df['delta_x']*self.fr
        self.df['v_y'] = self.df['delta_y']*self.fr


    

array = np.random.rand(1000).reshape((2, 500))
data = dataset(array, 60)