
.PHONY=beta beta-docs test-beta test-beta-docs release-docs release preview-release preview-docs clean

# CONFIGURATION
# python 2.6
MAYA_VERSION=2011
PYVERSION_ARGS=--maya-version=$(MAYA_VERSION)
REG_ARGS=--regression-tests=1
DOC_ARGS=--zip-archive --from-build-version
GIT_BETA_ARGS=--force-git-tag --use-git=1
GIT_RELEASE_ARGS=--use-git=1
GIT_ROOT_REMOTE_ARGS=--root-remotes=hub
GIT_DIST_ARGS=--dist-remotes=hubdistro $(GIT_ROOT_REMOTE_ARGS) 
GIT_DOCDIST_ARGS=--dist-remotes=hubdocdistro $(GIT_ROOT_REMOTE_ARGS)
SDIST=sdist --format=zip
POST_TESTING_ARGS=--post-testing=$(MAYA_VERSION)
BETA_OMIT_RELEASE_VERSION=--omit-release-version-for=develop

PYTHON_SETUP=/usr/bin/python setup.py

all:
	echo "Nothing to do - specify an actual target"
	exit 1

clean:
	$$(cd doc;./makedoc --clean)
	$(PYTHON_SETUP) clean --all
	
release-docs:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) $(GIT_RELEASE_ARGS) docdist $(DOC_ARGS) $(GIT_DOCDIST_ARGS)
	
beta-docs:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) $(GIT_BETA_ARGS) docdist $(DOC_ARGS) $(GIT_DOCDIST_ARGS) $(BETA_OMIT_RELEASE_VERSION)

# make beta docs, don't commit to git
test-beta-docs:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) docdist --zip-archive

# Moving-Tag Preview Commit 
beta:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) $(GIT_BETA_ARGS) clean --all $(SDIST) $(POST_TESTING_ARGS) $(GIT_DIST_ARGS) $(BETA_OMIT_RELEASE_VERSION)
	
release:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) $(GIT_RELEASE_ARGS) $(REG_ARGS) clean --all $(SDIST) $(POST_TESTING_ARGS) $(GIT_DIST_ARGS)
	
# Moving-Tag Preview Commit, no git 
test-beta:
	$(PYTHON_SETUP) $(PYVERSION_ARGS) clean --all $(SDIST) $(POST_TESTING_ARGS)
	
