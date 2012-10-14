#-*-coding:utf-8-*-
"""
@package mrv.maya.ui.panel
@brief Contains implementations of maya editors

@copyright 2012 Sebastian Thiel
"""

import base as uibase
import util as uiutil


class Panel( uibase.NamedUI, uiutil.UIContainerBase ):
    """ Structural base  for all Layouts allowing general queries and name handling
    Layouts may track their children """

