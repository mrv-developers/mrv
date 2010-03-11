# -*- coding: utf-8 -*-
""" Test the scene methods """
import unittest
from mayarv.maya.scene import Scene
import maya.OpenMaya as om
import os.path as path
import mayarv.maya.env as env
import tempfile
import shutil
import mayarv.test.maya as common
from mayarv.path import Path

class TestSceneRunner( unittest.TestCase ):
	""" Test the database """

	def setUp( self ):
		""" Initialize test scene """
		self.called = False				# reset callback check


	#{ Callback methods
	def cbgroup_zero( self, boolStatusRef, clientData ):
		self.called = True

	def cbgroup_one( self, retcode, fileobj, clientData ):
		self.called = True

	def cbgroup_two( self, clientData ):
		self.called = True
	#}

	def _runMessageTest( self, listenerID, sceneMessageID, function, callbackTriggerFunc ):
		""" Run a message test for the given sceneMessageID
		@param callbackTriggerFunc: called to trigger the callback we are testing"""
		sid = sceneMessageID
		ncb = len( Scene.Callbacks._callbacks.get( sid , [] ) )

		Scene.Callbacks.addListener( listenerID, function, sid )
		assert len( Scene.Callbacks._callbacks[ sid ] ) == ncb + 1 

		# make a new scene - we should be called
		callbackTriggerFunc()
		assert self.called 

		Scene.Callbacks.removeListener( listenerID, sid )
		assert len( Scene.Callbacks._callbacks[ sid ] ) == ncb 

	def test_cbgroup_zero( self ):
		"""mayarv.maya.scene: use group 0 check callbacks """
		if env.getAppVersion( )[0] == 8.5:
			return

		self._runMessageTest( "test_two", om.MSceneMessage.kBeforeNewCheck,
							 	lambda *args: TestSceneRunner.cbgroup_zero( self,*args ),
								Scene.new )

	def test_cbgroup_one( self ):
		"""mayarv.maya.scene: check file callback """
		if env.getAppVersion( )[0] == 8.5:
			return

		scenepath = common.get_maya_file( "sphere.ma" )
		triggerFunc = lambda : Scene.open( scenepath, force = 1 )
		self._runMessageTest( "test_one", om.MSceneMessage.kBeforeOpenCheck,
							 	lambda *args: TestSceneRunner.cbgroup_one( self,*args ),
								triggerFunc )

	def test_cbgroup_twp( self ):
		"""mayarv.maya.scene: Test ordinary scene callbacks """
		self._runMessageTest( "test_two", om.MSceneMessage.kBeforeNew,
							 	lambda *args: TestSceneRunner.cbgroup_two( self,*args ),
								lambda: Scene.new( force = True ) )

	def test_open( self ):
		"""mayarv.maya.scene: open file"""
		assert isinstance( Scene.open( common.get_maya_file( "empty.ma" ), force=True ), Path ) 

	def test_new( self ):
		"""mayarv.maya.scene: force a new scene """
		assert isinstance( Scene.new( force=1 ), Path ) 

	def test_saveAs( self ):
		"""mayarv.maya.scene: safe a file under new names and with different formats"""
		tmppath = Path( tempfile.gettempdir() ) / "maya_save_test"
		files = [ "mafile.ma" , "mb.mb", "ma.ma" ]
		for filename in files:
			mayafile = tmppath / filename
			Scene.save( mayafile , force=1 )
			assert mayafile.exists() 

		# must work for untitled files as well
		Scene.new( force = 1 )
		Scene.save( tmppath / files[-1], force = 1 )

		shutil.rmtree( tmppath )	# cleanup



	def tearDown( self ):
		""" Cleanup """
		pass

