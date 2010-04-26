#!/bin/bash
if [[ $1 == *help* || $1 == "-h" ]]; then
cat <<HELP
bpython [mayaversion]
starts a python interpreter using the optionally given maya version
where maya version is either 8.5 or 2008 or 2009 or 2010
HELP
exit 1
fi

# get maya version
mayaversiondefault=8.5
mayaversion=${1:-$mayaversiondefaul}
if [[ ! $mayaversion == 8.5 && ! $mayaversion == 20?? ]]; then
	# consider id an argument and keep it
	mayaversion=$mayaversiondefault
fi

# get rid of our parameter
if [[ $1 == $mayaversion ]]; then shift ; fi

# determine the basepath to maya
uname=`uname`
if [[ $uname == "Darwin" ]]; then
	mayaroot=/Applications/Autodesk/maya
	pylibdir=Frameworks/Python.framework/Versions/Current/lib

elif [[ $uname == "Linux" ]]; then
	mayaroot=/usr/autodesk/maya
	pylibdir=lib
	# determine bits in os
	if [ -e /lib64 ]; then osbits=-x64; fi
fi


if [[ ! $mayaroot ]]; then
	echo Could not determine maya location - cannot handle operating system
	exit 2
fi

# set MAYA_LOCATION
MAYA_LOCATION=${mayaroot}${mayaversion}${osbits}
if [ ! -d $MAYA_LOCATION ]; then
	echo Did not find maya at $MAYA_LOCATION
	exit 2
fi

# determine python version
for pyversion in 8.52.4 20082.5 20092.5 20102.6 20112.6 ; do
	if [[ $pyversion == ${mayaversion}* ]]; then
		python_version=${pyversion/$mayaversion/}
		break
	fi
done

test=${python_version:?Python version could not be determined for maya version $mayaversion}


# LD LIBARRY CONFIGURAION
if [[ $uname == "Linux" ]]; then
	# not required unless you load special libraries - if required, do this in your own wrapper
	# LD_PRELOAD="/usr/lib64/libstdc++.so.6:/usr/lib/gcc/x86_64-linux-gnu/4.2/libgcc_s.so"
	LD_LIBRARY_PATH=$MAYA_LOCATION/lib:$LD_LIBRARY_PATH
	export LD_PRELOAD LD_LIBRARY_PATH
elif [[ $uname == "Darwin" ]]; then
	# fix MAYA_LOCATION
	MAYA_LOCATION=$MAYA_LOCATION/Maya.app/Contents
	export DYLD_LIBRARY_PATH=$MAYA_LOCATION/MacOS:$DYLD_LIBRARY_PATH
	export DYLD_FRAMEWORK_PATH=$MAYA_LOCATION/Frameworks:$DYLD_FRAMEWORK_PATH
	export MAYA_NO_BUNDLE_RESOURCES=1	
	# assure we get the default osx interpreter first - otherwise we might get a version mismatch
	# export PATH=/usr/bin:$PATH
	
	# on osx, python will only use the main frameworks path and ignore 
	# its own sitelibraries. We put them onto the PYTHONPATH for that reason
	# MayaRV will take care of the initialization
	export PYTHONPATH=${PYTHONPATH:+$PYTHONPATH:}/Library/Python/$python_version/site-packages
fi


# adjust PYTHONPATH to look for maya includes
# need to make sure pylibdir gets expanded by filename subsitution which does not
# happen if we export things right away
# Only expand PYTHONPATH if it is really set - oterwise we might get a path we do not 
# need so imports can have name clashes

# set the python path to find our package

base=$(cd ${0%/*} && echo $PWD)
mayarvbase=$(cd $base/../.. && echo $PWD)
PYTHONPATH=${PYTHONPATH:+$PYTHONPATH:}$MAYA_LOCATION/$pylibdir/python$python_version/site-packages:$mayarvbase
export PYTHONPATH MAYA_LOCATION

# export the actual maya version to allow scripts to pick it up even before maya is launched
export MRV_MAYA_VERSION=$mayaversion

# execute the interpreter
# TODO: parse an optional option to specify the python version or just the maya version
IFS=''
/usr/bin/env python$python_version $@
