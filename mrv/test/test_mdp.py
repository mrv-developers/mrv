#-*-coding:utf-8-*-
"""
@package mrv.test.test_mdp
@brief test for mrv.mdp

@copyright 2012 Sebastian Thiel
"""

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

