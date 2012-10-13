#########
Changelog
#########

*************
v1.0.2 stable
*************
 * Support for maya 2012
 * Fixed broken printing of plugs in pymel
  * If mrv.maya.nt was imported, it would patch default maya types to make them more pythonic. This would cause pymel to misinterpret plugs.
 * **API CHANGE**
    * MPlug type replaced its patched ``__len__`` method with the ``length`` method. 

*************
v1.0.1 stable
*************
 * initial release