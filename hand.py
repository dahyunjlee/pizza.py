'''
Defines Hand object
'''

import numpy as np
import cv2 as cv
import math
from database import *


def angle(p1, p2):
    xDiff = p2[0] - p1[0]
    yDiff = p2[1] - p1[1]
    return math.degrees(math.atan2(yDiff, xDiff))



# TODO: set left hand as shape2, loc2

class Hand(object):
    def __init__(self,img,contours,hierarchy,shape=0,loc=-1):
        self.shape = shape
        self.shape2 = shape
        self.two_hand_shape = 0
        self.loc = loc
        self.loc2 = loc
        self.left = -1
        self.right = -1
        self.img = img
        self.img_size = img.shape[0] * img.shape[1]
        self.com = (-1,-1)
        self.com2 = (-1,-1)
        self.screen = (-1,-1)
        self.contours = contours
        self.hierarchy = hierarchy
        self.defects = []
        flag = self.filter_contours()
        if flag != 0:
            self.set_loc(flag)
            self.set_shape(flag)
            if flag == 2:
                self.set_two_hand_shape()

    def hooray(self):
        cx1 = self.com[0]
        cx2 = self.com2[0]

        w = self.img.shape[1]
        if cx2 < w/3 and cx1 > (2*w)/3 and self.shape not in [1,2,9] and self.shape2 not in [1,2,9]:
            return True
        else:
            return False

    def et(self):
        if self.shape == 1 and self.shape2 == 1:
            return True
        else:
            return False

    def set_two_hand_shape(self):
        if self.et():
            self.two_hand_shape = 13
        elif self.hooray():
            self.two_hand_shape = 11


    def get_inner_contour(self,i):
        inner_contour = -1
        h = self.hierarchy

        child = h[0][i][2]
        if child == -1:
            return inner_contour

        next_list = [child]
        next_contour = h[0][child][0]
        while next_contour != -1:
            next_list.append(next_contour)
            next_contour = h[0][next_contour][0]

        ic_area = 0
        for i in range(len(next_list)):
            area = cv.contourArea(self.contours[next_list[i]])
            if area > ic_area:
                ic_area = area
                inner_contour = self.contours[next_list[i]]

        inner_contour = self.contours[h[0][child][0]]

        return inner_contour

    '''
    return values
    0: no contours
    1: two contours, [largest contour, inner contour]
    2: four contours, [largest contour, its inner contour, second largest contour, its inner contour]
    '''
    def filter_contours(self):
        contour_count = 0

        if len(self.contours) == 0:
            return contour_count

        c1 = max(self.contours, key = cv.contourArea)
        c1_area = cv.contourArea(c1)

        # check if the contour is too small
        if c1_area < 0.01 * self.img_size:
            self.contours = []
            return contour_count

        contour_count = contour_count + 1

        # the contour is big enough, so get the next biggest contour
        for i in range(len(self.contours)):
            if np.array_equal(self.contours[i],c1):
                index1 = i

        if len(self.contours) >  1:
            c2_area = 0
            for i in range(len(self.contours)):
                if np.array_equal(self.contours[i],c1):
                    continue
                if c2_area < cv.contourArea(self.contours[i]):
                    c2_area = cv.contourArea(self.contours[i])
                    c2 = self.contours[i]
                    index2 = i
            if c2_area/c1_area > 0.7:
                contour_count = contour_count + 1

        # get the largest inner contour
        c1c = self.get_inner_contour(index1)
        if contour_count == 2:
            c2c = self.get_inner_contour(index2)
            self.contours = [c1,c1c,c2,c2c]
            return contour_count
        else:
            self.contours = [c1,c1c]
            return contour_count


    def set_shape(self,flag):
        shape = self.eval_shape(self.contours[:2])
        self.shape = shape
        if flag == 2:
            shape2 = self.eval_shape(self.contours[2:])
            if self.right == 0:
                self.shape = shape
                self.shape2 = shape2
            else:
                self.shape = shape2
                self.shape2 = shape

    def eval_shape(self,cnts):
        # determine the shape of the hand
        oh = False
        rec = False
        inner_contour = True

        c = cnts[0]
        cc = cnts[1]
        c_area = cv.contourArea(c)
        if isinstance(cc,int):
            inner_contour = False
        else:
            cc_area = cv.contourArea(cc)

        if inner_contour:
            if cc_area > 0.05 * c_area:
                (x,y),radius = cv.minEnclosingCircle(cc)
                radius = int(radius)
                circle_area = np.pi * radius * radius
                _,(w,h),_ = cv.minAreaRect(cc)
                rec_area = w*h
                if cc_area/circle_area > 0.6:
                    oh = True
                elif cc_area/rec_area > 0.75:
                    rec = True

        x,y,w,h = cv.boundingRect(c)
        hull = cv.convexHull(c,returnPoints = False)
        defects = cv.convexityDefects(c,hull)

        # determine the # of fingers
        finger_count = 1
        try:
            for i in range(defects.shape[0]):
                s,e,f,d = defects[i,0]
                start = tuple(c[s][0])
                end = tuple(c[e][0])
                far = tuple(c[f][0])
                if(abs(angle(far,end) - angle(far,start)) > 80 or math.sqrt(d) < 0.4 * h):
                    continue
                self.defects.append(far)
                finger_count = finger_count + 1
        except:
            pass

        height, width = self.img.shape[:2]

        if finger_count == 1:
            if rec == True:
                return 7
            elif oh == True:
                return 10
            else:
                mbr_area = w * h
                if c_area/mbr_area > 0.65 and w in range(int(0.7*h),int(1.4*h)):
                    return 9
                elif h > 1.2 * w:       # HUSH VS ONE
                        #return 12
                    #else:
                        #return 1
                    #else:
                        return 1
                else:
                    return 0
        else:
            if finger_count == 3 and oh == True:
                return 6
            else:
                return finger_count


    def eval_loc(self, cnt):
        # determine the location of the hand
        M = cv.moments(cnt)

        cx = int(M['m10']/M['m00'])
        cy = int(M['m01']/M['m00'])

        w = int(self.img.shape[1])
        h = int(self.img.shape[0])

        if cx < int(w/3):
            column = 0
        elif cx >= int(w/3) and cx < int((2*w)/3):
            column = 1
        else:
            column = 2

        if cy < int(h/3):
            row = 0
        elif cy >= int(h/3) and cy < int((2*h)/3):
            row = 1
        else:
            row = 2

        return 3 * row + column, cx, cy

    def set_loc(self,flag):
        loc, x, y = self.eval_loc(self.contours[0])
        self.loc = loc

        self.com = (x,y)
        w = int(self.img.shape[1])
        h = int(self.img.shape[0])
        self.screen = (x/w, y/h)

        self.right = 0
        if flag == 2:
            loc2, x2, y2 = self.eval_loc(self.contours[2])
            if x2 < x:
                self.loc2 = loc2
                self.com2 = (x2,y2)
                self.screen = (x2/w, y2/h)
                self.left = 2
            else:
                self.loc2 = loc
                self.com2 = (x,y)
                self.screen = (x/w, y/h)

                self.loc = loc2
                self.com = (x2,y2)
                self.screen = (x2/w, y2/h)

                self.right = 2
                self.left = 0
