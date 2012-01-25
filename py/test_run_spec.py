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
correct_failstar_msg = 'Frame observed  which is not in star list'
correct_planflags  = "{}"
correct_executable = os.path.join(os.getcwd(),correctplan.finalpath, correctplan.display_name+".csh")

def cleanup_savfile(testcalfile,testcalpath):
    savfile = "wave-"+testcalfile
    savfile = re.sub(".fits(.gz)?",".sav",savfile)
    if os.path.isfile(os.path.join(testcalpath,savfile)):
        os.unlink(os.path.join(testcalpath,savfile))

def cleanup_calfile(testcalfile,testcalpath):
    cleanup_savfile(testcalfile,testcalpath)
    if os.path.isfile(os.path.join(testcalpath,testcalfile)):
        os.unlink(os.path.join(testcalpath,testcalfile))
    if re.search(".fits.gz",testcalfile):
        testcalfile = re.sub("\.gz","",testcalfile)
        testcalfile = "wave-"+testcalfile
        if os.path.isfile(os.path.join(testcalpath,testcalfile)):
            os.unlink(os.path.join(testcalpath,testcalfile))


def cleanup_plandir(plan,testfile,testdir):

    if plan:
        # os.unlink(os.path.join(os.path.abspath(plan.finalpath),testfile))
        sfiles = glob.glob(os.path.join(testdir,plan.finalpath) + '/Science/*')
        for sf in sfiles:
            if os.path.isfile(sf):
                os.unlink(sf)
        os.rmdir(os.path.join(testdir,plan.finalpath,'Science'))
        files = glob.glob(os.path.join(testdir,plan.finalpath) + '/*')
        for f in files:
            if os.path.isfile(f):
                os.unlink(f)

        os.rmdir(os.path.join(testdir,plan.finalpath))
        os.rmdir(os.path.dirname(os.path.join(testdir,plan.finalpath)))

    

# first - linkedreduced returns a Boolean, true for success
if run_spec.linkreduced(calframe,correctplan,"wave-",os.getcwd()):
	print "success in linkreduced"
else:
	print "failed in linkreduced"

if not run_spec.linkreduced(calframe,correctplan,"wave-",os.getcwd()):
	print "success in linkreduced (fail test)"
	if os.path.isfile(os.path.join(testdir,testfiledir,"wave-"+testcalfile)):
		os.unlink(os.path.join(testdir,testfiledir,"wave-"+testcalfile))
		cleanup_savfile(testcalfile,os.path.join(testdir,testfiledir))
else:
	print "failed in linkreduced (fail test)"
	if os.path.isfile(os.path.join(testdir,testfiledir,"wave-"+testcalfile)):
		os.unlink(os.path.join(testdir,testfiledir,"wave-"+testcalfile))
		cleanup_savfile(testcalfile,os.path.join(testdir,testfiledir))

# second

match,msg = run_spec.find_calibframes(stdframe,correctplan,calframes,os.getcwd())
if match[0] == calframe and msg == "No flats for frame r101216_0093.fits.gz":
	print "success in find_calibframes"
	correctplan.frames.append(match[0])
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
if msg == correct_failstar_msg:
	print "success in find_if_okstar (fail test)"
else:
	print "failed in find_if_okstar (fail test)", msg

# fifth
msg = run_spec.check_if_std_frame(stdframe,stars)
if msg == correct_msg:
	print "success in check_if_std_frame"
else:
	print "failed in check_if_std_frame", msg

	
# sixth
planflags = run_spec.genplanflags(correctplan)
if planflags == correct_planflags:
	print "success in genplanflags"
else:
	print "failed in genplanflags", planflags

# seventh
executable = run_spec.writeplan(correctplan,os.getcwd(),idlenv)
if executable == correct_executable:
	print "success in writeplan"
        cleanup_calfile(testcalfile,os.path.join(testdir,testfiledir))

else:
	print "failed in writeplan", executable

# eight
curproc,msg,retplan = run_spec.buildandrunplan(testfile,testdir,testdir,pipes,calframes,stars,idlenv)
if retplan.display_name == correctplan.display_name:
	print "success in buildandrunplan"
        cleanup_plandir(retplan,testfile,testdir)
else:
	print "failed in buildandrunplan", retplan, msg
        cleanup_plandir(retplan,testfile,testdir)

curproc,msg,retplan = run_spec.buildandrunplan("",testdir,testdir,pipes,calframes,stars,idlenv)
if retplan == False:
	print "success in buildandrunplan (bad frame) - Previous line should have a \"cannot open\" error"
else:
	print "failed in buildandrunplan (bad frame)", msg

curproc,msg,retplan = run_spec.buildandrunplan(testcalfile,testdir,testdir,pipes,calframes,stars,idlenv)
if retplan == False:
	print "success in buildandrunplan (not a std frame)"
else:
	print "failed in buildandrunplan (not a std frame)", msg
