'''
db for shapes, locs, gestures
'''

shape_list = ['none', 'one', 'two', 'three', 'four', 'five', 'ok', 'screenshot', 'chop', 'fist','oh','hooray', 'hush', 'et']
loc_list = ['upper left','upper center','upper right','mid left','center','mid right','lower left','lower center','lower right']

mode_list = ['desktop', 'system settings', 'browser', 'mouse control', 'dock control']

def shape2id(shape):
    return shape_list.index(shape)

def id2shape(id):
    return shape_list[id]

def loc2id(loc):
    return loc_list.index(loc)

def id2loc(id):
    return loc_list[id]

def id2mode(id):
	if id >= 0:
		return mode_list[id]
	else:
		return mode_list[id+5]

