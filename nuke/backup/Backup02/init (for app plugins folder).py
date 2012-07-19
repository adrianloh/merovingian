# Copyright (c) 2009 The Foundry Visionmongers Ltd.  All Rights Reserved.

# This file is sourced by Nuke whenever it is run, either
# interactively or in order to run a script. The main purpose is
# to setup the plugin_path and to set variables used to generate
# filenames.

from __future__ import with_statement

import sys
import os.path
import nuke

# ----------------------  CUSTOM INITIALIZATIONS ----------------------- #
# These initializations are declared here because when rendering from 
# the command line, the init.py file in the user directory is ignored
# ---------------------------------------------------------------------- #

import os
import time
import re
from subprocess import Popen

os.environ["JOBS"] = "G:/jobs"
os.environ["DOTNUKE"] = "%s/.nuke" % os.environ["HOME"]

# -------------------------- BELOVED RV --------------------------- #

RVPATH = "C:\\bin\\rv.cmd"

def rv(nodes=None):

	global RVPATH

	n = nodes if nodes else [n for n in nuke.selectedNodes() if n.Class() == "Write" or n.Class() == "Read"]
	
	def get_file(n):
		return re.sub(r'%0\dd',"#",nuke.filename(n))

	if len(n) == 1:	# If one node is sent to RV
		cmd = """%s -fullscreen "%s" """ % ( RVPATH,get_file(n[0]) )
	elif len(n) > 1: # If multiple nodes are sent to RV, stack them to make compare possible
		paths = [get_file(nn) for nn in n]
		cmd = """%s -fullscreen -sessionType stack %s """ % ( RVPATH," ".join(paths) )
	else:
		pass
	
	Popen(cmd)

# -------------------- ENSURING SCRIPT METADATA ---------------------- #

allMetaPresent = False

while not allMetaPresent:
	try:
		nuke.root()['title'].value()
		nuke.root()['JOB'].value()
		nuke.root()['ID'].value()
		nuke.root()['SHOTROOT'].value()
		nuke.root()['versionMajor'].value()
		nuke.root()['versionMinor'].value()
		nuke.root()['status'].value()
		allMetaPresent = True
	except NameError:
		nuke.root().addKnob(nuke.String_Knob("title","Title"))
		nuke.root().addKnob(nuke.String_Knob("JOB","JOB"))
		nuke.root().addKnob(nuke.String_Knob("ID","SHOT"))
		nuke.root().addKnob(nuke.String_Knob("SHOTROOT","SHOTROOT"))
		nuke.root().addKnob(nuke.Int_Knob("versionMajor","versionMajor"))
		nuke.root().addKnob(nuke.Int_Knob("versionMinor","versionMinor"))
		nuke.root().addKnob(nuke.Enumeration_Knob("status","status",["Setup","WIP","Review","Qrender","Rendering","Attention","Locked","Published","Milestone"]))

def printJob():
	print "---- CURRENT SCRIPT ENVIRONMENT ----"
	print "JOBS %s" % os.environ["JOBS"]
	print "JOB %s" % os.environ["JOB"]
	print "SHOTROOT %s" % os.environ["SHOTROOT"]
	print "-"*80

def checkRootMetadata():
	if nuke.root()['JOB'].value() == "":
		job = nuke.getInput("Enter Job name:")
		nuke.root()['JOB'].setValue(job)

	if nuke.root()['SHOTROOT'].value() == "":
		shot = nuke.getInput("Enter Shot name:")
		nuke.root()['SHOTROOT'].setValue(shot)

	job = nuke.root()['JOB'].value()
	shot = nuke.root()['SHOTROOT'].value()
	os.environ['JOB'] = "%s/%s" % (os.environ['JOBS'],job)
	os.environ['SHOTROOT'] = "%s/%s" % (os.environ['JOB'],shot)
	printJob()

def loadRootMetadata():
	try:
		job = nuke.root()['JOB'].value()
		shot = nuke.root()['SHOTROOT'].value()
		os.environ['JOB'] = "%s/%s" % (os.environ['JOBS'],job)
		os.environ['SHOTROOT'] = "%s/%s" % (os.environ['JOB'],shot)
	except NameError:
		nuke.root().addKnob(nuke.String_Knob("JOB","JOB"))
		job = nuke.getInput("Enter Job name:")
		nuke.root()['JOB'].setValue(job)
		nuke.root().addKnob(nuke.String_Knob("SHOT","SHOT"))
		shot = nuke.getInput("Enter Shot name:")
		nuke.root()['SHOTROOT'].setValue(shot)
		os.environ['JOB'] = "%s/%s" % (os.environ['JOBS'],job)
		os.environ['SHOTROOT'] = "%s/%s" % (os.environ['JOB'],shot)

nuke.addOnScriptLoad(loadRootMetadata)
nuke.addOnScriptSave(checkRootMetadata)

# ------------------------------- MAIN RENDER OVERRIDE ----------------------------- #

ACTIVE_LAST_FRAME = None

nukeOriginalExecuteMultiple = nuke.executeMultiple

def customExecuteMultiple(_nodes,ranges=None,views=['main'],default_order=False):
	"""
	Render write nodes sequentially (nuke's default renders concurrently 
	across nodes) e.g. here:
				Write1 [1-25] --> Write2 [1-50] --> Write3 [1-75]
	Nuke's way:
				Write1 [1] Write2 [1] Write3 [1] --> Write1 [2] Write2 [2] Write3 [2]
	This means that Write nodes can call their own respective addBeforeRender
	scripts that alter the DAG (e.g. setSwitches) and additionally render 
	specific frame ranges on a node-to-node basis (via custom 'range' knob).
	"""
	global ACTIVE_LAST_FRAME # This hack enables #renderStatus2Twitter() to retrieve the lastFrame for each Write node

	### WTF: In Nuke >= 5.2v3 "Render All"" sends to nukescripts.execute_panel a nuke.root() argument for _nodes
	### instead of a list of Write nodes!

	if type(_nodes) is list:	
		# "Render Selected" passes the usual expected list of nodes
		nodes = _nodes
	elif nuke.selectedNodes("Write").__len__()==1:
		nodes = nuke.selectedNodes("Write")
	else:
		# Lazy checking, if "Render All" is invoked while nothing is selected -- assume we want all the Write nodes
		reply = nuke.ask("Render all Write nodes in comp?")
		if reply:
			nodes = nuke.allNodes("Write")
		else:
			return

	# Double check that we actually have Write nodes

	nodes = [n for n in nodes if n.Class() == "Write"]
	
	# Exclude disabled Write nodes
	
	disabled = [n for n in nodes if n['disable'].value()]
	if disabled:
		print "RENDER ERROR: Write nodes disabled: %s" % " ".join([d.name() for d in disabled])
		nodes = [n for n in nodes if n not in disabled]

	# Exclude Write nodes that are currently in Read mode

	reading = [n for n in nodes if n['reading'].value()]
	if reading:
		print "RENDER ERROR: Write nodes in Read mode: %s" % " ".join([r.name() for r in reading])
		nodes = [n for n in nodes if n not in reading]

	if not nodes:
		msg = "RENDER ERROR: No Write nodes to render"
		if nuke.env['gui']: 
			nuke.message(msg)
		else:
			print(msg)
		return

	# Make sure Write nodes contain their own 'range' knobs

	if not ranges:
		ranges = "%i-%i" % (nuke.root().firstFrame(),nuke.root().lastFrame())

	if default_order:
		# For whatever reason, render according to Nuke's default concurrent order
		nukeOriginalExecuteMultiple(nodes,ranges,views)
	else:
		try:
			nodes = sorted(nodes,key=lambda x: x['render_order'].value())
		except:
			nodes = nodes
		missing_range,cont = False,True
		for n in nodes:
			try:
				n['range'].value()
			except NameError:
				missing_range = True
				attach_range(n)
		if missing_range:
			cont = nuke.ask("Render range knobs were added to Write nodes\n\
							and set to %i-%i. Continue?" % (nuke.root().firstFrame(),nuke.root().lastFrame()))
		if cont:
			for n in nodes:
				name = n.name()
				t1,t2 = [int(i) for i in n['range'].value()]
				ACTIVE_LAST_FRAME = int(t2)
				print "--------- RENDERING: %s | %i-%i -----------" % (name,t1,t2)
				nuke.execute(name,t1,t2)
	
	if RVPATH != None and nuke.env['gui']:
		rep = nuke.ask("Play in RV?")
		if rep:
			rv(nodes)

nuke.executeMultiple = customExecuteMultiple

# --------------------------- BEFORE AND AFTER RENDER -------------------------- #

last_tweet_time = time.clock()

def tweet(message,force=False):
	"""
	Uses curl to broadcast a message to twitter asynchronously. DOES NOT
	check if broadcast is successful, returns control immedietly to parent process.	
	"""
	global last_tweet_time
	url = 'http://twitter.com/statuses/update.xml'
	cmd = 'curl -s -u Hiroshima_V1:yesterday -d status="%s" %s' % (message,url)
	if time.clock()-last_tweet_time > 90 or force:
		Popen(cmd)
		print "Posted: %s" % message
		last_tweet_time = time.clock()
		return

def renderStatus2Twitter(interval=10):
	"""
	Broadcasts the last frame rendered for a given Write node to twitter at
	every n-th interval frame. 	Can be optionally attached to nuke.addAfterFrameRender.
	"""
	global ACTIVE_LAST_FRAME
	
	if ACTIVE_LAST_FRAME is None:
		ACTIVE_LAST_FRAME = nuke.root().lastFrame()

	on_first_last = True if nuke.frame() <= 1 or nuke.frame() == ACTIVE_LAST_FRAME else False
	
	if nuke.frame() % interval == 0 or on_first_last:
		script_name = nuke.root()['name'].value()
		fileout_path = nuke.filename(nuke.thisNode())
		fileout_name = os.path.split(fileout_path)[-1]
		fileout_name = re.sub('%\d+d','#',fileout_name) # Replace "%05d" part with "#"
		msg = "NUKE %s | %s | %i of %i" % (script_name,fileout_name,nuke.frame(),ACTIVE_LAST_FRAME)
		if on_first_last:
			# For render start and complete, force update on twitter
			# ignoring twitter's post-per-hour limit
			tweet(msg,True)
		else:
			tweet(msg)

def createWriteDirs():
	"""
	Automatically create directories in Write path if path doesn't exists.
	"""
	f = nuke.filename(nuke.thisNode())
	dir = os.path.dirname(f)
	if not os.path.exists(dir):
		osdir = nuke.callbacks.filenameFilter(dir)
		os.makedirs(osdir)

def setSwitches(s):
	"""
	Used to hook into addBeforeRender of Write nodes to enable
	rendering different paths of the DAG. Use in the form:
		nk.setSwitches("ReadSwitch 0 MatteSwitch 1")
	"""
	ss = s.split(" ")
	for s in zip(ss[0::2],ss[1::2]):
		name = s[0]
		which = int(s[1])
		print "SWITCH: %s -> %i" % (name, which)
		if nuke.exists(name):
			nuke.toNode(name)['which'].setValue(which)
		else:
			msg = "%s switch does not exists!" % name
			nuke.message(msg)

def beforeRender():
	createWriteDirs()
	try:
		route = nuke.thisNode()['switchroute'].value()
		if route: setSwitches(route)
	except NameError:
		pass

nuke.addBeforeRender(beforeRender)
nuke.addAfterFrameRender(renderStatus2Twitter)

# ------------------ COMMAND LINE RENDERING ------------------  #
# REMEMBER: To use this, you must specifically use this format:
# nuke -it /path/to/script.nk -renderall
# nuke -it /path/to/script.nk -renderonly "Write1 Write4 Write5"
#
# THE EVAL SWITCH
# The -eval switch allows you to interrogate nuke scripts as
# if you were on a command line with nuke -t in the form:
# nuke -it /path/to/script.nk -eval "statement"
# 
# Remember to use '' vs "" within the statement. 
#
# EXAMPLE 1: retrieve the paths of all Write nodes that are not disabled:
# nuke -it /path/to/script.nk -eval "[nuke.filename(n) for n in nuke.allNodes('Write') if n['disable'].value() != True]"
# 
# EXAMPLE 2: get comp width and height
# nuke -it /path/to/script.nk -eval "'%ix%i'%(nuke.root().width(),nuke.root().height())"
#
# All returned values are passed to print() so you'll have to be smart about formatting data 
# into a string at the very end for STDOUT
# 
# You would implement this in a separate python script that requires data from a nuke script.
# This is how you do it, with all the code needed to clean the junk printed to STDOUT
#
# from subprocess import Popen,PIPE
# cmd = *** Command from Example 1 which returns an array
# po = Popen(cmd,stdout=PIPE).stdout.readlines()[-1].strip()  ### get last line from STDOUT (what we actually want) > strip away /r/n characters
# x = eval(po)   ** in the case of an array, this turns po back into a callable Python array!

if not nuke.env['gui']:
	f = [n for n in sys.argv if re.search("\.nk",n)]	
	Q = None
	if "-renderall" in sys.argv:
		nuke.scriptOpen(f[0])
		Q = nuke.allNodes("Write")
		nuke.executeMultiple(Q)
		sys.exit(0)
	elif "-renderonly" in sys.argv:
		nuke.scriptOpen(f[0])
		write_names = sys.argv[sys.argv.index('-renderonly')+1].split(" ")
		Q = [nuke.toNode(n) for n in write_names]
		if None in Q:
			ok = [n.name() for n in Q if n]
			fail = [p for p in write_names if p not in ok]
			print "RENDER ERROR -renderonly failed to find nodes: %s" % " ".join(fail)
			Q = [nuke.toNode(n) for n in write_names if n in ok]
		nuke.executeMultiple(Q)
		sys.exit(1)
	elif "-eval" in sys.argv:
		nuke.scriptOpen(f[0])
		command = sys.argv[sys.argv.index('-eval')+1]
		print eval(command)
		exit()
	else:
		pass

# ----------------------------------------------------------- END CUSTOM ------------------------------------------------------------ #

# always use utf-8 for all strings
if hasattr(sys, "setdefaultencoding"):
  sys.setdefaultencoding("utf_8")

# set $NUKE_TEMP_DIR, used to write temporary files:
nuke_subdir = "nuke"
try:
  nuke_temp_dir = os.environ["NUKE_TEMP_DIR"]
except:
  try:
    temp_dir = os.environ["TEMP"]
  except:
    if nuke.env["WIN32"]:
      temp_dir = "C:/temp"
    else:
      temp_dir = "/var/tmp"
      nuke_subdir += "-u" + str(os.getuid())

  nuke_temp_dir = os.path.join(temp_dir, nuke_subdir)

if nuke.env["WIN32"]:
  nuke_temp_dir = nuke_temp_dir.replace( "\\", "/" )

os.environ["NUKE_TEMP_DIR"] = nuke_temp_dir

# Stuff the NUKE_TEMP_DIR setting into the tcl environment.
# For some reason this isn't necessary on windows, the tcl environment
# gets it from the same place python has poked it back into, but on
# OSX tcl thinks NUKE_TEMP_DIR hasn't been set.
# But we'll do it all the time for consistency and 'just in case'.
# It certainly shouldn't do any harm or we've got another problem...
nuke.tcl('setenv','NUKE_TEMP_DIR',nuke_temp_dir)

nuke.pluginAddPath("./user", addToSysPath=False)


# Knob defaults
#
# Set default values for knobs. This must be done in cases where the
# desired initial value is different than the compiled-in default.
# The compiled-in default cannot be changed because Nuke will not
# correctly load old scripts that have been set to the old default value.
nuke.knobDefault("Assert.expression", "{{true}}")
nuke.knobDefault("Assert.message", "[knob expression] is not true")
nuke.knobDefault("PostageStamp.postage_stamp", "true")
nuke.knobDefault("Keyer.keyer", "luminance")
nuke.knobDefault("Copy.from0", "rgba.alpha")
nuke.knobDefault("Copy.to0", "rgba.alpha")
nuke.knobDefault("Constant.channels", "rgb")
nuke.knobDefault("ColorWheel.gamma", ".45")
nuke.knobDefault("Truelight.label", "Truelight v2.1")
nuke.knobDefault("Truelight3.label", "Truelight v3.0")
nuke.knobDefault("ScannedGrain.fullGrain", "[file dir $program_name]/FilmGrain/")
nuke.knobDefault("SphericalTransform.fix", "True");
nuke.knobDefault("Environment.mirror", "True");
nuke.knobDefault("TimeBlur.shutteroffset", "start")
nuke.knobDefault("TimeBlur.shuttercustomoffset", "0")
nuke.knobDefault("Truelight.output_raw", "true")
nuke.knobDefault("Truelight3.output_raw", "true")
nuke.knobDefault("Root.proxy_type", "scale")
nuke.knobDefault("Text.font",nuke.defaultFontPathname())
nuke.knobDefault("Text.yjustify", "center")


# Register default ViewerProcess LUTs.

# The ViewerProcess_None gizmo is a pass-through -- it has no effect on the image.
nuke.ViewerProcess.register("None", nuke.createNode, ("ViewerProcess_None", ))

# The ViewerProcess_1DLUT gizmo just contains a ViewerLUT node, which
# can apply a 1D LUT defined in the project LUTs. ViewerLUT features both
# software (CPU) and GPU implementations.

nuke.ViewerProcess.register("sRGB", nuke.createNode, ( "ViewerProcess_1DLUT", "current sRGB" ))
nuke.ViewerProcess.register("rec709", nuke.createNode, ( "ViewerProcess_1DLUT", "current rec709" ))

# Here are some more examples of ViewerProcess setup.
#
# nuke.ViewerProcess.register("Cineon", nuke.createNode, ("ViewerProcess_1DLUT", "current Cineon"))
#
# Note that in most cases you will want to create a gizmo with the appropriate
# node inside and only expose parameters that you want the user to be able
# to modify when they open the Viewer Process node's control panel.
#
# The VectorField node can be used to apply a 3D LUT.
# VectorField features both software (CPU) and GPU implementations.
#
# nuke.ViewerProcess.register("3D LUT", nuke.createNode, ("Vectorfield", "vfield_file /var/tmp/test.3dl"))
#
# You can also use the Truelight node.
#
# nuke.ViewerProcess.register("Truelight", nuke.createNode, ("Truelight", "profile /Applications/Nuke5.2v1/Nuke5.2v1.app/Contents/MacOS/plugins/truelight3/profiles/KodakVisionPremier display sRGB enable_display true"))


# Pickle support

class __node__reduce__():
  def __call__(s, className, script):
    n = nuke.createNode(className, knobs = script, inpanel = False)
    for i in range(n.inputs()): n.setInput(0, None)
    n.autoplace()
__node__reduce = __node__reduce__()

class __group__reduce__():
  def __call__(self, script):
    g = nuke.nodes.Group()
    with g:
      nuke.tcl(script)
    for i in range(g.inputs()): g.setInput(0, None)
    g.autoplace()
__group__reduce = __group__reduce__()

# Define image formats:
nuke.load("formats.tcl")
# back-compatibility for users setting root format in formats.tcl:
if nuke.knobDefault("Root.format")==None:
  nuke.knobDefault("Root.format", nuke.value("root.format"))
  nuke.knobDefault("Root.proxy_format", nuke.value("root.proxy_format"))


