import run_sens
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

def cleanup_sensoutput(path):
    if os.path.isdir(path):
        files = glob.glob(path + "/sens*")
        for f in files:
            os.remove(f)

# the above horrid construction sets up all of the input files and objects
cwd = os.getcwd()
correct_nspec = 4
correct_sens_str = '$IDL_DIR/bin/idl -e "lris_sensstd,'
correct_sens_str += "'%s'" % stdfile
correct_sens_str += ", CLOBBER=1, STD_OBJ=%d" % (correct_nspec)
correct_sens_str += '" >& sens.log'
correct_sens_str += '\n'
correct_executable = os.path.join(cwd,testdir,testfiledir,"sens.csh")

print "1 - select_spec"
# first, select the spectrum
nspec= run_sens.select_spec(stdframe,stdhdu)
if nspec == correct_nspec:
    print "Success in select_spec"
else:
    print "FAILED in select_spec", nspec, "does not equal",correct_nspec

# second
# make the sensstd str
print "2 - lrissenstd_str"
sens_str = run_sens.lrissenstd_str(stdfile,stdframe,correct_nspec)
if sens_str == correct_sens_str :
    print "Success in lrissensstd_str"
else:
    print "FAILED in lrissenstd_str", sens_str, "does not equal", correct_sens_str

# third
# make exceutable
print "3 - writesens_str"
executable = run_sens.writesens_str(correctplan,cwd,correct_sens_str,idlenv)
if executable == correct_executable:
    print "Success in writesens_str"
else:
    print "FAILED in writsens_str", executable, "does not equal",correct_executable

print "4 - run_sensstd"
msg = run_sens.run_sensstd(correctplan,cwd,idlenv)
idloutput = os.path.isfile(os.path.join(cwd,correctplan.finalpath,"Science","sens.log"))

if idloutput and msg == "":
    print "Success in run_sensstd"
else:
    print "FAILED in run_sensstd", msg

cleanup_sensoutput(os.path.join(cwd,correctplan.finalpath,"Science"))
