from nukeDB import *
from bottle import route, run, view, send_file, redirect, abort, request, response
from subprocess import Popen
import os

os.environ['COMMON'] = "G:\\jobs\\temp"

@route('/')
def index():
    return 'Hello World!'

@route('/projects')
@view('list_projects')
def list_projects():
	items = Projects.get()
	return dict(title="Running Projects",items=items)

@route('/projects/:pid/shots')
@view('list_shots')
def list_shots(pid):
	pname = Projects.get(id=pid)[0].name
	items = Shots.get(project_id=pid).order_by("id")
	return dict(title="Shotlist: %s" % pname,items=items)

@route('/projects/:pid/:sid/nuke')
@view('list_versions')
def list_versions(pid,sid):
	pname = Projects.get(id=pid)[0].name
	items = Nuke_versions.get(project_id=pid,shot_id=sid).order_by("modified","DESC")
	title = "Nuke Revision History : %s >> %s" % (pname,sid)
	return dict(title=title,items=items)

@route('/static/:filename')
def static_file(filename):
    send_file(filename, root='/Users/adrianloh/.nuke/static/')

@route('/images/:filename')
def static_file(filename):
    send_file(filename, root='/Users/adrianloh/.nuke/static/images/')

def fileout(vid):
	v = Nuke_versions.get(id=vid)[0]
	filename = "%s_%s_%s_%s.%s.nk" % (v.title,v.project_id,v.shot_id,v.versionMajor,v.versionMinor)
	path = os.path.join(os.environ['COMMON'],filename)
	f = open(path,'w')
	f.write(v.script)
	f.close()
	return [path,v]
	
@route('/render/:vid')
def render_comp(vid):
	path,v = fileout(vid)
	return "Rendering %s | %s-%s | %s.%s" % (v.title,v.project_id,v.shot_id,v.versionMajor,v.versionMinor)

@route('/edit/:vid')
def edit_comp(vid):
	path,v = fileout(vid)
	print path
	print v
	Popen("/bin/nuke.cmd %s"%path)
	return "Editing %s | %s-%s | %s.%s" % (v.title,v.project_id,v.shot_id,v.versionMajor,v.versionMinor)

run(host='127.0.0.1', port=8000)
