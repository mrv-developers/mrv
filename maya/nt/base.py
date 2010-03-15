# -*- coding: utf-8 -*-
"""
Contains some basic  classes that are required to run the nodes system

All classes defined here can replace classes in the node type hierarachy if the name
matches. This allows to create hand-implemented types.

Implementing an undoable method
-------------------------------
   - decorate with @undoable
   - minimize probability that your operation will fail before creating an operation ( for efficiency )
   - only use operation's doIt() method to apply your changes
   - if you raise, you should not have created an undo operation
"""
from typ import nodeTypeToMfnClsMap, nodeTypeTree, MetaClassCreatorNodes
from mayarv.util import uncapitalize, capitalize, getPythonIndex, Call 
from mayarv.interface import iDuplicatable, iDagItem
from mayarv.maya.util import StandinClass
import maya.OpenMaya as api
import maya.cmds as cmds
import maya.OpenMayaMPx as mpx
import mayarv.maya.ns as nsm
import mayarv.maya.undo as undo
from new import instancemethod
from util import in_double3_out_vector, undoable_in_double3_as_vector

# direct import to safe api. lookup
from maya.OpenMaya import MFnDagNode, MDagPath, MObject, MObjectHandle

from itertools import chain
import sys

_nodesdict = None				# will be set during maya.nodes initialization



############################
#### Cache 			  	####
##########################
# to prevent always creating instances of the same class per call
_nameToApiSelList = api.MSelectionList()
_mfndep = api.MFnDependencyNode()
_mfndag = api.MFnDagNode()

# cache functions
_mfndep_setobject = _mfndep.setObject
_mfndag_setObject = _mfndag.setObject
_mfndep_typename = _mfndep.typeName
_mfndag_typename = _mfndag.typeName
_mfndep_name = _mfndep.name

api_mdagpath_node = MDagPath.node
_apitype_to_name = dict()			# [int] - > type name string



############################
#### Methods 		  	####
##########################

#{ Conversions

def nodeTypeToNodeTypeCls( nodeTypeName ):
	""" Convert the given  node type (str) to the respective python node type class
	@param nodeTypeName: the type name you which to have the actual class for  """
	try:
		nodeTypeCls = _nodesdict[capitalize( nodeTypeName )]
	except KeyError:
		raise TypeError( "NodeType %s unknown - it cannot be wrapped" % nodeTypeName )

	if isinstance( nodeTypeCls, StandinClass ):
		nodeTypeCls = nodeTypeCls.createCls( )

	return nodeTypeCls


def _makeAbsolutePath( nodename ):
	# if dag paths are passed in, we do nothing as a dag object is obviously meant.
	# Otherwise prepend a '|' to make it a dag object - the calling method will deal
	# with it accordingly
	if nodename.count( '|' )  == 0:
		return '|' + nodename
	return nodename

def isAbsolutePath( nodename ):
	return nodename.startswith( '|' )

def toDagPath( apiobj ):
	"""Find ONE valid dag path to the given dag api object"""
	dagpath = MDagPath( )
	MFnDagNode( apiobj ).getPath( dagpath )
	return dagpath


def toApiobj( nodename ):
	""" Convert the given nodename to the respective MObject
	@note: uses unique names only, and will fail if a non-unique path is given, which is
	as selection lists do not work properly with partial names !
	@note: even dag objects will end up as MObject
	@note: code repeats partly in toApiobjOrDagPath as its supposed to be as fast
	as possible - this method gets called quite a few times in benchmarks"""
	global _nameToApiSelList
	_nameToApiSelList.clear()

	nodename = _makeAbsolutePath( nodename )

	objnamelist = [ nodename ]
	if nodename.startswith( "|" ) and nodename.count( '|' ) == 1:
		objnamelist.append( nodename[1:] )

	for name in objnamelist:
		try:	# DEPEND NODE ?
			_nameToApiSelList.add( name )
		except:
			continue
		else:
			obj = MObject()
			_nameToApiSelList.getDependNode( 0, obj )

			# if we requested a dg node, but got a dag node, fail
			if name.count( '|' ) == 0 and obj.hasFn( api.MFn.kDagNode ):
				print "Skipped %s as a dependency node was expected, but got a dag node" % name
				continue

			return obj
		# END if no exception on selectionList.add
	# END for each test-object
	return None



def toApiobjOrDagPath( nodename ):
	"""Convert the given nodename to the respective MObject or MDagPath
	@note: we treat "nodename" and "|nodename" as the same objects as they occupy the
	same namespace - one time a dep node is meant, the other time a dag node.
	If querying a dag node, the dep node with the same name is not found, although it is in
	the same freaking namespace ! IMHO this is a big bug !"""
	global _nameToApiSelList
	_nameToApiSelList.clear()

	nodename = _makeAbsolutePath( nodename )

	objnamelist = [ nodename ]
	if nodename.startswith( "|" ) and nodename.count( '|' ) == 1:	# check dep node too !	 ( "|nodename", but "nodename" could exist too, occupying the "|nodename" name !
		objnamelist.append( nodename[1:] )

	for name in objnamelist:
		try:	# DEPEND NODE ?
			_nameToApiSelList.add( name )
		except:
			continue
		else:
			try:
				dag = MDagPath()
				_nameToApiSelList.getDagPath( 0 , dag )
				return dag
			except RuntimeError:
				obj = MObject()
				_nameToApiSelList.getDependNode( 0, obj )

				# if we requested a dg node, but got a dag node, fail
				if name.count( '|' ) == 0 and obj.hasFn( api.MFn.kDagNode ):
					print "Skipped %s as a dependency node was expected, but got a dag node" % name
					continue

				return obj
		# END if no exception on selectionList.add
	# END for each object name
	return None

def toSelectionList( nodeList, mergeWithExisting = False ):
	"""Convert an iterable filled with Nodes to a selection list
	@param nodeList: iterable filled with dg and dag nodes as well as plugs, dagpaths or mobjects or strings
	@param mergeWithExisting: if true, the selection list will not allow dupliacates , but adding objects
	also takes ( much )  longer, depending on the size of the list
	@return: selection list filled with objects from node list"""
	if isinstance( nodeList, api.MSelectionList ):		# sanity check
		return nodeList

	sellist = api.MSelectionList()
	for node in nodeList:
		if isinstance( node, DagNode ):
			sellist.add( node.getMDagPath(), MObject(), mergeWithExisting )
		elif isinstance( node, DependNode ):
			sellist.add( node.getMObject(), mergeWithExisting )
		else: # probably plug or something else like an mobject or dagpath
			# cannot properly apply our flag here without intensive checking
			# TODO: probably put in the instance checks !
			sellist.add( node )
	# END for each item in input array
	return sellist

def toComponentSelectionList( nodeCompList, mergeWithExisting = False ):
	"""As above, but only works on DagNodes having components - the components
	can be a nullObject though to add the whole object after all.
	@param nodeCompList: list of tuple( DagNode, Component ), Component can be
	filled component or null MObject"""
	if isinstance( nodeCompList, api.MSelectionList ):		# sanity check
		return nodeList

	sellist = api.MSelectionList()
	for node, component in nodeCompList:
		sellist.add( node.getMDagPath(), component, mergeWithExisting )

	return sellist

def toSelectionListFromNames( nodenames ):
	"""Convert the given iterable of nodenames to a selection list
	@return: MSelectionList, use L{iterSelectionList} to retrieve the objects"""
	sellist = api.MSelectionList()
	for name in nodenames:
		sellist.add( name )

	return sellist

def fromSelectionList( sellist, handlePlugs=1, **kwargs ):
	"""@return: list of Nodes and MPlugs stored in the given selection list
	@param **kwargs: passed to selectionListIterator"""
	kwargs['asNode'] = 1
	kwargs['handlePlugs'] = handlePlugs
	return list(sellist.toIter(**kwargs))

def toNodesFromNames( nodenames, **kwargs ):
	"""@return: list of wrapped nodes from the given list of node names
	@note: this function is supposed to be faster for multiple nodes compared to
	just creating a Node directly as we optimize the process due to the intermediate
	selection list getting the api objects for the given names
	@param **kwargs: passed to L{fromSelectionList}"""
	return fromSelectionList( toSelectionListFromNames( nodenames ), **kwargs )

def getByName( name , **kwargs ):
	"""@return: list of node matching name, whereas simple regex using * can be used
	to describe a pattern
	@param name: string like pcube, or pcube*, or pcube*|*Shape
	@param **kwargs: passed to L{fromSelectionList}"""
	sellist = api.MSelectionList()
	api.MGlobal.getSelectionListByName( name, sellist )

	return fromSelectionList( sellist, **kwargs )

#} END conversions



#{ Base

def objExists( objectname ):
	"""@return: True if given object exists, false otherwise
	@param objectname: we always use absolute paths to have a unique name
	@note: perfer this method over mel as the API is used directly as we have some special
	handling to assure we get the right nodes"""
	return toApiobj( objectname ) is not None


@undoable
def delete( *args, **kwargs ):
	"""Delete the given Node instances
	@note: all deletions will be stored on one undo operation
	@param presort: if True, default False, will do alot of pre-work to actually
	make the deletion work properly using  the UI, thus we :
		* sort dag nodes by dag path token length to delete top level ones first
		and individually
		* delete all dependency nodes in a bunch
	Using this flag will be slower, but yields much better results if deleting complex
	dag and dependency trees with locked attributes, conversion nodes, transforms and shapes
	@note: in general , no matter which options have been chosen , api deletion does not work well
	as the used algorithm is totally different and inferior to the mel implementaiton
	@note: will not raise in case of an error, but print a notification message"""
	presort = kwargs.get( "presort", False )

	# presort - this allows objects high up in the hierarchy to be deleted first
	# Otherwise we might have trouble deleting the ones lower in the hierarchy
	# We are basically reimplementing the MEL command 'delete' which does the
	# same thing internally I assume
	nodes = args
	if presort:
		depnodes = list()
		dagnodes = list()
		for node in args:
			if isinstance( node, DagNode ):
				dagnodes.append( node )
			else:
				depnodes.append( node )
		# END for each node in args for categorizing

		# long paths first
		dagnodes.sort( key = lambda n: len( str( n ).split( '|' ) ), reverse = True )

		# use all of these in order
		nodes = chain( dagnodes, depnodes )
	# END presorting

	# NOTE: objects really want to be deleted individually - otherwise
	# maya might just crash for some reason !!
	for node in nodes:
		if not node.isValid():
			continue

		try:
			node.delete()
		except RuntimeError:
			print "Deletion of %s failed" % node
		# END exception handling
	# END for each node to delete

def getSelection( filterType=api.MFn.kInvalid, **kwargs ):
	"""@return: list of Nodes from the current selection
	@parma filterType: The type of nodes to return exclusively. Defaults to 
	returning all nodes.
	@param **kwargs: passed to L{fromSelectionList}"""
	sellist = api.MSelectionList()
	api.MGlobal.getActiveSelectionList( sellist )
	kwargs['filterType'] = filterType
	return fromSelectionList( sellist, **kwargs )
	
def getSelectionList( ):
	"""@return: MSelectionList of the current selection list"""
	sellist = api.MSelectionList()
	api.MGlobal.getActiveSelectionList( sellist )
	return sellist
	
def iterSelection(filterType=api.MFn.kInvalid, **kwargs):
	"""@return: iterator over current scene selection
	@param filterType: MFn type specifying the node type to iterate upon. Defaults
	to all node types.
	@param **kwargs: passed to L{it.iterSelectionList}
	@note: This iterator will always return Nodes"""
	sellist = api.MSelectionList()
	api.MGlobal.getActiveSelectionList( sellist )
	
	kwargs['asNode'] = 1	# remove our overridden warg
	kwargs['filterType'] = filterType
	return sellist.toIter(**kwargs)

def select( *nodesOrSelectionList , **kwargs ):
	"""Select the given list of wrapped nodes or selection list in maya
	@param nodesOrSelectionList: single selection list or multiple wrapped nodes
	, or multiple names
	@param listAdjustment: default api.MGlobal.kReplaceList
	@note: as this is a convenience function that is not required by the api itself,
	but for interactive sessions, it will be undoable
	@note: Components are only supported if a selection list is given
	@note: This method is implicitly undoable"""
	nodenames = list()
	other = list()

	for item in nodesOrSelectionList:
		if isinstance( item, basestring ):
			nodenames.append( item )
		else:
			other.append( item )
		# END handel item type
	# END for each item

	if len( other ) == 1 and isinstance( other[0], api.MSelectionList ):
		other = other[0]

	sellist = toSelectionList( other )

	if nodenames:
		sellistnames = toSelectionListFromNames( nodenames )
		sellist.merge( sellistnames )

	adjustment = kwargs.get( "listAdjustment", api.MGlobal.kReplaceList )
	api.MGlobal.selectCommand( sellist , adjustment )


@undoable
def createNode( nodename, nodetype, autocreateNamespace=True, renameOnClash = True,
			     forceNewLeaf=True , maxShapesPerTransform = 0 ):
	"""Create a new node of nodetype with given nodename
	@param nodename: like "mynode" or "namespace:mynode" or "|parent|mynode" or
	"|ns1:parent|ns1:ns2:parent|ns3:mynode". The name may contain any amount of parents
	and/or namespaces.
	@note: For reasons of safety, dag nodes must use absolute paths like "|parent|child" -
	otherwise names might be ambiguous ! This method will assume absolute paths !
	@param nodetype: a nodetype known to maya to be created accordingly
	@param autocreateNamespace: if True, namespaces given in the nodename will be created
	if required
	@param renameOnClash: if True, nameclashes will automatcially be resolved by creating a unique
	name - this only happens if a dependency node has the same name as a dag node
	@param forceNewLeaf: if True, nodes will be created anyway if a node with the same name
	already exists - this will recreate the leaf portion of the given paths. Implies renameOnClash
	If False, you will receive an already existing node if the name and type matches.
	@param maxShapesPerTransform: only used when renameOnClash is True, defining the number of
	shapes you may have below a transform. If the number would be exeeded by the creation of
	a shape below a given transform, a new auto-renamed transform will be created automatically.
	This transform is garantueed to be new and will be used as new parent for the shape.
	@raise RuntimeError: If nodename contains namespaces or parents that may not be created
	@raise NameError: If name of desired node clashes as existing node has different type
	@note: As this method is checking a lot and tries to be smart, its relatively slow ( creates ~400 nodes / s )
	@return: the newly create Node"""
	global _mfndep_setobject, _mfndep_name

	if nodename in ( '|', '' ):
		raise RuntimeError( "Cannot create '|' or ''" )

	subpaths = nodename.split( '|' )

	parentnode = None
	createdNode = None
	lenSubpaths = len( subpaths )
	start_index = 1

	# SANITY CHECK ! Must use absolute dag paths
	if  nodename[0] != '|':
		nodename = "|" + nodename				# update with pipe
		subpaths.insert( 0, '' )
		lenSubpaths += 1

	for i in xrange( start_index, lenSubpaths ):						# first token always pipe, need absolute paths
		nodepartialname = '|'.join( subpaths[ 0 : i+1 ] )				# full path to the node so far

		# DAG ITEM EXISTS ?
		######################
		if objExists( nodepartialname ):
			# could be that the node already existed, but with an incorrect type
			if i == lenSubpaths - 1:				# in the last iteration
				if not forceNewLeaf:
					parentnode = createdNode = toApiobj( nodepartialname )
					existing_node_type = uncapitalize( api.MFnDependencyNode( createdNode ).typeName() )
					nodetypecmp = uncapitalize( nodetype )
					if nodetypecmp != existing_node_type:
						# allow more specialized types, but not less specialized ones
						if nodetypecmp not in nodeTypeTree.parent_iter( existing_node_type ):
							msg = "node %s did already exist, its type %s is incompatible with the requested type %s" % ( nodepartialname, existing_node_type, nodetype )
							raise NameError( msg )
					# END nodetypes different

					continue
				# END force new leaf handling
				else:
					# just go ahead, but create a new node
					renameOnClash = True		# allow clashes and rename
			# END leaf path handling
			else:
				# remember what we have done so far and continue
				parentnode = createdNode = toApiobj( nodepartialname )
				continue
		# END node item exists


		# it does not exist, check the namespace
		dagtoken = '|'.join( subpaths[ i : i+1 ] )

		if autocreateNamespace:
			nsm.createNamespace( ":".join( dagtoken.split( ":" )[0:-1] ) )	# will resolve to root namespace at least

		# see whether we have to create a transform or the actual nodetype
		actualtype = "transform"
		if i + 1 == lenSubpaths:
			actualtype = nodetype

		# create the node - either with or without parent
		# NOTE: usually one could just use a dagModifier for everything, but I do not
		# trust wrapped inherited methods with default attributes
		if parentnode or actualtype == "transform":

			# create dag node
			mod = undo.DagModifier( )
			newapiobj = None
			if parentnode:		# use parent
				newapiobj = mod.createNode( actualtype, parentnode )		# create with parent
			else:
				newapiobj = mod.createNode( actualtype )							# create

			mod.renameNode( newapiobj, dagtoken )									# rename
			mod.doIt()																# apply op

			parentnode = createdNode = newapiobj				# update parent
		else:
			# create dg node - really have to check for clashes afterwards
			mod = undo.DGModifier( )
			newapiobj = mod.createNode( actualtype )								# create
			mod.renameNode( newapiobj, dagtoken )									# rename
			mod.doIt()
			createdNode = newapiobj
		# END (partial) node creation

		# CLASHING CHECK ( and name update ) !
		# PROBLEM: if a dep node with name of dagtoken already exists, it will
		# rename the newly created (sub) node although it is not the same !
		_mfndep_setobject( newapiobj )
		actualname = _mfndep_name()
		if actualname != dagtoken:
			# Is it a renamed node because because a dep node of the same name existed ?
			# Could be that a child of the same name existed too
			if not renameOnClash:
				msg = "named %s did already exist - cannot create a dag node with same name due to maya limitation" % nodepartialname
				raise NameError( msg )
			else:
				# update the tokens and use the new path
				subpaths[ i ] =  actualname
				nodepartialname = '|'.join( subpaths[ 0 : i+1 ] )
		# END dag token renamed

	# END for each partial path

	if createdNode is None:
		raise RuntimeError( "Failed to create %s ( %s )" % ( nodename, nodetype ) )

	return NodeFromObj( createdNode )

#} END base


def _checkedInstanceCreationDagPathSupport( mobject_or_mdagpath, clsToBeCreated, basecls ):
	"""Same purpose and attribtues as L{_checkedInstanceCreation}, but supports
	dagPaths as input as well"""
	apiobj = mobject_or_mdagpath
	dagpath = None
	if isinstance( mobject_or_mdagpath, MDagPath ):
		dagpath = mobject_or_mdagpath
	# END if we have a dag path

	clsinstance = _checkedInstanceCreation( mobject_or_mdagpath, _lookup_type(mobject_or_mdagpath), clsToBeCreated, basecls )
	if isinstance( clsinstance, DagNode ):
		_setupDagNodeDelayedMethods( clsinstance, apiobj, dagpath )

	return clsinstance

def _checkedInstanceCreation( apiobj, typeName, clsToBeCreated, basecls ):
	"""Utiliy method creating a new class instance according to additional type information
	Its used by __new__ constructors to finalize class creation
	@param apiobj: the MObject of object to wrap
	@param typeName: the name of the node type to be created
	@param clsToBeCreated: the cls object as passed in to __new__
	@param basecls: the class of the caller containing the __new__ method
	@return: create clsinstance if the proper type ( according to nodeTypeTree"""
	# get the node type class for the api type object

	nodeTypeCls = nodeTypeToNodeTypeCls( typeName )

	# NON-MAYA NODE Type
	# if an explicit type was requested, assure we are at least compatible with
	# the given cls type - our node type is supposed to be the most specialized one
	# cls is either of the same type as ours, or is a superclass.
	# It is also okay if the user provided a class which is a subclass of the most 
	# suitable class we know, which acts like a virtal specialization
	if clsToBeCreated is not basecls and clsToBeCreated is not nodeTypeCls:
		vclass_attr = '__mayarv_virtual_subtype__'
		# If the class is a virtual subtype and indeed a subclass of our best known type,  
		# its a valid class
		if not issubclass( nodeTypeCls, clsToBeCreated ) and \
			not ( hasattr(clsToBeCreated, vclass_attr) and issubclass(clsToBeCreated, nodeTypeCls) ):
			raise TypeError( "Explicit class %r must be %r or a superclass of it. Consider setting the %s attribute to indicate you are a virtual subtype." % ( clsToBeCreated, nodeTypeCls, vclass_attr ) )
		else:
			nodeTypeCls = clsToBeCreated						# respect the wish of the client
	# END if explicit class given

	# FINISH INSTANCE
	# At this point, we only support type as we expect ourselves to be lowlevel
	clsinstance = object.__new__( nodeTypeCls )

	object.__setattr__( clsinstance, '_apiobj',  apiobj )
	return clsinstance

def _setupDagNodeDelayedMethods( dagnode, mobject, mdagpath ):
	"""Setup the given dagnode with the instance methods it needs to handle the gven 
	mobject OR mdagpath accordingly, one of them may be None"""
	instcls = type(dagnode)
	if mdagpath is None:
		# next time the MDagPath is accessed, we retrieve it from the MObject
		object.__setattr__(dagnode, 'getMDagPath', instancemethod(instcls._getMDagPath_delayed, dagnode, instcls))
		object.__setattr__(dagnode, 'getMObject', instancemethod(instcls._getMObject_cached, dagnode, instcls))
	else:
		# MObject has to be retrieved on demand
		# this is the default
		object.__setattr__( dagnode, '_apidagpath', mdagpath )
	# END handle missing MDagPath or MObject
	

def _createInstByPredicate( apiobj, cls, basecls, predicate ):
	"""Allows to wrap objects around MObjects where the actual compatabilty
	cannot be determined by some nodetypename, but by the function set itself.
	Thus it uses the nodeTypeToMfnClsMap to get mfn cls for testing
	@param cls: the class to be created
	@param basecls: the class where __new__ has actually been called
	@param predicate: returns true if the given nodetypename is valid, and its mfn
	should be taken for tests
	@return: new class instance, or None if no mfn matched the apiobject"""
	# try which node type fits
	# All attribute instances end with attribute
	# NOTE: the capital case 'A' assure we do not get this base class as option - this would
	# be bad as it is compatible with all classes
	global nodeTypeToMfnClsMap
	attrtypekeys = [ a for a in nodeTypeToMfnClsMap.keys() if predicate( a ) ]

	for attrtype in attrtypekeys:
		attrmfncls = nodeTypeToMfnClsMap[ attrtype ]
		try:
			mfn = attrmfncls( apiobj )
		except RuntimeError:
			continue
		else:
			newinst = _checkedInstanceCreation( apiobj, attrtype, cls, basecls )		# lookup in node tree
			return newinst
	# END for each known attr type
	return None


def _getUniqueName( dagpath ):
	"""Create a unique name based on the given dagpath by appending numbers"""
	copynumber = 1
	newpath = str( dagpath )
	while cmds.objExists( newpath ):
		newpath = "%s%i" % ( dagpath, copynumber )
		copynumber += 1
	# END while dagpath does exist
	return newpath

############################
#### Classes		  	####
##########################


#{ Utilities
class SetFilter( tuple ):
	"""Utility Class  returning True or False on call, latter one if
	the passed object does not match the filter"""
	def __new__( cls, apitype, exactTypeFlag, deformerSet ):
		return tuple.__new__( cls, ( apitype, exactTypeFlag, deformerSet ) )

	def __call__( self, apiobj ):
		"""@return: True if given api object matches our specifications """
		if self[ 2 ]:			# deformer sets
			setnode = NodeFromObj( apiobj )
			for elmplug in setnode.usedBy:	# find connected deformer
				iplug = elmplug.getInput()
				if iplug.isNull():
					continue

				if iplug.getNodeMObject().hasFn( api.MFn.kGeometryFilt ):
					return True
			# END for each connected plug in usedBy array

			return False		# no deformer found
		# deformer set handling

		if self[ 1 ]:			# exact type
			return apiobj.apiType() == self[ 0 ]

		# not exact type
		return apiobj.hasFn( self[ 0 ] )
	# END SetFilter


#}


#{ Base

class Node( object ):
	"""Common base for all maya nodes, providing access to the maya internal object
	representation
	Use this class to directly create a maya node of the required type"""
	__metaclass__ = MetaClassCreatorNodes
	__api_type_tuple = ( MObject, MDagPath )

	def __new__ ( cls, *args, **kwargs ):
		"""return the proper class for the given object
		@param args: arg[0] is the node to be wrapped
			- string: wrap the API object with the respective name
			- MObject
			- MObjectHandle
			- MDagPath
		If args is empty, a new node of the given type will be created within
		maya. Shapes will automatically receive a parent transform. 
		**kwargs will be passed to L{createNode} in that case.
		@note: This multi-purpose constructor is not perfectly optimized for speed, 
		consider using L{NodeFromObj} instead"""

		if not args:
			if not issubclass(cls, DependNode): # cls can be DependNode as well
				raise TypeError("Can only create types being subclasses of Node, not %r" % cls)
			# END handle invalid class
			
			typename = uncapitalize(cls.__name__)
			instname = typename
			if issubclass(cls, Shape):	# cls can be DagNode as well
				instname = "%s|%sShape" % (instname, instname)
			# END handle dag objects
			
			return createNode( instname, typename, **kwargs)
		# END handle creation mode

		objorname = args[0]
		mobject_or_mdagpath = None

		# GET AN API OBJECT
		if isinstance( objorname, cls.__api_type_tuple ):
			mobject_or_mdagpath = objorname
		elif isinstance( objorname, basestring ):
			if objorname.find( '.' ) != -1:
				raise ValueError( "%s cannot be handled - create a node, then access its attribute like Node('name').attr" % objorname )
			mobject_or_mdagpath = toApiobjOrDagPath( objorname )
		elif isinstance( objorname, MObjectHandle ):
			mobject_or_mdagpath = objorname.object()
		else:
			raise TypeError( "Objects of type %s cannot be handled" % type( objorname ) )


		skip_checks = ( len( args ) > 1 and args[1] ) or False
		if ( not skip_checks and ( mobject_or_mdagpath is None
			or ( isinstance( mobject_or_mdagpath, MDagPath ) and not mobject_or_mdagpath.isValid() )
			or ( isinstance( mobject_or_mdagpath, MObject ) and mobject_or_mdagpath.isNull() ) ) ):
			raise ValueError( "object does not exist: %s" % objorname )
		# END evil validity checking

		# CREATE INSTANCE
		return _checkedInstanceCreationDagPathSupport( mobject_or_mdagpath, cls, Node )


	#{ Overridden Methods
	def __eq__( self, other ):
		"""compare the nodes according to their api object.
		Valid inputs are other Node, MObject or MDagPath instances"""
		otherapiobj = None
		if not isinstance( other, Node ):
			otherapiobj = NodeFromObj(other).getMObject()
		else: # assume Node
			otherapiobj = other.getMObject()
		# END handle types

		return self.getMObject() == otherapiobj		# does not appear to work as expected ...

	def __ne__( self, other ):
		return not Node.__eq__( self, other )

	def __hash__( self ):
		"""@return: our name as hash - as python keeps a pool, each name will
		correspond to the exact object.
		@note: using asHashable of openMayaMPx did not work as it returns addresses
		to instances - this does not work for MObjects though"""
		return hash(str(self))

	#} END overridden methods

	#{ Interface
	def getApiObject( self ):
		"""@return: the highest qualified api object of the actual superclass,
		usually either MObject or MDagPath"""
		raise NotImplementedError( "To be implemented in subclass" )

	def getMFnClasses( self ):
		"""@return: list of all function set classes this node supports, most derived
		function set comes first"""
		return [ cls._mfncls for cls in self.__class__.mro() if hasattr( cls, '_mfncls' ) ]

	def getApiType( self ):
		"""@return: the MFn Type id of the wrapped object"""
		return self.getApiObject().apiType()

	def hasFn( self, mfntype ):
		"""@return: True if our object supports the given function set type"""
		return self.getApiObject().hasFn( mfntype )

	#} END interface

def _lookup_type( mobject_or_mdagpath ):
	"""@return: node type name of the given MObject or MDagPath"""
	global _apitype_to_name
	try:
		return _apitype_to_name[mobject_or_mdagpath.apiType()]
	except KeyError:
		global _mfndep_setobject, _mfndag_setObject, _mfndep_typename, _mfndag_typename
		# cache miss - fill in the type
		if isinstance(mobject_or_mdagpath, MDagPath):
			_mfndag_setObject(mobject_or_mdagpath)
			typename =_mfndag_typename()
		else:
			_mfndep_setobject(mobject_or_mdagpath)
			typename = _mfndep_typename()
		# END handle input type 
		_apitype_to_name[mobject_or_mdagpath.apiType()] = typename
		
		return typename
	# END handle cache miss

	

class NodeFromObj( object ):
	"""Virtual Constructor, producing nodes as the L{Node} does, but it will only
	accept MObjects or dagpaths which are expected to be valid. 
	As no additional checking is performed, it might be more unsafe to use, but 
	will be faster as it does not perform any runtime checks
	
	It duplicates code from L{_checkedInstanceCreation} and L{_checkedInstanceCreationDagPathSupport}
	to squeeze out the last tiny bit of performance as it can make quite a few more 
	assumptions and reduces method calls.
	
	@note: Do not derive from this class, derive from L{Node} instead
	@note: We will always create the node type as determined by the type hierarchy"""
	def __new__ ( cls, mobject_or_mdagpath ):
		global _apitype_to_name
		
		apiobj = mobject_or_mdagpath
		dagpath = None
		if isinstance( mobject_or_mdagpath, MDagPath ):
			dagpath = mobject_or_mdagpath
		# END if we have a dag path
	
		clsinstance = object.__new__(nodeTypeToNodeTypeCls(_lookup_type(mobject_or_mdagpath)))
		
		# apiobj is None, or MObject, or MDagPath, but will be set to the proper type 
		# later
		object.__setattr__( clsinstance, '_apiobj',  apiobj )
	
		# DagNode created from a MObject ?
		if isinstance( clsinstance, DagNode ):
			_setupDagNodeDelayedMethods( clsinstance, apiobj, dagpath )
		# END handel DagObjects
	
		# for some reason, we have to call init ourselves in that case, probably
		# since we are not afficliated with the actual instance we returned which 
		# makes a little bit of sense.
		clsinstance.__init__(mobject_or_mdagpath)
		return clsinstance
		
		
class NodeFromStr( object ):
	"""Virtual constructor similar to L{NodeFromObj}, but it will only accept strings
	to produce a wrapped node as fast as possible. Therefore, the error checking is 
	left out."""
	def __new__ ( cls, node_string ):
		return NodeFromObj(toApiobjOrDagPath(node_string))


class DependNode( Node, iDuplicatable ):		# parent just for epydoc -
	""" Implements access to dependency nodes

	Depdency Nodes are manipulated using an MObjectHandle which is safest to go with,
	but consumes more memory too !"""
	__metaclass__ = MetaClassCreatorNodes

	#{ Overridden Methods
	def __getattr__( self, attr ):
		"""Interpret attributes not in our dict as attributes on the wrapped node,
		create a plug for it and add it to our class dict, effectively caching the attribute"""
		base = super( DependNode, self )
		try:
			plug = self.findPlug( attr)
		except RuntimeError:		# perhaps a base class can handle it
			try:
				return base.__getattribute__( attr )
			except AttributeError:
				raise AttributeError( "Attribute '%s' does not exist on '%s', neither as function not as attribute" % ( attr, self.name() ) )
			# END try to get attribute by base class
		# END find plug exception handling 
		
		# cache the plug on our instance
		base.__setattr__( attr, plug )
		# and assure our class knows about it so in future the plug will be retrieved
		# right away, before having a function lookup miss
		attr = str(attr)
		setattr(type(self), attr, property(lambda self: self.findPlug(attr)))
		
		return plug

	def __str__( self ):
		"""@return: name of this object"""
		return self.getName()

	def __repr__( self ):
		"""@return: class call syntax"""
		import traceback
		return '%s("%s")' % ( self.__class__.__name__, DependNode.__str__( self ) )
	#} END overridden methods


	#( iDuplicatable

	@notundoable
	def duplicate( self, name = None, *args, **kwargs ):
		"""Duplicate our node and return a wrapped version to it
		@param name: if given, the newly created node will use the given name
		@param renameOnClash: if Trrue, default True, clashes are prevented by renaming the new node
		@param autocreateNamespace: if True, default True, namespaces will be created if mentioned in the name
		@note: the copyTo method may not have not-undoable side-effects to be a proper
		implementation
		@note: undo could be implemented for dg nodes - but for reasons of consistency, its disabled here -
		who knows how much it will crap out after a while as duplicate is not undoable ( mel command )  -
		it never really worked to undo a mel command from within python, executed using a dgmodifier - unfortunately
		it does not return any result making it hard to find the newly duplicated object !"""
		# returns name of duplicated node
		duplnode = NodeFromStr( cmds.duplicate( str( self ) )[0] )

		# RENAME
		###########
		# find a good name based on our own one - the default name is just not nice
		if not name:
			name = _getUniqueName( self )
		else:
			if '|' in name:
				raise ValueError( "Names for dependency nodes my not contain pipes: %s" % name )
		# END name handling

		rkwargs = dict()
		rkwargs[ 'renameOnClash' ] = kwargs.pop( 'renameOnClash', True )
		rkwargs[ 'autocreateNamespace' ] = kwargs.pop( 'autocreateNamespace', True )
		duplnode = duplnode.rename( name, **rkwargs )

		# call our base class to copy additional information
		self.copyTo( duplnode, *args, **kwargs )
		return duplnode

	#) END iDuplicatable

	#{ preset type filters
	fSetsObject = SetFilter( api.MFn.kSet, True, 0 )				# object fSets only
	fSets = SetFilter( api.MFn.kSet, False, 0 )			 		# all set types
	#} END type filters

	#{ Sets Handling

	def _getSetPlug( self ):
		"""@return: message plug - for non dag nodes, this will be connected """
		return self.message

	def getConnectedSets( self, setFilter = fSets ):
		"""@return: list of object set compatible Nodes having self as member
		@param setFilter: tuple( apiType, use_exact_type ) - the combination of the
		desired api type and the exact type flag allow precise control whether you which
		to get only renderable shading engines, only objectfSets ( tuple[1] = True ),
		or all objects supporting the given object type.
		Its preset to only return shading engines
		@note: the returned sets order is defined by the order connections to instObjGroups
		@note: only sets will be returned that have the whole object as member, thus you will not
		see sets having component assignments like per-compoent shader assignments or deformer sets """

		# have to parse the connections to fSets manually, finding fSets matching the required
		# type and returning them
		outlist = list()
		iogplug = self._getSetPlug()

		for dplug in iogplug.getOutputs():
			setapiobj = dplug.getNodeMObject()

			if not setFilter( setapiobj ):
				continue
			outlist.append( NodeFromObj( MObject( setapiobj ) ) )
		# END for each connected set

		return outlist

	# alias - getConnectedSets derives from the MayaAPI, but could be shorter
	getSets = getConnectedSets

	def isMemberOf( self, setnode, component = MObject() ):
		"""@return: True if self is part of setnode
		@note: method is undoable
		@see: L{ObjectSet}"""
		return setnode.isMember( self, component = component )

	def addTo( self, setnode, component = MObject(), **kwargs ):
		"""Add ourselves to the given set
		@note: method is undoable
		@see: L{ObjectSet}"""
		return setnode.addMember( self, component = component, **kwargs )

	def removeFrom( self, setnode, component = MObject() ):
		"""remove ourselves to the given set
		@note: method is undoable
		@see: L{ObjectSet}"""
		return setnode.removeMember( self, component = component )

	#} END sets handling

	#{ Edit

	@undoable
	def rename( self, newname, autocreateNamespace=True, renameOnClash = True ):
		"""Rename this node to newname
		@param newname: new name of the node
		@param autocreateNamespace: if true, namespaces given in newpath will be created automatically, otherwise
		a RuntimeException will be thrown if a required namespace does not exist
		@param renameOnClash: if true, clashing names will automatically be resolved by adjusting the name
		@return: renamed node which is the node itself
		@note: for safety reasons, this node is dagnode aware and uses a dag modifier for them !"""
		if '|' in newname:
			raise NameError( "new node names may not contain '|' as in %s" % newname )

		# is it the same name ?
		if newname == api.MFnDependencyNode( self.getMObject() ).name():
			return self

		# ALREADY EXISTS ?
		if not renameOnClash:
			exists = False

			if isinstance( self, DagNode ):	# dagnode: check existing children under parent
				parent = self.getParent()
				if parent:
					testforobject = parent.getFullChildName( newname )	# append our name to the path
					if objExists( testforobject ):
						raise RuntimeError( "Object %s did already exist - renameOnClash could have resolved this issue" % testforobject )
				# END if we have a parent
			else:
				exists = objExists( newname )	# depnode: check if object exists

			if exists:
				raise RuntimeError( "Node named %s did already exist, failed to rename %s" % ( newname, self ) )
		# END not renameOnClash handling

		# NAMESPACE
		ns = ":".join( newname.split( ":" )[:-1] )
		if not nsm.existsNamespace( ns ) and not autocreateNamespace:
			raise RuntimeError( "Cannot rename %s to %s as namespace %s does not exist" % ( self, newname, ns ) )
		ns = nsm.createNamespace( ns )		# assure its there


		# NOTE: this stupid method will also rename shapes !!!
		# you cannot prevent it, so we have to store the names and rename it lateron !!
		shapenames = shapes = None			# HACK: this is dagnodes only ( only put here for convenience, should be in DagNode )

		# rename the node
		mod = None
		if isinstance( self, DagNode ):
			mod = undo.DagModifier( )
			shapes = self.getShapes( )
			shapenames = [ s.getBasename( ) for s in shapes  ]
		else:
			mod = undo.DGModifier( )
		mod.renameNode( self.getMObject(), newname )


		# RENAME SHAPES BACK !
		#######################
		# Yeah, of course the rename method renames shapes although this has never been
		# requested ... its so stupid ...
		if shapes:
			for shape,shapeorigname in zip( shapes, shapenames ): 	 # could use izip, but this is not about memory here
				mod.renameNode( shape.getMObject(), shapeorigname )
			# END for each shape to rename
		# END handle renamed shapes
		
		mod.doIt()

		return self

	@undoable
	def delete( self ):
		"""Delete this node
		@note: if the undo queue is enabled, the object becomes invalid, but stays alive until it
		drops off the queue
		@note: if you want to delete many nodes, its more efficient to delete them
		using the global L{delete} method"""
		mod = undo.DGModifier( )
		mod.deleteNode( self.getMObject() )
		mod.doIt()

	def _addRemoveAttr( self, attr, add ):
		"""DoIt function adding or removing attributes with undo"""
		mfninst = self._mfncls( self.getMObject() )
		doitfunc = mfninst.addAttribute

		if not add:
			doitfunc = mfninst.removeAttribute

		doitfunc( attr )

	def addAttribute( self, attr ):
		"""Add the given attribute to the node as local dynamic attribute
		@param attr: MObject of attribute or Attribute instance as retrieved from
		a plug
		@return: plug to the newly added attribute
		@note: This method is explicitly not undoable as attributes are being deleted
		in memory right in the moment they are being removed, thus they cannot
		reside on the undo queue"""
		# return it if it already exists
		attrname = api.MFnAttribute( attr ).name()
		try:
			return self.findPlug( attrname, False )
		except RuntimeError:
			pass

		self._addRemoveAttr( attr, True )
		return self.findPlug( api.MFnAttribute( attr ).name() )

	def removeAttribute( self, attr ):
		"""Remove the given attribute from the node
		@param attr: see L{addAttribute}"""
		# don't do anyting if it does not exist
		attrname = api.MFnAttribute( attr ).name()
		try:
			self.findPlug( attrname, False )
		except RuntimeError:
			# it does not exist, that's what was requested
			return

		self._addRemoveAttr( attr, False )

	@undoable
	def setNamespace(self, newns, **kwargs ):
		"""@return: self after being moved to the given namespace. This will effectively
		rename the object.
		@param newns: Namespace instance to put this Node into
		@param **kwargs: to be passed to L{rename}"""
		namespace, objname = nsm.Namespace.splitNamespace(self.getBasename())
		return self.rename(newns + objname, **kwargs)

	#} END edit

	@undoable
	def setLocked( self, state ):
		"""Lock or unloack this node
		@param state: if True, the node is locked. Locked nodes cannot be deleted,
		renamed or reparented
		@note: you can query the lock state with L{isLocked}"""
		curstate = self.isLocked()
		# also works for dag nodes !
		depfn = api.MFnDependencyNode( self.getMObject() )

		op = undo.GenericOperation( )
		op.setDoitCmd( depfn.setLocked, state )
		op.setUndoitCmd( depfn.setLocked, curstate )
		op.doIt()


	#{ Connections and Attributes

	def getConnections( self ):
		"""@return: MPlugArray of connected plugs"""
		cons = api.MPlugArray( )
		mfn = DependNode._mfncls( self.getMObject() ).getConnections( cons )
		return cons

	def getDependencyInfo( self, attribute, by=True ):
		"""@return: list of attributes that given attribute affects or that the given attribute
		is affected by
		if the attribute turns dirty.
		@param attribute: attribute instance or attribute name
		@param by: if false, affected attributes will be returned, otherwise the attributes affecting this one
		@note: see also L{MPlug.getAffectedByPlugs}
		@note: USING MEL: as api command and mObject array always crashed on me ... don't know :("""
		if isinstance( attribute, basestring ):
			attribute = self.getAttribute( attribute )
		attrs = cmds.affects( attribute.getName() , str(self), by=by )

		outattrs = []
		for attr in attrs:
			outattrs.append( self.getAttribute( attr ) )
		return outattrs

	def affects( self, attribute ):
		"""@return: list of attributes affected by this one"""
		return self.getDependencyInfo( attribute, by = False )

	def affected( self , attribute):
		"""@return: list of attributes affecting this one"""
		return self.getDependencyInfo( attribute, by = True )

	#} END connections and attribtues

	#{ Status
	def isValid( self ):
		"""@return: True if the object exists in the scene
		@note: objects on the undo queue are NOT valid, but alive"""
		return MObjectHandle( self.getMObject() ).isValid()

	def isAlive( self ):
		"""@return: True if the object exists in memory
		@note: objects on the undo queue are alive, but NOT valid"""
		return MObjectHandle( self.getMObject() ).isAlive()

	#} END status

	#{ General Query
	def getMObject( self ):
		"""@return: the MObject attached to this Node"""
		return self._apiobj

	getApiObject = getMObject		# overridden from Node

	def getReferenceFile( self ):
		"""@return: name ( str ) of file this node is coming from - it could contain
		a copy number as {x}
		@note: will raise if the node is not referenced, use isReferenced to figure
		that out"""
		# apparently, we have to use MEL here :(
		return cmds.referenceQuery( str( self ) , f=1 )

	def getBasename(self):
		"""@return: name of this instance
		@note: it is mainly for compatability with dagNodes which need this method 
		in order to return the name of their leaf node"""
		return self.name()

	#}END general query

	#{ Edit Methods


	#}


class Entity( DependNode ):		# parent just for epydoc
	"""Common base for dagnodes and paritions"""
	__metaclass__ = MetaClassCreatorNodes


class DagNode( Entity, iDagItem ):	# parent just for epydoc
	""" Implements access to DAG nodes """
	__metaclass__ = MetaClassCreatorNodes
	_sep = "|"
	kNextPos = MFnDagNode.kNextPos


	#{ Overridden from Object
	def __eq__( self, other ):
		"""Compare MDagPaths directly
		Valid inputs are Node, DagNode, MObject and MDagPath instances."""
		if not isinstance( other, Node ):
			other = NodeFromObj( other )
		if isinstance( other, DagNode ):
			return self.getMDagPath() == other.getMDagPath()
		return self.getMObject() == other.getMObject()

	def __ne__( self, other ):
		return not DagNode.__eq__( self, other )

	def __getitem__( self, index ):
		"""@return: if index >= 0: Node( child )  at index
		if index < 0: Node parent at  -(index+1)( if walking up the hierarchy )
		If index is string, use DependNodes implementation
		@note: returned child can be transform or shape, use L{getShapes} or
		L{getChildTransforms} if you need a quickfilter """
		if index > -1:
			return self.getChild( index )
		else:
			for i,parent in enumerate( self.iterParents( ) ):
				if i == -(index+1):
					return parent
			# END for each parent
			raise IndexError( "Parent with index %i did not exist for %r" % ( index, self ) )

	#} END overridden from objects

	#{ Set Handling
	def _getSetPlug( self ):
		"""@return: the iogplug properly initialized for self
		Dag Nodes have the iog plug as they support instancing """
		return self.iog.getByLogicalIndex( self.getInstanceNumber() )
	#} END set handling

	#{ DAG Modification

	def _setWorldspaceTransform( self, parentnode ):
		"""Set ourselve's transformation matrix to our absolute worldspace transformation,
		possibly relative to the optional parentnode
		@param parentnode: if not None, it is assumed to be the future parent of the node,
		our transformation will be set such that we retain our worldspace position if parented below
		parentnode"""
		if not isinstance( self, Transform ):
			return

		nwm = self.wm.getByLogicalIndex( self.getInstanceNumber() ).asData().transformation().asMatrix()

		# compenstate for new parents transformation ?
		if parentnode is not None:
			# use world - inverse matrix
			parentInverseMatrix = parentnode.wim.getByLogicalIndex( parentnode.getInstanceNumber( ) ).asData().transformation().asMatrix()
			nwm = nwm * parentInverseMatrix
		# END if there is a new parent

		self.set( api.MTransformationMatrix( nwm ) )



	@undoable
	def reparent( self, parentnode, renameOnClash=True, raiseOnInstance=True, keepWorldSpace = False ):
		""" Change the parent of all nodes ( also instances ) to be located below parentnode
		@param parentnode: Node instance of transform under which this node should be parented to
		if None, node will be reparented under the root ( which only works for transforms )
		@param renameOnClash: resolve nameclashes by automatically renaming the node to make it unique
		@param instanceCheck: if True, this method will raise if you try to reparent an instanced object.
		If false, instanced objects will be merged into the newly created path under parentnode, effectively
		eliminating all other paths , keeping the newly created one
		@param keepWorldSpace: if True and node to be reparented is a transform, the world space position
		will be kept by adjusting the transformation accordingly.
		WARNNG: Currently we reset pivots when doing so
		@return : copy of self pointing to the new dag path self
		@note: will remove all instance of this object and leave this object at only one path -
		if this is not what you want, use the addChild method instead as it can properly handle this case
		@note: this method handles namespaces properly """
		if raiseOnInstance and self.getInstanceCount( False ) > 1:
			raise RuntimeError( "%r is instanced - reparent operation would destroy direct instances" % self )

		if not renameOnClash and parentnode and self != parentnode:
			# check existing children of parent and raise if same name exists
			# I think this check must be string based though as we are talking about
			# a possbly different api object with the same name - probably api will be faster
			testforobject = parentnode.getFullChildName( self.getBasename( ) )	# append our name to the path
			if objExists( testforobject ):
				raise RuntimeError( "Object %s did already exist" % testforobject )
		# END rename on clash handling

		# keep existing transformation ? Set the transformation accordingly beforehand
		if keepWorldSpace:
			# transform check done in method
			self._setWorldspaceTransform( parentnode )
		# END if keep worldspace


		# As stupid dagmodifier cannot handle instances right ( as it works on MObjects
		mod = None		# create it once we are sure the operation takes place
		if parentnode:
			if parentnode == self:
				raise RuntimeError( "Cannot parent object %s under itself" % self )

			mod = undo.DagModifier( )
			mod.reparentNode( self.getMObject(), parentnode.getMObject() )
		else:
			# sanity check
			if isinstance( self, Shape ):
				raise RuntimeError( "Shape %s cannot be parented under root '|' but needs a transform" % self )
			mod = undo.DagModifier( )
			mod.reparentNode( self.getMObject() )
		# END handle parent node

		mod.doIt()

		# UPDATE DAG PATH
		# find it in parentnodes children
		if parentnode:
			for child in parentnode.getChildren():
				if DependNode.__eq__( self, child ):
					return child
		else: # return updated version of ourselves
			return NodeFromObj( self.getMObject() )
		# END post-handle parent Node


		raise AssertionError( "Could not find self in children after reparenting" )
		
	@undoable
	def unparent(self, **kwargs):
		"""As L{reparent}, but will unparent this transform under the scene root"""
		return self.reparent(None, **kwargs)

	@undoable
	def addInstancedChild( self, childNode, position=MFnDagNode.kNextPos ):
		"""Add childnode as instanced child to this node
		@note: for more information, see L{addChild}
		@note: its a shortcut to addChild allowing to clearly indicate what is happening"""
		return self.addChild( childNode, position = position, keepExistingParent=True )

	@undoable
	def removeChild( self, childNode, allowZeroParents = False ):
		"""remove the given childNode ( being a child of this node ) from our child list, effectively
		parenting it under world !
		@param childNode: Node to unparent - if it is not one of our children, no change takes place
		@param allowZeroParents: if True, it is possible to leave a node unparented, thus no valid
		dag paths leads to it. If False, transforms will just be reparented under the world
		@return: copy of childnode pointing to the first valid dag path we find.
		@note: to prevent the child ( if transform ) to dangle in unknown space if the last instance
		is to be removed, it will instead be reparented to world.
		@note: removing shapes from their last parent will result in an error"""
		# reparent if we have a last-instance of something
		if not allowZeroParents:
			if childNode.getInstanceCount( False ) == 1:
				if isinstance( childNode, Transform ):
					return childNode.reparent( None )
				else:
					# must be shape - raise
					# TODO: could create new transform node which is pretty close to the maya default behaviour
					raise RuntimeError( "Shapenodes cannot be unparented if no parent transform would be left" )
			# END if instance count == 1
		# END if not allowZeroParents

		op = undo.GenericOperation( )
		dagfn = api.MFnDagNode( self.getMDagPath() )

		# The method will not fail if the child cannot be found in child list
		# just go ahead

		op.setDoitCmd( dagfn.removeChild, childNode.getMObject() )
		op.setUndoitCmd( self.addChild, childNode, keepExistingParent=True )	# TODO: add child to position it had
		op.doIt()

		return NodeFromObj( childNode.getMObject() )	# will attach A new dag path respectively - it will just pick the first one it gets


	@undoable
	def addChild( self, childNode, position=MFnDagNode.kNextPos, keepExistingParent=False,
				 renameOnClash=True, keepWorldSpace = False ):
		"""Add the given childNode as child to this Node. Allows instancing !
		@param childNode: Node you wish to add
		@param position: the index to which to add the new child, kNextPos will add it as last child.
		It supports python style negative indices
		@param keepExistingParent: if True, the childNode will be instanced as it will
		have its previous parent and this one, if False, the previous parent will be removed
		from the child's parent list
		@param renameOnClash: resolve nameclashes by automatically renaming the node to make it unique
		@param keepWorldSpace: see L{reparent}, only effective if the node is not instanced
		@return: childNode whose path is pointing to the new child location
		@raise ValueError: if keepWorldSpace is requested with directly instanced nodes
		@note: the keepExistingParent flag is custom implemented as it would remove all existng parentS,
		not just the one of the path behind the object ( it does not use a path, so it must remove all existing
		parents unfortunatly ! )
		@note: as maya internally handles add/remove child as instancing operation, even though
		keepExistingParent is False, it will mess up things and for a short period of time in fact
		have two n + 1 instances, right before one is unlinked, This still fills a slot or something, and
		isInstanced will be true, although the pathcount is 1.
		Long story short: if the item to be added to us is not instanced, we use reparent instead. It
		will not harm in direct instances, so its save to use.
		@note: if the instance count of the item is 1 and keepExistingParent is False, the position
		argument is being ignored"""
		# should we use reparent to get around an instance bug ?
		is_direct_instance = childNode.getInstanceCount( 0 ) > 1
		if not keepExistingParent and not is_direct_instance:	# direct only
			return childNode.reparent( self, renameOnClash=renameOnClash, raiseOnInstance=False,
									  	keepWorldSpace = keepWorldSpace )
		# END reparent if not-instanced

		# CHILD ALREADY THERE ?
		#########################
		# We do not raise if the user already has what he wants
		# check if child is already part of our children
		children = None
		# lets speed things up - getting children is expensive
		if isinstance( childNode, Transform ):
			children = self.getChildTransforms( )
		else:
			children = self.getShapes( )

		# compare MObjects
		for exChild in children:
			if DependNode.__eq__( childNode, exChild ):
				return exChild								# exchild has proper dagpath
		del( children )			# release memory

		if not renameOnClash:
			# check existing children of parent and raise if same name exists
			# I think this check must be string based though as we are talking about
			# a possbly different api object with the same name - probably api will be faster
			testforobject = self.getFullChildName( childNode.getBasename( ) )	# append our name to the path
			if objExists( testforobject ):
				raise RuntimeError( "Object %s did already exist below %r" % ( testforobject , self ) )
		# END rename on clash handling


		# ADD CHILD
		###############
		op = undo.GenericOperationStack( )

		pos = position
		if pos != self.kNextPos:
			pos = getPythonIndex( pos, self.getChildCount() )

		dagfn = api.MFnDagNode( self.getMDagPath() )
		docmd = Call( dagfn.addChild, childNode.getMObject(), pos, True )
		undocmd = Call( self.removeChild, childNode )

		op.addCmd( docmd, undocmd )


		# EXISTING PARENT HANDLING
		############################
		# if we do not keep parents, we also have to re-add it to the original parent
		# therefore wer create a dummy do with a real undo
		undocmdCall = None
		parentTransform = None
		if not keepExistingParent:
			# remove from childNode from its current parent ( could be world ! )
			parentTransform = childNode.getParent( )
			validParent = parentTransform
			if not validParent:
				# get the world, but initialize the function set with an mobject !
				# works for do only in the world case !
				worldobj = api.MFnDagNode( childNode.getMDagPath() ).parent( 0 )
				validParent = DagNode( worldobj )
			# END if no valid parent

			docmd = Call( validParent.removeChild, childNode )
			# TODO: find current position of item at parent restore it exactly
			undocmdCall = Call( validParent.addChild, childNode, keepExistingParent= True )	# call ourselves

			# special case to add items back to world
			# MGlobal. AddToMOdel does not work, and addChild on the world dag node
			# does not work either when re-adding the child ( but when removing it !! )
			# clear undocmd as it will not work and bake a mel cmd !
			op.addCmd( docmd, undocmdCall )
		# END if not keep existing parent

		op.doIt()

		# UPDATE THE DAG PATH OF CHILDNODE
		################################
		# find dag path at the used index
		dagIndex = pos
		if pos == self.kNextPos:
			dagIndex = self.getChildCount() - 1	# last entry as child got added
		newChildNode = NodeFromObj(MDagPathUtil.getChildPathAtIndex(self.getMDagPath(), dagIndex))

		# update undo cmd to use the newly created child with the respective dag path
		undocmd.args = [ newChildNode ]

		# ALTER CMD FOR WORLD SPECIAL CASE ?
		######################################
		# alter undo to readd childNode to world using MEL ? - need final name for
		# this, which is why we delay so much
		if not keepExistingParent and not parentTransform and undocmdCall is not None:			# have call and child is under world
			undocmdCall.func = cmds.parent
			undocmdCall.args = [ str( newChildNode ) ]
			undocmdCall.kwargs = { "add":1, "world":1 }

		return newChildNode

	@undoable
	def addParent( self, parentnode, **kwargs ):
		"""Adds ourselves as instance to the given parentnode at position
		@param **kwargs: see L{addChild}
		@return: self with updated dag path"""
		kwargs.pop( "keepExistingParent", None )
		return parentnode.addChild( self, keepExistingParent = True, **kwargs )

	@undoable
	def setParent( self, parentnode, **kwargs ):
		"""Change the parent of self to parentnode being placed at position
		@param **kwargs: see L{addChild}
		@return: self with updated dag path"""
		kwargs.pop( "keepExistingParent", None )	# knock off our changed attr
		return parentnode.addChild( self, keepExistingParent = False,  **kwargs )

	@undoable
	def removeParent( self, parentnode  ):
		"""Remove ourselves from given parentnode
		@return: None"""
		return parentnode.removeChild( self )


	#} END DAG modification

	#{ Edit
	@undoable
	def delete( self ):
		"""Delete this node - this special version must be
		@note: if the undo queue is enabled, the object becomes invalid, but stays alive until it
		drops off the queue
		@note: if you want to delete many nodes, its more efficient to delete them
		using the global L{delete} method"""
		mod = undo.DagModifier( )
		mod.deleteNode( self.getMObject() )
		mod.doIt()


	@notundoable
	def duplicate( self, newpath='', autocreateNamespace=True, renameOnClash=True,
				   newTransform = False, **kwargs ):
		"""Duplciate the given node to newpath
		@param newpath: result depends on its format
		   - '' - empty string, creates a unique name based on the actual node name by appending a copy number
		   to it, if newTransform is True, the newly created shape/transform will keep its name, but receives a new parent
		   - 'newname' - relative path, the node will be duplicated not changing its current parent if newTransform is False
		   - '|parent|newname' - absolute path, the node will be duplicated and reparented under the given path
		   if newTransform is True, a new transform name will be created based on your name by appending a unique copy number
		@param autocreateNamespace: if true, namespaces given in newpath will be created automatically, otherwise
		a RuntimeException will be thrown if a required namespace does not exist
		@param renameOnClash: if true, clashing names will automatically be resolved by adjusting the name
		@param newTransform: if True, a new transform will be created based on the name of the parent transform
		of this shape node, appending a unique copy number to it.
		Only has an effect for shape nodes
		@return: newly create Node
		@note: duplicate performance could be improved by checking more before doing work that does not
		really change the scene, but adds undo operations
		@note: inbetween parents are always required as needed
		@todo: add example for each version of newpath
		@note: instancing can be realized using the L{addChild} function
		@note: If meshes have tweaks applied, the duplicate will not have these tweaks and the meshes will look
		mislocated.
		Using MEL works in that case ... ( they fixed it there obviously ) , but creates invalid objects
		@todo: Undo implementation - every undoable operation must in fact be based on strings to really work, all
		this is far too much - dagNode.duplicate must be undoable by itself
		@todo: duplicate should be completely reimplemented to support all mel options and actually work with
		meshes and tweaks - the underlying api duplication would still be used of course, as well as
		connections ( to sets ) and so on ... """
		selfIsShape = isinstance( self, Shape )

		# NAME HANDLING
		# create a valid absolute name to have less special cases later on
		# if there is no name given, create a name
		if not newpath:		# "" or None
			if newTransform:
				newpath = "%s|%s" % ( _getUniqueName( self.getTransform( ) ), self.getBasename() )
			else:
				newpath = _getUniqueName( self )
			# END newTransform if there is no new path given
		elif newTransform and selfIsShape:
			newpath = "%s|%s" % ( _getUniqueName( self.getTransform( ) ), newpath.split('|')[-1] )
		elif '|' not in newpath:
			myparent = self.getParent()
			parentname = ""
			if myparent is not None:
				parentname = str( myparent )
			newpath = "%s|%s" % ( parentname, newpath )
		# END path name handling

		# Instance Parent Check
		dagtokens = newpath.split( '|' )


		# ASSERT NAME
		#############
		# need at least transform and shapename if path is absolute
		numtokens = 3				# like "|parent|shape" -> ['','parent', 'shape']
		shouldbe = '|transformname|shapename'
		if not selfIsShape:
			numtokens = 2			# like "|parent" -> ['','parent']
			shouldbe = '|transformname'

		if '|' in newpath and ( newpath == '|' or len( dagtokens ) < numtokens ):
			raise NameError( "Duplicate paths should be at least %s, was %s" % ( shouldbe, newpath ) )
		# END not instance path checking


		# TARGET EXISTS ?
		#####################
		if '|' in newpath and objExists( newpath ):
			exnode = NodeFromStr( newpath )
			if not isinstance( exnode, self.__class__ ):
				raise RuntimeError( "Existing object at path %s was of type %s, should be %s"
									% ( newpath, exnode.__class__.__name__, self.__class__.__name__ ) )
			return 	exnode# return already existing one as it has a compatible type
		# END target exists check



		# DUPLICATE IT WITHOUT UNDO
		############################
		# it will always duplicate the transform and return it
		# in case of instances, its the only way we have to get it below an own parent
		# bake all names into strings for undo and redo
		duplicate_node_parent = NodeFromObj( api.MFnDagNode( self.getMDagPath() ).duplicate( False, False ) )		# get the duplicate


		# RENAME DUPLICATE CHILDREN
		###########################
		#
		childsourceparent = self.getTransform()			# works if we are a transform as well
		self_shape_duplicated = None		# store Node of duplicates that corresponds to us ( only if self is shape )

		srcchildren = childsourceparent.getChildrenDeep( )
		destchildren = duplicate_node_parent.getChildrenDeep( )


		if len( srcchildren ) != len( destchildren ):
			# Happens if we have duplicated a shape, whose transform hat several shapes
			# To find usually, there should be only one shape which is our duplicated shape
			if len( destchildren ) != 1:
				raise AssertionError( "Expected %s to have exactly one child, but it had %i" % ( duplicate_node_parent, len( destchildren ) ) )
			self_shape_duplicated = destchildren[0].rename( self.getBasename() )
		else:
			# this is the only part where we have a one-one relationship between the original children
			# and their copies - store the id the current basename once we encounter it
			selfbasename = self.getBasename()
			for i,targetchild in enumerate( destchildren ):
				srcchildbasename = srcchildren[ i ].getBasename( )
				targetchild.rename( srcchildbasename )
				# HACK: we should only check the intermediate children, but actually conisder them deep
				# trying to reduce risk of problem by only setting duplicate_shape_index once
				if not self_shape_duplicated and selfbasename == srcchildbasename:
					self_shape_duplicated = targetchild
			# END for each child to rename
		# END CHILD RENAME


		# REPARENT
		###############
		# create requested parents of our duplicate
		parenttokens = dagtokens[:-1]
		leafobjectname = dagtokens[-1]		# the basename of the dagpath
		duplparentname = None
		if selfIsShape and newTransform:
			parenttokens = dagtokens[:-2]	# the parent of the duplicate node parent transform
			duplparentname = dagtokens[-2]
		# END shape and new transform handling


		if parenttokens:			# could be [''] too if newpath = '|newpath'
			parentnodepath = '|'.join( parenttokens )
			parentnode = childsourceparent			# in case we have a relative name

			# happens on input like "|name",
			# handle case that we are duplicating a transform and end up with a name
			# that already exists - createNode will return the existing one, and error if
			# the type does not match
			# We have to keep the duplicate as it contains duplicated values that are not
			# present in a generic newly created transform node
			parentnode = None
			if cmds.objExists( parentnodepath ):
				parentnode = NodeFromStr( parentnodepath )
			elif parentnodepath != '':
				parentnode = createNode( parentnodepath, "transform",
			     						  renameOnClash=renameOnClash,
										  autocreateNamespace=autocreateNamespace )
			# END create parent handling


			# reparent our own duplicated node - this is always a transform at this
			# point
			if parentnode is not None:
				if selfIsShape and not newTransform:
					# duplicate_shape_parent is not needed, reparent shape to our valid parent
					# name and remove the intermediate parent
					self_shape_duplicated = self_shape_duplicated.reparent( parentnode, renameOnClash = renameOnClash )
					if str( duplicate_node_parent ) not in str( parentnode ):
						duplicate_node_parent.delete()
						duplicate_node_parent = None
					# END if we may delete the duplicate node parent
				# END self is shape
				else:
					# we are a transform and will reparent under our destined parent node
					duplicate_node_parent = duplicate_node_parent.reparent( parentnode, renameOnClash=renameOnClash )
			# END if there is a new parent node
		# END PARENT HANDLING

		# if we are a shape duplication, we have to rename the duplicated parent node as well
		# since maya's duplication routine really does a lot to change my names :)
		if duplparentname and duplicate_node_parent is not None:
			duplicate_node_parent = duplicate_node_parent.rename( duplparentname, renameOnClash=renameOnClash )
		# END dupl parent rename

		# FIND RETURN NODE
		######################
		final_node = rename_target = duplicate_node_parent		# item that is to be renamed to the final name later

		# rename target must be the child matching our name
		if selfIsShape:	# want shape, have transform
			final_node = rename_target = self_shape_duplicated


		# RENAME TARGET
		# rename the target to match the leaf of the path
		# we currently do not check whether the name is already set
		# - the rename method does that for us
		final_node = rename_target.rename( leafobjectname, autocreateNamespace = autocreateNamespace,
										  	renameOnClash=renameOnClash )

		# call our base class to copy additional information
		self.copyTo( final_node, **kwargs )
		return final_node

	#} END edit


	#{ DAG Status Information
	def _checkHierarchyVal( self, plugName, cmpval ):
		"""@return: cmpval if the plug value of one of the parents equals cmpval
		as well as the current entity"""
		if getattr( self, plugName ).asInt() == cmpval:
			return cmpval

		for parent in self.iterParents():
			if getattr( parent, plugName ).asInt() == cmpval:
				return cmpval

		return 1 - cmpval

	def _getDisplayOverrideValue( self, plugName ):
		"""@return: the given effective display override value or None if display
		overrides are disabled"""
		if self.do['ove'].asInt():
			return getattr( self.do, plugName ).asInt()

		for parent in self.iterParents():
			if parent.do['ove'].asInt():
				return parent.do[ plugName ].asInt()

		return None

	def isVisible( self ):
		"""@return: True if this node is visible - its visible if itself and all parents are
		visible"""
		return self._checkHierarchyVal( 'v', False )

	def isTemplate( self ):
		"""@return: True if this node is templated - this is the case if itself or one of its
		parents are templated """
		return self._checkHierarchyVal( 'tmp', True )

	def getDisplayOverrideValue( self, plugName ):
		"""@return: the override display value actually identified by plugName affecting
		the given object ( that should be a leaf node for the result you see in the viewport.
		The display type in effect is always the last one set in the hierarchy
		returns None display overrides are disabled"""
		return self._getDisplayOverrideValue( plugName )
	#} END dag status information

	#{ Overridden from DependNode

	def isValid( self ):
		"""@return: True if the object exists in the scene
		@note: Handles DAG objects correctly that can be instanced, in which case
		the MObject may be valid , but the respective dag path is not.
		Additionally, if the object is not parented below any object, everything appears
		to be valid, but the path name is empty """
		return self.getMDagPath().isValid() and self.getMDagPath().fullPathName() != '' and DependNode.isValid( self )

	def getName( self ):
		"""@return: fully qualified ( long ) name of this dag node"""
		return self.fullPathName( )

	# override dependnode implementation with the original one
	getBasename = iDagItem.getBasename
	#{ DAG Query

	def getParentAtIndex( self, index ):
		"""@return: Node of the parent at the given index - non-instanced nodes only have one parent
		@note: if a node is instanced, it can have L{getParentCount} parents
		@todo: Update dagpath afterwards ! Use dagpaths instead !"""
		sutil = api.MScriptUtil()
		sutil.createFromInt(index)
		uint = sutil.asUint()

		return NodeFromObj( api.MFnDagNode(self.getMDagPath()).parent( uint ) )

	def getTransform( self ):
		"""@return: Node to lowest transform in the path attached to our node
		@note: for shapes this is the parent, for transforms the transform itself"""
		# this should be faster than asking maya for the path and converting
		# back to a Node
		if isinstance( self, Transform ):
			return self
		return NodeFromObj( self.getMDagPath().transform( ) )

	def getParent( self ):
		"""@return: Maya node of the parent of this instance or None if this is the root"""
		# implement raw not using a wrapped path
		copy = MDagPath( self.getMDagPath() )
		copy.pop( 1 )
		if copy.length() == 0:		# ignore world !
			return None
		return NodeFromObj( copy )

	def getChildren( self, predicate = lambda x: True, asNode=True ):
		"""@return: all child nodes below this dag node if predicate returns True for passed Node
		@param asNode: if True, you will receive the children as wrapped Nodes, otherwise you 
		get MDagPaths"""
		out = list()
		ownpath = self.getMDagPath()
		for i in range( ownpath.childCount() ):
			copy = MDagPath( ownpath )
			copy.push( MDagPath.child( ownpath, i ) )
			
			if asNode:
				copy = NodeFromObj( copy )

			if not predicate( copy ):
				continue

			out.append( copy )
		# END for each child
		return out

	def getChildrenByType( self, nodeType, predicate = lambda x: True ):
		"""@return: all childnodes below this one matching the given nodeType and the predicate
		@param nodetype: class of the nodeTyoe, like nt.Transform"""
		return [ p for p in self.getChildren() if isinstance( p, nodeType ) and predicate( p ) ]

	def getShapes( self, predicate = lambda x: True ):
		"""@return: all our Shape nodes
		@note: you could use getChildren with a predicate, but this method is more
		efficient as it uses dagpath functions to filter shapes"""
		shapeNodes = map(NodeFromObj, MDagPathUtil.getShapes(self.getMDagPath()))	# could use getChildrenByType, but this is faster
		return [ s for s in shapeNodes if predicate( s ) ]

	def getChildTransforms( self, predicate = lambda x: True ):
		"""@return: list of all transform nodes below this one """
		transformNodes = map(NodeFromObj, MDagPathUtil.getTransforms(self.getMDagPath())) # could use getChildrenByType, but this is faster
		return [ t for t in transformNodes if predicate( t ) ]

	def getInstanceNumber( self ):
		"""@return: our instance number
		@note: 0 does not indicate that this object is not instanced - use getInstanceCount instead"""
		return self.getMDagPath().instanceNumber()

	def getInstance( self, instanceNumber ):
		"""@return: Node to the instance identified by instanceNumber
		@param instanceNumber: range( 0, self.getInstanceCount()-1 )"""
		# secure it - could crash if its not an instanced node
		if self.getInstanceCount( False ) == 1:
			if instanceNumber:
				raise AssertionError( "instanceNumber for non-instanced nodes must be 0, was %i" % instanceNumber )
			return self

		allpaths = api.MDagPathArray()
		self.getAllPaths( allpaths )
		# copy the path as it will be invalidated once the array goes out of scope !
		return NodeFromObj( MDagPath( allpaths[ instanceNumber ] ) )

	def hasChild( self, node ):
		"""@return: True if node is a child of self"""
		return api.MFnDagNode( self.getMDagPath() ).hasChild( node.getMObject() )

	def getChild( self, index ):
		"""@return: child of self at index
		@note: this method fixes the MFnDagNode.child method - it returns an MObject,
		which doesnt work well with instanced nodes - a dag path is required, which is what
		we use to aquire the object"""
		copy = MDagPath( self.getMDagPath() )
		copy.push( MDagPath.child( self.getMDagPath(), index ) )
		return NodeFromObj( copy )

	child = getChild 		# assure the mfnmethod cannot be called anymore - its dangerous !
	#} END dag query

	#{ General Query

	def _getMDagPath_delayed( self ):
		"""Handles the retrieval of a dagpath from an MObject if it is not known
		at first."""
		global _mfndag_setObject, _mfndag
		self._apidagpath = MDagPath( )
		_mfndag_setObject(self._apiobj)
		_mfndag.getPath( self._apidagpath )
		cls = type(self)
		object.__setattr__(self, 'getMDagPath', instancemethod(cls._getMDagPath_cached, self, cls))
		return self._apidagpath
		
	def _getMDagPath_cached( self ):
		"""@return: MDagPath attached to this node from a cached location"""
		return self._apidagpath

	def _getMObject_cached( self ):
		"""@return: MObject associated with the path of this instance from a cached location"""
		return self._apiobj
		
	def _getMObject_delayed( self ):
		"""@return: MObject as retrieved from the MDagPath of our Node"""
		self._apiobj = self._apidagpath.node()		# expensive call
		cls = type(self)
		object.__setattr__(self, 'getMObject', instancemethod(cls._getMObject_cached, self, cls))
		return self._apiobj

	# delayed mobject retrieval is the default for DagNodes as they are created from 
	# MDagPaths most of the time
	getMObject = _getMObject_delayed
	
	def getMDagPath( self ):
		"""@return: the original DagPath attached to this Node - it's not wrapped
		for performance"""
		return self._apidagpath

	def getApiObject( self ):
		"""@return: our dag path as this is our api object - the object defining this node best"""
		return self.getMDagPath()

	#}END general query

	#{ Iterators
	def iterInstances( self, excludeSelf = False ):
		"""Get iterator over all ( direct and indirect )instances of this node
		@param excludeSelf: if True, self will not be returned, if False, it will be in
		the list of items
		@note: Iterating instances is more efficient than querying all instances individually using
		L{getInstance}
		@todo: add flag to allow iteration of indirect instances as well """
		# prevents crashes if this method is called within a dag instance added callback
		if self.getInstanceCount( True ) == 1:
			if not excludeSelf:
				yield self
			raise StopIteration

		ownNumber = -1
		if excludeSelf:
			ownNumber = self.getInstanceNumber( )

		allpaths = api.MDagPathArray()
		self.getAllPaths( allpaths )

		# paths are ordered by instance number
		for i in range( allpaths.length() ):
			# index is NOT instance number ! If transforms are instanced, children increase instance number
			dagpath = allpaths[ i ]
			if dagpath.instanceNumber() != ownNumber:
				yield NodeFromObj( MDagPath( dagpath ) )
		# END for each instance

	#}


	#{ Name Remapping
	name = getName
	#} END name remapping


#} END base ( classes )

#{ Attributes

class Attribute( MObject ):
	"""Represents an attribute in general - this is the base class
	Use this general class to create attribute wraps - it will return
	a class of the respective type """

	__metaclass__ = MetaClassCreatorNodes

	def __new__ ( cls, *args, **kwargs ):
		"""return an attribute class of the respective type for given MObject
		@param args: arg[0] is attribute's MObject to be wrapped
		@note: this area must be optimized for speed"""

		if not args:
			raise ValueError( "First argument must specify the Attribute as MObject to be wrapped" )

		attributeobj = args[0]
		if cls != Attribute:
			# the user knows which type he wants, created it directly
			newinst = object.__new__(cls, attributeobj)
			# NOTE: Although this class is implemented not to need the _apiobj anymore
			# as we ARE an MObject, we are learning from the issue in Component
			# and just keep another reference to it, to be on the safe side
			newinst._apiobj = newinst
			return newinst
		# END optimization
		
		newinst = _createInstByPredicate( attributeobj, cls, cls, lambda x: x.endswith( "Attribute" ) )

		if newinst is None:
			mfnattr = api.MFnAttribute( attributeobj )
			raise ValueError( "Attribute %s typed %s was could not be wrapped into any function set" % ( mfnattr.name(), attributeobj.apiTypeStr() ) )

		return newinst
		# END for each known attr type
		
		
	@classmethod
	def create(cls, full_name, brief_name, *args, **kwargs):
		"""@return: A new Attribute 
		@param full_name: the long name of the attribute
		@param brief_name: the brief name of the attribute
		@param *args, **kwargs: passed to the respective function set instance
		@note: specialize this method in derived types !"""
		if cls == Attribute:
			raise TypeError("Cannot create plain Attributes, choose a subclass of Attribute instead")
		# END handle invalid type
		
		attr = cls._mfncls().create(full_name, brief_name, *args, **kwargs)
		return cls(attr)
		
		
class UnitAttribute( Attribute ):
	#{ Constants
	types = ( api.MFnUnitAttribute.kAngle, api.MFnUnitAttribute.kDistance, api.MFnUnitAttribute.kTime )
	kAngle, \
	kDistance, \
	kTime, = types
	#} END constants


class TypedAttribute( Attribute ):
	#{ Constants 
	types = (  	api.MFnData.kString, 
				api.MFnData.kMatrix, 
				api.MFnData.kStringArray, 
				api.MFnData.kDoubleArray, 
				api.MFnData.kIntArray, 
				api.MFnData.kPointArray, 
				api.MFnData.kVectorArray, 
				api.MFnData.kComponentList, 
				api.MFnData.kMesh, 
				api.MFnData.kLattice, 
				api.MFnData.kNurbsCurve, 
				api.MFnData.kNurbsSurface, 
				api.MFnData.kSphere, 
				api.MFnData.kDynArrayAttrs, 
				api.MFnData.kDynSweptGeometry, 
				api.MFnData.kSubdSurface, 
				api.MFnData.kNObject )
	
	kString, \
	kMatrix, \
	kStringArray, \
	kDoubleArray, \
	kIntArray, \
	kPointArray, \
	kVectorArray, \
	kComponentList, \
	kMesh, \
	kLattice, \
	kNurbsCurve, \
	kNurbsSurface, \
	kSphere, \
	kDynArrayAttrs, \
	kDynSweptGeometry, \
	kSubdSurface, \
	kNObject = types
	#} END constants
	

class NumericAttribute( Attribute ):
	#{ Constants
	types = (	api.MFnNumericData.kBoolean,
				api.MFnNumericData.kByte, 
				api.MFnNumericData.kChar, 
				api.MFnNumericData.kShort, 
				api.MFnNumericData.k2Short,
				api.MFnNumericData.k3Short,
				api.MFnNumericData.kLong,
				api.MFnNumericData.kInt, 
				api.MFnNumericData.k2Long,
				api.MFnNumericData.k2Int,
				api.MFnNumericData.k3Long,
				api.MFnNumericData.k3Int,
				api.MFnNumericData.kFloat,
				api.MFnNumericData.k2Float, 
				api.MFnNumericData.k3Float,
				api.MFnNumericData.kDouble,
				api.MFnNumericData.k2Double,
				api.MFnNumericData.k3Double,
				api.MFnNumericData.kAddr	)
	
	kBoolean, \
	kByte, \
	kChar, \
	kShort, \
	k2Short, \
	k3Short, \
	kLong, \
	kInt, \
	k2Long, \
	k2Int, \
	k3Long, \
	k3Int, \
	kFloat, \
	k2Float, \
	k3Float, \
	kDouble, \
	k2Double, \
	k3Double, \
	kAddr = types
	#} END constants
	
	@classmethod
	def _create_using(cls, method_name, *args):
		attr = getattr(cls._mfncls(), method_name)(*args)
		return cls(attr)
	
	@classmethod
	def createColor(cls, full_name, brief_name ):
		"""@return: An attribute representing a RGB color
		@param full_name, brief_name: see L{create}"""
		return cls._create_using('createColor', full_name, brief_name)
	
	@classmethod
	def createPoint(cls, full_name, brief_name ):
		"""@return: An attribute representing a point with XYZ coordinates
		@param full_name, brief_name: see L{create}"""
		return cls._create_using('createPoint', full_name, brief_name)
		
	
class MessageAttribute( Attribute ):
	pass 
	
	
class MatrixAttribute( Attribute ):
	#{ Constants
	types = ( 	api.MFnMatrixAttribute.kFloat, api.MFnMatrixAttribute.kDouble )
	kFloat, kDouble = types
	#} END constants
	
	
class LightDataAttribute( Attribute ):
	pass 
	

class GenericAttribute( Attribute ):
	pass 
	
	
class EnumAttribute( Attribute ):
	pass 
	
	
class CompoundAttribute( Attribute ):
	pass 

#} END attributes


#{ Data 

class Data( MObject ):
	"""Represents an data in general - this is the base class
	Use this general class to create data wrap objects - it will return a class of the respective type """

	__metaclass__ = MetaClassCreatorNodes

	def __new__ ( cls, *args, **kwargs ):
		"""return an data class of the respective type for given MObject
		@param args: arg[0] is data's MObject to be wrapped
		@note: this area must be optimized for speed"""

		if not args:
			raise ValueError( "First argument must specify the MObject data to be wrapped" )

		dataobj = args[0]
		if cls != Data:
			# the user knows which type he wants, created it directly
			newinst = object.__new__(cls, dataobj)
			# NOTE: Although this class is implemented not to need the _apiobj anymore
			# as we ARE an MObject, we are learning from the issue in Component
			# and just keep another reference to it, to be on the safe side
			newinst._apiobj = newinst
			return newinst
		# END optimization

		newinst = _createInstByPredicate( dataobj, cls, cls, lambda x: x.endswith( "Data" ) )

		if newinst is None:
			raise ValueError( "Data api object typed '%s' could not be wrapped into any function set" % dataobj.apiTypeStr() )

		return newinst
		# END for each known attr type
		
		
	@classmethod
	def create(cls, *args, **kwargs):
		"""@return: A new instance of data wrapped in the desired Data type
		@note: specialize this method in derived types !"""
		if cls == Data:
			raise TypeError("Cannot create 'plain' data, choose a subclass of Data instead")
		# END handle invalid type
		
		# keep the instance alive until we have wrapped the MObject which essentiall
		# creates a copy and increments its maya ref count.
		mfninst = cls._mfncls() 
		data = mfninst.create(*args, **kwargs)
		return cls(data)
		

class VectorArrayData( Data ):
	pass


class UInt64ArrayData( Data ):
	pass


class StringData( Data ):
	pass


class StringArrayData( Data ):
	pass


class SphereData( Data ):
	pass


class PointArrayData( Data ):
	pass


class PluginData( Data ):
	"""Wraps plugin data as received by a plug. If plugin's registered their data
	types and tracking dictionaries using the L{registerPluginDataTrackingDict},
	the original self pointer can easily be retrieved using this classes interface"""


	def getData( self ):
		"""@return: python data wrapped by this plugin data object
		@note: the python data should be made such that it can be changed using
		the reference we return - otherwise it will be read-only as it is just a copy !
		@note: the data retrieved by this method cannot be used in plug.setMObject( data ) as it
		is ordinary python data, not an mobject
		@raise RuntimeError: if the data object's id is unknown to this class"""
		mfn = self._mfncls( self._apiobj )
		datatype = mfn.typeId( )
		try:
			trackingdict = sys._dataTypeIdToTrackingDictMap[ datatype.id() ]
		except KeyError:
			raise RuntimeError( "Datatype %r is not registered to python as plugin data" % datatype )
		else:
			# retrieve the data pointer
			dataptrkey = mpx.asHashable( mfn.data() )
			try:
				return trackingdict[ dataptrkey ]
			except KeyError:
				raise RuntimeError( "Could not find data associated with plugin data pointer at %r" % dataptrkey )
			# END exception handling tracking dict
		# END exception handling dict access


class NumericData( Data ):
	pass


class NObjectData( Data ):
	pass


class MatrixData( Data ):
	pass


class IntArrayData( Data ):
	pass


class GeometryData( Data ):
	"""Wraps geometry data providing additional convenience methods"""

	def getUniqueObjectId( self ):
		"""@return: an object id that is guaranteed to be unique
		@note: use it with addObjectGroup to create a new unique group"""
		# find a unique object group id
		objgrpid = 0
		for ogid in range( self.objectGroupCount() ):
			exog = self.objectGroup( ogid )
			while exog == objgrpid:
				objgrpid += 1
		# END for each existing object group
		return objgrpid


class SubdData( GeometryData ):
	pass


class NurbsSurfaceData( GeometryData ):
	pass


class NurbsCurveData( GeometryData ):
	pass


class MeshData( GeometryData ):
	pass


class LatticeData( GeometryData ):
	pass


class DynSweptGeometryData( Data ):
	pass


class DoubleArrayData( Data ):
	pass


class ComponentListData( Data ):
	"""Improves the default wrap by adding some required methods to deal with
	component lists"""

	def __getitem__( self, index ):
		"""@return: the item at the given index"""
		return self._mfncls( self )[ index ]
		
	def __len__( self ):
		"""@return: number of components stored in this data"""
		return self.length()
		
	def __contains__( self, component ):
		"""@return: True if the given component is contained in this data"""
		return self.has(component)


class ArrayAttrsData( Data ):
	pass



#} END data


#{ Components 

class Component( MObject ):
	"""Represents a shape component - its derivates can be used to handle component lists
	to be used in object sets and shading engines """
	__metaclass__ = MetaClassCreatorNodes
	_mfnType = None	# to be set in the subclass component

	def __new__ ( cls, *args, **kwargs ):
		"""return an data class of the respective type for given MObject
		@param args: arg[0] is data's MObject to be wrapped.
		@note: this area must be optimized for speed"""
		if not args:
			raise ValueError("Please provide the component data to be wrapped or the MFn:: component type to be created")
		# END handle empty args
		
		componentobj = args[0]
		if cls != Component:
			# the user knows which type he wants, created it directlys
			newinst = object.__new__(cls, componentobj)
			# NOTE: Although this class is implemented not to need the _apiobj anymore
			# as we ARE an MObject, it appears that the reference counting stays an 
			# issue, and if we keep this ref, things won't crash.
			newinst._apiobj = newinst
			return newinst
		# END optimization
		newinst = _createInstByPredicate( componentobj, cls, cls, lambda x: x.endswith( "Component" ) )

		if not newinst:
			raise ValueError( "Component api object typed '%s' could not be wrapped into any component function set" % componentobj.apiTypeStr() )

		return newinst
		# END for each known attr type
		
	@classmethod
	def create(cls, component_type):
		"""@return: A new component instance carrying data of the given component type
		@param component_type: MFn:: component type to be created. 
		@note: It is important that you call this function on the Component Class of 
		a compatible type, or a RuntimeError will occour"""
		if cls == Component:
			raise TypeError("The base compnent type cannot be instantiated")
		# END handle invalid type
		
		cdata = cls._mfncls().create(component_type)
		return cls(cdata)
	
	@classmethod
	def getMFnType( cls ):
		"""@return: mfn type of this class
		@note: the type returned is *not* the type of the shape component"""
		return cls._mfnType
		
	def addElements( self, *args ):
		"""Operates exactly as described in the MFn...IndexComponent documentation, 
		but returns self to allow combined calls and on-the-fly component generation
		@return: self"""
		self._mfncls(self).addElements(*args)
		return self

	def addElement( self, *args ):
		"""see L{addElements}
		@return: self
		@note: do not use this function as it will be really slow when handling many
		items, use addElements instead"""
		self._mfncls(self).addElement(*args)
		return self


class SingleIndexedComponent( Component ):
	"""precreated class for ease-of-use"""
	_mfnType = api.MFn.kSingleIndexedComponent
		
	def getElements(self):
		"""@return: MIntArray containing the indices this component represents"""
		u = api.MIntArray()
		api.MFnSingleIndexedComponent(self).getElements(u)
		return u


class DoubleIndexedComponent( Component ):	# derived just for epydoc
	"""Fixes some functions that would not work usually """
	_mfnType = api.MFn.kDoubleIndexedComponent
	
	def getElements(self):
		"""@return: (uIntArray, vIntArray) tuple containing arrays with the u and v
		indices this component represents"""
		u = api.MIntArray()
		v = api.MIntArray()
		api.MFnDoubleIndexedComponent(self).getElements(u, v)
		return (u,v) 
		
	
class TripleIndexedComponent( Component ):
	"""precreated class for ease-of-use"""
	_mfnType = api.MFn.kTripleIndexedComponent

	def getElements(self):
		"""@return: (uIntArray, vIntArray, wIntArray) tuple containing arrays with 
		the u, v and w indices this component represents"""
		u = api.MIntArray()
		v = api.MIntArray()
		w = api.MIntArray()
		api.MFnDoubleIndexedComponent(self).getElements(u, v, w)
		return (u,v,w)

#} END components

#{ Basic Types

class MDagPathUtil( object ):
	"""Performs operations on MDagPaths which are hard or inconvenient to do otherwise
	@note: We do NOT patch the actual api type as this would make it unusable to be passed in
	as reference/pointer type unless its being created by maya itself."""

	#{ Query

	@classmethod
	def getParentPath( cls, path ):
		"""@return: MDagPath to the parent of path or None if path is in the scene 
		root."""
		copy = MDagPath( path )
		copy.pop( 1 )
		if copy.length() == 0:		# ignore world !
			return None
		return copy

	@classmethod
	def getNumShapes( cls, path ):
		"""@return: return the number of shapes below path"""
		sutil = api.MScriptUtil()
		uintptr = sutil.asUintPtr()
		sutil.setUint( uintptr , 0 )

		path.numberOfShapesDirectlyBelow( uintptr )

		return sutil.getUint( uintptr )

	@classmethod
	def getChildPathAtIndex( cls, path, index ):
		"""@return: MDagPath pointing to this path's child at the given index"""
		copy = MDagPath(path)
		copy.push(path.child(index))
		return copy

	@classmethod
	def getChildPaths( cls, path, predicate = lambda x: True ):
		"""@return: list of child MDagPaths which have path as parent
		@param predicate: returns True for each path which should be included in the result."""
		outPaths = list()
		for i in xrange( path.childCount() ):
			childpath = cls.getChildPathAtIndex( path, i )
			if predicate( childpath ):
				outPaths.append( childpath )
		return outPaths

	#} END query

	#{ Edit Inplace
	@classmethod
	def pop( cls, path, num ):
		"""Pop the given number of items off the end of the path
		@return: path itself"""
		path.pop( num )
		return path

	@classmethod
	def extendToChild( cls, path, num ):
		"""Extend path to the given child number - can be shape or transform
		@return: path itself"""
		path.extendToShapeDirectlyBelow( num )
		return self

	@classmethod
	def getChildPathsByFn( cls, path, fn, predicate = lambda x: True ):
		"""Get all children below path supporting the given MFn.type
		@return: MDagPaths to all matched paths below this path
		@param fn: member of MFn
		@param predicate: returns True for each path which should be included in the result."""
		isMatch = lambda p: p.hasFn( fn )
		return [ p for p in cls.getChildPaths( path, predicate = isMatch ) if predicate( p ) ]

	@classmethod
	def getShapes( cls, path, predicate = lambda x: True ):
		"""@return: MDagPaths to all shapes below path
		@param predicate: returns True for each path which should be included in the result.
		@note: have to explicitly assure we do not get transforms that are compatible to the shape function
		set for some reason - this is just odd and shouldn't be, but it happens if a transform has an instanced
		shape for example, perhaps even if it is not instanced"""
		return [ shape for shape in cls.getChildPathsByFn( path, api.MFn.kShape, predicate=predicate ) if shape.apiType() != api.MFn.kTransform ]

	@classmethod
	def getTransforms( cls, path, predicate = lambda x: True ):
		"""@return: MDagPaths to all transforms below path
		@param predicate: returns True to include path in result"""
		return cls.getChildPathsByFn( path, api.MFn.kTransform, predicate=predicate )
	#} END edit in place


#} END basic types

#{ Default Types

class Reference( DependNode ):
	"""Implements additional utilities to work with references"""
	
	def getFileReference(self):
		"""@return: L{FileReference} instance initialized with the reference we 
		represent"""
		import mayarv.maya.ref as refmod
		return refmod.FileReference(refnode=self)
	

class Transform( DagNode ):		# derived just for epydoc
	"""Precreated class to allow isinstance checking against their types and
	to add undo support to MFnTransform functions, as well as for usability
	@note: bases determined by metaclass
	@note: to have undoable set* functions , get the ( improved ) transformation matrix
	make your changes to it and use the L{set} method """
	__metaclass__ = MetaClassCreatorNodes

	#{ MFnTransform Overrides

	@undoable
	def set( self, transformation ):
		"""Set the transformation of this Transform node"""
		curtransformation = self.transformation()
		setter = self._api_set
		op = undo.GenericOperation()
		op.setDoitCmd( setter, transformation )
		op.setUndoitCmd( setter, curtransformation )
		op.doIt()

	#} END mfntransform overrides


	#{ Convenience Overrides
	def getScale(self):
		"""@return: MVector containing the scale of the transform"""
		return in_double3_out_vector(self._api_getScale)
		
	def getShear(self):
		"""@return: MVector containing the shear of the transform"""
		return in_double3_out_vector(self._api_getShear)

	@undoable
	def setScale(self, vec_scale):
		"""Set the scale of the transform with undo support from a single vector"""
		return undoable_in_double3_as_vector(self._api_setScale, self.getScale(), vec_scale)
		
	@undoable
	def setShear(self, vec_shear):
		"""Set the shear value of the transform with undo support from single vector"""
		return undoable_in_double3_as_vector(self._api_setShear, self.getShear(), vec_shear)

	@undoable
	def shearBy(self, vec_value):
		"""Add the given vector to the transform's shear"""
		return undoable_in_double3_as_vector(self._api_shearBy, self.getShear(), vec_value)
	
	@undoable
	def scaleBy(self, vec_value):
		"""Add the given vector to the transform's scale"""
		return undoable_in_double3_as_vector(self._api_scaleBy, self.getScale(), vec_value)
	
	#} END convenience overrides
	

class Shape( DagNode ):	 # base for epydoc !
	"""Interface providing common methods to all geometry shapes as they can be shaded.
	They usually support per object and per component shader assignments

	@note: as shadingEngines are derived from objectSet, this class deliberatly uses
	them interchangably when it comes to set handling.
	@note: for convenience, this class implements the shader related methods
	whereever possible
	@note: bases determined by metaclass"""

	__metaclass__ = MetaClassCreatorNodes




	#{ preset type filters
	fSetsRenderable = SetFilter( api.MFn.kShadingEngine, False, 0 )	# shading engines only
	fSetsDeformer = SetFilter( api.MFn.kSet, True , 1)				# deformer sets only
	#} END type filters

	#{ Sets Interface

	def _parseSetConnections( self, allow_compoents ):
		"""Manually parses the set connections from self
		@return: tuple( MObjectArray( setapiobj ), MObjectArray( compapiobj ) ) if allow_compoents, otherwise
		just a list( setapiobj )"""
		sets = api.MObjectArray()
		iogplug = self._getSetPlug()			# from DagNode , usually iog plug

		# this will never fail - logcical index creates the plug as needed
		# and drops it if it is no longer required
		if allow_compoents:
			components = api.MObjectArray()

			# take full assignments as well - make it work as the getConnectedSets api method
			for dplug in iogplug.getOutputs():
				sets.append( dplug.getNodeMObject() )
				components.append( MObject() )
			# END full objecft assignments

			for compplug in iogplug['objectGroups']:
				for setplug in compplug.getOutputs():
					sets.append( setplug.getNodeMObject() )		# connected set

					# get the component from the data
					compdata = compplug['objectGrpCompList'].asData()
					if compdata.getLength() == 1:			# this is what we can handle
						components.append( compdata[0] ) 	# the component itself
					else:
						raise AssertionError( "more than one compoents in list" )

				# END for each set connected to component
			# END for each component group

			return ( sets, components )
		else:
			for dplug in iogplug.getOutputs():
				sets.append( dplug.getNodeMObject() )
			return sets
		# END for each object grouop connection in iog


	def getComponentAssignments( self, setFilter = fSetsRenderable, use_api = True, asComponent = True ):
		"""@return: list of tuples( ObjectSetNode, Component_or_MObject ) defininmg shader
		assignments on per component basis.
		If a shader is assigned to the whole object, the component would be a null object, otherwise
		it is an instance of a wrapped IndexedComponent class
		@note: The returned Component will be an MObject(kNullObject) only in case the component is 
		not set. Hence you should check whether it isNull() before actually using it.
		@param setFilter: see L{getConnectedSets}
		@param use_api: if True, api methods will be used if possible which is usually faster.
		If False, a custom non-api implementation will be used instead.
		This can be required if the apiImplementation is not reliable which happens in
		few cases of 'weird' component assignments
		@param asComponent: If True, the components will be wrapped into the matching MayaRV compontent type
		to provide a nicer interface. This might slightly slow down the process, but this is usually 
		neglectable.
		@note: the sets order will be the order of connections of the respective component list
		attributes at instObjGroups.objectGroups
		@note: currently only meshes and subdees support per component assignment, whereas only
		meshes can have per component shader assignments
		@note: SubDivision Components cannot be supported as the component type kSubdivCVComponent
		cannot be wrapped into any component function set - reevaluate that with new maya versions !
		@note: deformer set component assignments are only returned for instance 0 ! They apply to all
		output meshes though"""

		# SUBDEE SPECIAL CASE
		#########################
		# cannot handle components for subdees - return them empty
		if self._apiobj.apiType() == api.MFn.kSubdiv:
			print "WARNING: components are not supported for Subdivision surfaces due to m8.5 api limitation"
			sets = self.getConnectedSets( setFilter = setFilter )
			return [ ( setnode, MObject() ) for setnode in sets ]
		# END subdee handling

		sets = components = None

		# MESHES AND NURBS
		##################
		# QUERY SETS AND COMPONENTS
		# for non-meshes, we have to parse the components manually
		if not use_api or not self._apiobj.hasFn( api.MFn.kMesh ) or not self.isValidMesh():
			# check full membership
			sets,components = self._parseSetConnections( True )
		# END non-mesh handling
		else:
			# MESH - use the function set
			# take all fSets by default, we do the filtering
			sets = api.MObjectArray()
			components = api.MObjectArray()
			self.getConnectedSetsAndMembers( self.getInstanceNumber(), sets, components, False )
		# END sets/components query
                                         

		# wrap the sets and components
		outlist = list()
		for setobj,compobj in zip( sets, components ):
			if not setFilter( setobj ):
				continue

			setobj = NodeFromObj( MObject( setobj ) )								# copy obj to get memory to python
			if not compobj.isNull() and asComponent:
				compobj = Component( compobj )	# this copies the object as well
			else:
				compobj = MObject( compobj )	# make it ours
			# END handle component type
			
			outlist.append( ( setobj, compobj ) )
		# END for each set/component pair
		return outlist

	#} END set interface


#} END default types

