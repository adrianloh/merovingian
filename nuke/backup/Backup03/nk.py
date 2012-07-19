import nuke
import nukescripts
import re
import os
import random
from twitter import tweet

# NOTE: When naming functions, functions that begin with nk are automatically 
# loaded by menu.py and words should be dilineated with undescores. They *must*
# contain docstrings, the first line of which is used as the label of the function
# in nuke's menus. "Internal" functions (aka functions that cannot be called 
# directly from the UI) should be camelcased.

# GLOBALS

SUPPORTED_FORMATS = "tif tiff tif16 tiff16 ftif ftiff tga targa rla xpm yuv avi cin dpx exr gif \
					hdr hdri jpg jpeg iff png png16 mov r3d raw psd sgi rgb rgba sgi16 pic".split(" ")

ACTIVE_LAST_FRAME = None

SCRIPT_RELATIVE_PATH = "[file dirname [value root.name]]"

def initScriptEnv():
	path = nuke.root()['name'].value()
	os.environ["SCRIPTNAME"] = os.path.split(path)[-1] if path else "UNTITLED"
	job = os.environ["JOB"]
	os.chdir(job)
	for n in re.split("[_ \.]",os.environ["SCRIPTNAME"]):
		if os.path.exists(n):
			os.environ["SHOT"] = "%s/%s"%(job,n)
		else:
			os.environ["SHOT"] = os.path.dirname(path)
	os.chdir(os.environ["SHOT"])
	print "---- CURRENT SCRIPT ENVIRONMENT ----"
	print "JOBS %s" % os.environ["JOBS"]
	print "JOB %s" % os.environ["JOB"]
	print "SHOT %s" % os.environ["SHOT"]
	print "-"*80
	
def initRelativePaths():
	"""
	Resolve all file paths into relative paths
	"""
	for n in nuke.allNodes():
		try:
			fn = n['file'].value()
			if fn and not fn.startswith("["):
				fn = toRelativePath(fn)
				n['file'].setValue(fn)
		except NameError:
			continue

## NODE OVERRIDES ##

nukeOriginalCreateNode = nuke.createNode
nukeOriginalSelectedNodes = nuke.selectedNodes
nukeOriginalGetClipname = nuke.getClipname
nukeOriginalGetFilename = nuke.getFilename

def toRelativePath(path,returnRange=True):
	"""
	Absolute filepaths are resolved relative to the order:
	Script -> Job -> Jobs
	"""
	jobs = os.environ['JOBS']
	job = os.environ['JOB']
	shot = os.environ['SHOT']
	range = re.findall("(\d+-\d+)$",path)
	if range:
		fn = " ".join(path.split(" ")[:-1])
		range = range[0]
	else:
		fn = path
	if fn.startswith(shot):
		p = re.sub(shot,SCRIPT_RELATIVE_PATH,fn)	# [getenv SHOT] deprecated but declared for backward compatibility
	elif fn.startswith(job):
		p = re.sub(job,"[getenv JOB]",fn)
	elif fn.startswith(jobs):
		p = re.sub(jobs,"[getenv JOBS]",fn)
	else:
		p = fn
	if returnRange and range:
		return "%s %s" % (p,range)
	else:
		return p

def customSelectedNodes(nodeClass=None):
	sel = nukeOriginalSelectedNodes(nodeClass) if nodeClass else nukeOriginalSelectedNodes()
	sel.reverse()
	return sel

def customCreateNode(node,knobs="",inpanel=True):
	if node == "Log2Lin":
		# LUT for EXRs exported from Fusion
		return nukeOriginalCreateNode("Log2Lin",knobs="black 0 white 1023 gamma 1.3",inpanel=True)
	elif node == "Write":
		# By default render RGBA
		n = nukeOriginalCreateNode("Write",knobs="channels {rgba.red rgba.green rgba.blue rgba.alpha}",inpanel=True)
		k = nuke.UV_Knob("range","Range")
		n.addKnob(k)
		n["range"].setValue([nuke.root().firstFrame(),nuke.root().lastFrame()])
		n["label"].setValue("[knob range]")
		return n
	elif node == "Bezier":
		# By default splines output only alpha
		return nukeOriginalCreateNode("Bezier",knobs="output alpha",inpanel=True)
	elif node == "Switch":
		# Label of Switch node displays active input of node
		return nukeOriginalCreateNode("Switch",knobs=""" label "\[knob which]" """,inpanel=True)
	elif node == "Card2":
		c = nukeOriginalCreateNode("Card2",inpanel=True)
		c['label'].setValue("[knob translate.x] [knob translate.y] [knob translate.z]")
	else:
		return nukeOriginalCreateNode( node, knobs, inpanel )

def customGetClipname(message,multiple=True):
	files = nukeOriginalGetClipname(message,multiple=True)
	return [toRelativePath(f) for f in files]

## NK MODULE ##

def this():
	return nuke.selectedNode()
	
def these():
	return nuke.selectedNodes()

def get(nodeName):
	return [n for n in nuke.allNodes() if n.name() == nodeName][0]

def val(obj,parm,value=None):
	if value:
		obj[parm].setValue(value)
		return obj
	else:
		return obj[parm].value()
		
def animate(obj,parm,curve):
	"""
	Animate parameters in the form:
		nk.animate(node,parameter,[ [frame1,(x,y,z) , [frame2,(x,y,z), [frame3,(x,y,z) ])
	"""
	obj[parm].setAnimated()
	for animTuple in curve:
		[t,v] = animTuple
		try:
			for i,vv in enumerate(v):
				obj[parm].setValueAt(vv,t,i)
		except TypeError:
			obj[parm].setValueAt(v,t)

def setRange(n):
	"""
	Set In and Out points of the *selected Viewer*. Meant to be key-binded to
	achieve FCP-like functionality.
	"""
	viewer = nuke.selectedNode()
	frame = nuke.frame()
	if viewer.Class() == "Viewer":
		viewer['frame_range_lock'].setValue(True)
		i,o = re.split("\W",viewer['frame_range'].value())
		new_range = (n == 0) and (frame,o) or (i,frame)
		viewer['frame_range'].setValue("%s %s" % new_range)
	else:
		pass
	
def group(nodes):
	[n['selected'].setValue(False) for n in nuke.allNodes()]
	[n['selected'].setValue(True) for n in nodes]
	nuke.makeGroup()

def nk_new_scene(nodes=None):
	""" 
	New scene
	Creates a new 3D scene with renderer and a camera attached. If invoked with 
	nodes selected, they are fed into the 3D Scene node.
	"""
	if not nodes:
		nodes = nuke.selectedNodes()
	if nodes != [] and nodes[-1].Class() == "Scene":
		scene = nodes[-1]
		inputs = nodes[0:-1]
	else:
		scene = nuke.nodes.Scene()
		camera = nuke.nodes.Camera()
		val(camera,"translate",[0,0,1])
		render = nuke.nodes.ScanlineRender()
		scene.setInput(scene.inputs(),camera)
		render.setInput(0,camera)
		render.setInput(1,scene)
		inputs = nodes
	for input in inputs:
		connected = scene.setInput(scene.inputs(),input)
		if not connected:
			card = nuke.nodes.Card()
			card.setInput(0,input)
			scene.setInput(scene.inputs(),card)
	return scene
	
def nk_importBoujou():
	"""
	Import Boujou Maya
	Import Maya 4.0++ .ma files exported from Boujou. Will work only with
	scene files containing a single camera solve.
	"""
	path = nuke.getFilename("Select Maya Ascii file...","*.ma")
	file = open(path).readlines()
	scene = nuke.nodes.Scene()
	input = nuke.nodes.Input()
	scene.setInput(scene.inputs(),input)

	marker = nuke.createNode("Constant","color {0.8 1 0 0}",inpanel=False)
	marker_lines = [i+1 for (i,l) in enumerate(file) if re.search('auto.+reference_points',l)]
	points = [nuke.createNode("Card","image_aspect false uniform_scale 0.03 translate {%s}" % " ".join(l.strip()[:-2].split(" ")[-3:]),inpanel=False) for (i,l) in enumerate(file) if i in marker_lines]
	for point in points:
		point.setInput(0,marker)
		scene.setInput(scene.inputs(),point)
		
	tt = [[float(x.split(" ")[1]) for x in re.findall("\]\" (.+)",line.strip())[0].split("  ")[:-1]] for line in file if re.search("ktv",line)][1:]
	camera = nuke.createNode("Camera",knobs="rot_order XYZ",inpanel=False)
	animate(camera,'focal',[[i,v] for i,v in enumerate(tt[0])])
	animate(camera,'translate',[[i,v] for i,v in enumerate(zip(tt[1],tt[2],tt[3]))])
	animate(camera,'rotate',[[i,v] for i,v in enumerate(zip(tt[4],tt[5],tt[6]))])

	def maya2nuke_aperture(x,y):
		return x/(x/(y*25.4))

	w = nuke.root()['format'].value().width()
	h = nuke.root()['format'].value().height()
	mh,mv = [line.strip()[:-1].split(" ")[-2:] for line in file if re.search("cap",line)][0]
	camera['haperture'].setValue(maya2nuke_aperture(w,float(mh)))
	camera['vaperture'].setValue(maya2nuke_aperture(h,float(mv)))

	masterScene = nuke.nodes.Scene()
	render = nuke.nodes.ScanlineRender()
	render.setInput(2,camera)
	render.setInput(1,masterScene)

	points.append(scene)
	points.append(input)
	points.append(marker)
	group(points)
	[nuke.delete(n) for n in points]

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

def nk_load_directory():
	"""
	Load directory
	"""
	loadDir = nukeOriginalGetFilename("Select a folder...")
	if os.path.isdir(loadDir):
		for f,ff,fff in os.walk(loadDir):
			clips = getClips(f)
			if clips:
				for clip in clips.keys():
					if os.path.splitext(clip)[-1][1:] in SUPPORTED_FORMATS:
						path = "%s%s" % (f,clip)
						path = toRelativePath(path,False) # Return only the path without the range range
						first = clips[clip][0]
						last =	clips[clip][1]
						nuke.createNode("Read",inpanel=False,knobs="""file "%s" first %i last %i before bounce after bounce""" % (path,first,last))

def nk_connect_to_switches():
	"""
	=> Switches
	Connect multiple reads into multiple Switches and randomizes all
	TimeOffset nodes up to maxTime.
	"""
	sel = nuke.selectedNodes()
	switches = [n for n in sel if n.Class() == "Switch"]
	others = [n for n in sel if n not in switches]
	[s.setInput(s.inputs(),n) for s in switches for n in others]

def nk_randomize_selected_switches_timeOffsets(maxTime=300):
	"""
	Rand Switch + TimeOffset
	"""
	for n in nukeOriginalSelectedNodes("TimeOffset"):
		r = [nn for nn in allDependencies(n) if nn.Class() == "Read"]
		if r:
			max_time = r[0]['last'].value()
	maxTime *= -1
	[n['time_offset'].setValue(random.randrange(maxTime,0)) for n in nukeOriginalSelectedNodes("TimeOffset")]
	for switch in nukeOriginalSelectedNodes("Switch"):
		max = switch.inputs()
		switch['which'].setValue(random.randrange(0,max))

def align(direction):
	
	def cmpX(x,y):
		return (x.xpos() > y.xpos()) and 1 or -1

	def cmpY(x,y):
		return (x.ypos() > y.ypos()) and -1 or 1

	nodes = [n for n in sorted(nuke.selectedNodes(),cmp=cmpX)]
	ypos = [n.ypos() for n in nodes]
	xpos = [n.xpos() for n in nodes]

	if direction == "horz":
		med = min(ypos)
		leftmost = min(xpos)
		[n['ypos'].setValue(med) for n in nodes]
		[n['xpos'].setValue(leftmost+(i*100)) for (i,n) in enumerate(nodes)]
	elif direction == "vert":
		med = min(xpos)
		topmost = nodes[0].ypos()
		[n['xpos'].setValue(med) for n in nodes]
		[n['ypos'].setValue(topmost+(i*125)) for (i,n) in enumerate(nodes)]

def nk_align_horizontal():
	"""
	||
	"""
	align("horz")
	
def nk_align_vertical():
	"""
	===
	"""
	align("vert")
	
def nk_new_channel_from_rgba():
	"""
	RGBA > Channels
	Copy RGBA channels from A input into *new channels* of B input. New channels
	are created globally and named after the node of A input. Useful when you
	need to merge multiple RGBA inputs into a multichannel EXR.
	"""
	for n in nuke.selectedNodes():
		cp = nuke.createNode("Copy",inpanel=False)
		nuke.inputs(cp,0)
		cp.setInput(1,n)
		chan = n.name()
		nuke.tcl("add_layer {%s %s.red %s.green %s.blue %s.alpha}" % (chan,chan,chan,chan,chan))
		cp['from0'].setValue("rgba.red")
		cp['from1'].setValue("rgba.green")
		cp['from2'].setValue("rgba.blue")
		cp['to0'].setValue("%s.red" % chan)
		cp['to1'].setValue("%s.green" % chan)
		cp['to2'].setValue("%s.blue" % chan)
		input_alpha = [c for c in nuke.channels(n) if c.split(".")[1] == "alpha"]
		if input_alpha:
			cp['from3'].setValue("rgba.alpha")
			cp['to3'].setValue("%s.alpha" % chan)

def nk_execute_multiple_write_ranges():
	"""
	X Writes
	For multiple write nodes with different render ranges, 
	label each write node with a frame range in the form "1-10".
	"""
	global ACTIVE_LAST_FRAME # This hack enables #renderStatus2Twitter() to retrieve the lastFrame for each Write node
	writes = nukeOriginalSelectedNodes("Write")
	if not writes:
		writes = nuke.allNodes("Write")
	for n in writes:
		name = n.name()
		t1,t2 = [int(i) for i in n['range'].value()]
		ACTIVE_LAST_FRAME = int(t2)
		print "RENDERING: %s | %i-%i" % (name,t1,t2)
		nuke.execute(name,t1,t2)

def createWriteDirs():
	"""
	Automatically create directories in Write path if path doesn't exists.
	"""
	file = nuke.filename(nuke.thisNode())
	dir = os.path.dirname(file)
	if not os.path.exists(dir):
		osdir = nuke.callbacks.filenameFilter(dir)
		os.makedirs(osdir)

def renderStatus2Twitter(interval=10):
	"""
	Broadcasts the last frame rendered for a given Write node to twitter at
	every n-th interval frame. 	Can be optionally attached to #nuke.addAfterFrameRender.
	"""
	global ACTIVE_LAST_FRAME
	
	if ACTIVE_LAST_FRAME is None:
		ACTIVE_LAST_FRAME = nuke.thisNode().lastFrame()

	if nuke.frame() <= 1 or nuke.frame() == ACTIVE_LAST_FRAME:
	# The first and last frame are "sepcial" cases
		on_first_last = True
	else:
		on_first_last = False
	
	if nuke.frame() % interval == 0 or on_first_last:
		script_name = os.environ["SCRIPTNAME"]
		fileout_path = nuke.filename(nuke.thisNode())
		fileout_name = os.path.split(fileout_path)[-1]
		fileout_name = re.sub('%\d+d','#',fileout_name) # Replace "%05d" part with "#"
		msg = "%s | %s | %i of %i" % (script_name,fileout_name,nuke.frame(),ACTIVE_LAST_FRAME)
		if on_first_last:
			# For render start and complete, force update on twitter
			# ignoring twitter's post-per-hour limit
			tweet(msg,True)
		else:
			tweet(msg)

def dynamicFavorites():
	# Favorite parent folder of current script
	script_path = os.environ["SHOT"]
	script_dirname = os.path.split(script_path)[-1]
	nuke.addFavoriteDir(script_dirname,script_path)

def nk_connect():
	"""
	Connect
	Connect nodes. First select source nodes in order by which
	they should be connected to target. Lastly, select target node.
	"""
	sel = nuke.selectedNodes()
	sources = sel[0:-1]
	target = sel[-1]
	for i,n in enumerate(sources):
		target.setInput(i,n)

def nk_color_tiles():
	"""
	Color
	"""
	color = nuke.getColor()
	[n['tile_color'].setValue(color) for n in nuke.selectedNodes()]
		
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

def allDependencies(source):
	"""
	Returns a list containing *only* and *all* ancestors of a given node 
	aka. all nodes required to produce the output of the specified node.
	"""
	d = []
	g = []
	[g.append(n) for n in nuke.dependencies(source)]
	while len(g) != 0:
		n = g.pop()
		d.append(n)
		[g.append(n) for n in nuke.dependencies(n)]
	return d
	
def nk_select_all_dependencies():
	"""
	Select all dependencies
	"""
	d = allDependencies(nuke.selectedNode())
	[n['selected'].setValue(True) for n in d]
	
def nk_set_write_paths_ranges_from_reads():
	"""
	Read |=> Write
	"""
	for w in nuke.allNodes("Write"):
		r = [nn for nn in allDependencies(w) if nn.Class() == "Read"]
		if r and r[0].Class() == "Read":
			r = r[0]
			fn = nuke.filename(r)
			fn = os.path.split(fn)[-1].split(".")[0]
			w['file'].setValue("[getenv SHOT]/%s.mov"%fn)
			range = [r['first'].value(),r['last'].value()]
			w['range'].setValue(range)

def nk_paste_to_selected_nodes():
	"""
	Paste special
	"""
	sel = nuke.selectedNodes()
	[n['selected'].setValue(False) for n in nuke.selectedNodes()]
	for n in sel:
		n['selected'].setValue(True)
		nuke.nodePaste(nukescripts.cut_paste_file())
		n['selected'].setValue(False)

def nk_expose_group_node():
	"""
	Open Group
	"""
	nuke.showDag(nuke.selectedNode())
	
def setSwitches(s):
	"""
	Used to hook into "Before Render" of Write nodes to enable 
	Write nodes to render different paths of the DAG. Use in the form:
		nk.setSwitches("ReadSwitch 0 MatteSwitch 1")
	while another may possibly be:
		nk.setSwitches("ReadSwitch 1 MatteSwitch 0")
	"""
	ss = s.split(" ")
	for s in zip(ss[0::2],ss[1::2]):
		name = s[0]
		which = int(s[1])
		print "SWITCH: %s -> %i" % (name, which)
		if nuke.exists(name):
			get(name)['which'].setValue(which)
		else:
			msg = "%s switch does not exists!" % name
			nuke.message(msg)