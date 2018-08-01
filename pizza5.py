'''
Hand Gesture Mac Control
'''

import numpy as np
import cv2 as cv
from hand import *
from sequence import *
from database import *

PROFILE_COUNT = 5

def get_sampling_coord(dim):
    height = int(dim[0])
    width = int(dim[1])

    rec_h = int(height/5)
    rec_w = int(width/12)

    rec_y = np.random.randint(height-rec_h,size=1)
    rec_x = np.random.randint(width-rec_w,size=1)

    return rec_x[0],rec_y[0],rec_h,rec_w

def get_profile(roi):
    hsv = cv.cvtColor(roi,cv.COLOR_BGR2HSV)
    roihist = cv.calcHist([hsv.astype('float32')],[0, 1], None, [180, 256], [0, 180, 0, 256] )
    cv.normalize(roihist,roihist,0,255,cv.NORM_MINMAX)

    return roihist

def get_thresh(frame,profile):
    hsvt = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
    dst = cv.calcBackProject([hsvt.astype('float32')],[0,1],profile,[0,180,0,256],1)
    disc = cv.getStructuringElement(cv.MORPH_ELLIPSE,(5,5))
    cv.filter2D(dst,-1,disc,dst)

    # threshold
    ret,thresh = cv.threshold(dst,0,255,0)

    return thresh

def denoise(frame, iterations = 1):
    kernel = np.ones((3,3),np.uint8)
    for i in range(iterations):
        frame = cv.medianBlur(frame,3)
        frame = cv.GaussianBlur(frame,(3,3),0)
        frame = cv.erode(frame,kernel,iterations=3)
        frame = cv.dilate(frame,kernel,iterations=1)
    
    return frame

def main():
    cap = cv.VideoCapture(0)
    profile = []
    rec = False
    seq = Sequence()

    displayaction = -1
    savedaction = None


    # ignore first two frames
    for i in range(2):
        ret, frame = cap.read()

    while(True):
        ret, frame = cap.read()
        frame = cv.flip(frame,1)
        frame_o = cv.resize(frame,(0,0),fx=0.3,fy=0.3)
        #frame = denoise(frame_o,iterations = 3)
        frame = frame_o

        # Increase contrast of the image
        frame_lab = cv.cvtColor(frame, cv.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv.split(frame_lab)
        clahe = cv.createCLAHE(clipLimit=3, tileGridSize=(8, 8))
        cl = clahe.apply(l_channel)
        merged_channels = cv.merge((cl, a_channel, b_channel))
        frame = cv.cvtColor(merged_channels, cv.COLOR_LAB2BGR)

        # START PROFILING
        if len(profile) < PROFILE_COUNT:
            cv.putText(frame,"Cover the area with your hand and press c",(int(0.05*frame.shape[1]),int(0.97*frame.shape[0])),cv.FONT_HERSHEY_SIMPLEX,0.35,(0,255,255),1,8)
            if not rec:
                x,y,h,w = get_sampling_coord(frame.shape)
                rec = True
            cv.rectangle(frame_o,(x,y),(x+w,y+h),(0,255,0))
            cv.imshow('sampling',frame_o)
            k = cv.waitKey(1)
            if k & 0xFF == ord('c'):
                roi = frame[y:y+h,x:x+w]
                rec = False
                profile.append(get_profile(roi))
                continue
            elif k & 0xFF == ord('q'):
                cap.release()
                cv.destroyAllWindows()
                break
            else:
                continue
        else:
            cv.destroyWindow('sampling')

        # DONE PROFILING
        thresh_list = []
        for i in range(PROFILE_COUNT):
            thresh_list.append(get_thresh(frame,profile[i]))

        thresh = thresh_list[0]
        for i in range(1,len(thresh_list)):
            thresh = cv.bitwise_or(thresh,thresh_list[i])

        frame[thresh==0]=0

        # blur, erode, dilate
        thresh = denoise(thresh,iterations=2)

        _,contours,hierarchy = cv.findContours(thresh.astype('uint8'), cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

        
        h = Hand(thresh,contours,hierarchy)
        if len(h.contours) != 0:
            cnts = h.contours
            out = np.zeros_like(thresh)
            mask = np.zeros_like(thresh)
            cv.drawContours(mask,[cnts[0]],-1,255,-1)
            out[mask == 255] = thresh[mask == 255]
            if len(cnts) == 4:
                mask2 = np.zeros_like(thresh)
                cv.drawContours(mask2,[cnts[2]],-1,255,-1)
                out[mask2 == 255] = thresh[mask2 == 255]

            out = cv.cvtColor(out,cv.COLOR_GRAY2BGR)
            cv.drawContours(out,[cnts[0]],0,(255,255,255),-1)
            hull = cv.convexHull(cnts[0])
            cv.drawContours(out, [hull], 0, (0,0,255),2)
            if len(cnts) == 4:
                cv.drawContours(out,[cnts[2]],0,(255,255,255),-1)
                hull2 = cv.convexHull(cnts[2])
                cv.drawContours(out, [hull2], 0, (0,0,255),2)
            for i in range(len(h.defects)):
                cv.circle(out,h.defects[i],5,[255,0,255],2)


        #loc = id2loc(h.loc)
        #loc2 = 'none'
        #if h.loc2 != -1:
        #    loc2 = id2loc(h.loc2)
        shape = id2shape(h.shape)
        shape2 = id2shape(h.shape2)
        two_hand_shape = id2shape(h.two_hand_shape)
        action = seq.update(h)
        if seq.gesture is not None:
            if isinstance(seq.gesture, tuple):
                s1, m = seq.gesture
                motion = id2shape(s1) + ' ' + m
            else:
                motion = seq.gesture
            cv.putText(out,motion,(int(0.02*frame.shape[1]),int(0.05*frame.shape[0])),cv.FONT_HERSHEY_SIMPLEX,0.35,(0,255,0),1,8)


        #motion = seq.detect_motion()
        #if motion != 'no motion':
        #    print(motion)
        #    if motion != 'still':
        #        print(seq.seq[0])
        cv.putText(out,'hand1: '+shape,(int(0.02*frame.shape[1]),int(0.1*frame.shape[0])),cv.FONT_HERSHEY_SIMPLEX,0.35,(0,255,0),1,8)
        cv.putText(out,'hand2: '+shape2,(int(0.3*frame.shape[1]),int(0.1*frame.shape[0])),cv.FONT_HERSHEY_SIMPLEX,0.35,(0,255,0),1,8)
        cv.putText(out,'two hand: '+two_hand_shape,(int(0.02*frame.shape[1]),int(0.15*frame.shape[0])),cv.FONT_HERSHEY_SIMPLEX,0.35,(0,255,0),1,8)
        cv.putText(out,'mode: '+id2mode(seq.mode),(int(0.02*frame.shape[1]),int(0.2*frame.shape[0])),cv.FONT_HERSHEY_SIMPLEX,0.35,(0,255,0),1,8)



        if displayaction >= 0:
            displayaction -= 1
            if action == '':
                cv.putText(out, savedaction, (int(0.6*frame.shape[1]),int(0.05*frame.shape[0])), cv.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),1,8)

        if action != '':
            savedaction = action
            cv.putText(out, action, (int(0.6*frame.shape[1]),int(0.05*frame.shape[0])), cv.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),1,8)
            displayaction = 10


        thresh = cv.cvtColor(thresh,cv.COLOR_GRAY2BGR)
        res = np.vstack((out,thresh))

        cv.imshow('Output',res)

        k = cv.waitKey(1)
        if k & 0xFF == ord('q'):
            cap.release()
            cv.destroyAllWindows()
            break

if __name__ == "__main__":
    main()
