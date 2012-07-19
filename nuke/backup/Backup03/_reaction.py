from bottle import route, run, view, send_file, redirect, abort, request, response, debug
from subprocess import Popen,PIPE
import os
import base64
import re
import json

from couchdb import *
db = Database("http://127.0.0.1/nuke_reactor")

@route('/')
@view('index')
def index():
	send_file("index.html",root='/Users/adrianloh/.nuke/static/')

@route('/getjson')
def getjson():
	db.query
	return h

@route('/static/:filename')
def static_file(filename):
    send_file(filename, root='/Users/adrianloh/.nuke/static/')

run(host='127.0.0.1', port=80, reloader=True)