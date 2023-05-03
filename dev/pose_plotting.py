from dlclive import DLCLive, Processor
import numpy as np
import serial, cv2, sys, os, json, pickle
from pypylon import pylon, genicam
import time
from time import sleep
import pandas as pd

from multiprocessing import Process
from threading import Thread

from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from qt_material import apply_stylesheet
import matplotlib.pyplot as plt


class dataset():
    '''
    if you have your x and y values as separate arrays, then pass the 2 arrays in order (x, y) using args
    when instantiating the class [dataset(x_arr, y_arr]. otherwise, you can pass a (2, n) size array
    that includes both [dataset(data_arr)] also input the dimensions of the arena as a tuple, and the units as a str
    '''
    def __init__(self, data:np.ndarray, framerate:int, arena_dims:tuple, video_dims:tuple, dims_units:str):

        self.x, self.y = data
        self.df = pd.DataFrame(data = {'x_pos' : self.x, 'y_pos' : self.y})
        self.fr = framerate
        self.deltas()
        self.x_factor = arena_dims[1]/video_dims[1]
        self.y_factor = arena_dims[0]/video_dims[0]
        self.dims = arena_dims
        self.units = dims_units


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
        self.df['v_x'] = self.df['delta_x']*self.fr
        self.df['v_y'] = self.df['delta_y']*self.fr

    def plot_poses(self):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_xlabel(f"x position ({self.units})");ax.set_ylabel(f"y position ({self.units})")
        ax.plot(self.x_factor*self.x, self.y_factor*self.y, ".")
        plt.show()
        # return fig


    
path = "C:\\Users\\yasudalab\\Downloads\\sample_data.csv"
fr = 20; arena_dims = (16, 12); video_dims = (1032, 772);units = "in"


raw_data = pd.read_csv(path, names = ['x', 'y'])
data = np.array((raw_data.x, raw_data.y))

dataset_ = dataset(data, fr, arena_dims, video_dims, units)

"""
to plot the figure, do self.plot_poses()

to get the dataframe, do self.df

to display the dataframe, therefore, use self.df.head()

to get summary statistics, get the series using 'np.array(self.df.v_x)' and 'np.array(self.df.v_y)'


"""