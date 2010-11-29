# -*- coding: utf-8 -*-
"""Tests for the mdp dependency parser commandline tool"""
from mrv.test.lib import *

try:
	from mrv.mdp import *
except TypeError:
	pass # expected 
else:
	raise AssertionError("Shouldn't be possible to import mdp directly")
# END import testing


class TestMDPTool( unittest.TestCase ):
	def test_base( self ):
		# tests just the import for now
		pass

