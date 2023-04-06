from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
import sys;import os
import numpy as np
import json
from qt_material import apply_stylesheet
from time import time, sleep;import time


class Processor(QObject):
    def __init__(self):
        super().__init__()
        self.main_thread = self.thread()

    
    def func1(self):
        for i in range(1, 11):
            sleep(1)
            print(i)
        # self.fin.emit()
        print(self.thread() == self.main_thread)
        self.thread().quit()


    def func2(self):
        for i in range(1, 11):
            sleep(2)
            print(10*i)
        # self.fin.emit()
        print(self.thread() == self.main_thread)
        self.thread().quit()


    def func3(self):
        for i in range(1, 11):
            sleep(3)
            print(i**3)
        # self.fin.emit()
        print(self.thread() == self.main_thread)
        self.thread().quit()

    def reset_thread(self):
       prev_thread = self.thread()
       prev_thread.started.disconnect()
       self.moveToThread(self.main_thread)
       prev_thread.quit()


class MazeGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.showFullScreen()
        self.exit= QAction("Exit Application",shortcut=QKeySequence("Esc"),triggered=self.close)
        self.addAction(self.exit)
        self.tabs = QTabWidget()
        self.tab_names = ['livestream', 'buttons']
        livestream = QWidget()
        buttons =  QWidget()
        self.processor = Processor()#;self.processor.fin.connect(self.thread_check)
        buttons.setLayout(self.button_setup())        
        self.tab_dict = {'buttons':buttons, 'livestream':livestream}
        for key, value in self.tab_dict.items():
            self.tabs.addTab(value, key)            
        self.main_layout = QHBoxLayout();self.main_layout.addWidget(self.tabs)
        self.setLayout(self.main_layout)
        self.thread1 = QThread();self.thread2 = QThread();self.thread3 = QThread()

    def button_setup(self):
        layout = QVBoxLayout()
        self.button1 = QPushButton(text = f"Thread 1 (1-10, step 1)")
        self.button2 = QPushButton(text = f"Thread 2 (1-100, step 10)")
        self.button3 = QPushButton(text = f"Thread 3 (1-1000, step n^3)")
        self.button1.clicked.connect(self.one)
        self.button2.clicked.connect(self.two)
        self.button3.clicked.connect(self.three)
        layout.addWidget(self.button1)
        layout.addWidget(self.button2)
        layout.addWidget(self.button3)
        
        
        return layout
    
    def one(self):
      
        self.processor.moveToThread(self.thread1)
        self.thread1.started.connect(self.processor.func1)
        self.thread1.finished.connect(self.finished_confirmation);self.thread1.finished.connect(self.thread_done)
        self.thread1.start()

    def two(self):
        self.processor.moveToThread(self.thread2)
        self.thread2.started.connect(self.processor.func2)
        self.thread2.finished.connect(self.finished_confirmation);self.thread2.finished.connect(self.thread_done)
        self.thread2.start()

    def three(self):
        self.processor.moveToThread(self.thread3)
        self.thread3.started.connect(self.processor.func3)
        self.thread3.finished.connect(self.finished_confirmation);self.thread3.finished.connect(self.thread_done)
        self.thread3.start()

    def thread_done(self):
        thread = self.processor.thread()
        thread.started.disconnect()
        thread.finished.disconnect()
        thread.started.connect(self.processor.reset_thread)
        thread.finished.connect(self.finished_confirmation)
        thread.start() 

        print('thread successfully reset')


    def finished_confirmation(self):
        print('thread successfully finished')



app =  QApplication(sys.argv)
win = MazeGUI()
apply_stylesheet(app, theme='dark_cyan.xml')
win.show()
app.exec()



