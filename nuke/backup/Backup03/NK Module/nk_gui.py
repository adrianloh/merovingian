
# -----------------------------------------------------
# This module contains functions that extend the GUI
# workings of Nuke on a non-node-specific basis.
# ----------------------------------------------------

import nuke
import nukescripts
import os
import re
from subprocess import Popen,PIPE

os.environ['RVPATH'] = "/bin/rv.cmd"

def nk_rv(nodes=None):
	"""
	RV
	SS Shift+f
	""" 

	get_file = lambda n: re.sub(r'%0\dd',"#",nuke.filename(n))

	n = nodes if nodes else [n for n in nuke.selectedNodes() if n.Class() == 'Write' or n.Class() == 'Read']
	
	if len(n) == 1:	
		# If one node is sent to RV
		cmd = """%s -fullscreen "%s" """ % ( os.environ['RVPATH'],get_file(n[0]) )
	elif len(n) > 1: 
		# If multiple nodes are sent to RV, stack them to make compare possible
		paths = [get_file(nn) for nn in n]
		cmd = """%s -fullscreen -sessionType stack %s """ % ( os.environ['RVPATH']," ".join(paths) )
	else:
		return
	
	Popen(cmd,stdout=PIPE)

def nk_new_scene(nodes=None):
	""" 
	New scene
	SS Shift+b
	Creates a new 3D scene with renderer and a camera attached. If invoked with 
	any other node selected *and a scene node*, they are fed into the scene node.
	"""
	if not nodes:
		nodes = nuke.selectedNodes()
	if nodes != [] and nodes[-1].Class() == "Scene":
		scene = nodes[-1]
		inputs = nodes[0:-1]
	else:
		scene = nuke.nodes.Scene()
		camera = nuke.nodes.Camera2()
		camera['translate'].setValue([0,0,1])
		render = nuke.nodes.ScanlineRender()
		scene.setInput(scene.inputs(),camera)
		render.setInput(2,camera)
		render.setInput(1,scene)
		inputs = nodes
	for input in inputs:
		connected = scene.setInput(scene.inputs(),input)
		if not connected:
			card = nuke.nodes.Card()
			card.setInput(0,input)
			scene.setInput(scene.inputs(),card)
	return scene

def nk_batchChangeSelected():
	"""
	Batch change on nodes
	"""
	input = nuke.getInput("""Eg. translate=[0,1,3] / rotate=90.0 / label="some text" """)
	try:
		param,value = input.split("=")
		[n[param].setValue(eval(value)) for n in nuke.selectedNodes()]
	except:
		pass

def nk_autoBackdrop():
	"""
	Autobackdrop
	"""
	import operator, random
	selNodes = nuke.selectedNodes()
	if not selNodes:
		return nuke.nodes.BackdropNode()
	positions = [(i.xpos(), i.ypos()) for i in selNodes]
	xPos = sorted(positions, key = operator.itemgetter(0))
	yPos = sorted(positions, key = operator.itemgetter(1))
	xMinMaxPos = (xPos[0][0], xPos[-1:][0][0])
	yMinMaxPos = (yPos[0][1], yPos[-1:][0][1])
	n = nuke.nodes.BackdropNode(xpos = xMinMaxPos[0]-10,
				    bdwidth = xMinMaxPos[1]-xMinMaxPos[0]+110,
				    ypos = yMinMaxPos[0]-85,
				    bdheight = yMinMaxPos[1]-yMinMaxPos[0]+160,
				    tile_color = int((random.random()*(13-11)))+11,
				    note_font_size = 42)
	n['selected'].setValue(False)
	# revert to previous selection
	[i['selected'].setValue(True) for i in selNodes]
	return n
	
def nk_connect_to_switches():
	"""
	Connect to Switches
	Connect all selected nodes into all Switches
	"""
	sel = nuke.selectedNodes()
	switches = [n for n in sel if n.Class() == "Switch"]
	others = [n for n in sel if n not in switches]
	[s.setInput(s.inputs(),n) for s in switches for n in others]
	
def nk_paste_to_selected_nodes():
	"""
	Paste into selected
	"""
	sel = nuke.selectedNodes()
	[n['selected'].setValue(False) for n in nuke.selectedNodes()]
	for n in sel:
		n['selected'].setValue(True)
		nuke.nodePaste(nukescripts.cut_paste_file())
		n['selected'].setValue(False)
	
def nk_color_others():
	"""
	Color others with first selected node
	"""
	nk_color_tiles(True)

def nk_color_tiles(src=False):
	"""
	Color nodes with swatch
	"""
	nodes = nuke.selectedNodes()
	color = nodes[0]['tile_color'].value() if src else nuke.getColor()
	dst = nodes[1:]	if src else nodes
	[n['tile_color'].setValue(color) for n in dst]

def getClips(dir,format="nuke",symbol="@"):
	"""
	Given a directory, returns a dictionary of sequence files in the form:
		dict[sequence_template] = [first_frame,last_frame]
	e.g.
		when format is "nuke":
			d[sequence_v1.%05d.exr] = [1,100]
		when format is "shake":
			d[sequence_v1.@@@@@@.exr] = [1,100]
	"""
	
	d = {}
	r = {}

	def make_pattern(filename):
		"""
		Creates a regular expression pattern from a filename, aka a "template"
		to match against other files. Assumes that leftmost consecutive digits 
		is the "index counter". E.g:
			shot01_project1234_version01.0001.exr #-> shot01_project1234_version01.\d\d\d\d.exr
		"""
		sf = re.sub('\d',"@",fn)
		rmost_counter = re.findall("@{1,}",sf)[-1]
		pat_len = len(rmost_counter)
		pat_position = sf.rindex(rmost_counter)
		bfn = re.findall(".",filename)
		for i in range(pat_len):
			pp = pat_position+i
			bfn[pp] = r"\d"
		t = "^"+"".join(bfn)+"$"
		return t
		
	os.chdir(dir)

	fff = [f for f in os.listdir(dir) if os.path.isfile(f)]
	
	if fff:

		for fn in fff:
			template = make_pattern(fn)
			if template in d:
				continue
			else:
				d.setdefault(template,[])

		for t in d.keys():
			for f in fff:
				if re.search(t,f):
					d[t].append(f)

		for dr in d.keys():
			c = dr.count("\d")
			printf = re.sub("(\\\d)+","%%0%id"%c,dr)[1:-1]
			substr = re.sub("\\\d","%s"%symbol,dr)[1:-1]
			np = re.sub("(\\\d)+","("+"\d"*c+")",dr)
			cc = sorted(d[dr])
			first = int(re.findall(np,cc[0])[0])
			last = int(re.findall(np,cc[-1])[0])
			if format == "nuke":
				r[printf] = [first,last]
			elif format == "shake":
				r[substr] = [first,last]

	return r

def nk_load_directory():
	"""
	Load directory
	"""
	formats = "tif tiff tif16 tiff16 ftif ftiff tga targa rla xpm yuv avi cin dpx exr gif \
				hdr hdri jpg jpeg iff png png16 mov r3d raw psd sgi rgb rgba sgi16 pic"
	
	SUPPORTED_FORMATS = "["+ "|".join(formats) + "]"	# Compile regex pattern

	loadDir = nuke.getClipname("Select a folder...")
	if os.path.isdir(loadDir):
		for f,ff,fff in os.walk(loadDir):
			clips = getClips(f)
			if clips:
				for clip in clips.keys():
					extension = os.path.splitext(clip)[-1][1:]
					if re.search(SUPPORTED_FORMATS,extension,re.IGNORECASE):
						path = "%s/%s" % (f,clip)
						first,last = clips[clip][0],clips[clip][1]
						read = nuke.createNode("Read",inpanel=False,knobs="first %i last %i before bounce after bounce" % (first,last))
						read['file'].setValue(path)

def nk_backburner():
	"""
	Background render
	Note: this assumes that the nuke executeble is in PATH
	"""
	import threading
	import shutil
	nuke.scriptSave()
	op = nuke.root()['name'].value()
	name = nuke.selectedNode().name()
	np = op+"%s.bburn"%name
	shutil.copy2(op,np)
	ranges = "%s-%s" % (nuke.root().firstFrame(),nuke.root().lastFrame())
	cmd = "nuke -m %i -F %s -X %s -ix %s" % (int(nuke.env['numCPUs']/2),ranges,name,np)
	print cmd
	
	def render():
		print "Background rendering %s" % name
		Popen(cmd).wait()
		nuke.executeInMainThread(nuke.toNode(name)['tile_color'].setValue,552079871) #TODO: This executes but doesn't refresh in the DAG
		nuke.executeInMainThread(nuke.toNode(name)['postage_stamp'].setValue,True)
		nuke.executeInMainThread(nuke.toNode(name)['reading'].setValue,True)
		print "Background rendering done! %s" % name
		os.remove(np)

	this = nuke.toNode(name)
	this['tile_color'].setValue(943405567)
	this['postage_stamp'].setValue(False)
	this['reading'].setValue(False)
	T = threading.Thread(None,render)
	T.start()

if nuke.env['gui']:

	toolbar = nuke.menu('Nodes')

	NKMenu = toolbar.addMenu('NK')
	for func in [f for f in dir() if f.startswith("nk")]:
		exec("nuke.%s=%s" % (func,func))
		f = eval("%s" % func)
		docstring = [l.strip() for l in f.__doc__.split("\n")]
		label = docstring[1]
		if docstring[2].startswith("SS"):
			shortcut = docstring[2].split(" ")[1]
			NKMenu.addCommand(label,"nuke.%s()" % func,shortcut)
		else:
			NKMenu.addCommand(label,"nuke.%s()" % func)
		
	gizMenu = toolbar.addMenu('Gizmos')
	for giz in [os.path.splitext(n)[0] for n in os.listdir(os.path.join(os.environ["HOME"],".nuke")) if re.search("gizmo",n)]:
		gizMenu.addCommand(giz,"nuke.createNode('%s')"%giz)			
			
			
