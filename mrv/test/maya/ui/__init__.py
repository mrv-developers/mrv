#-*-coding:utf-8-*-
"""
@package mrv.test.maya.ui
@brief tests for mrv.maya.ui

@copyright 2012 Sebastian Thiel
"""


from util import NotificatorWindow 

#{ Globals
instructor = None
#} END globals

def _initialize_globals():
    """Installs the notification window which will show after the first set of 
    tests was added"""
    global instructor
    instructor = NotificatorWindow()
# END init

_initialize_globals()

