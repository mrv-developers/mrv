
.PHONY=beta beta-docs test-beta test-beta-docs release-docs release preview

# CONFIGURATION
# python 2.6
MAYA_VERSION=2010
PYVERSION_ARGS=--maya-version=$(MAYA_VERSION)
REG_ARGS=--regression-tests=$(MAYA_VERSION)
DOC_ARGS=--zip-archive --coverage=0 --sphinx-autogen=0 --epydoc=0
GIT_BETA_ARGS=--force-git-tag --use-git=1
GIT_RELEASE_ARGS=--use-git=1
GIT_DIST_ARGS=--dist-remotes=tdistro --root-remotes=bak
BUILD_PY=build_py

PYTHON_SETUP=/usr/bin/python setup.py

all:
	echo "Nothing to do - specify an actual target"
	exit 1

release-docs:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) $(GIT_RELEASE_ARGS) docdist $(DOC_ARGS) $(GIT_DIST_ARGS)
	
beta-docs:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) $(GIT_BETA_ARGS) docdist $(DOC_ARGS) $(GIT_DIST_ARGS)

# make beta docs, don't commit to git
test-beta-docs:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) docdist $(DOC_ARGS)

# Moving-Tag Preview Commit 
beta:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) $(GIT_BETA_ARGS) clean --all $(BUILD_PY) $(GIT_DIST_ARGS)
	
release:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) $(GIT_RELEASE_ARGS) $(REG_ARGS) clean --all $(BUILD_PY) $(GIT_DIST_ARGS)
	
# Moving-Tag Preview Commit, no git 
test-beta:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) $(REG_ARGS) clean --all $(BUILD_PY)
	
# Moving-Tag Preview Commit 
preview: 
	$(PYTHON_SETUP) $(GIT_BETA_ARGS) --regression-tests=1 clean --all sdist --format=zip --post-testing=2011 --dist-remotes=distro,hubdistro --root-remotes=gitorious,hub docdist --zip-archive --from-build-version --dist-remotes=docdistro,hubdocdistro --root-remotes=gitorious,hub
