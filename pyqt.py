import PyQt6 as pq
from PyQt6.QtCore import Qt
from PyQt6 import QtWidgets as qw
import sys

class QGB(qw.QGridLayout):
    def __init__(self):
        super().__init__()
        self.groups = ["video setup", "experiment setup", "controls setup", "execute exp"]
        self.gboxes = []
        for i in self.groups:
            box = qw.QGroupBox(i)
            layout = qw.QVBoxLayout()
            box.setLayout(layout)
            self.gboxes.append(box)
        for i in range(2):
            for j in range(2):
                ind = i + j
                self.addWidget(self.gboxes[ind], i, j)

class MazeGUI(qw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('MazeController')
        self.setGeometry(0,0,1000,1000)
        
        self.tabs = qw.QTabWidget

        self.tab_names = ['livestream', 'buttons']

        self.grid_layout = QGB()

        livestream = qw.QLabel()
        buttons = qw.QWidget();buttons.setLayout(self.grid_layout)

        self.tab_dict = {'livestream':livestream, 'buttons':buttons}

        for i in self.tab_names:
            self.tabs.addTab(self.tab_dict[i], i)
        



app = qw.QApplication(sys.argv)


win = MazeGUI()
win.show()

app.exec()


