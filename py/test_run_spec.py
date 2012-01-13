import run_spec
from model import Frame, Plan, Instrument, Pipeline
import types
import time
import glob
import Frameutil
import Planutil
import LRISFrameutil
import XIDLLongPlanutil
import pyfits
import numpy
import os, os.path
import re
import datetime
import subprocess
import sys
import optparse
import stat
from test_setup import *


correct_msg = ""
correct_planflags  = "{}"

def cleanup_savfile(testcalfile,testcalpath):
        savfile = "wave-"+testcalfile
        if re.search(".fits.gz",savfile):
            savfile = re.sub(".fits.gz",".sav",savfile)
            os.unlink(os.path.join(testcalpath,savfile))
        else:
            savfile = re.sub(".fits",".sav",savfile)
            os.unlink(os.path.join(testcalpath,savfile))


# first - linkedreduced returns a Boolean, true for success
if run_spec.linkreduced(calframe,plan,"wave-",os.getcwd()):
	print "success in linkreduced"
else:
	print "failed in linkreduced"

if not run_spec.linkreduced(calframe,plan,"wave-",os.getcwd()):
	print "success in linkreduced"
	if os.path.isfile(os.path.join(testdir,testfiledir,"wave-"+testcalfile)):
		os.unlink(os.path.join(testdir,testfiledir,"wave-"+testcalfile))
		cleanup_savfile(testcalfile,os.path.join(testdir,testfiledir))
else:
	print "failed in linkreduced"

# second

match,msg = run_spec.find_calibframes(stdframe,plan,calframes,os.getcwd())
if match[0] == calframe and msg == "No flats for frame r101216_0093.fits.gz":
	print "success in find_calibframes"
	plan.frames.append(match[0])
	if os.path.isfile(os.path.join(testdir,testfiledir,"wave-"+testcalfile)):
		os.unlink(os.path.join(testdir,testfiledir,"wave-"+testcalfile))
		cleanup_savfile(testcalfile,os.path.join(testdir,testfiledir))
else:
	print "failed in find_calibframes"

#
# third
pipe = run_spec.find_pipeline(stdframe,[xidlpipe])
if pipe == xidlpipe:
	print "success in find_pipeline"
else:
	print "failed in find_pipeline"

# fourth
msg = run_spec.find_if_okstar(stdframe.target,stars)
if msg == correct_msg:
	print "success in find_if_okstar"
else:
	print "failed in find_if_okstar", msg
msg = run_spec.find_if_okstar("",stars)
if not msg == correct_msg:
	print "success in find_if_okstar"
else:
	print "failed in find_if_okstar", msg

# fifth
msg = run_spec.check_if_std_frame(stdframe,stars)
if msg == correct_msg:
	print "success in check_if_std_frame"
else:
	print "failed in check_if_std_frame", msg

	
# sixth
planflags = run_spec.genplanflags(plan)
if planflags == correct_planflags:
	print "success in genplanflags"
else:
	print "failed in genplanflags", planflags
