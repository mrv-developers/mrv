#-*-coding:utf-8-*-
"""
@package mrv.test.lib
@brief Various utilities are available from this package

@copyright 2012 Sebastian Thiel
"""

from util import *
# needs to stay in a module, otherwise nose will pick up the runTest method 
# from the TestCase class which is just a string - its odd 
import unittest 