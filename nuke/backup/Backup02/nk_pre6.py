import nuke
import nukescripts
import re
import os
import random
import threading
import mayacam
from custom import *
from subprocess import Popen

# NOTE: When naming functions, functions that begin with nk are automatically 
# loaded by menu.py and words should be dilineated with undescores. They *must*
# contain docstrings, the first line of which is used as the label of the function
# in nuke's menus. "Internal" functions (aka functions that cannot be called 
# directly from the UI) should be camelcased.

# GLOBALS

SCRIPT_RELATIVE_PATH = "[file dirname [value root.name]]"

ACTIVE_LAST_FRAME = None

RVPATH = "C:\\bin\\rv.cmd"
NUKE_PATH ="C:\\Program Files\\Nuke5.2v3\\Nuke5.2.exe"

# -------------- CALLBACK FUNCTIONS ---------------- #

def initScriptEnv():
	path = nuke.root()['name'].value()
	os.environ["SCRIPTNAME"] = os.path.split(path)[-1][:-3] if path else "UNTITLED"
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

def beforeRender():
	print "Rendering %s" % nuke.thisNode().name()
	try:
		route = nuke.thisNode()['switchroute'].value()
		if route: setSwitches(route)
	except NameError:
		pass

def afterRender():
	sf = "%s/notify.wav" % os.environ["DOTNUKE"]
	if nuke.env["WIN32"]:
		import winsound
		winsound.PlaySound(sf, winsound.SND_FILENAME|winsound.SND_ASYNC)

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
	
	def addFav(path):
		name = os.path.split(path)[-1]
		nuke.addFavoriteDir(name,path)

	addFav(os.environ["SHOT"])
	addFav(os.environ["JOB"])

# -------------- WANKER FUNCTIONS ---------------- #

def whereami():
	script = "SCRIPT %s" % os.environ["SCRIPTNAME"]
	path = "ROOT %s" % nuke.root()['name'].value()
	jobs = "JOBS %s" % os.environ["JOBS"]
	job = "JOB %s" % os.environ["JOB"]
	shot = "SHOT %s" % os.environ["SHOT"]
	msg = "\n".join([script,path,jobs,job,shot])
	nuke.message(msg)

# -------------- KNOB CREATION ---------------- #

def pyScriptKnob(label,script):
	K = nuke.PyScript_Knob(randstring(10),label)
	K.setValue(script)
	return K

def attach_file_operations(n):
	n = draw_line(n,"File Operations")
	n.addKnob(pyScriptKnob("Copy","nk.file(0)"))
	n.addKnob(pyScriptKnob("Move","nk.file(1)"))
	n.addKnob(nuke.Boolean_Knob("update_source","update_source"))
	return n

def attach_range(n):
	k = nuke.UV_Knob("range","render range")
	n.addKnob(k)
	n["range"].setValue([nuke.root().firstFrame(),nuke.root().lastFrame()])
	return n

def attach_switch_routing(n):
	n.addKnob(nuke.String_Knob("switchroute"))
	n.addKnob(pyScriptKnob(" Get current route ","nk.setSwitchRoute()"))
	return n

def draw_line(n,label):
	n.addKnob(nuke.Text_Knob(randstring(10),label))
	return n

# -------------- NUKE OVERRIDES ---------------- #

nukeOriginalCreateNode = nuke.createNode
nukeOriginalSelectedNodes = nuke.selectedNodes
nukeOriginalGetClipname = nuke.getClipname
nukeOriginalGetFilename = nuke.getFilename
nukeOriginalExecuteMultiple = nuke.executeMultiple

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
		# Hereon, always render RGBA by default
		n = nukeOriginalCreateNode("Write",knobs="channels {rgba.red rgba.green rgba.blue rgba.alpha}",inpanel=True)
		n = attach_range(n)
		n = attach_switch_routing(n)
		n = attach_file_operations(n)
		n['update_source'].setValue(1)
		n["label"].setValue("[knob range]")
		n['file'].setValue("%s/[knob name].%%05d.exr" % SCRIPT_RELATIVE_PATH)
		return n
	elif node == "Read":
		# All read nodes contain custom file operation buttons
		n = nukeOriginalCreateNode( node, knobs, inpanel )
		n = attach_file_operations(n)
		n['update_source'].setValue(1)
		return n
	elif node == "Bezier":
		# Hereon, splines output only alpha by default
		return nukeOriginalCreateNode("Bezier",knobs="output alpha",inpanel=True)
	elif node == "Switch":
		# Label of Switch node displays active input
		n = nukeOriginalCreateNode("Switch",knobs=""" label "\[knob which]" """,inpanel=True)
		n['note_font'].setValue("Arial Bold")
		n['note_font_size'].setValue(20)
		return n
	elif node == "Card2":
		# Label of cards display 3D coordinates
		n = nukeOriginalCreateNode("Card2",inpanel=True)
		n['label'].setValue("[knob translate.x] [knob translate.y] [knob translate.z]")
		return n
	else:
		return nukeOriginalCreateNode( node, knobs, inpanel )

def customGetClipname(message,multiple=True):
	files = nukeOriginalGetClipname(message,multiple=True)
	try:
		return [toRelativePath(f) for f in files]
	except:
		pass

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
	else:
		# Lazy checking, if "Render All" is invoked -- or nothing is selected -- 
		# assume we want all the Write nodes
		reply = nuke.ask("Render all Write nodes in comp?")
		if reply:
			nodes = nuke.allNodes("Write")
		else:
			return

	nodes = [n for n in nodes if n.Class() == "Write"]	# Double check that we actually have Write nodes

	if not nodes:
		nuke.message("No Write nodes to render")
		return

	if not ranges:
		ranges = "%i-%i" % (nuke.root().firstFrame(),nuke.root().lastFrame())

	if default_order:
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
				print "RENDERING: %s | %i-%i" % (name,t1,t2)
				nuke.execute(name,t1,t2)
	
	if RVPATH != None:
		rep = nuke.ask("Play in RV?")
		if rep:
			rv(nodes)

nuke.createNode = customCreateNode
nuke.selectedNodes = customSelectedNodes
nuke.getClipname = customGetClipname
nuke.getFilename = customGetClipname
nuke.executeMultiple = customExecuteMultiple

# -------------- LAZY SCRIPTING ---------------- #

def this():
	return nuke.selectedNode()
	
def these():
	return nuke.selectedNodes()

def val(obj,parm,value=None):
	if value:
		obj[parm].setValue(value)
		return obj
	else:
		return obj[parm].value()

def animate(obj,parm,curve):
	"""
	Animate parameters in the form:
		nk.animate(node,parameter,[ [frame1,(x,y,z)] , [frame2,(x,y,z)], [frame3,(x,y,z)] ])
	"""
	obj[parm].setAnimated()
	for animTuple in curve:
		[t,v] = animTuple
		try:
			for i,vv in enumerate(v):
				obj[parm].setValueAt(vv,t,i)
		except TypeError:
			obj[parm].setValueAt(v,t)

def dirr(k=None):
	"""
	Returns all callable methods of nuke that match the string k.
	If k is not given, returns everything.
	"""
	k = k if k else "."
	for nn in sorted([n for n in dir(nuke) if re.search(k,n,re.I)]):
		print nn

# -------------- PLAYING WITH OTHERS ---------------- #

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

def importMaya():
	
	shape_params = ["horizontalFilmAperture","verticalFilmAperture","focusDistance","focalLength"]
	trans_params = ["translateX","translateY","translateZ","rotateX","rotateY","rotateZ"]

	#path = nukeOriginalGetFilename("Select Maya Ascii file...","*.ma")
	#filein = open(path).readlines()

	filein = open("/Users/adrianloh/Desktop/test_baked.ma").readlines()
	
	user_cams = mayacam.get_cameras(filein)
	
	def maya2nuke_aperture(x,y):
		return x/(x/(y*25.4))

	for cam in user_cams:
		camShapeStrings = ["%s_%s"%(cam[0],p) for p in shape_params]
		camTransStrings = ["%s_%s"%(cam[1],p) for p in trans_params]
		animations = {}

		for string in camShapeStrings:
			anim_data = mayacam.get_animation_data(string,filein)
			if anim_data:
				label = string.split("_")[-1]
				animations[label] = anim_data

		for string in camTransStrings:
			anim_data = mayacam.get_animation_data(string,filein)
			if anim_data:
				label = string.split("_")[-1]
				animations[label] = anim_data

		if len(animations.keys()) == len(shape_params) + len(trans_params):
			knobs_args = "name %s rot_order XYZ" % cam[1].capitalize()
			camera = nukeOriginalCreateNode("Camera2",knobs=knobs_args,inpanel=False)

			w = nuke.root()['format'].value().width()
			h = nuke.root()['format'].value().height()

			translations = zip(animations['translateX'],animations['translateY'],animations['translateZ'])
			rotations = zip(animations['rotateX'],animations['rotateY'],animations['rotateZ'])
			animate(camera,'translate',[[i,v] for i,v in enumerate(translations)])
			animate(camera,'rotate',[[i,v] for i,v in enumerate(rotations)])

			hapertures = [maya2nuke_aperture(w,m) for m in animations['horizontalFilmAperture']]
			vapertures = [maya2nuke_aperture(h,m) for m in animations['verticalFilmAperture']]			
			animate(camera,'haperture',[[i,v] for i,v in enumerate(hapertures)])
			animate(camera,'vaperture',[[i,v] for i,v in enumerate(vapertures)])

			animate(camera,'focal',[[i,v] for i,v in enumerate(animations['focalLength'])])

def importBoujou_depracted():
	"""
	Import Boujou Maya
	Import Maya 4.0++ .ma files exported from Boujou. Will work only with
	scene files containing a single camera solve.
	"""
	path = nukeOriginalGetFilename("Select Maya Ascii file...","*.ma")
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
	camera = nuke.createNode("Camera2",knobs="rot_order XYZ",inpanel=False)
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

# -------------- NK AUTOLOADS FACELESS FUNCTIONS ---------------- #

def nk_align_horizontal():
	"""
	===
	"""
	align("horz")
	
def nk_align_vertical():
	"""
	||
	"""
	align("vert")

def nk_select_all_dependencies():
	"""
	Select all dependencies
	"""
	d = allDependencies(nuke.selectedNode())
	[n['selected'].setValue(True) for n in d]

# -------------- FACELESS FUNCTIONS ---------------- #

def nk_backburner():
	"""
	Backburner
	"""
	import shutil
	nuke.scriptSave()
	op = nuke.root()['name'].value()
	name = nuke.selectedNode().name()
	np = op+"%s.bburn"%name
	shutil.copy2(op,np)
	ranges = "-".join([str(int(f)) for f in nuke.selectedNode()['range'].value()])
	cmd = "%s -m %i -F %s -X %s -ix %s" % (NUKE_PATH,int(nuke.env['numCPUs']/2),ranges,name,np)
	print cmd
	
	def render():
		from nukescripts import utils
		print "Background rendering %s" % name
		Popen(cmd).wait()
		utils.executeInMainThread(nuke.toNode(name)['tile_color'].setValue,536805631) #TODO: This executes but doesn't refresh in the DAG
		utils.executeInMainThread(nuke.toNode(name)['postage_stamp'].setValue,True)
		utils.executeInMainThread(nuke.toNode(name)['reading'].setValue,True)
		print "Background rendering done! %s" % name
		os.remove(np)

	this = nuke.toNode(name)
	this['tile_color'].setValue(1996488704)
	this['postage_stamp'].setValue(False)
	this['reading'].setValue(False)
	r = this['range'].value()
	i,o = int(r[0]),int(r[1])+1
	try:
		[os.remove(nuke.filename(this)%i) for i in range(i,o) if os.path.exists(nuke.filename(this)%i)]
		T = threading.Thread(None,render)
		T.start()
	except:
		nuke.message("Hmmm, try again....")
	
def setSwitchRoute():
	switches = [(n.name(),int(n['which'].value())) for n in nuke.allNodes("Switch")]
	state = " ".join([n[0]+" "+str(n[1]) for n in switches])
	nuke.thisNode()['switchroute'].setValue(state)

def batchChangeSelected():
	"""
	Change parameters command-line style in GUI
	"""
	input = nuke.getInput("""Eg. translate=[0,1,3] / rotate=90.0 / label="some text" """)
	try:
		param,value = input.split("=")
		[n[param].setValue(eval(value)) for n in nuke.selectedNodes()]
	except:
		pass

def file(oper):
	"""
	Enables copying/moving source files of Read/Write nodes.
	For Writes, the nodes should have the custom parameters:
		BOOLEAN_KNOB:'source_update'
		UV_KNOB:'range'
	Dialog box enables choosing a destination directory 
	to relocate/copy files. Optionally, if a new name is entered,
	the files will be moved/copied and finally renamed.
	"""
	import shutil
	n = nuke.selectedNode()
	first = last = None
	if n.Class() == "Read":
		first = n['first'].value()
		last = n['last'].value()
	elif n.Class() == "Write":
		try:
			first,last = n['range'].value()
		except NameError:
			attach_range(n)
			nuke.message("Please set range and try again")
	else:
		pass
	if first and last:
		old_path = os.path.dirname(nuke.filename(n))
		new_path = nukeOriginalGetFilename("Choose a new location...")
		rename = True if re.search(r'%0\dd',new_path) else False
		get_path = lambda p: new_path%i if rename else new_path
		files = [(nuke.filename(n)%i,get_path(i)) for i in range(first,last+1) if os.path.exists(nuke.filename(n)%i)]
		if oper==1:
			mainMsg = "Relocating files..."
			subMsg = "Moved"
		else:
			mainMsg = "Copying files..."
			subMsg = "Copied"
		task = nuke.ProgressTask(mainMsg)
		T = len(files)
		good = 0
		for (i,f) in enumerate(files):
			op,np = f[0],f[1]
			print "%s --> %s" % (op,np)
			try:
				shutil.copy2(op,np)
				good+=1
				task.setMessage("%s:%s"%(subMsg,op))
				x = int((i/float(T)*100))
				task.setProgress(x)
			except:
				break
		if good == T:
			if oper==1:
				try:
					[os.remove(f[0]) for f in files]
					nuke.message("All files were relocated")
				except:
					nuke.message("All files were copied but originals could not be removed")
			else:
				nuke.message("All files were copied")
			if n['update_source'].value():
				filename = os.path.split(nuke.filename(n))[-1]
				set_new_path = rename and toRelativePath(new_path) or toRelativePath(new_path+filename)
				n['file'].setValue(set_new_path)
	else:
		pass

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

# -------------- STUFF THEY SHOULD'VE THOUGHT OF ---------------- #

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
		camera = nuke.nodes.Camera2()
		val(camera,"translate",[0,0,1])
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
	SUPPORTED_FORMATS = "tif tiff tif16 tiff16 ftif ftiff tga targa rla xpm yuv avi cin dpx exr gif \
						hdr hdri jpg jpeg iff png png16 mov r3d raw psd sgi rgb rgba sgi16 pic".split(" ")
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
	Connect multiple reads into multiple Switches
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
		comp_dur = nuke.root().lastFrame()-nuke.root().firstFrame() # Duration of comp
		r = [nn for nn in allDependencies(n) if nn.Class() == "Read"]
		if r:
			clip_dur = r[0]['last'].value()-r[0]['first'].value()
			x = comp_dur - clip_dur
			if x == 0 or x > 0:
				maxTime = clip_dur*-1
			elif x < 0:
				maxTime = x
			else:
				maxTime = random.randrange(-1000,0)
		n['time_offset'].setValue(random.randrange(maxTime,0))

	for switch in nukeOriginalSelectedNodes("Switch"):
		max = switch.inputs()
		switch['which'].setValue(random.randrange(0,max))

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
		if target.inputs() <= i:
			target.setInput(i,n)
		else:
			target.setInput(target.inputs(),n)

def nk_color_with_tile():
	"""
	Color with tile
	"""
	nk_color_tiles(True)

def nk_color_tiles(src=False):
	"""
	Color nodes
	"""
	nodes = nuke.selectedNodes()
	color = nodes[0]['tile_color'].value() if src else nuke.getColor()
	dst = nodes[1:]	if src else nodes
	[n['tile_color'].setValue(color) for n in dst]
	
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
	Paste into selected
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

def nk_clear_from_selected_node():
	"""
	Batch deanimate selected nodes.
	"""
	parm = nuke.getInput("Parameter to deanimate?")
	[n[parm].clearAnimated() for n in nuke.selectedNodes()]