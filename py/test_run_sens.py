import run_sens
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

# the above horrid construction sets up all of the input files and objects

correct_nspec = 3
correct_sens_str = 'echo "lris_sensstd,'
correct_sens_str += "'%s'" % stdfile
correct_sens_str += ", CLOBBER=1, STD_OBJ=%d" % (correct_nspec)
correct_sens_str += '" | $IDL_DIR/bin/idl >& sens.log'
correct_sens_str += '\n'
correct_executable = os.path.join(os.getcwd(),testdir,testfiledir,"sens.csh")


# first, select the spectrum
nspec= run_sens.select_spec(stdframe,stdhdu)
if nspec == correct_nspec:
    print "success in select_spec"
else:
    print "failed in select_spec", nspec

# second
# make the sensstd str
sens_str = run_sens.lrissenstd_str(stdfile,stdframe,correct_nspec)
if sens_str == correct_sens_str :
    print "success in lrissensstd_str"
else:
    print "failed in lrissenstd_str", sens_str

# third
# make exceutable
executable = run_sens.writesens_str(correctplan,os.getcwd(),correct_sens_str,idlenv)
if executable == correct_executable:
    print "success in writesens_str"
else:
    print "failed in writsens_str", executable

msg = run_sens.run_sensstd(correctplan,os.getcwd(),idlenv)
if msg == "":
    print "success in run_sensstd"
else:
    print "failed in run_sensstd", msg


