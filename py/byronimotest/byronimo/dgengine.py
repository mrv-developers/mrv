"""B{byronimotest.byronimo.util}
Test dependency graph engine


@newfield revision: Revision
@newfield id: SVN Id
"""

__author__='$Author: byron $'
__contact__='byron@byronimo.de'
__version__=1
__license__='MIT License'
__date__="$Date: 2008-05-06 12:45:38 +0200 (Tue, 06 May 2008) $"
__revision__="$Revision: 8 $"
__id__="$Id: decorators.py 8 2008-05-06 10:45:38Z byron $"
__copyright__='(c) 2008 Sebastian Thiel'


import unittest
from networkx import DiGraph
from byronimo.dgengine import *
from random import randint

nodegraph = Graph()
A = Attribute

#{ TestNodes 
class SimpleNode( NodeBase ):
	"""Create some simple attributes"""
	#{ Plugs 
	outRand = plug( "outRand", A( float, 0 ) )
	outMult = plug( "outMult", A( float, A.uncached ) )
	
	inInt = plug( "inInt", A( int, A.writable ) )
	inFloat = plug( "inFloat", A( float, 0, default = 2.5 ) )
	inFloatNoDef = plug( "inFloatNoDef", A( float, 0 ) )
	outFailCompute = plug( "outFail", A( str, A.computable ) )
	
	inFloat.affects( outRand )
	inFloatNoDef.affects( outRand )
	
	inInt.affects( outMult )
	inFloat.affects( outMult )
	
	#inFloat.affects( 
	#}
	
	
	def __init__( self ):
		super( SimpleNode, self ).__init__( nodegraph )
		
		
	def compute( self, plug, mode ):
		"""Compute some values"""
		if plug == SimpleNode.outFailCompute:
			raise ComputeFailed( "Test compute failed" )
		elif plug == SimpleNode.outRand:
			return float( randint( 1, self.inFloat.get( ) * 10000 ) )
		elif plug == SimpleNode.outMult:
			return self.inInt.get( ) * self.inFloat.get( )
		raise PlugUnhandled( )


#}


class TestDAGTree( unittest.TestCase ):
	
	def test_fullFeatureTest( self ):
		"""dgengine: Test full feature set"""
		s1 = SimpleNode( )
		
		self.failUnless( SimpleNode.outRand.providesOutput() )
		self.failUnless( SimpleNode.inFloat.providesInput() )
		
		# SET VALUES
		#############
		self.failUnlessRaises( NotWritableError, s1.inFloat.set, "this" )
		self.failUnlessRaises( NotWritableError, s1.outRand.set, "that" )
		
		# computation failed check
		self.failUnlessRaises( ComputeFailed, s1.outFailCompute.get  )
		
		# missing default value
		self.failUnlessRaises( MissingDefaultValueError, s1.inInt.get )
		
		# now we set a value 
		self.failUnlessRaises( TypeError, s1.inInt.set, "this" )	# incompatible type
		s1.inInt.set( 5 )											# this should work though
		self.failUnless( s1.inInt.get( ) == 5 )					# should be cached 
		s1.inInt.clearCache()
		
		self.failUnlessRaises( MissingDefaultValueError, s1.inInt.get )	# cache is gone
		self.failUnless( s1.inFloat.get( ) == 2.5 )
		self.failUnlessRaises( NotWritableError, s1.inFloat.set, "this" )
		
		myint = s1.outRand.get( )		# as it is cached, the value should repeat
		self.failUnless( s1.outRand.hasCache() )
		self.failUnless( s1.outRand.get( ) == myint )
		s1.outRand.plug.attr.flags &= Attribute.uncached
		
		
		# CONNECTIONS
		##############
		s2 = SimpleNode()
		s3 = SimpleNode()
		s1.outRand.connect( s2.inFloat )
		s1.outRand.connect( s2.inFloat )		# works as it is already connected to what we want
		
		# check its really connected
		self.failUnless( s2.inFloat.getInput( ) == s1.outRand )
		self.failUnless( s1.outRand.getOutputs()[0] == s2.inFloat )
		
		
		# connecting again should throw without force
		self.failUnlessRaises( PlugAlreadyConnected, s3.outRand.connect, s2.inFloat )
		# force works though, disconnects otheone
		s3.outRand.connect( s2.inFloat, force = 1 )
		self.failUnless( s2.inFloat.getInput( ) == s3.outRand )
		self.failUnless( len( s1.outRand.getOutputs() ) == 0 )
		
		
		# MULTI CONNECT 
		##################
		s1.inFloat.connect( s3.inFloat )
		s2.inInt.connect( s3.inInt )
		
		# inInt does not have a default value, so computation fails unhandled 
		self.failUnlessRaises( ComputeError, s3.outMult.get )	
		
		# set in int and it should work
		s2.inInt.set( 4 )
		self.failUnless( s3.outMult.get( ) == 10 )	# 2.5 * 4
		
		# make the float writable 
		s1.inFloat.plug.attr.flags |= A.writable
		s1.inFloat.set( 2.0 )
		self.failUnless( s3.outMult.get( ) == 8 )	# 2.0 * 4
		
		
		# DIRTY CHECKING
		###################
		s3.outMult.plug.attr.flags ^= A.uncached
		self.failUnless( s3.outMult.get( ) == 8 )		# now its cached 
		s1.inFloat.set( 3.0 )								# plug is being dirtied and cache is deleted 
		self.failUnless( s3.outMult.get( ) == 12 )
		
		
		
		
		# ITERATION
		############
		# breadth first by default, no pruning, UP
		piter = iterPlugs( s3.outMult )
		
		self.failUnless( piter.next() == s3.outMult )
		self.failUnless( piter.next() == s3.inFloat )
		self.failUnless( piter.next() == s3.inInt )
		self.failUnless( piter.next() == s1.inFloat )
		self.failUnless( piter.next() == s2.inInt )
		self.failUnlessRaises( StopIteration, piter.next )
		
		# branch_first 
		piter = iterPlugs( s3.outMult, branch_first = True )
		self.failUnless( piter.next() == s3.outMult )
		self.failUnless( piter.next() == s3.inFloat )
		self.failUnless( piter.next() == s1.inFloat )
		self.failUnless( piter.next() == s3.inInt )
		self.failUnless( piter.next() == s2.inInt )
		self.failUnlessRaises( StopIteration, piter.next )
		
		# DOWN ITERATION
		##################
		piter = iterPlugs( s2.inInt, direction="down", branch_first = True )
		
		self.failUnless( piter.next() == s2.inInt )
		self.failUnless( piter.next() == s3.inInt )
		self.failUnless( piter.next() == s3.outMult )
		self.failUnless( piter.next() == s2.outMult )
		self.failUnlessRaises( StopIteration, piter.next )
		
		piter = iterPlugs( s2.inInt, direction="down", branch_first = False )
		
		self.failUnless( piter.next() == s2.inInt )
		self.failUnless( piter.next() == s3.inInt )
		self.failUnless( piter.next() == s2.outMult )
		self.failUnless( piter.next() == s3.outMult )
		self.failUnlessRaises( StopIteration, piter.next )
		
		# NODE BASED CONNECTION QUERY 
		##############################
		self.failUnless( len( s3.getConnections( 1, 0 ) ) == 2 )
		self.failUnless( len( s3.getConnections( 0, 1 ) ) == 1 )
		self.failUnless( len( s3.getConnections( 1, 1 ) ) == 3 )
		
		
		
		# PLUG FILTERING 
		#################
		intattr = A( int, 0 )
		floatattr = A( float, 0 )
		inplugs = SimpleNode.getInputPlugs()
		
		self.failUnless( len( SimpleNode.filterCompatiblePlugs( inplugs, intattr ) ) == 1 )
		self.failUnless( len( SimpleNode.filterCompatiblePlugs( inplugs, intattr, raise_on_ambiguity=1 ) ) == 1 )
		
		self.failUnless( len( SimpleNode.filterCompatiblePlugs( inplugs, floatattr ) ) == 2 )
		self.failUnlessRaises( TypeError, SimpleNode.filterCompatiblePlugs, inplugs, floatattr, raise_on_ambiguity = 1 )
		
	def test_copy( self ):
		"""dgengine: copy the graph"""
		# test shallow copy 
		global nodegraph
		cpy = nodegraph.copy()
		
		self.failUnless( len( cpy._nodes ) == len( nodegraph._nodes ) )
		