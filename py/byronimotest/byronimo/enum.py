# -*- coding: utf-8 -*-
"""B{byronimotset.byronimo.enum}

@note: adjusted by Sebastian Thiel
@newfield revision: Revision
@newfield id: SVN Id
"""

__author__='Don Garret'
__contact__='garret at bgb dot cc'
__version__=1
__license__='freeware'
__date__="$Date: 2008-05-29 02:30:46 +0200 (Thu, 29 May 2008) $"
__revision__="$Revision: 16 $"
__id__="$Id:$"
__copyright__='(c) 2003 Don Garret'

import unittest
import byronimo.enum as Enumeration
import operator
import pickle
from cStringIO import StringIO


class ElementTestCase(unittest.TestCase):
	def testElementComparisons(self):
		"""byronimo.enum: testElementComparisons"""
		e = Enumeration.create('fred', 'bob', 'joe', 'larry', 'moe')
		e2 = Enumeration.create('red', 'green', 'blue')
		e3 = Enumeration.create('fred', 'bob', 'joe', 'larry', 'moe')
		element = e.fred

		self.failUnless(e.fred == e.fred)
		self.failUnless(e.fred != e.bob)
		self.failUnless(e.fred < e.bob)
		self.failUnless(e.fred <= e.bob)
		self.failUnless(e.bob > e.fred)
		self.failUnless(e.bob >= e.bob)
		
		self.failUnless(element == e.fred)
		self.failUnless(element < e.bob)

		self.failUnless(e.fred < e.moe)
		self.failUnless(e.larry > e.bob)
		self.failUnless(e.joe < e.moe)
		
		self.failUnless(e.fred != e2.red)
		self.failUnless(e.fred != e3.fred)

		enumList = list(e)
		enumList.sort()

		for i in xrange(len(e)):
			self.failUnless(enumList[i] == e[i])

		self.failUnless(e == e)
		self.failUnless(e != e2)
		self.failUnless(e != e3)
		
		self.failUnless(e.fred != 'fred')

	def testElementRepresentation(self):
		"""byronimo.enum: testElementRepresentation"""
		e = Enumeration.create('fred', 'bob')

		self.failUnless('fred' == str(e.fred))
		self.failUnless('bob' == str(e[1]))

	def testElementToEnumeration(self):
		"""byronimo.enum: testElementToEnumeration"""
		e = Enumeration.create('fred', 'bob')

		i = e.fred

		self.failUnless(i.enumeration is e)
		self.failUnless(e.bob.enumeration is e)

	
class EnumerateTestCase(unittest.TestCase):

	def testMembers(self):
		"""byronimo.enum: testMembers"""
		e = Enumeration.create('George',
							   'John',
							   ('Paul', 2),
							   ('Ringo', 'drummer'))

		e.George
		e.John
		e.Paul
		e.Ringo

		try:
			e.Fred
			self.fail("Unkown member was found")
		except:
			pass


	def testTupleness(self):
		"""byronimo.enum: testTupleness"""
		e = Enumeration.create('George',
							   'John',
							   ('Paul', 2),
							   ('Ringo', 'drummer'))

		self.failUnless(len(e) == 4)

		constlist = [e.George, e.John, 2, 'drummer']

		extractlist = []
		for beatle in e:
			extractlist.append(beatle)

		self.failUnless(constlist == extractlist)
		self.failUnless(constlist == list(e))

		self.failUnless(e.George in e)
		self.failUnless('drummer' in e)
		self.failIf('Fred' in e)

		self.failUnless(e.George == e[0])
		self.failUnless(e.John	 == e[1])
		self.failUnless(e.Paul	 == e[2])
		self.failUnless(e.Ringo	 == e[3])

		
	def testMultipleEnums(self):
		"""byronimo.enum: testMultipleEnums"""
		e  = Enumeration.create('fred', 'bob')
		e2 = Enumeration.create('joe', 'bob')
		
		e.fred
		e.bob
		e2.joe
		e2.bob

		# elements in different sets should NOT be equal
		self.failUnless(e.bob != e2.bob)

		try:
			e.joe
			self.fail("Value from wrong enum")
		except:
			pass
		
	def testReadOnly(self):
		"""byronimo.enum: testReadOnly"""
		e = Enumeration.create('fred', 'bob')

		try:
			e.fred = e.bob
			self.fail("value assignment was allowed")
		except:
			pass

		try:
			e[0] = 1
			self.fail("index assignment was allowed")
		except:
			pass

		try:
			e.joe = 1
			self.fail("new value assignment was allowed")
		except:
			pass


	def testNameLookup(self):
		"""byronimo.enum: testNameLookup"""
		e = Enumeration.create('George', 'John',
							   ('Paul', 2), ('Ringo', 'drummer'))

		self.failUnless(e.George == e.valueFromName('George'))
		self.failUnless('drummer' == e.valueFromName('Ringo'))
		self.failUnless(e('Paul') == 2)

		try:
			e.valueFromName('jerry')
			self.fail("invalid name lookup was allowed")
		except:
			pass

	def testValueLookup(self):
		"""byronimo.enum: testValueLookup"""
		e = Enumeration.create('George', 'John',
							   ('Paul', 2), ('Ringo', 'drummer'))

		self.failUnless('George' == e.nameFromValue(e.George))
		self.failUnless('John' == e.nameFromValue(e.John))
		self.failUnless('Paul' == e.nameFromValue(2))
		self.failUnless('Ringo' == e.nameFromValue('drummer'))
		
		self.failUnless( e( "George" ) == e.George )
		
	def testNextAndPrevious( self ):
		"""byronimo.enum: testNextAndPrevious"""
		e2 = Enumeration.create('joe', 'bob')
		e1 = Enumeration.create( 'joe' )
		
		self.failUnless( e2.next( e2[0] ) == e2[1] )	# next
		self.failUnlessRaises( ValueError, e2.next, e2[-1], wrap_around=0 )	# next - wraparound
		self.failUnless( e2.next( e2[-1], wrap_around=1 ) == e2[0] )	# next + wraparound 
		
		self.failUnless( e2.previous( e2[-1] ) == e2[-2] )	# previous
		self.failUnlessRaises( ValueError, e2.previous, e2[0], wrap_around=0 )	# previous - wraparound
		self.failUnless( e2.previous( e2[0], wrap_around=1 ) == e2[-1] )	# previous + wraparound
		
		self.failUnless( e1.next( e1[0], wrap_around = 1 ) == e1[0] )
		self.failUnless( e1.previous( e1[0], wrap_around = 1 ) == e1[0] )
		
	def testPickleUnpickle( self ):
		"""byronimo.enum: test pickling and unpiclking results
		
		This test actually shows that the cycle in the """
		src = StringIO()
		p = pickle.Pickler(src)
		
		e1 = Enumeration.create( "hello" )
		
		# remove cycle ! Hangs otherwise 
		e1[0].enumeration = None
		
		p.dump( e1[0] )
		
		dst = StringIO( src.getvalue() )
		up = pickle.Unpickler( dst )

		elm = up.load( )
		self.failUnless( elm == e1[0] ) 
		

	def testBitFlags( self ):
		"""byronimo.enum: test bitflag capabilities"""
		e1 = Enumeration.create( "foo", "bar", "this", bitflag = 1 )
		
		orres = e1.foo | e1.bar
		assert isinstance( orres, int )
		self.failUnlessRaises( TypeError, operator.or_, e1.foo, 4 )
		
		self.failUnless( e1.foo & orres )
		self.failUnless( e1.bar & orres )
		self.failUnless( not e1.this & orres )
		
		# try to pass too many 
		self.failUnlessRaises( ValueError, Enumeration.create, *[ str( e ) for e in range( 150 ) ], **{ "bitflag" : 1 } )
		
		# mixed args 
		self.failUnlessRaises( TypeError, Enumeration.create, "hello", ( "this", "fails" ), bitflag = 1 )
		
		# xor
		assert e1.foo ^ e1.foo.getValue() == 0  
		
	def test_dict( self ):
		"""byronimo.enum: assure that sets and dicts work properly"""
		# should always work as elements or global items 
		e1 = Enumeration.create( "foo", "bar", "this" )
		e2 = Enumeration.create( "foo1", "bar2", "this3" )
		
		d = dict()
		d[ e1.foo ] = 1
		assert e1.foo in d
		
		d[ e1.bar ] = 2
		assert e1.bar in d
		
		assert len( d ) == 2