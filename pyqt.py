import PyQt6 as pq
from PyQt6.QtCore import Qt
from PyQt6 import QtWidgets as qw
import sys

class MazeGui(qw.QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle('MazeGui')

        # page = qw.QVBoxLayout()
        self.buttons = qw.QTabWidget()
        self.buttons.setTabPosition(qw.QTabWidget.West)
        # self.stack = qw.QStackedLayout()

        for i in range(4):
            slider = self.stack.addWidget(qw.QSlider(Qt.Orientation.Horizontal))
            self.buttons.addTab(slider, i)

        widget = qw.QWidget();widget.setLayout(self.stack)
        self.setCentralWidget(self.buttons)
    

app = qw.QApplication(sys.argv)


win = MazeGui()
win.show()

app.exec()


