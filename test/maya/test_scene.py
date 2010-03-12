# -*- coding: utf-8 -*-
""" Test the scene methods """
from mayarv.test.maya import *
from mayarv.maya.scene import *
import maya.OpenMaya as api
import mayarv.maya.env as env
from mayarv.path import Path
import mayarv.maya.ref as ref

import tempfile
import shutil

class TestScene( unittest.TestCase ):
	""" Test the database """

	#{ Callback methods
	def cbgroup_zero( self, boolStatusRef, clientData ):
		self.called = True

	def cbgroup_one( self, retcode, fileobj, clientData ):
		self.called = True

	def cbgroup_two( self, clientData ):
		self.called = True
	#}

	def _runMessageTest( self, eventName, eventfunc, callbackTriggerFunc ):
		
		event_inst = getattr(Scene, eventName)
		assert event_inst._callbackId is None
		
		# register for event
		setattr(Scene(), eventName, eventfunc)
		
		self.called = False 
		callbackTriggerFunc()
		assert self.called
		
		
		assert event_inst._callbackId is not None
		getattr(Scene(), eventName).remove(eventfunc)
		assert event_inst._callbackId is None

	def test_cbgroup_zero( self ):
		"""mayarv.maya.scene: use group 0 check callbacks """
		if env.getAppVersion( )[0] == 8.5:
			return

		self._runMessageTest( 'beforeNewCheck',
							 	lambda *args: self.cbgroup_zero(*args ),
								Scene.new )

	def test_cbgroup_one( self ):
		"""mayarv.maya.scene: check file callback """
		if env.getAppVersion( )[0] == 8.5:
			return

		scenepath = get_maya_file( "sphere.ma" )
		triggerFunc = lambda : Scene.open( scenepath, force = 1 )
		self._runMessageTest( "beforeOpenCheck",
							 	lambda *args: self.cbgroup_one(*args ),
								triggerFunc )

	def test_cbgroup_twp( self ):
		"""mayarv.maya.scene: Test ordinary scene callbacks """
		self._runMessageTest( "beforeNew",
							 	lambda *args: self.cbgroup_two( *args ),
								lambda: Scene.new( force = True ) )

	def test_open( self ):
		scene_path = get_maya_file("empty.ma")
		opened_scene = Scene.open(scene_path, force=True)
		assert opened_scene == scene_path and isinstance(opened_scene, Path)
		
		# None reloads the current scene
		trans = cmds.group(empty=1)
		Scene.open(force=True)
		assert not cmds.objExists(trans)

	def test_new( self ):
		assert isinstance( Scene.new( force=1 ), Path )
		
	@with_scene('empty.ma')
	def test_rename(self):
		new_ext = ".mb"
		new_path = Scene.rename(Scene.getName()	.splitext()[0] + "newname%s" % new_ext)
		assert new_path.p_ext == new_ext

	@with_scene('empty.ma')
	def test_saveAs_export( self ):
		tmpdir = Path( tempfile.gettempdir() ) / "maya_save_test"
		try:
			shutil.rmtree( tmpdir )	# cleanup
		except OSError:
			pass
		
		files = [ "mafile.ma" , "mb.mb", "ma.ma" ]
		for filename in files:
			mayafile = tmpdir / filename
			assert not mayafile.exists()
			Scene.save( mayafile , force=1 )
			assert mayafile.exists() 
		# END for each file to save
		
		# test remove unknown nodes
		assert Scene.getName().p_ext == ".ma"
		target_path = tmpdir / 'withoutunknown.mb'
		unode = cmds.createNode("unknown")
		
		# this doesnt work unless we have real unknown data - an unknown node 
		# itself is not enough
		# self.failUnlessRaises(RuntimeError, Scene.save, target_path)
		Scene.save(target_path, autodeleteUnknown=True)
		
		assert not cmds.objExists(unode)
		
		# must work for untitled files as well
		Scene.new( force = 1 )
		Scene.save( tmpdir / files[-1], force = 1 )

		
		# TEST EXPORT
		#############
		# as long as we have the test dir
		# export all 
		eafile = tmpdir / "export_all.ma"
		assert not eafile.exists()
		assert Scene.export(eafile) == eafile
		assert eafile.exists()
		
		# export selected
		nodes = cmds.polySphere()
		cmds.select(cl=1)				 # selects newly created ... 
		
		esfile = tmpdir / "export_selected.ma"
		assert not esfile.exists()
		
		assert not cmds.ls(sl=1)
		assert Scene.export(esfile, nodes) == esfile
		assert not cmds.ls(sl=1)			# selection unaltered
		
		assert esfile.exists()
		
		# it truly exported our sphere
		Scene.new(force=1)
		esref = ref.createReference(esfile)
		assert len(list(esref.iterNodes(api.MFn.kMesh))) == 1
		
		shutil.rmtree( tmpdir )	# cleanup

