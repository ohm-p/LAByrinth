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
