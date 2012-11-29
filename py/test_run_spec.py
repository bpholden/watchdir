import run_spec
from model import Frame, Plan, Instrument, Pipeline
import types
import time
import glob
import Frameutil
import Planutil
import LRISFrameutil
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
correct_executable = 'idl -e long_reduce\n'
correct_planfile = "r101216_0093/plan.par"

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
                #        os.rmdir(os.path.join(testdir,plan.finalpath,'Science'))
        files = glob.glob(os.path.join(testdir,plan.finalpath) + '/*')
        for f in files:
            if os.path.isfile(f):
                os.unlink(f)
            elif os.path.isdir(f):
                os.rmdir(f)

        os.rmdir(os.path.join(testdir,plan.finalpath))
        os.rmdir(os.path.dirname(os.path.join(testdir,plan.finalpath)))
    return
    

# first - linkedreduced returns a Boolean and a msg, the Boolean is
# true for Success

print "Testing run_spec.py"        
        
print "1 - linkreduced"
cleanup_calfile(testcalfile,os.path.join(testdir,testfiledir))
# the above line cleans up old cal files, in case the file
# was left in the directory 
# 

retval,msg = run_spec.linkreduced(calframe,correctplan,"wave-",os.getcwd())
if retval:
	print "Success in linkreduced"
else:
	print "FAILED in linkreduced, %s" % msg

retval, msg = run_spec.linkreduced(calframe,correctplan,"wave-",os.getcwd())
if not retval:
	print "Success in linkreduced (fail test) %s " % msg
        cleanup_calfile(testcalfile,os.path.join(testdir,testfiledir))
else:
	print "FAILED in linkreduced (fail test) %s " % msg
        cleanup_calfile(testcalfile,os.path.join(testdir,testfiledir))

# second
print "2 - find_calibframes"
match,msg = run_spec.find_calibframes(stdframe,correctplan,calframes,os.getcwd())
if match[0] == calframe :
	print "Success in find_calibframes"
	correctplan.frames.append(match[0])
	if os.path.isfile(os.path.join(testdir,testfiledir,"wave-"+testcalfile)):
		os.unlink(os.path.join(testdir,testfiledir,"wave-"+testcalfile))
		cleanup_savfile(testcalfile,os.path.join(testdir,testfiledir))
else:
	print "FAILED in find_calibframes %s " % msg

#
# third
print "3 - find_pipeline"
pipe = run_spec.find_pipeline(stdframe,[xidlpipe])
if pipe == xidlpipe:
	print "Success in find_pipeline"
else:
	print "FAILED in find_pipeline"

# fourth
print "4 - find_if_okstar"        
msg = run_spec.find_if_okstar(stdframe.target,stars)
if msg == correct_msg:
	print "Success in find_if_okstar"
else:
	print "FAILED in find_if_okstar", msg
msg = run_spec.find_if_okstar("",stars)
if msg == correct_failstar_msg:
	print "Success in find_if_okstar (fail test)"
else:
	print "FAILED in find_if_okstar (fail test)", msg

# fifth
print "5 - check_if_std_frame"                
msg = run_spec.check_if_std_frame(stdframe,stars)
if msg == correct_msg:
	print "Success in check_if_std_frame"
else:
	print "FAILED in check_if_std_frame", msg

	
print "6 - genplanflags"                
# sixth
planflags = run_spec.genplanflags(correctplan)
if planflags == correct_planflags:
	print "Success in genplanflags"
else:
	print "FAILED in genplanflags", planflags

# seventh
print "7 - writeplan"                        
executable = run_spec.writeplan(correctplan,os.getcwd(),idlenv)
if correct_executable in executable and os.path.isfile(os.path.join(testdir,correct_planfile)):
	print "Success in writeplan"
        cleanup_calfile(testcalfile,os.path.join(testdir,testfiledir))
elif executable == correct_executable and not os.path.isfile(os.path.join(testdir,correct_planfile)): 
	print "FAILED in writeplan, no planfile written, %s" % correctplan
        cleanup_calfile(testcalfile,os.path.join(testdir,testfiledir))
elif executable != correct_executable and os.path.isfile(os.path.join(testdir,correct_planfile)): 
	print "FAILED in writeplan, wrong executable string, %s" % executable
        cleanup_calfile(testcalfile,os.path.join(testdir,testfiledir))
else:
	print "FAILED in writeplan"

# eight
print "8 - buildandrunplan"   
flag = dict(redo=True)
msg,retplan = run_spec.buildandrunplan(testfile,testdir,testdir,pipes,calframes,stars,idlenv,flag)
if msg == '' and os.path.isfile(os.path.join(testdir,retplan.finalpath,"longreduce.log")):
	print "Success in buildandrunplan"
        cleanup_plandir(retplan,testfile,testdir)
else:
	print "FAILED in buildandrunplan", retplan, msg
        cleanup_plandir(retplan,testfile,testdir)

# nine
msg,retplan = run_spec.buildandrunplan("",testdir,testdir,pipes,calframes,stars,idlenv,flag)
if retplan == False:
	print "Success in buildandrunplan (bad frame) - Previous line should have a \"cannot open\" error"
else:
	print "FAILED in buildandrunplan (bad frame)", msg

msg,retplan = run_spec.buildandrunplan(testcalfile,testdir,testdir,pipes,calframes,stars,idlenv,flag)
if retplan == False:
	print "Success in buildandrunplan (not a std frame)"
else:
	print "FAILED in buildandrunplan (not a std frame)", msg
