#IMPORTS
from tkinter import *
from tkinter import ttk
import tkinter as tk

from dlclive import DLCLive, Processor

import numpy as np
import serial

from time import time
from datetime import datetime, date
from PIL import ImageTk, Image
import cv2

from multiprocessing import Process
from threading import Thread
import sys
from functools import partial



class MazeGUI():
    def __init__(self):
        self.root = Tk()
        self.root.title('MazeController')
        self.root.resizable(width = FALSE, height = FALSE)
        self.root.geometry('1000x1000')
        self.frm1 = ttk.LabelFrame(self.root,  width = 1000, height = 600, padding=5, text='image')
        self.frm2 = ttk.LabelFrame(self.root, width = 1000, height = 200, padding=5, text='controls')
        self.frm1.grid(row = 0, column = 0, padx = 5, pady = 5,sticky = 's');self.frm2.grid(row = 1, column = 0, pady = 10)    
        
        
class MazeController(Processor, MazeGUI):
    def __init__(self):
        self.mag = np.array([782, 582])
        self.times_inzone = []
        self.poses = []
        
        self.dt = datetime.strftime(datetime.now(), "d%y.%m.%d_t%H.%M.%S")

        # self.vid = cv2.VideoCapture(0, cv2.CAP_DSHOW);self.vid.set(cv2.CAP_PROP_FRAME_WIDTH, 782); self.vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 582)
        self.vid = cv2.VideoCapture(0)
        fourcc = cv2.VideoWriter_fourcc(*'mp42')
        self.framerate = float(30)
        self.out = cv2.VideoWriter("C:\\Users\\yasudalab\\tracking_system\\tracking_experiments\\system_results\\" +
                                    self.dt + '_recording.mp4', fourcc, self.framerate, tuple(self.mag))
        print(f"is the camera open?: {self.vid.isOpened()}")
    
        self.dlc_proc = Processor()
        self.dlc_live = DLCLive("C:\\Users\\yasudalab\\tracking_system\\tracking_experiments\\exported_models\\sample_exportedmodel\\DLC_sample_mobilenet_v2_1.0_iteration-0_shuffle-1", processor=self.dlc_proc)
        
        self.shock_on = False
        self.ser = serial.Serial();self.ser.port= 'COM5';self.ser.baudrate = 115200      

        self.commands = [[0x01, 1], #1: rotation setup: default counter clockwise, 4-100rpm
        [0x02, 0x01], #2: rotate, 0x01 to start
        [0x02, 0x00], #3: rotate, 0x00 to stop
        [0x03, 5], #4: shock current, (1-40)/10 mA (enter an integer)
        [0x04, 0x01], #5: shock, 0x01 to start
        [0x04, 0x00]] #6: shock, 0x00 to stop
        self.end_commands = [self.command(6), self.command(3)]
        self.start_commands = [self.command(1), self.command(2), self.command(4)]
        
        self.colors = [(0,255,171), (171,0,255), (212, 255,0)]
        self.trial = False

        
        self.gui = MazeGUI()
        self.threads = []
        self.buttons = {}
        im = Image.new(mode="RGB", size=(200, 200))
        imtk = ImageTk.PhotoImage(im)
        self.lbl = tk.Label(self.gui.frm1, image = imtk);self.lbl.grid()
        
    def main(self):
        ret, frame = self.vid.read()
        if ret:
            self.dlc_live.init_inference(frame)
            print("not yet...")
            self.gui_setup()
            self.gui_idle()
            # proc = Process(target=self.process, args=(pose,))
            # proc.start();proc.join()
            self.gui.root.mainloop()
                # thr.start();thr.join()


    # =============================================================================
    # {|||}this is just commented out rn because i dont want to keep deleting annoying files during testing and refinement
    #                 #saves the poses array as a txt/csv file, hence the ',' delim
    #                 np.savetxt(("C:\\Users\\yasudalab\\tracking_system\\tracking_experiments\\system_results\\" +
    #                             self.dt + '_positions.csv'), self.poses, delimiter=',')
    #                 #same thing as above, except with the shocktimes (should be empty rn)
    #                 np.savetxt(("C:\\Users\\yasudalab\\tracking_system\\tracking_experiments\\system_results\\" +
    #                             self.dt + '_shocktimes.csv'), self.times_inzone, delimiter=',')
    # =============================================================================
        return
    
    def gui_setup(self):
        stop = ttk.Button(self.gui.frm2, text='exit', command = partial(self.exit, False, None))
        start= ttk.Button(self.gui.frm2, text='start', command=self.thread_start)
        stop.grid(row=0, column=0);start.grid(row=0, column=1)
        self.buttons['start'] = start; self.buttons['stop'] = stop        
        
    def gui_idle(self):
        while not self.trial:
            ret, frame= self.vid.read()
            pose = self.dlc_live.get_pose(frame)
            imgtk = self.create_mod(frame, pose)
            self.lbl.config(image = imgtk)
            self.gui.root.update()
            # print("the pose is updated!")
    # def gui_processing(self, frame, pose):
        # self.buttons[0].config(state = 'disabled')



    def process(self, pose):
        #if all 3 points of the subject are in the sector, this condition is true
        # redundancy of commands is prevented by self.shock_on
        if(self.in_sector(pose[0,0], pose[0,1])
            and self.in_sector(pose[1,0], pose[1,1])
            and self.in_sector(pose[2,0], pose[2,1])):
                #the subject is in the sector, so shock is delivered (turned on if off)
                if not self.shock_on:
                    self.ser.write(self.command(5))
                    self.shock_on = True
                    #notes the time that the shock started, for later use
                    self.start_timer = time()
                   
        else:
                #shock is not delivered since the subject is not in the sector (turned off if on)
                if self.shock_on:
                    self.ser.write(self.command(6))
                    self.shock_on = False
                    #notes the time that the shock ended, subtracts from start and adds to the array
                    self.final_time = time() - self.start_timer
                    self.times_inzone = np.append(self.times_inzone, self.final_time)
                   
        return pose
      

    def create_mod(self, frame, pose):
        mod = frame.copy()
        dims = (7,7)
        for i in range(3):
            coords = (int(pose[i, 0]), int(pose[i, 1]))
            cv2.ellipse(mod, (coords, dims, 0), self.colors[i], -1)
        center = (int(self.mag[0]/2), int(self.mag[1]/2))
        cv2.ellipse(mod, (center, (50,50), 0), (0,0,0), -1)
        img = Image.fromarray(mod)
        imgtk = ImageTk.PhotoImage(img)
        return imgtk

    def in_sector(self, x, y):
        #math
        vec_1 = np.array([x, y])
        vec_2 = self.mag/2
        diff = vec_1 - vec_2;ratio = diff[1]/diff[0]
        theta = np.degrees(np.arctan(ratio))
        # true if calculated theta is in the 60 degree sector from -30 to 30 degrees
        if (theta < 30 and theta > -30):
            #DELETE THIS LATER, just to make sure the math is correct for now
            print("subject is in the shock zone!")
            #boolean output for the shock function
            return True
      

    # simplified command function, see previous version for legacy (eliminated 5 other commands and simplified process)
    def command(self, inp):
         d2, d3 = self.commands[inp - 1]
         d0 = 0xaa
         d1 = 0xbb
         d4 = 0x00
         d5 = (d2 + d3 + d4) & 0xff
         d6 = 0xcc
         d7 = 0xdd 
         
         #creates a list that will be converted to a byte array
         l = [d0, d1, d2, d3, d4, d5, d6, d7]
         
         return bytearray(l)
     
    def thread_start(self):
         thr = Thread(target = self.starttrial)
         thr.start()
     
     
    def starttrial(self):
        self.ser.open()
        self.working("starttrial")
        self.trial = True
        for i in self.start_commands:
            self.ser.write(i)
        while self.trial:
            ret, frame = self.vid.read()
            #same logic as above ret logic
            if not ret: 
                break
            pose = self.dlc_live.get_pose(frame)
            #saves the poses into an np array, important
            self.poses.append(pose)
            self.out.write(frame)
            imgtk = self.create_mod(frame, pose)
            self.lbl.config(image = imgtk)
            self.process(pose)

    def stoptrial(self, msg:str or None)->str:
        self.working("stoptrial")
        if self.ser.isOpen():
            for i in self.end_commands:
                self.ser.write(i)
            self.ser.close()
        self.trial = False
        self.gui.root.destroy()
        for thr in self.threads:
            thr.stop()
        sys.exit(str(msg))

        
    #this is just to see if the buttons are working
    def working(self, button:str)->str:
        print(f"this button is working: {button}")

    def exit(self, fail:bool, error_str:str or None)->'str':
        if not fail:
            error = 'thank you for using the GUI!'
        elif fail:
            error = str(error_str)
        else:
            error = 'there is an error in the \'error\' function!'
        self.stoptrial(error)



# if __name__ == '__main__':
#     new = MazeController()
    

#     new.main_processing()

#     new.stoptrial()
    

