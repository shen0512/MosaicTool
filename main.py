
from PIL import Image as PImage, ImageTk
import sys
from os import getenv
from typing import List

import platform
import numpy as np
import cv2 as cv
import os

if(sys.version_info[0] == 2):
    from Tkinter import *
    import tkMessageBox
elif(sys.version_info[0] == 3):
    from tkinter import *
    from tkinter import messagebox as tkMessageBox
    from tkinter import filedialog

class MyPoint:
    def __init__(self, x:int, y:int)->None:
        self.x:int = int(x)
        self.y:int = int(y)
        
    def __call__(self)->tuple:
        return (self.x, self.y)

class MyBox:
    def __init__(self, tl:MyPoint, br:MyPoint)->None:
        assert type(tl) == MyPoint and type(br) == MyPoint

        self.tl:MyPoint = tl
        self.br:MyPoint = br
        self.tr:MyPoint = MyPoint(br.x, tl.y)
        self.bl:MyPoint = MyPoint(tl.x, br.y)

    def getWidth(self)->int:
        return self.br.x - self.tl.x
    
    def getHeight(self)->int:
        return self.br.y - self.tl.y
    
    def getArea(self)->int:
        return self.getWidth() * self.getHeight()
    
    def getCenterPoint(self)->MyPoint:
        return MyPoint(self.tl.x+int(self.getWidth()/2), self.tl.y+int(self.getHeight()/2))


class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.protocol("WM_DELETE_WINDOW", self.on_close)

        self.parent.title("mosaic tool")
        self.parent.geometry('+50+50')
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width = False, height = False)
        self.window_w = 1080
        self.window_h = 720

        # initialize global state
        self.tkimg = None
        self.tmpX = None
        self.tmpY = None

        # reference to bbox
        self.hl = None
        self.vl = None
        self.boxes:List[MyBox] = []

        # ----------------- GUI stuff ---------------------
        self.explBtn = Button(self.frame, text = "瀏覽", command = self.loadData)
        self.explBtn.grid(row = 0, column = 2, sticky = W+S+E,columnspan=2)
        self.mainPanel = Canvas(self.frame, cursor='tcross')

        self.mainPanel.bind("<Button-1>", self.mouseLeftClick)
        self.mainPanel.bind("<B1-Motion>", self.mouseMove)
        self.mainPanel.bind("<Motion>", self.mouseMove)

        self.mainPanel.grid(row = 0, column = 1, rowspan = 7, sticky = W+N)

        #
        self.btnSave = Button(self.frame, text = '儲存', command = self.saveData)
        self.btnSave.grid(row = 1, column = 2, sticky = W+E+N,columnspan=2)
        self.btnSave = Button(self.frame, text = '回上一步', command = self.undo)
        self.btnSave.grid(row = 2, column = 2, sticky = W+E+N,columnspan=2)

    def on_close(self):
        # self.saveData()
        self.parent.destroy()
    
    def loadData(self):
        self.boxes:List[MyBox] = []
        self.filePath = filedialog.askopenfile().name

        self.oriImg = PImage.open(self.filePath)
        self.tmpImg = self.oriImg.copy()

        if max(self.tmpImg.width, self.tmpImg.height) > 1080:
            if self.tmpImg.width > self.tmpImg.height:
                self.tmpImg = self.tmpImg.resize((1080, int(self.tmpImg.height*720.0/1080)))
            else:
                self.tmpImg = self.tmpImg.resize((int(self.tmpImg.width*720.0/1080), 1080))
            
        
        self.tkimg = ImageTk.PhotoImage(self.tmpImg)
        # self.mainPanel.config(width = self.window_w, height = self.window_h)
        self.mainPanel.config(width = self.tmpImg.width, height = self.tmpImg.height)
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)

    def saveData(self):
        if self.tmpImg is None:
            return
        
        tmpBox = self.convertPoint()
        
        copyImg = np.array(self.oriImg)
        for box in tmpBox:
            copyImg = self.doMosaic(copyImg, box)
        
        finalImg = PImage.fromarray(copyImg)
        
        fileRoot = os.path.dirname(self.filePath)
        fileName = os.path.basename(self.filePath)
        newFileName = f'{fileName.split(".")[0]}_m.{fileName.split(".")[1]}'
        newFilePath = os.path.join(fileRoot, newFileName)
        
        if os.path.isfile(newFilePath):
            result = tkMessageBox.askquestion("警告", 
                                            f"{newFileName} 檔案已經存在，是否要覆蓋", 
                                            icon='warning')
            if result == 'yes':
                finalImg.save(newFilePath)
                tkMessageBox.showinfo(f'檔案儲存成功', 
                                    message=f'檔案路徑: {newFilePath}')
        else:
            finalImg.save(newFilePath)
            tkMessageBox.showinfo(f'檔案儲存成功', 
                                    message=f'檔案路徑: {newFilePath}')
    
    def convertPoint(self):
        if self.tmpImg is None:
            return
        
        newBoxes:List[MyBox] = []
        for box in self.boxes:
            newTl = MyPoint(int(box.tl.x*self.oriImg.width*1.0/self.tmpImg.width),
                            int(box.tl.y*self.oriImg.height*1.0/self.tmpImg.height))
            newBr = MyPoint(int(box.br.x*self.oriImg.width*1.0/self.tmpImg.width),
                            int(box.br.y*self.oriImg.height*1.0/self.tmpImg.height))
            
            newBox = MyBox(newTl, newBr)
            newBoxes.append(newBox)
        
        return newBoxes
    
    def mouseLeftClick(self, event):
        if self.tkimg is None:
            return

        if self.tmpX == None and self.tmpY == None:
            self.tmpX = event.x
            self.tmpY = event.y
        else:
            self.draw(event.x, event.y, True)
            self.tmpX = None
            self.tmpY = None

    def mouseMove(self, event):
        if self.tkimg is None:
            return

        tmp_width = self.tkimg.width()
        tmp_height = self.tkimg.height()

        if self.hl:
            self.mainPanel.delete(self.hl)
        self.hl = self.mainPanel.create_line(0, event.y, tmp_width, event.y, width = 3, fill='black')
        if self.vl:
            self.mainPanel.delete(self.vl)
        self.vl = self.mainPanel.create_line(event.x, 0, event.x, tmp_height, width = 3, fill='black')

        self.draw(event.x, event.y)

    def draw(self, x, y, save:bool=False):
        if self.tmpX is not None and self.tmpY is not None:
            copyImg = np.array(self.tmpImg)

            for box in self.boxes:
                copyImg = self.doMosaic(copyImg, box)
            
            tlx = min(self.tmpX, x)
            tly = min(self.tmpY, y)
            brx = max(self.tmpX, x)
            bry = max(self.tmpY, y)
            if not (tlx == brx or tly == bry):
                tmpBox = MyBox(MyPoint(tlx, tly), MyPoint(brx, bry))
                copyImg = self.doMosaic(copyImg, tmpBox)
                
                if save:
                    self.boxes.append(tmpBox)

            
            newImg = PImage.fromarray(copyImg)                
            self.tkimg = ImageTk.PhotoImage(newImg)
            self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)
    
    def undo(self):
        if len(self.boxes) <= 0:
            return
        
        self.boxes.pop()

        copyImg = np.array(self.tmpImg)

        for box in self.boxes:
            copyImg = self.doMosaic(copyImg, box)
        
        newImg = PImage.fromarray(copyImg)                
        self.tkimg = ImageTk.PhotoImage(newImg)
        self.mainPanel.create_image(0, 0, image = self.tkimg, anchor=NW)

    def doMosaic(self, img:np.ndarray, area:MyBox, mosaicW=9):
        '''
        image moszic

        param box: 馬賽克區塊
        param mosaicW: 馬賽克寬度

        '''
        
        assert type(img) == np.ndarray
        imgH, imgW = img.shape[:2]
        assert area.tl.x >= 0 and area.tl.y >= 0
        assert area.getWidth() < imgW and area.getHeight() < imgH
        assert type(area) == MyBox

        tmp = img[area.tl.y:area.br.y, area.tl.x:area.br.x]
        tmp = cv.GaussianBlur(tmp, (13, 13), 0)
        img[area.tl.y:area.br.y, area.tl.x:area.br.x] = tmp


        for i in range(0, area.getHeight() - mosaicW, mosaicW):
            for j in range(0, area.getWidth() - mosaicW, mosaicW):
                
                tl = MyPoint(j + area.tl.x, i + area.tl.y)
                br = MyPoint(j + area.tl.x + mosaicW - 1, i + area.tl.y + mosaicW - 1)

                color = img[i + area.tl.y][j + area.tl.x].tolist()
                
                cv.rectangle(img, tl(), br(), color, -1)
        
        return img

if __name__ == '__main__':
    root = Tk()
    tool = LabelTool(root)
    root.mainloop()
