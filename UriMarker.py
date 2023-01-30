# import the necessary packages
import numpy as np
import argparse
import cv2
import copy
import os
import csv
from shapely.geometry import Polygon
import configparser

#There was need to analyse a series of UV photos of paper sheets with mice urine markings.
#This script was created to automate the process of finding these markings, estabilishing their total area and where they were in the paper.
#It's final objective was to be compiled into and .exe that my colleagues could use by simply editing a config.ini file with a few parameters.

### Parameters
Config = configparser.ConfigParser()
Config.read("Config.ini")

topLeftCornerX = int(Config.get('Paper Location', 'Top Left Corner X'))# 1059 #430 #1059
topLeftCornerY =int(Config.get('Paper Location', 'Top Left Corner Y')) #237  #917
outsideW =int(Config.get('Paper Location', 'Paper Length in pixels')) #2920 #2129
outsideH =int(Config.get('Paper Location', 'Paper Heigh in pixels')) #1664 #1132
insidePercW = float(Config.get('Paper Location', 'Inside Length Percentage')) 
insidePercH = float(Config.get('Paper Location', 'Inside Height Percentage')) 
thresholdArea = int(Config.get('Thresholding Parameters For Spots', 'Threshold Lookup Area'))  #501
thresholdAdjust = int(Config.get('Thresholding Parameters For Spots', 'Threshold Adjustment')) #-25
outsideWcm = float(Config.get('Paper Location', 'Paper Length in cm'))
minimumSize= float(Config.get('Thresholding Parameters For Spots', 'Minimum Spot Size Percentage')) 
directory = Config.get('Folder', 'Picture Folder')
thresholdAreaP = int(Config.get('Thresholding Parameters For Paper', 'Threshold Lookup Area'))  #501
thresholdAdjustP = int(Config.get('Thresholding Parameters For Paper', 'Threshold Adjustment')) #-25
expectedPsize = int(Config.get('Thresholding Parameters For Paper', 'Expected Paper Length Size in Pixels'))



#######Code

scale = pow(outsideWcm/outsideW,2)

if not os.path.exists(directory+"/results"):
   os.mkdir(directory+"/results")
   
with open(directory+"/results/Results.csv", 'w', newline='', encoding='UTF8') as csvToWrite:
    writer = csv.writer(csvToWrite)
    writer.writerow(['File Name','Inside Area','Outside Area','Inside Area Percentage','Outside Area Percentage']) 
             
    for filename in os.listdir(directory): #Runs through all the files in the directory

        f = os.path.join(directory, filename)
        if os.path.isfile(f):
          print(f)
          
          ###Find the paper
          img = cv2.imread(f)
          gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
          gray = cv2.GaussianBlur(gray, (19, 19), 0)
          threshTotalP = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,thresholdAreaP,thresholdAdjustP)
          contours,hierarchy = cv2.findContours(threshTotalP,cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)# 1, 2)
          threshTotalP = cv2.cvtColor(threshTotalP, cv2.COLOR_GRAY2BGR)
          for i in contours:
            x,y,w,h = cv2.boundingRect(i)
            if (expectedPsize > 0): #If paper size was set sets the boundaries with 10% error margin
                wMax = expectedPsize*1.1
                wMin = expectedPsize*0.9
            else:
                wMax = 4000
                wMin = 1500
            if  (1.8 > w/h > 1.4) and  wMax> w > wMin: #Finds the paper if there is a rectangle with the correct dimensions
                topLeftCornerY = y
                topLeftCornerX = x
                outsideH = h
                outsideW = w
                cv2.rectangle(threshTotalP,(x,y),(x+w,y+h),(0,255,0),6)
                print("Paper found!")
                break   
          
          
          ###Now it crops to the paper size and then looks for the urine markings
          
          img = cv2.imread(f)
          img = img[topLeftCornerY:(topLeftCornerY+outsideH),topLeftCornerX:(topLeftCornerX+outsideW)] #Crop image

          gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
          gray = cv2.GaussianBlur(gray, (19, 19), 0)
          threshTotal = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_MEAN_C,cv2.THRESH_BINARY,thresholdArea,thresholdAdjust)

          thresh = threshTotal
          contours,hierarchy = cv2.findContours(thresh, 1, 2)
          
          #Creates the rectangle that divides the center of the paper from the outside
          x1 = int(outsideW*(1-insidePercW))
          y1 = int(outsideH*(1-insidePercH))
          x2 = int(outsideW*insidePercW)
          y2 = int(outsideH*insidePercH)
          insidePolygon = Polygon([(x1,y1),(x1,y2),(x2,y2),(x2,y1)]) 

          totalInsideArea=0
          totalOutsideArea=0
          int_coords = lambda x: np.array(x).round().astype(np.int32)

          for i in contours: #For each marking found
            try:
              x,y,w,h = cv2.boundingRect(i)
              if  ((w > minimumSize*max(outsideW,outsideH) or h > minimumSize*max(outsideW,outsideH)) and 5 > w/h > 0.20): #Checks if the size and format is what is expected
                  (x,y),radius = cv2.minEnclosingCircle(i)
                  center = (int(x),int(y))
                  radius = int(radius)
                  cv2.circle(img,center,radius,(0,255,0),6)
                  contour = np.squeeze(i)
                  ctPoly = Polygon(contour)
                  exterior = [int_coords(ctPoly.exterior.coords)]
                  cv2.fillPoly(img, exterior, color=(255, 255, 0))        
                  totalInsideArea+=ctPoly.intersection(insidePolygon).area #Sums the area inside the center
                  totalOutsideArea+=ctPoly.area-ctPoly.intersection(insidePolygon).area #Sums the area outside the center
            except:
                print("Error with polygons") #Some small artifact markings can generate errors, these should be ignored
                
          cv2.rectangle(img,(int(outsideW*(1-insidePercW)),int(outsideH*insidePercH)),(int(outsideW*insidePercW),int(outsideH*(1-insidePercH))),(0,255,0),6) #Paints the rectangle that divides the center
          threshTotal = cv2.cvtColor(threshTotal, cv2.COLOR_GRAY2BGR)
          threshTotalP = cv2.resize(threshTotalP, (len(threshTotal[0]), len(threshTotal)), None)
          imageToDisplay = np.vstack((threshTotalP,threshTotal, img))
          imageToDisplay = cv2.resize(imageToDisplay, (0, 0), None, .25, .25)

         # cv2.imshow("Shapes", imageToDisplay) #Shows the image, only for testing
                   
          #Finally writes to the csv file the calculated areas and the name of the file. It also writes the image with the urine markings that were considered highlighted
          cv2.imwrite(directory+"/results/"+filename,imageToDisplay)      
          writer.writerow([filename,str(totalInsideArea*scale),str(totalOutsideArea*scale),str((totalInsideArea/totalOutsideArea+totalInsideArea)*scale),str((totalOutsideArea/totalOutsideArea+totalInsideArea)*scale)])
