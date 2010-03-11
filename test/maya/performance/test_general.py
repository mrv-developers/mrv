# -*- coding: utf-8 -*-
""" Test general performance """
from mayarv.test.maya import *
import mayarv.maya as bmaya
import mayarv.maya.nodes as nodes
from mayarv.maya.nodes import Node, NodeFromObj
import mayarv.test.maya as common
import sys
import maya.cmds as cmds
import maya.OpenMaya as api
import string
import random
import time
import mayarv.maya.nodes.it as it

class TestGeneralPerformance( unittest.TestCase ):
	"""Tests to benchmark general performance"""

	deptypes =[ "facade", "groupId", "objectSet"  ]
	dagtypes =[ "nurbsCurve", "nurbsSurface", "subdiv", "transform" ]

	def _createNodeFromName( self, name ):
		"""@return: newly created maya node named 'name', using the respective
		type depending on its path ( with pipe or without"""
		nodetype = None
		if '|' in name:			# name decides whether dag or dep node is created
			nodetype = random.choice( self.dagtypes )
		else:
			nodetype = random.choice( self.deptypes )

		return nodes.createNode( name, nodetype, renameOnClash=True )


	def test_buildTestScene( self ):
		"""mayarv.maya.benchmark.general: build test scene with given amount of nodes  """
		return 	# disabled
		 
		numNodes = 100000
		cmds.undoInfo( st=0 )
		targetFile = common.get_maya_file( "large_scene_%i.mb" % numNodes )
		bmaya.Scene.new( force = True )

		print 'Creating benchmark scene at "%s"' % targetFile

		nslist = genNestedNamesList( numNodes / 100, (0,3), genRandomNames(10,(3,8)),":" )
		nodenames = genNodeNames( numNodes, (1,8),(3,8),nslist )

		for i, name in enumerate( nodenames ):
			try:
				self._createNodeFromName( name )
			except NameError:
				pass

			if i % 500 == 0:
				print >>sys.stderr, "%i of %i nodes created" % ( i, numNodes )
		# END for each nodename

		cmds.undoInfo( st=1 )
		bmaya.Scene.save( targetFile )


	def test_dagwalking( self ):
		"""mayarv.maya.benchmark.general.dagWalking: see how many nodes per second we walk"""

		# numnodes = [ 2500, 25000, 100000 ]
		numnodes = [ 2500 ]
		for nodecount in numnodes:
			benchfile = common.get_maya_file( "large_scene_%i.mb" % nodecount )
			bmaya.Scene.open( benchfile, force = 1 )

			# DIRECT ITERATOR USE
			st = time.time( )
			iterObj = api.MItDag( )
			nc = 0
			while not iterObj.isDone( ):
				dPath = api.MDagPath( )
				iterObj.getPath( dPath )
				iterObj.next()
				nc += 1
			# END for each dagpath
			elapsed = time.time() - st
			print >>sys.stderr, "Walked %i nodes directly in %f s ( %f / s )" % ( nc, elapsed, nc / elapsed )

			
			for dagPath in range(2):
				for traversalmode in range(2):
					for asNode in range(2):
						# DAGPATHS NO NODE CONVERSION
						st = time.time( )
						nc = 0
						for dagpath in it.iterDagNodes( dagpath = dagPath, depth=traversalmode, asNode = asNode ):
							nc += 1
						elapsed = time.time() - st
						print >>sys.stderr, "iterDagNode: Walked %i dag nodes (dagPath=%i, depth-first=%i, asNode=%i) in %f s ( %f / s )" % ( nc, dagPath, traversalmode, asNode, elapsed, nc / elapsed )
					# END for each asNode value
				# END for each traversal
			# END for each dagpath mode
			
			# FROM LS
			st = time.time( )
			sellist = nodes.toSelectionListFromNames( cmds.ls( type="dagNode" ) )
			nsl = len(sellist)
			for node in it.iterSelectionList( sellist, handlePlugs = False, asNode = False ):
				pass
			elapsed = time.time() - st
			print >>sys.stderr, "Listed %i nodes with ls in %f s ( %f / s )" % ( nsl, elapsed, nsl / elapsed )

			cmds.select( cmds.ls( type="dagNode" ) )
			st = time.time( )
			sellist = api.MSelectionList()
			api.MGlobal.getActiveSelectionList( sellist )
			nsl = len(sellist)
			
			# selection list testing
			for asNode in range(2):
				for handlePlugs in range(2):
					for handleComponents in range(2):
						st = time.time( )
						for item in it.iterSelectionList( sellist, handlePlugs=handlePlugs, 
															asNode=asNode, handleComponents=handleComponents ):
							pass
						# END for each item
						elapsed = time.time() - st
						print >>sys.stderr, "iterSelList: Listed %i nodes from active selection (asNode=%i, handlePlugs=%i, handleComponents=%i) in %f s ( %f / s )" % ( nsl, asNode, handlePlugs, handleComponents, elapsed, nsl / elapsed )
					# END for handle components
				# END for handle plugs 
			# END for asNode
				
			# dg walking
			for asNode in range(2):
				nc = 0
				st = time.time( )
				for node in it.iterDgNodes(asNode=asNode):
					nc += 1
				# END for each node
				elapsed = time.time() - st
				print >>sys.stderr, "iterDgNodes: Walked %i nodes (asNode=%i) in %f s ( %f / s )" % ( nc, asNode, elapsed, nc / elapsed )
			# END for each node

		# END for each run

	def test_createNodes( self ):
		"""mayarv.maya.benchmark.general: test random node creation performance"""
		bmaya.Scene.new( force = True )
		runs = [ 100,2500 ]
		all_elapsed = []

		numObjs = len( cmds.ls() )
		for numNodes in runs:

			nslist = genNestedNamesList( numNodes / 100, (0,3), genRandomNames(10,(3,8)),":" )
			nodenames = genNodeNames( numNodes, (1,5),(3,8),nslist )

			st = time.time( )
			undoobj = undo.StartUndo( )
			for nodename in nodenames:
				try:	# it can happen that he creates dg and dag nodes with the same name
					self._createNodeFromName( nodename )
				except NameError:
					pass
			# END for each node
			del( undoobj )	# good if we raise runtime errors ( shouldnt happend )

			elapsed = time.time() - st
			all_elapsed.append( elapsed )
			print >>sys.stderr, "Created %i nodes in %f s ( %f / s )" % ( numNodes, elapsed, numNodes / elapsed )

			# UNDO OPERATION
			st = time.time()
			cmds.undo()
			elapsed = time.time() - st
			print >>sys.stderr, "Undone Operation in %f s" % elapsed

		# END for each run

		# assure the scene is the same as we undo everything
		self.failUnless( len( cmds.ls() ) == numObjs )


		# TEST MAYA NODE CREATION RATE
		#################################
		# redo last operation to get lots of nodes
		cmds.redo( )
		nodenames = cmds.ls( l=1 )
		Nodes = []

		st = time.time( )
		for name in nodenames:
			Nodes.append( Node( name ) )

		elapsed = time.time() - st
		print >>sys.stderr, "Created %i WRAPPED Nodes ( from STRING ) in %f s ( %f / s )" % ( len( nodenames ), elapsed, len( nodenames ) / elapsed )


		# CREATE MAYA NODES FROM DAGPATHS AND OBJECTS
		st = time.time( )
		tmplist = list()	# previously we measured the time it took to append the node as well
		for node in Nodes:
			if isinstance( node, nodes.DagNode ):
				tmplist.append( Node( node._apidagpath ) )
			else:
				tmplist.append( Node( node._apiobj ) )
		# END for each wrapped node

		api_elapsed = time.time() - st
		print >>sys.stderr, "Created %i WRAPPED Nodes ( from APIOBJ ) in %f s ( %f / s ) -> %f %% faster" % ( len( nodenames ), api_elapsed, len( nodenames ) / api_elapsed, (elapsed / api_elapsed) * 100 )


		# CREATE MAYA NODES USING THE FAST CONSTRUCTOR
		st = time.time( )
		tmplist = list()	# previously we measured the time it took to append the node as well
		for node in Nodes:
			if isinstance( node, nodes.DagNode ):
				tmplist.append( NodeFromObj( node._apidagpath ) )
			else:
				tmplist.append( NodeFromObj( node._apiobj ) )
		# END for each wrapped node

		api_elapsed = time.time() - st
		print >>sys.stderr, "Created %i WRAPPED Nodes ( from APIOBJ using NodeFromObj) in %f s ( %f / s ) -> %f %% faster" % ( len( nodenames ), api_elapsed, len( nodenames ) / api_elapsed, (elapsed / api_elapsed) * 100 )


		# RENAME PERFORMANCE
		st = time.time()
		for node in (n for n in tmplist if isinstance(n, nodes.DagNode)):
			node.rename(node.getBasename()[:-1])
		# END for each node 
		elapsed = time.time() - st
		ltl = len(tmplist)
		print >>sys.stderr, "Renamed %i WRAPPED Nodes in %f s ( %f / s )" % ( ltl, elapsed, ltl / elapsed )


	def test_intarray_creation(self):
		pass
		# is tested in test_geometry through the Mesh class
	
	@with_scene("samurai_jet_graph.mb")
	def test_graph_iteration(self):
		root = nodes.Node('Jetctrllers')
		for rootitem in (root, root.drawInfo):
			for breadth in range(2):
				for plug in range(2):
					for asNode in range(2):
						st = time.time( )
						ic = 0
						for item in it.iterGraph(rootitem, breadth=breadth, plug=plug, asNode=asNode): 
							ic += 1
						# END for each item
						elapsed = time.time() - st
						print >>sys.stderr, "iterGraph: Traversed %i items from %s (asNode=%i, plug=%i, breadth=%i) in %f s ( %f / s )" % ( ic, rootitem, asNode, plug, breadth, elapsed, ic / elapsed )
					# END for each asNode value
				# END for each asPlug value
			# END for each traversal type
		# END for each root
		

	def test_wrappedFunctionCall( self ):
		"""mayarv.maya.benchmark.general: test wrapped funtion calls and compare them"""

		bmaya.Scene.new( force = True )

		p = Node('perspShape')

		# method access
		a = time.time()
		na = 10000
		for i in xrange( na ):
			p.focalLength  # this wraps the API
		b = time.time()
		print >>sys.stderr, "%f s (%f/s) : node.focalLength" % ( b - a, na/(b-a) )

		# node wrapped
		a = time.time()
		for i in xrange( na ):
			p.focalLength()  # this wraps the API
		b = time.time()
		print >>sys.stderr, "%f s (%f/s) : node.focalLength()" % ( b - a, na/(b-a) )

		# node speedwrapped
		a = time.time()
		for i in xrange( na ):
			p._api_focalLength()  # this wraps the API directly
		b = time.time()
		print >>sys.stderr, "%f s (%f/s): node._api_focalLength()" % ( b - a, na/(b-a) )

		# node speedwrapped + cached
		a = time.time()
		api_get_focal_length = p._api_focalLength
		for i in xrange( na ):
			api_get_focal_length()  # get rid of the dictionary lookup
		b = time.time()
		print >>sys.stderr, "%f s (%f/s): _api_focalLength()" % ( b - a, na/(b-a) )

		# mfn recreate
		a = time.time()
		for i in xrange( na ):
			camfn = api.MFnCamera( p.getMObject() )
			camfn.focalLength()  # this wraps the API
		b = time.time()
		print >>sys.stderr, "%f s (%f/s): recreated + call" % ( b - a, na/(b-a) )

		# mfn directly
		camfn = api.MFnCamera( p.getMObject() )
		a = time.time()
		for i in xrange( na ):
			camfn.focalLength()  # this wraps the API
		b = time.time()
		print >>sys.stderr, "%f s (%f/s): mfn.focalLenght()" % ( b - a, na/(b-a) )

		# plug wrapped
		a = time.time()
		for i in xrange( na ):
			p.fl.asFloat()  # this wraps the API
		b = time.time()
		print >>sys.stderr, "%f s (%f/s): node.plug.asFloat()" % ( b - a, na/(b-a) )

		# single plug access
		a = time.time()
		for i in xrange( na ):
			p.fl
		b = time.time()
		print >>sys.stderr, "%f s (%f/s): node.fl" % ( b - a, na/(b-a) )
		
		# plug cached
		a = time.time()
		fl = p.fl
		for i in xrange( na ):
			fl.asFloat()  # this wraps the API
		b = time.time()
		print >>sys.stderr, "%f s (%f/s): plug.asFloat()" % ( b - a, na/(b-a) )
		
	
	def test_create_nodes(self):
		bmaya.Scene.new(force=1)
		
		nn = 1000
		for node_type in ("network", "transform"):
			# CREATE NODES
			st = time.time()
			node_list = list()
			for number in xrange(nn):
				n = nodes.createNode(node_type, node_type)
				node_list.append(n)
			# END for each node to created
			elapsed = time.time() - st
			print >>sys.stderr, "Created %i %s nodes in  %f s ( %f nodes / s )" % (nn, node_type, elapsed, nn/elapsed)
			
			# RENAME
			st = time.time()
			for node in node_list:
				if isinstance(node, nodes.DagNode):
					node.rename(node.getBasename()[:-1])
				else:
					node.rename(node.name()[:-1])
				# END rename nodes handling
			# END for each node to rename
			elapsed = time.time() - st
			print >>sys.stderr, "Renamed %i %s nodes in  %f s ( %f nodes / s )" % (nn, node_type, elapsed, nn/elapsed)
		# END for each node type
		



#{ Name Generators
def genRandomNames( numNames, wordLength ):
	"""Generate random names from characters allowed by maya
	@param wordLength: length of the generated word
	@return: list of names
	@note: currently we do not use numbers"""
	outlist = []
	for n in xrange( numNames ):
		name = ''
		for i in xrange( random.randint( wordLength[0], wordLength[1] ) ):
			name += random.choice( string.ascii_letters )
		outlist.append( name )
	# END for each name
	return outlist

def genNestedNamesList( numNames, nestingRange, wordList, sep ):
	"""Create a random list of nested names where each subname is separated by sep, like
	[ 'asdf:efwsf','asdfic:oeafsdf:asdfas' ]
	@param numNames: number of names to generate
	@param maxNestingLevel: tuple( min,max ) 0 for single names, other for names combined using sep
	@param wordList: words we may choose from to create nested names
	@param sep: separator between name tokens
	@return: list of nested words"""
	outnames = []
	for n in xrange( numNames ):
		nlist = []
		for t in xrange( random.randint( nestingRange[0], nestingRange[1] ) ):
			nlist.append( random.choice( wordList ) )
		outnames.append( sep.join( nlist ) )
	return outnames

def genNodeNames( numNames, dagLevelRange, wordRange, nslist ):
	"""Create  random nodenames with a dag path as depe as maxDagLevel using
	@param numNames: number of names to generate
	@param dagLevelRange: tuple( min, max ), defining how deept the nesting may be
	@param wordRange: tuple ( min,max ), defining the minimum and maximum word length
	@note: subnamespaces can repeat in name
	@return: the generated name """
	# gen names
	nodenames = genRandomNames( numNames, wordRange )
	dagpaths = genNestedNamesList( numNames, dagLevelRange, nodenames, '|' )
	if not nslist:
		return dagpaths

	# otherwise put the namespaces in there, random pick
	nsdagpaths = []
	for dagpath in dagpaths:
		tokens = dagpath.split( '|' )
		for i in xrange( len( tokens ) ):
			tokens[ i ] = random.choice( nslist ) + ":" + tokens[ i ]
		nsdagpaths.append( '|'.join( tokens ) )
	# END for each dagpath
	return nsdagpaths

#} END name generators
