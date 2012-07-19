# Copyright (c) 2009 The Foundry Visionmongers Ltd.  All Rights Reserved.

# This file is sourced by Nuke whenever it is run, either
# interactively or in order to run a script. The main purpose is
# to setup the plugin_path and to set variables used to generate
# filenames.

from __future__ import with_statement

import sys
import os.path
import nuke
# --------------- FACILITY WIDE PLATFORM DEPENDENT ----------------#

os.environ['JOBS'] = "/mnt/gomorrah/jobs"

# ---------------------------------------------------------------- #

import nk_reactor
import nk_switchroute
import nk_fileops
import nk_callbacks
import nk_gui
import nk_overrides
import nk_customize

nuke.addFormat("1280 720 0 0 1280 720 1 720p")
nuke.knobDefault("Root.format","720p")

# ---------------------------------------------------------------- #
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


