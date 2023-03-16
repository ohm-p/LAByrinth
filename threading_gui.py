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
        pass
    
    def func1(self):
        for i in range(10):
            sleep(1)
            print(i)

    def func2(self):
        for i in range(10):
            sleep(2)
            print(10*i)

    def func3(self):
        for i in range(10):
            sleep(3)
            print(i**3)

class MazeGUI(QWidget):
    def __init__(self):
        super().__init__()
        apply_stylesheet(app, theme='dark_cyan.xml')
        self.showFullScreen()
        self.exit= QAction("Exit Application",shortcut=QKeySequence("Esc"),triggered=self.close)
        self.addAction(self.exit)
        self.tabs = QTabWidget()
        self.tab_names = ['livestream', 'buttons']
        livestream = QWidget()
        buttons =  QWidget()
        self.thread1 = QThread()
        self.thread2 = QThread()
        self.thread3 = QThread()
        self.main_thread = QThread.currentThread()
        self.processor = Processor()
        buttons.setLayout(self.button_setup())        
        self.tab_dict = {'buttons':buttons, 'livestream':livestream}
        for key, value in self.tab_dict.items():
            self.tabs.addTab(key, value)            
        self.main_layout = QHBoxLayout();self.main_layout.addWidget(self.tabs)
        self.setLayout(self.main_layout)

        



    def button_setup(self):
        layout = QVBoxLayout()
        self.button1 = QPushButton(text = f"Thread 1 (1-10, step 1)")
        self.button2 = QPushButton(text = f"Thread 2 (1-100, step 10)")
        self.button3 = QPushButton(text = f"Thread 1 (1-1000, step n^3)")
        self.button1.clicked.connect(self.one)
        self.button2.clicked.connect(self.two)
        self.button3.clicked.connect(self.three)
        layout.addWidget(self.button1)
        layout.addWidget(self.button2)
        layout.addWidget(self.button3)
        self.thread1.started.connect(self.processor.func1)
        self.thread1.finished.connect(self.thread_done)
        self.thread2.started.connect(self.processor.func2)
        self.thread2.finished.connect(self.thread_done)
        self.thread3.started.connect(self.processor.func3)
        self.thread3.finished.connect(self.thread_done)
        return layout
    
    def one(self):
        self.thread1.start()
        self.thread1.started.connect(self.processor.func1)
        self.thread1.finished.connect(self.thread_done)

    def two(self):
        self.thread2.start()
        self.thread2.started.connect(self.processor.func2)
        self.thread2.finished.connect(self.thread_done)

    def three(self):
        self.thread3.start()
        self.thread3.started.connect(self.processor.func3)
        self.thread3.finished.connect(self.thread_done)

    def thread_done(self, thread):
        if thread == 1:
            self.thread1.started.connect(self.processor.moveToThread(self.main_thread))
            self.thread1.start()
        elif thread == 2:
            self.thread2.started.connect(self.processor.moveToThread(self.main_thread))
            self.thread2.start()
        elif thread == 3:
            self.thread3.started.connect(self.processor.moveToThread(self.main_thread))
            self.thread3.start()
        else:
            sys.exit('processor transfer messed up')



            


QApplication.setStyle(QStyleFactory.create('fusion'))
app =  QApplication(sys.argv)


win = MazeGUI()
# win.main()
win.show()

app.exec()


