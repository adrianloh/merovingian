
# -----------------------------------------------------
# This module contains callback functions that bind to the
# major events of a script's lifecycle, namely when scripts
# are loaded, saved and rendered
# ----------------------------------------------------

import nuke
import os
import re

def createWriteDirs():
	""" Automatically create directories in Write path if path doesn't exists. """
	f = nuke.filename(nuke.thisNode())
	dir = os.path.dirname(f)
	if not os.path.exists(dir):
		osdir = nuke.callbacks.filenameFilter(dir)
		os.makedirs(osdir)

def setEnvironment():
	"""Any knob added to a script's Root panel whose name is all capitalized is declared
	as an environment variable callable from within the nodes with [getenv]"""
	
	isAllCaps = lambda s: True if s.upper() == s else False

	N = [nuke.root()[i].name() for i in nuke.root().knobs() if isAllCaps(nuke.root()[i].name())]
	V = [nuke.root()[i].value() for i in nuke.root().knobs() if isAllCaps(nuke.root()[i].name())]
	h = dict(zip(N,V))
	for k in h.keys(): os.environ[k] = h[k]

nuke.addBeforeRender(createWriteDirs)
nuke.addOnScriptLoad(setEnvironment)