# -*- coding: utf-8 -*-
"""B{byronimo.interfaces}
Contains interface definitions

@newfield revision: Revision
@newfield id: SVN Id
"""

__author__='$Author: byron $'
__contact__='byron@byronimo.de'
__version__=1
__license__='MIT License'
__date__="$Date: 2008-07-16 22:41:16 +0200 (Wed, 16 Jul 2008) $"
__revision__="$Revision: 22 $"
__id__="$Id: configuration.py 22 2008-07-16 20:41:16Z byron $"
__copyright__='(c) 2008 Sebastian Thiel'

from collections import deque as Deque


class iDagItem( object ):
	""" Describes interface for a DAG item.
	Its used to unify interfaces allowing to access objects in a dag like graph
	Of the underlying object has a string representation, the defatult implementation 
	will work natively.
	
	Otherwise the getParent and getChildren methods should be overwritten
	@note: a few methods of this class are abstract and need to be overwritten
	@note: this class expects the attribute '_sep' to exist containing the 
	separator at which your object should be split ( for default implementations ).
	This works as the passed in pointer will belong to derived classes that can 
	define that attribute on instance or on class level"""
	
	kOrder_DepthFirst, kOrder_BreadthFirst = range(2)
	
	#{ Configuration
	# separator as appropriate for your class if it can be treated as string
	# if string treatment is not possibly, override the respective method
	_sep = None
	#} END configuration 
	
	#{ Query Methods 
	
	def isRoot( self ):
		"""@return: True if this path is the root of the DAG """
		return self ==  self.getRoot()
		
	def getRoot( self ):
		"""@return: the root of the DAG - it has no further parents"""
		parents = self.getParentDeep( )
		if not parents:
			return self
		return parents[-1]
	
	def getBasename( self ):
		"""@return: basename of this path, '/hello/world' -> 'world'"""
		return str(self).split( self._sep )[-1]
		
	def getParent( self ):
		"""@return: parent of this path, '/hello/world' -> '/hello' or None if this path 
		is the dag's root"""
		tokens =  str(self).split( self._sep )
		if len( tokens ) <= 2:		# its already root 
			return None
			
		return self.__class__( self._sep.join( tokens[0:-1] ) )
		
	def getParentDeep( self ):
		"""@return: all parents of this path, '/hello/my/world' -> [ '/hello/my','/hello' ]"""
		return list( self.iterParents( ) )
		
		return out 
		
	def getChildren( self , predicate = lambda x: True):
		"""@return: list of intermediate children of path, [ child1 , child2 ]
		@param predicate: return True to include x in result
		@note: the child objects returned are supposed to be valid paths, not just relative paths"""
		raise NotImplementedError( )
		
	def getChildrenDeep( self , order = kOrder_BreadthFirst, predicate=lambda x: True ):
		"""@return: list of all children of path, [ child1 , child2 ]
		@param order: order enumeration 
		@param predicate: returns true if x may be returned
		@note: the child objects returned are supposed to be valid paths, not just relative paths"""
		out = []
		
		if order == self.kOrder_DepthFirst:
			def depthSearch( child ):
				if not predicate( c ):
					return 
				children = child.getChildren( predicate = predicate )
				for c in children:
					depthSearch( c )
				out.append( child )
			# END recursive search method
			
			depthSearch( self )
		# END if depth first 
		elif order == self.kOrder_BreadthFirst:
			childstack = Deque( [ self ] )		
			while childstack:
				item = childstack.pop( )
				if not predicate( item ):
					continue 
				children = item.getChildren( predicate = predicate )
				
				childstack.extendleft( children )
				out.extend( children )
			# END while childstack
		# END if breadth first 
		return out
		
	def isPartOf( self, other ):
		"""@return: True if self is a part of other, and thus can be found in other
		@note: operates on strings only"""
		return str( other ).find( str( self ) ) != -1
		
	def isRootOf( self, other ):
		"""@return: True other starts with self
		@note: operates on strings
		@note: we assume other has the same type as self, thus the same separator"""
		selfstr =  self.addSep( str( self ), self._sep )
		other = self.addSep( str( other ), self._sep )
		return other.startswith( selfstr )
		
	#} END Query Methods
	
	#{ Iterators 
	def iterParents( self , predicate = lambda x : True ):
		"""@return: generator retrieving all parents up to the root
		@param predicate: returns True for all x that you want to be returned"""
		curpath = self
		while True:
			parent = curpath.getParent( )
			if not parent:
				raise StopIteration
			
			if predicate( parent ):	
				yield parent
				
			curpath = parent
		# END while true
		
		
	#} END Iterators 

	#{ Name Generation
	@classmethod
	def addSep( cls, item, sep ):
		"""@return: item with separator added to it ( just once )
		@note: operates best on strings
		@param item: item to add separator to
		@param sep: the separator"""
		if not item.endswith( sep ):
			item += sep
		return item
		
	def getFullChildName( self, childname ):
		"""Add the given name to the string version of our instance
		@return: string with childname added like name _sep childname"""
		sname = self.addSep( str( self ), self._sep )
		
		if childname.startswith( self._sep ):
			childname = childname[1:]
			
		return sname + childname		
	
	#} END name generation


class iDuplicatable( object ):
	"""Simple interface allowing any class to be properly duplicated
	@note: to implement this interface, implement L{createInstance} and 
	L{copyFrom} in your class """
	#{ Interface 
	
	def createInstance( self, *args, **kwargs ):
		"""Create and Initialize an instance of self.__class__( ... ) based on your own data
		@return: new instance of self
		@note: using self.__class__ instead of an explicit class allows derived 
		classes that do not have anything to duplicate just to use your implementeation
		@note: you must support *args and **kwargs if one of your iDuplicate bases does"""
		raise NotImplementedError( "Implement like self.__class__( yourInitArgs )" )
		
	def copyFrom( self, other, *args, **kwargs ):
		"""Copy the data from other into self as good as possible
		Only copy the data that is unique to your specific class - the data of other 
		classes will be taken care of by them !
		@note: you must support *args and **kwargs if one of your iDuplicate bases does"""
		raise NotImplementedError( "Copy all data you know from other into self" )
		
	#} END interface
	
	def duplicate( self, *args, **kwargs ):
		"""Implements a c-style copy constructor by creating a new instance of self
		and applying the L{copyFrom} methods from base to all classes implementing the copyfrom 
		method. Thus we will call the method directly on the class
		@param *args,**kwargs : passed to copyFrom and createInstance method to give additional directions"""
		try:
			createInstFunc = getattr( self, 'createInstance' ) 
			instance = createInstFunc( *args, **kwargs )
		except TypeError,e: 		#	 could be the derived class does not support the args ( although it should
			#raise
			raise AssertionError( "The subclass method %s must support *args and or **kwargs if the superclass does, error: %s" % ( createInstFunc, e ) )
		
		
		# Sanity Check 
		if not ( instance.__class__ is self.__class__ ):
			msg = "Duplicate must have same class as self, was %s, should be %s" % ( instance.__class__, self.__class__ )
			raise AssertionError( msg )
			
		return self.copyTo( instance, *args, **kwargs )
		
	def copyTo( self, instance, *args, **kwargs ):
		"""Copy the values of ourselves onto the given instance which must be an 
		instance of our class to be compatible.
		Only the common classes will be copied to instance
		@return: altered instance
		@note: instance will be altered during theat process"""
		if not isinstance( instance, self.__class__ ):
			raise TypeError( "copyTo: Instance must be of type %s but was type %s" % ( type( self ), type( instance ) ) ) 
			
		# Get reversed mro, starting at lowest base
		mrorev = instance.__class__.mro()
		mrorev.reverse()
		
		# APPLY COPY CONSTRUCTORS !
		##############################
		for base in mrorev:
			if base is iDuplicatable:
				continue
			
			# must get the actual method directly from the base ! Getattr respects the mro ( of course )
			# and possibly looks at the base's superclass methods of the same name
			try:
				copyFromFunc = base.__dict__[ 'copyFrom' ] 
				copyFromFunc( instance, self, *args, **kwargs )
			except KeyError:
				pass 
			except TypeError,e: 		#	 could be the derived class does not support the args ( although it shold
				raise AssertionError( "The subclass method %s.%s must support *args and or **kwargs if the superclass does, error: %s" % (base, copyFromFunc,e) )
		# END for each base 
		
		# return the result !
		return instance
		
		
class iChoiceDialog( object ):
	"""Interface allowing access to a simple confirm dialog allowing the user 
	to pick between a selection of choices, one of which he has to confirm
	@note: for convenience, this interface contains a brief implementation as a 
	basis for subclasses """
	
	def __init__( self, *args, **kwargs ):
		"""Allow the user to pick a choice
		@note: all paramaters exist in a short and a long version for convenience, given 
		in the form short/long 
		@param t/title: optional title of the choice box, quickly saying what this choice is about 
		@param m/message: message to be shown, informing the user in detail what the choice is about 
		@param c/choices: single item or list of items identifying the choices if used as string
		@param dc/defaultChoice: choice in set of choices to be used as default choice, default is first choice
		@param cc/cancelChoice: choice in set of choices to be used if the dialog is cancelled using esc, 
		default is last choice"""
		self.title = kwargs.get( "t", kwargs.get( "title", "Choice Dialog" ) )
		self.message = kwargs.get( "m", kwargs.get( "message", None ) )
		assert self.message
		
		self.choices = kwargs.get( "c", kwargs.get( "choices", None ) )
		assert self.choices
		
		# internally we store a choice list 
		if not isinstance( self.choices, ( list, tuple ) ):
			self.choices = [ self.choices ]
			
		self.default_choice = kwargs.get( "dc", kwargs.get( "defaultChoice", self.choices[0] ) )
		self.cancel_choice = kwargs.get( "cc", kwargs.get( "cancelChoice", self.choices[-1] ) )
		
		
	def getChoice( self ):
		"""Make the choice 
		@return: name of the choice made by the user, the type shall equal the type given 
		as button names
		@note: this implementation always returns the default choice"""
		print self.title
		print "-"*len( self.title )
		print self.message
		print " | ".join( ( str( c ) for c in self.choices ) ) 
		print "answer: %s" % self.default_choice
		
		return self.default_choice
		
	
class iProgressIndicator( object ):
	"""Interface allowing to submit progress information
	The default implementation just prints the respective messages
	Additionally you may query whether the computation has been cancelled by the user
	@note: this interface is a simple progress indicator itself, and can do some computations
	for you if you use the get() method yourself"""
	
	#{ Initialization 
	def __init__( self, min = 0, max = 100, is_relative = True, may_abort = False, **kwargs ):
		"""@param min: the minimum progress value
		@param max: the maximum progress value
		@param is_relative: if True, the values given will be scaled to a range of 0-100, 
		if False no adjustments will be done
		@param kwargs: additional arguments being ignored"""
		self.setRange( min, max )
		self.setRelative( is_relative )
		self.setAbortable( may_abort )
		self.__progress = min
		
		
		
	def begin( self ):
		"""intiialize the progress indicator before calling L{set} """
		self.__progress = self.__min		# refresh
	
	def end( self ):
		"""indicate that you are done with the progress indicator - this must be your last
		call to the interface""" 
		pass 
		
	#} END initialization 
	
	#{ Edit
	def refresh( self, message = None ):
		"""Refresh the progress indicator so that it represents its values on screen.
		@param message: message passed along by the user"""
		p = self.get( )
		
		if not message:
			message = self.getPrefix( p )
			
		print message
		
	def set( self, value, message = None , omit_refresh=False ):
		"""Set the progress of the progress indicator to the given value
		@param value: progress value ( min<=value<=max )
		@param message: optional message you would like to give to the user
		@param omit_refresh: by default, the progress indicator refreshes on set, 
		if False, you have to call refresh manually after you set the value"""
		self.__progress = value
		
		if not omit_refresh:
			self.refresh( message = message )
	
	def setRange( self, min, max ):
		"""set the range within we expect our progress to occour"""
		self.__min = min
		self.__max = max
	
	def setRelative( self, state ):
		"""enable or disable relative progress computations"""
		self.__relative = state
		
	def setAbortable( self, state ):
		"""If state is True, the progress may be interrupted, if false it cannot 
		be interrupted"""
		self.__may_abort = state
		
	def setup( self, range=None, relative=None, abortable=None, begin=True ):
		"""Multifunctional, all in one convenience method setting all important attributes
		at once. This allows setting up the progress indicator with one call instead of many
		@note: If a kw argument is None, it will not be set
		@param range: Tuple( min, max ) - start ane end of progress indicator range
		@param relative: equivalent to L{setRelative}
		@param abortable: equivalent to L{setAbortable}
		@param begin: if True, L{begin} will be called as well"""
		if range is not None:
			self.setRange( range[0], range[1] )
			
		if relative is not None:
			self.setRelative( relative )
		
		if abortable is not None:
			self.setAbortable( abortable )
			
		if begin:
			self.begin()
		
	#} END edit  
	
	#{ Query
	def get( self ):
		"""@return: the current progress value
		@note: if set to relative mode, values will range 
		from 0.0 to 100.0"""
		if not self.isRelative():
			mn,mx = self.getRange()
			return min( max( self.__progress, mn ), mx ) 
			
		# compute the percentage
		p = self.__progress
		mn,mx = self.getRange()
		return min( max( ( p - mn ) / float( mx - mn ), 0.0 ), 1.0 ) * 100.0
		
	def getRange( self ):
		"""@return: tuple( min, max ) value"""
		return ( self.__min, self.__max )
		
	def getPrefix( self, value ):
		"""@return: a prefix indicating the progress according to the current range
		and given value """
		prefix = ""
		if self.isRelative():
			prefix = "%i%%" % value
		else:
			mn,mx = self.getRange()
			prefix = "%i/%i" % ( value, mx )
			
		return prefix 
		
	def isAbortable( self ):
		"""@return: True if the process may be cancelled"""
		return self.__may_abort
		
	def isRelative( self ):
		"""@return: true if internal progress computations are relative, False if 
		they are treated as absolute values"""
		return self.__relative
		
	def isCancelRequested( self ):
		"""@return: true if the operation should be aborted"""
		return False
	#} END query 
