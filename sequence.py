'''
Keeps track of a sequence of Hand objects
'''

import os
import numpy as np
from collections import deque as dq
from collections import defaultdict
from hand import *
from database import *

'''
left swipe (loc): (upper right or mid right or lower right) -> (
'''

TRIGGER = 2
SCREENX = 1440
SCREENY = 900

## DESKTOP
gesture_map0 = {    #for applescript

    # swipe screen
    (1, 'swipe left') :     # ctrl + right
        [ 'swipe screen left',"""
        osascript -e '
        tell application "System Events"
            key code 124 using {control down}
        end tell'
        """],
    (1, 'swipe right') :    # ctrl + left
        ['swipe screen right', """
        osascript -e '
        tell application "System Events"
            key code 123 using {control down}
        end tell'
        """],

    (1, 'swipe up') :       # GET DOCK
        ['get dock', """
        osascript -e '
        tell application "Finder"
            set resolution to bounds of window of desktop
            set w to item 3 of resolution
            set h to item 4 of resolution

            do shell script "/usr/local/bin/MouseTools" & " -x " & w/2 & " -y " & h-1
        end tell
        '
        """],

    (1, 'swipe down') :     # Click
        """
        """,

    # app expose 
    (3, 'swipe up') :
        ['show app expose', """
        osascript -e '
        tell application "System Events"
            key code 160
        end tell'
        """],
    (3, 'swipe down') : 
        ['exit app expose', """
        osascript -e '
        tell application "System Events"
            key code 53
        end tell'
        """],

    # mission control
    (4, 'swipe up') :
        ['show mission control', """
        osascript -e '
        tell application "System Events"
            key code 131
        end tell'
        """],

    (4, 'swipe down') :
        ['exit mission control', """
        osascript -e '
        tell application "System Events"
            key code 53
        end tell'
        """],

    # show desktop
    (5, 'swipe up') : 
        ['show desktop', """
        osascript -e '
        tell application "System Events"
            key code 103 
        end tell'
        """],

    (5, 'swipe down') : 
        ['show screen', """
        osascript -e '
        tell application "System Events"
            key code 103 
        end tell'
        """]
}

###SYSTEM SETTINGS
gesture_map1 = {

    #Volume control
    (1, 'swipe up') : 
        ['volume up', """osascript -e 'set theOutput to output volume of (get volume settings) 
        set volume output volume (theOutput + 6.25)'"""],
        #'do shell script "afplay /System/Library/Sounds/Pop.aiff"']
    (1, 'swipe down') :
        ['volume down', """
        osascript -e '
        set theOutput to output volume of (get volume settings)
        set volume output volume (theOutput - 6.25)
        '
        """],

    # brightness control
    (2, 'swipe up') : 
        ['brightness up', """osascript -e '
        tell application "System Events" 
            key code 113 
        end tell'"""],

    (2, 'swipe down') : 
        ['brightness down' , """osascript -e '
        tell application "System Events" 
            key code 107 
        end tell'"""]

}

###### BROWSER
gesture_map2 = {       
    # scroll browser
    (1, 'swipe up') : 
        ['scroll up', 
        """osascript -e '
        tell application "System Events"
            key code 126 using option down
        end tell'
        """],

    (1, 'swipe down') :
        ['scroll down',
        """osascript -e '
        tell application "System Events"
            key code 125 using option down
        end tell'
        """],

    (1, 'swipe left') :     # ctrl + right
        [ 'go back',"""
        osascript -e '
        tell application "System Events"
            key code 123 
        end tell'
        """],

    (1, 'swipe right') :    # ctrl + left
        ['go forward', """
        osascript -e '
        tell application "System Events"
            key code 124
        end tell'
        """],

    (4, 'swipe up') : 
        ['new window', 
        """osascript -e '
        tell application "System Events"
            keystroke "n" using command down
        end tell'
        """],

    (5, 'swipe up') : 
        ['new window',
        """osascript -e '
        tell application "System Events"
            keystroke "n" using command down
        end tell'
        """],

    (5, 'swipe down') :
        ['close window', 
        """osascript -e '
        tell application "System Events"
            keystroke "w" using command down
        end tell'
        """],

    'zoom in' :
        ['zoom in', 
        """osascript -e '
        tell application "System Events"
            key code 24 using command down
        end tell'
        """],

    'zoom out' :
        ['zoom out', """
        osascript -e '
        tell application "System Events"
            key code 27 using command down
        end tell'
        """]
}

gesture_map_global = {

    'screenshot' :
        """
        osascript -e '
        set theDesktop to POSIX path of (path to desktop as string)
        set {short date string:d, time string:t} to current date
        set d to do shell script "/bin/echo " & quoted form of d & " | tr / -"
        set t to do shell script "/bin/echo " & quoted form of t & " | tr : -"
        set t to (characters 1 through ((length of t) - 3) of t) as string
        set shellCommand to "/usr/sbin/screencapture " & theDesktop & d & "-"  & t & ".png"
        do shell script shellCommand'
        """,

    'hush' :
        """
        osascript -e 'set volume with output muted'
        """,

    'sleep' :
        """
        osascript -e 'tell application "Finder" to sleep'
        """,

    'bye' : 
        """
        osascript -e '
        tell application "System Events" to tell process "python"
            set frontmost to true
            keystroke "q"
        end tell
            '
        """,

    'ok':
        """
        osascript -e '
        set {x,y} to paragraphs of (do shell script "/usr/local/bin/MouseTools" & " -location")
        do shell script "/usr/local/bin/MouseTools -x 1241 -y 75 -leftClick"
        do shell script "/usr/local/bin/MouseTools -releaseMouse"
        do shell script "/usr/local/bin/MouseTools" & " -x " & x & " -y " & y        
        '
        """

}

gesture_list = [ gesture_map0, gesture_map1, gesture_map2]

def id2gesture(id):
    return shape_list[id]

def loc2id(loc):
    return loc_list.index(loc)

def movemouse(x,y=0,dock=False):

    if dock:
        if (x >= 0):
            #print('move!')
            cmd = """
                osascript -e '
                set {{x, y}} to paragraphs of (do shell script "/usr/local/bin/MouseTools" & " -location")
                set newx to x+{0}
                if newx is greater than or equal to {1} then 
                    set newx to {2}-1
                end if
                do shell script "/usr/local/bin/MouseTools" & " -x " & newx & " -y " & y
                '
                """.format(x, SCREENX, SCREENX)

        else:
            cmd = """
                osascript -e '
                set {{x, y}} to paragraphs of (do shell script "/usr/local/bin/MouseTools" & " -location")
                set newx to x{0}
                if newx is less than 0 then 
                    set newx to 0
                end if
                do shell script "/usr/local/bin/MouseTools" & " -x " & newx & " -y " & y
                '
                """.format(x)

    else:

        if x >= 0 and y >= 0:
            cmd = """
                osascript -e '
                set {{x, y}} to paragraphs of (do shell script "/usr/local/bin/MouseTools" & " -location")
                set newx to x+{0}
                set newy to y+{1}
                set screenx to {2}
                set screeny to {3}
                if newx is greater than or equal to screenx then 
                    set newx to screenx-1
                end if
                if newy is greater than or equal to screeny then 
                    set newx to screeny-1
                end if
                do shell script "/usr/local/bin/MouseTools" & " -x " & newx & " -y " & newy'""".format(x, y, SCREENX, SCREENY)

        elif x >= 0 and y < 0:
            cmd = """
                osascript -e '
                set {{x, y}} to paragraphs of (do shell script "/usr/local/bin/MouseTools" & " -location")
                set newx to x+{0}
                set newy to y{1}
                set screenx to {2}
                if newx is greater than or equal to screenx then 
                    set newx to screenx-1
                end if
                if newy is less than 0 then 
                    set newx to 0
                end if
                do shell script "/usr/local/bin/MouseTools" & " -x " & newx & " -y " & newy'""".format(x, y, SCREENX)

        elif x < 0 and y >= 0:
            cmd = """
                osascript -e '
                set {{x, y}} to paragraphs of (do shell script "/usr/local/bin/MouseTools" & " -location")
                set newx to x{0}
                set newy to y+{1}
                set screeny to {2}
                if newx is less than 0 then 
                    set newx to 0
                end if
                if newy is greater than or equal to screeny then 
                    set newx to screeny-1
                end if
                do shell script "/usr/local/bin/MouseTools" & " -x " & newx & " -y " & newy'""".format(x, y, SCREENY)

        else:
            cmd = """
                osascript -e '
                set {{x, y}} to paragraphs of (do shell script "/usr/local/bin/MouseTools" & " -location")
                set newx to x{0}
                set newy to y{1}
                if newx is less than 0 then 
                    set newx to 0
                end if
                if newy is less than 0 then 
                    set newx to 0
                end if
                do shell script "/usr/local/bin/MouseTools" & " -x " & newx & " -y " & newy'""".format(x, y)

    #print(cmd)
    os.system(cmd)

def clickmouse(dock=False):
    if dock:
        cmd = """
        osascript -e '
        set {x, y} to paragraphs of (do shell script "/usr/local/bin/MouseTools" & " -location")
        tell application "System Events"
            click at {x, y}
        end tell
        do shell script "/usr/local/bin/MouseTools" & " -x " & x & " -y " & y-200
        '
        """
    else:
        cmd = """
        osascript -e '
        set {x, y} to paragraphs of (do shell script "/usr/local/bin/MouseTools" & " -location")
        do shell script "/usr/local/bin/MouseTools" & " -x " & x & " -y " & y & " -leftClick"
        do shell script "/usr/local/bin/MouseTools" & " -releaseMouse"'

        """
        '''
        tell application "System Events"
            click at {x, y}
        end tell'
        '''
    #print(cmd)
    os.system(cmd)
    return

def startcopy():
    cmd = """
    osascript -e '
    set {x, y} to paragraphs of (do shell script "/usr/local/bin/MouseTools" & " -location")
    do shell script "/usr/local/bin/MouseTools" & " -leftClick"
    do shell script "/usr/local/bin/MouseTools" & " -leftClickNoRelease"
    '
    """
    os.system(cmd)
    return

def finishcopy():
    cmd = """
    osascript -e '
    do shell script "/usr/local/bin/MouseTools" & " -releaseMouse"
    tell application "System Events" to keystroke "c" using command down
    '
    """
    os.system(cmd)
    return

def paste():
    cmd = """
    osascript -e '
    tell application "System Events" to keystroke "v" using command down
    '
    """
    os.system(cmd)
    return


class Sequence(object):
    def __init__(self,buf=3):
        #self.seq = dq([(-1,(-1,-1))]*buf) # (shape,loc) tuples
        self.seq = dq([None] * buf)
        self.gesture = None
        self.coord = -1

        self.twohand = None
        self.triggered = -1
        self.mode = 0
        self.framenum = 15
        self.righthanded = True
        self.copying = False
        self.numframes = 0
        self.sleepbuf = None

    def update(self,hand):
        self.seq.popleft()
        #if hand.shape == 'none':
        #    hand.shape = self.seq[1][0]
        #self.seq.append((hand.shape,hand.com))
        self.seq.append(hand)

        if hand.two_hand_shape != 0:
            if hand.two_hand_shape == 11:
                if self.twohand == None:
                    self.sleepbuf = [False] * 10
                #print(self.sleepbuf)
            elif self.sleepbuf is not None:
                self.sleepbuf = None
            self.twohand = hand.two_hand_shape

        if hand.two_hand_shape == 0 and self.twohand:
            if self.twohand == 11:
                self.sleepbuf = None
            self.twohand = None
            self.triggered = self.framenum

        if self.triggered >= 0:
            self.triggered -= 1
            return ''


        motion = self.detect_motion()
        self.gesture = self.get_gesture(motion)
        if self.mode >= 0:
            if self.gesture in gesture_map_global:          # Global gesture
                os.system(gesture_map_global[self.gesture])
                self.triggered = self.framenum + 10
                return self.gesture
            if self.gesture in gesture_list[self.mode]:    # check applescript dict
                os.system(gesture_list[self.mode][self.gesture][1])
                if self.mode == 0 and self.gesture == (1, 'swipe up'):  # enter dock mode
                    self.mode = -1
                self.triggered = self.framenum
                return gesture_list[self.mode][self.gesture][0]
            if self.gesture == 'oh':
                print('enter mouse control')
                self.mode = -2
                self.triggered = self.framenum
                return 'enter mouse control'

        else:
            # DOCK MODE
            if self.mode == -1:
                movemouse( 3*(hand.com[0] - self.seq[1].com[0]), dock=True)
                if self.gesture == (1,'swipe down'):        # exit dock mode
                    clickmouse(dock = True)
                    self.mode = 2
                    return 'exit dock mode'

            ## MOUSE CONTROL MODE
            if self.mode == -2: 
                if hand.shape == 5 or hand.shape == 4 :      # MOVE MOUSE
                    movemouse( 5*(hand.com[0] - self.seq[1].com[0]), y=5*(hand.com[1] - self.seq[1].com[1]) )
                    #print(5*(hand.com[0] - self.seq[1].com[0]), 20*(hand.com[1] - self.seq[1].com[1]) )
                    return ''
                if self.gesture == 'click' :
                    self.triggered = self.framenum
                    if not self.copying :       # Click
                        print('click')
                        clickmouse()
                        return 'click'
                    else:                       # Finish Copying
                        self.copying = False
                        finishcopy()
                        return 'finish copying'

                if self.gesture == 'copy':     # Start Copying
                    if self.copying:
                        return ''
                    else:
                        if self.numframes > 15:
                            self.numframes = 0
                            self.copying = True
                            startcopy()
                            return 'start copying'              
                        else:
                            self.numframes += 1

                if self.gesture == 'paste':     # Paste
                    if self.numframes > 15:                     ### loss of robustness in using same variable as copy
                        self.numframes = 0
                        paste()
                        self.triggered = self.framenum + 10
                        return 'paste'
                    else:
                        self.numframes += 1
                elif self.gesture == 'oh':                    # exit mouse control mode
                    self.mode = 2
                    self.triggered = self.framenum 
                    if self.copying:
                        finishcopy()
                        self.copying = False
                    return 'exit mouse control mode'
        return ''


    def detect_shape(self):
        pass

    def detect_motion(self):
        if None in self.seq:
            return 'no motion'
        prev, curr = self.seq[0].com, self.seq[2].com
        if prev == (-1,-1) or curr==(-1,-1):
            return 'no motion'


        #if self.triggered >= 0:
        #    self.triggered -= 1
        #    return 'no motion'

        # IF ONLY ONE HAND
        if not self.twohand and (self.seq[0].two_hand_shape == self.seq[2].two_hand_shape == 0):
            x, y = curr[0]-prev[0], curr[1]-prev[1]
            if abs(x) < 7 and abs(y) < 7:
                return 'still'
            if abs(x) > 3* abs(y) :
                if abs(x) > 30:
                    if x > 0:
                        return 'swipe right'
                    else:
                        return 'swipe left'
            if abs(y) > 3* abs(x) :
                if y > 0:
                    return 'swipe down'
                else:
                    return 'swipe up'
            return 'no motion'

        # IF TWO HANDS
        prev2, curr2 = self.seq[0].com2, self.seq[2].com2

        # IF HOORAY SLEEP BUFFER ALLOCATED
        if self.seq[1].two_hand_shape == self.seq[2].two_hand_shape == 11: # Hooray
            prevx = self.seq[1].com[0] - self.seq[1].com2[0]
            currx = curr[0] - curr2[0]
            diffx = currx-prevx
            diffy = curr[1] - prev[1]
            if abs(diffx) < 10 and diffy > 5:
                return 'hooray down'
            else: 
                return 'hooray not down'

        # IF ET
        if self.seq[0].two_hand_shape == self.seq[2].two_hand_shape == 13: # ET
            prevx = prev[0] - prev2[0]
            currx = curr[0] - curr2[0]
            diffx = currx-prevx
            if abs(diffx) > 20:         ##### THRESHOLD FOR ZOOM
                if diffx > 0:
                    return 'zoom in'
                else:
                    return 'zoom out'


    def get_gesture(self, motion):

        # if Mouse control mode
        if self.mode == -2:
            s1, s2, s3 = self.seq[0].shape, self.seq[1].shape, self.seq[2].shape
            if s1 == 5 or s2 == 5 or s3 == 5:
                return 'five'

        if motion == 'no motion':
            return None 
        if motion == 'still':
            s1, s2, s3 = self.seq[0].shape, self.seq[1].shape, self.seq[2].shape

            if s1 == s2 and s2 == s3:
                # CHANGE MODE
                if self.mode > 0:
                    if self.righthanded and self.seq[0].loc == 3:
                        if s1 == 1 or s1 == 2 or s1 == 3:
                            if self.mode != s1-1:
                                self.mode = s1 - 1
                                self.triggered = self.framenum
                                print(self.mode)
                    if not self.righthanded and self.seq[0].loc == 5:
                        if s1 == 1 or s1 == 2 or s1 == 3:
                            if self.mode != s1-1:
                                self.mode = s1 - 1
                                self.triggered = self.framenum
                                print(self.mode)

                # SCREENSHOT
                if s1 == 7:
                    return 'screenshot'

                # HUSH
                #if s1 == 12:
                #    return 'hush'

                # ENTER MOUSE CONTROL MODE
                if s1 == 10:
                    return 'oh'

                if s1 == 6:
                    return 'ok'

                # CLICK
                if s1 == 9:
                    return 'click'

                if s1 == 2:
                    return 'copy'
                if s1 == 3:
                    return 'paste'


                #return id2shape(s1)

        if motion == 'swipe up':
            s1, s2, s3 = self.seq[0].shape, self.seq[1].shape, self.seq[2].shape
            #if s2 == s3
            print (id2shape(s3), motion)
            print (id2shape(s1),id2shape(s2),id2shape(s3))
            return (s3, motion)

        if motion == 'swipe down':
            s1 = self.seq[0].shape
            if s1 == 'none':
                s1 = self.seq[1].shape
            if s1 == 'none':
                s1 = self.seq[2].shape

            print (id2shape(s1), motion)
            return (s1, motion)

        if motion == 'swipe right' or motion =='swipe left':
            s1 = self.seq[2].shape
            print (id2shape(s1), motion)
            return (1, motion)

        if motion == 'zoom in' or motion == 'zoom out':
            return motion

        if motion == 'hooray down':
            self.sleepbuf.pop(0)
            self.sleepbuf.append(True)
            if all(self.sleepbuf):
                print('bye')
                return 'bye'
        if motion == 'hooray not down':
            self.sleepbuf.pop(0)
            self.sleepbuf.append(False)




            



