from reactorDB import *
from bottle import route, run, view, send_file, redirect, abort, request, response, debug
from subprocess import Popen,PIPE
import os
import base64
import re

debug(True)
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

	def get_scriptname_in_rar(path_to_rar):
		return re.findall("(.+\.nk)",Popen("rar l %s" % path_to_rar,stdout=PIPE).stdout.read())[0].strip()

	v = Nuke_versions.get(id=vid)[0]
	rar_name = "%s_%s_%s_%s.%s.rar" % (v.title,v.project_id,v.shot_id,v.versionMajor,v.versionMinor)
	path_to_rar = os.path.join(os.environ['COMMON'],rar_name)
	print path_to_rar
	f = open(path_to_rar,'wb')
	f.write(base64.decodestring(v.script))
	f.close()
	script_name = get_scriptname_in_rar(path_to_rar)
	Popen("rar x -y %s %s" % (path_to_rar,os.environ['COMMON']))
	path_to_script = os.path.join(os.environ['COMMON'],script_name)
	return [path_to_script,v]
	
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

run(host='127.0.0.1', port=80)