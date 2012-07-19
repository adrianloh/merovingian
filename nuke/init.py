# Note: init.py gets executed in both gui and cli mode.
# To have it run only in gui, use menu.py

import nuke
import nk
import os, re
from pprint import pprint

nuke.addFormat("1280 720 0 0 1280 720 1 720p")
nuke.addFormat("2048 1024 0 0 2048 1024 1 RED_2K")
nuke.knobDefault("Root.format","RED_2K")

os.environ['RVPATH'] = r"rv"

scratches = ["/media/Warpath/NukeCacheLinux", "IGNORE", "W:/NukeCache"]
platform = [nuke.env['LINUX'], nuke.env['MACOS'], nuke.env['WIN32']].index(True)
scratch = scratches[platform]
if os.path.exists(scratch): 
	os.environ['NUKE_TEMP_DIR'] = scratch

def rename(fn):
	fn = re.sub("^.+NVAPCG\/", os.environ['NVAPCG_BASE']+"/", fn)
	return fn

nuke.addFilenameFilter(rename)

def spotlight(f):
	indexCmds = ("es", "mdfind -name", "cat")
	platform = [nuke.env['WIN32'], nuke.env['MACOS'], nuke.env['LINUX']].index(True)
	cmd = indexCmds[platform]
	return [l.strip() for l in os.popen('%s %s' % (cmd,f)).readlines()]

nuke.spotlight = spotlight

def nukepath(fp):
	fp = re.sub(r'\\',r'/',fp)
	return re.sub(r' ',r'\ ',fp)

nuke.pacify = nukepath

def inspect(obj,name=None):
	if name:
		pprint(sorted([f for f in dir(obj) if re.search(name,f)]))
	else:
		pprint(sorted(dir(obj)))

nuke.inspect = inspect

def nukethumb(readPath, cut_in=None, cut_out=None):
	""" Use nuke to create a jpg thumbnail from the input clip. """
	if not os.path.exists(readPath):
		return None
	else:
		thumbDir = nuke.pacify(os.path.join(os.path.expanduser("~"), "Desktop"))
		readPath = nuke.pacify(readPath)
		readNode = nuke.createNode('Read','file %s' % readPath)
		if cut_in is None and cut_out is None:
			cut_in = readNode['first'].value()
			cut_out = readNode['last'].value()
		posterFrame = (cut_out+cut_in)/2
		(path,filename) = os.path.split(readPath)
		outPath = thumbDir + '/' + filename + '.jpg'
		writeNode = nuke.createNode('Write','file ' + outPath)
		try:
			nuke.execute(writeNode.name(), posterFrame, posterFrame)
		except Exception as e:
			print e
		[nuke.delete(node) for node in [readNode, writeNode]]
		return outPath

nuke.thumb = nukethumb

def this():
	return nuke.selectedNode()

def these():
	return nuke.selectedNodes()

nuke.pluginAddPath('./rvnuke')
