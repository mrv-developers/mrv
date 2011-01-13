# -*- coding: utf-8 -*-
"""Contains an implementation for the Persistence plugin for easy access within 
mrv and derived nodes.
"""
__docformat__ = "restructuredtext"

import os
from persistence import PyPickleData
import maya.OpenMaya as api

import mrv.maya.undo as undo
from mrv.util import iDuplicatable

from base import Node, DependNode, Data, createNode, delete
from set import ObjectSet

import copy

MFnDependencyNode = api.MFnDependencyNode

__all__ = ("StorageBase", "StorageNode")

#{ Procedural Access
# Functions to access most functionality of the storagebase without actually deriving from it
# They are as low-level as possible regarding their input parameters

def findStoragePlug(masterPlug, dataID):
	""":return: compound plug containing all data and connections for the given dataID
	:param masterPlug: compound plug containing all data"""
	for compoundplug in masterPlug:
		if compoundplug.child(0).asString() == dataID:
			return compoundplug
	# END for each elemnt (in search for mathching dataID)
	return None

@undoable
def _makeElementPlug(masterPlug, dataID):
	"""Find an empty logical plug index and return the newly created
	logical plug with given dataID - unconditionally"""
	elementPlug = masterPlug.mnextLogicalPlug()
	elementPlug.child(0).msetString(dataID)
	return elementPlug

@undoable
def storagePlug(masterPlug, dataID, plugType = None, autoCreate=False):
	"""
	:return: plug of the given type, either as tuple of two plugs or the plug
		specified by plugType
	:param masterPlug: masterPlug to search for data
	:param dataID: the name of the plug to be returned
	:param plugType:
		StorageBase.kMessage: return message array plug only
		StorageBase.kValue: return python pickle array plug only
		StorageBase.kStorage: return the storage plug itself containing message and the value plug
		StorageBase.kFlags return plug to integer which can be used as storage for bitflags to accompany the id
		None: return (picklePlug , messagePlug)
	:param autoCreate: if True, a plug with the given dataID will be created if it does not
		yet exist
	:raise AttributeError: if a plug with dataID does not exist and default value is None
	:raise TypeError: if  plugtype unknown """
	matchedplug = findStoragePlug(masterPlug, dataID)
	if matchedplug is None:
		if autoCreate:
			matchedplug = _makeElementPlug(masterPlug, dataID)
		else:
			raise AttributeError("Plug with id %s not found" % dataID)
	# END matched plug not found handling
	
	# return the result
	if plugType is None:
		return (matchedplug.child(2), matchedplug.child(3))
	elif plugType == StorageBase.kStorage:
		return matchedplug
	elif plugType == StorageBase.kValue:
		return matchedplug.child(2)
	elif plugType == StorageBase.kMessage:
		return matchedplug.child(3)
	elif plugType == StorageBase.kFlags:
		return matchedplug.child(1)
	else:
		raise TypeError("Invalid plugType value: %s" % plugType)
	#END handle plug type

@undoable
def makePlug(masterPlug, dataID):
	"""retrieve or create a plug that corresponds to the given dataID
	:param dataID: string identifier
	:return: the created data plug, containing subplugs dval and dmsg
		for generic data and  message connections respectively """
	existingPlug = findStoragePlug(masterPlug, dataID)
	if existingPlug is not None:
		return existingPlug

	# otherwise create it - find a free logical index - do a proper search
	return _makeElementPlug(masterPlug, dataID)

def setsByPlug(mdplug):
	""":return: all objectSets stored at the given message data plug"""
	allnodes = [p.mwrappedNode() for p in mdplug.minputs()]
	return [n for n in allnodes if isinstance(n, ObjectSet)]

def partition(mdplug):
	""":return: parition node attached to the sets of the given message data plug or None"""
	sets = setsByPlug(mdplug)

	# get the dominant partition
	partitions = list()
	for s in sets:
		partitions.extend(s.partitions())

	for p in partitions:
		if hasattr(p, StorageBase.kPartitionIdAttr):
			return p
	# END for each partition

	# nothing found, there is no partition yet
	return None
	
@undoable
def objectSet(mdplug, setIndex, autoCreate=True, setPrefix=''):
	"""Get an object set identified with setIndex at the given dataId
	
	:param mdplug: data message plug whose object set to handle
	:param setIndex: logical index at which the set will be connected to our message plug array
	:param autoCreate: if True, a set will be created if it does not yet exist
	:param setPrefix: if given, the string will be used as prefix for the name of newly created
		object sets
	:raises ValueError: if a set does not exist at setIndex and autoCreate is False
	:raises AttributeError: if the plug did not exist (and autocreate is False)
	:note: method is implicitly undoable if autoCreate is True, this also means that you cannot
		explicitly undo this operation as you do not know if undo has been queued or not
	:note: newly created sets will automatically use partitions if one of the sets does"""
	mp = mdplug
	
	# array plug having our sets
	setplug = mp.elementByLogicalIndex(setIndex)
	inputplug = setplug.minput()
	if inputplug.isNull():
		if not autoCreate:
			raise AttributeError("Set at %s[%i] did not exist" % (mp.name(), setIndex))
		su = undo.StartUndo()			# make the following operations atomic
		objset = createNode(setPrefix + "Set", "objectSet", forceNewLeaf = True)
		inputplug = objset.message
		inputplug.mconnectTo(setplug)

		# hook it up to the partition
		if partition(mdplug):
			setPartition(mdplug, True)
	# END create set as needed

	# return actual object set
	return inputplug.mwrappedNode()
	
def dataIDs(masterPlug, data_prefix=''):
	"""
	:return: list of all data ids available in the given master plug
	:param data_prefix: the string prefix of data names which must match with the prefix
		of the data id to be returned, with the matching prefix pruned. 
		By default, all data ids will match"""
	outids = list()
	for compoundplug in masterPlug:
		did = compoundplug.child(0).asString()
		if did.startswith(data_prefix):
			outids.append(did[len(data_prefix):])
		# END if is valid id
	# END for each compound plug element
	return outids
	
@undoable
def setPartition(mdplug, state):
	"""Make all sets of the given data message plug use a partition or not
	:param state: if True, a partition will be used, if False, it will be disabled
	:note: this method makes sure that all sets are hooked up to the partition
	:raise ValueError: If we did not have a single set to which to add to the partition
	:raise AttributeError: If the dataID has never had sets
	:return: if state is True, the name of the possibly created (or existing) partition"""
	sets = setsByPlug(mdplug)
	pt = partition(mdplug)

	if state:
		if pt is None:
			if not sets:
				raise ValueError("Cannot create partition as plug %s did not have any connected sets" % mdplug)
			# END check sets exist
			# create partition
			pt = createNode("storagePartition", "partition", forceNewLeaf=True)

			tattr = api.MFnTypedAttribute()
			attr = tattr.create(StorageBase.kPartitionIdAttr, "pid", api.MFnData.kString)
			pt.addAttribute(attr)
		# END create partition

		# make sure all sets are members of our partition
		pt.addSets(sets)
		return pt
	else:
		if pt:
			# delete partition
			# have to clear partition as, for some reason, or own node will be killed as well !
			pt.clear()
			delete(pt)
		# END if we have a partision
	# END state check

# implicitly undoable
def clearDataPlug(vdplug):
	"""Clear the data in the given value data plug"""
	plugindataobj = api.MFnPluginData().create(PyPickleData.kPluginDataId)
	vdplug.msetMObject(plugindataobj)

@undoable
def clearAllData(masterPlug):
	"""Empty all data storage plugs beneath the given masterPlug. Message connections are currently
	not affected"""
	for compoundplug in masterPlug:
		clearDataPlug(compoundplug.child(2))
	#END for each element plug
			
@undoable
def deleteObjectSet(mdplug, setIndex):
	"""Delete the object set at the given message data plug, at the given setIndex
	:note: use this method to delete your sets instead of manual deletion as it will automatically
		remove the managed partition in case the last set is being deleted"""
	try:
		objset = objectSet(mdplug, setIndex, autoCreate = False)
	except AttributeError:
		# did not exist, its fine
		return
	else:
		# if this is the last set, remove the partition as well
		if len(setsByPlug(mdplug)) == 1:
			setPartition(mdplug, False)
	
		delete(objset)
	# END obj set handling
			
#} END procedural access

#{ Storage Access

class StorageBase(iDuplicatable):
	"""A storage node contains a set of attributes allowing it to store
	python data and objects being stored in a pickled format upon file save.
	Additionally you can store connections.
	Nodes used with this interface must be compatible to the following attribute scheme.
	To create that scheme, use `createStorageAttribute`

	**Attribute Setup**::
	
		(shortname (description) [data type])
		dta (data)[multi compound]
			id (data id)[string]
			type (data type) [int]	# for your own use, store bitflags to specify attribute
			dval (data value) [python pickle]
			dmsg (data message)[multi message]

	**Configuration**::
	
		data_prefix: will prefix every value name when setting and getting values - this allows
			several clients to use the same storage attribute (on the same node for example)
			It acts like a namespace
		attr_prefix: prefixes the actual maya attribute to access
		maya_node: the maya node holding the actual attributes

	:note: A mrv node should derive from this class to allow easy attribute access of its
		own compatible attributes - its designed for flexiblity
	:note: attribute accepts on the generic attribute should be set by a plugin node when it
		creates its attributes
	:todo: should self._node be stored as weakref ?"""
	kValue, kMessage, kStorage, kFlags = range(4)
	kPartitionIdAttr = "bda_storagePartition"		# may not change !

	class PyPickleValue(object):
		"""Wrapper object prividing native access to the wrapped python pickle object
		and to the corresponding value plug, providing utlity methods for easier handling"""
		__slots__ = ('_plug', '_pydata', '_isReferenced', '_updateCalled')

		def __init__(self, valueplug, pythondata):
			"""value plug contains the plugin data in pythondata"""
			sa = object.__setattr__ 
			sa(self, '_plug', valueplug)
			sa(self, '_pydata', pythondata)
			# note: Dont' use the wrapped node to prevent dependency cycles and improve performance
			sa(self, '_isReferenced', MFnDependencyNode(valueplug.node()).isFromReferencedFile())
			sa(self, '_updateCalled', False)

		def __len__(self):
			return len(self._pydata)

		def __iter__(self):
			return iter(self._pydata)

		def __getattr__(self, attr):
			return getattr(self._pydata, attr)

		def __setattr__(self, attr, val):
			try:
				object.__setattr__(self, attr, val)
			except AttributeError:
				self._pydata[attr] = val

		def __getitem__(self, key):
			return self._pydata[key]

		def __setitem__(self, key, value):
			self._pydata[key] = value
			if self._isReferenced:
				self._valueChanged()		# assure we make it into the reference , but only if we change

		def __delitem__(self, key):
			del(self._pydata[key])
			
		def _valueChanged(self):
			"""Will be called automatically if the underlying value changed if
			the node of the underlying plug is referenced
			
			:note: this method will only be called once during the lifetime of this object if it changes,
				as its enough to trigger reference to write the value if it changes once.
				Getting and setting data is expensive as there is a tracking dict in the background
				being spawned with internally created copies."""
			if self._updateCalled:
				return
			self._plug.msetMObject(self._plug.asMObject())
			self._updateCalled = True

		#{ Interface
		
		def isReferenced(self):
			""":return: True if the data is from a referenced plug"""
			return self._isReferenced

		#} END interface
	# END class pypickle value

	__slots__ = ('_dprefix', '_aprefix', '_node')

	#{ Overridden Methods
	def __init__(self, data_prefix='', maya_node = None, attr_prefix=''):
		"""Allows customization of this base to modify its behaviour
		:note: see more information on the input attributes in the class description"""
		# now one can derive from us and override __setattr__
		object.__init__(self)
		self._dprefix = data_prefix
		self._aprefix = attr_prefix
		self._node = maya_node
		if not maya_node:
			if not isinstance(self, Node):
				raise TypeError("StorageNode's derived class must be an instance of type %r if maya_node is not given" % Node)
			self._node = self
		# END no maya node given handling

	#} END overridden methods

	#(iDuplicatable
	def createInstance(self, *args, **kwargs):
		"""Create a new instance with our type"""
		return self.__class__(self._dprefix, self._node, self._aprefix)

	def copyFrom(self, other, *args, **kwargs):
		"""Copy all values from other to ourselves
		
		:param kwargs:
			 * shallow:
			 	if True, default False, only a shallow copy will
				be made. If False, a deep copy will be made
		:note: only does so if the attribute and data prefixes actually match (which should be
			the case if we get here, checking for it anyway
		:note: as pickle data always copies by reference to be efficient, we have to explicitly
			create new data to assure we really copy it
		:todo: copy connections to our messages as well, make it an option at least"""
		self.setDataPrefix(other.dataPrefix())
		self.setAttributePrefix(other.attributePrefix())

		shallow = kwargs.pop("shallow", False)
		for dataid in other.dataIDs():
			othervalplug = other.storagePlug(dataid, plugType = self.kValue, autoCreate = False)
			ownvalplug = self.storagePlug(dataid, plugType = self.kValue, autoCreate = True)

			clearDataPlug(ownvalplug)

			if shallow:
				ownvalplug.msetMObject(othervalplug.asMObject())
			else:
				owndict = self.pythonDataFromPlug(ownvalplug)
				otherdict = other.pythonDataFromPlug(othervalplug)

				# copy each value
				for key in otherdict:
					val = otherdict[key]
					if isinstance(val, iDuplicatable):
						owndict[key] = val.duplicate()
					else:
						# try deep copy, use shallow copy on error
						try:
							owndict[key] = copy.deepcopy(val)
						except copy.Error:
							owndict[key] = val
					# END copy operation
				# END for each key to deep copy
			# END shallow/deep copy
		# END for each dataid

	#) END iDuplicatable

	#{ Edit
	
	def makePlug(self, dataID):
		"""see ``makePlug`` module level function"""
		return makePlug(self.masterPlug(), self._dprefix + dataID)

	@undoable
	def clearAllData(self):
		"""see ``clearAllData`` module level method
		:note: use this method if you want to make sure your node
			is empty after it has been duplicated (would usually be done in the postContructor"""
		return clearAllData(self.masterPlug())

	@undoable
	def clearData(self, dataID):
		"""Clear all data stored in the given dataID"""
		try:
			valueplug = self.storagePlug(dataID, plugType=self.kValue, autoCreate = False)
		except AttributeError:
			return
		else:
			clearDataPlug(valueplug)
		# ELSE attr exists and clearage is required

	#} END edit


	#{ Query Plugs
	
	def _elementPlug(self, dataID, dataType, autoCreate=False):
		""":return: element plug of the given type"""
		return storagePlug(self.masterPlug(), self._dprefix + dataID, dataType, autoCreate)
	
	def findStoragePlug(self, dataID):
		""":return: compound plug with given dataID or None"""
		return findStoragePlug(self.masterPlug(), self._dprefix + dataID)

	def masterPlug(self):
		""":return: master plug according to our attributePrefix"""
		return self._node.findPlug(self._aprefix + 'dta')

	def dataIDs(self):
		"""see module level function with the same name"""
		return dataIDs(self.masterPlug(), self._dprefix)

	def storagePlug(self, dataID, plugType = None, autoCreate=False):
		"""see ``storagePlug`` module level function"""
		return storagePlug(self.masterPlug(), self._dprefix+dataID, plugType, autoCreate)

	#} END query plugs


	#{ Query Data
	def pythonData(self, dataID, **kwargs):
		""":return: PyPickleVal object at the given index (it can be modified natively)
		:param dataID: id of of the data to retrieve
		:param kwargs:
			 * index: 
			 	element number of the plug to retrieve, or -1 to get a new plug.
				Plugs will always be created, the given index specifies a logical plug index
			 * Additionally all arguments supported by `storagePlug`""" 
		return self.pythonDataFromPlug(self._elementPlug(dataID, StorageBase.kValue, **kwargs))

	@classmethod
	def pythonDataFromPlug(cls, valplug):
		"""Exract the python data using the given plug directly
		
		:param valplug: data value plug containing the plugin data
		:return: PyPickleData object allowing data access"""

		# initialize data if required
		# if the data is null, we do not get a kNullObject, but an exception - fair enough ...
		try:
			plugindata = valplug.masData()
		except RuntimeError:
			# set value
			plugindataobj = api.MFnPluginData().create(PyPickleData.kPluginDataId)

			# data gets copied here - re-retrieve data
			valplug.msetMObject(plugindataobj) # use original version only - no undo support
			plugindata = Data(plugindataobj)

		# exstract the data
		#return plugindata.data()
		return StorageBase.PyPickleValue(valplug, plugindata.data())

	#} END query Data

	#{ Set Handling
	@undoable
	def objectSet(self, dataID, setIndex, autoCreate = True):
		"""see module level ``objectSet`` function"""
		return objectSet(self._elementPlug(dataID, self.kMessage, autoCreate), setIndex, autoCreate, dataID)

	@undoable
	def deleteObjectSet(self, dataID, setIndex):
		"""See the module level method called ``deleteObjectSet``"""
		try:
			return deleteObjectSet(self._elementPlug(dataID, self.kMessage, autoCreate = False), setIndex)
		except (ValueError, AttributeError):
			# did not exist, its fine
			raise
			return
		# END handle no such plug exists
		
	def setsByID(self, dataID):
		""":return: all object sets stored under the given dataID"""
		return setsByPlug(self._elementPlug(dataID, self.kMessage, autoCreate=False))


	@undoable
	def setPartition(self, dataID, state):
		"""see ``setPartition`` function on module level"""
		return setPartition(self._elementPlug(dataID, self.kMessage, autoCreate=False), state)


	def partition(self, dataID):
		""":return: partition Node attached to the sets at dataID or None if state is disabled"""
		return partition(self._elementPlug(dataID, self.kMessage, autoCreate=False))

	#} END set handling

	# Query General

	def storageNode(self):
		""":return: Node actually being used as storage"""
		return self._node

	def setStorageNode(self, node):
		"""Set ourselves to use the given storage compatible node
		
		:note: use this if the path of our instance has changed - otherwise
			trying to access functions will fail as the path of our node might be invalid"""
		self._node = node

	def setDataPrefix(self, prefix):
		"""Change the data prefix to the given value string"""
		self._dprefix = prefix

	def dataPrefix(self):
		""":return: our data prefix"""
		return self._dprefix

	def attributePrefix(self):
		""":return: our attribute prefix"""
		return self._aprefix
		
	def setAttributePrefix(self, prefix):
		"""Change the prefix with which to access to the actual storage data attributes on our node
		to the given string"""
		self._aprefix = prefix

	# END query general


class StorageNode(DependNode, StorageBase):
	"""This node can be used as pythonic and easy-to-access value container - it could
	be connected to your node, and queried for values actually being queried on your node.
	As value container, it can easily be replaced by another one, or keep different sets of information
	
	:note: the storage node can only use generic attributes and recover them properly during scene reload
		if the configuration of the generic attributes have been setup properly - they are unique only per
		node type, not per instance of the node type.
		Thus it is recommened to use the storage node attribute base on your own custom type that setsup the
		generic attributes as it requires during plugin load"""

	#{ Overrriden Methods
	def __init__(self, *args):
		"""initialize bases properly"""
		DependNode.__init__(self)
		StorageBase.__init__(self)


	#} END overridden methods

#} END storage access
