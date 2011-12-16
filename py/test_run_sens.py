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

testfile = "r101216_0093.fits.gz"
testdir = "test_data"
stdfile = "std-r101216_0093.fits.gz"


correct_nspec = 4
correct_sens_str = 'echo "lris_sensstd,'
correct_sens_str += "'%s'" % stdfile
correct_sens_str += ", CLOBB=1, WVTIME=[6000., 7000., 8000., 9000., 10000.], STD_OBJ=%d" % (correct_nspec)
correct_sens_str += '" | $IDL_DIR/bin/idl >& sens.log'
correct_sens_str += '\n'
correct_executable = os.path.join(os.getcwd(),testdir,"sens.csh")

# first input stuff
try:
    hdr = pyfits.getheader(os.path.join(testdir,testfile),0)
    instrument = Frameutil.find_instrument_name(hdr)
    obsdate,obstime = Frameutil.getobsdate(hdr)
    nmsg,stdframe = Frameutil.addframe(testfile,hdr,obsdate,obstime,testfile,testdir,instrument)
    xidlpipe = Pipeline(display_name="XIDL for LRIS",
                        runstr=u'echo \"long_reduce,\'%s\'" | $IDL_DIR/bin/idl  > & longreduce.log\n'
        )
    xidlpipe.instrument=stdframe.instrument
    xidlpipe.framelist="Object Line IntFlat Flat DmFlat Trace"

    plan = Planutil.buildplan(stdframe,"test.plan",testdir,xidlpipe)
    stdhdu = pyfits.open(os.path.join(testdir,stdfile))

    # first, select the spectrum
    nspec= run_sens.select_spec(stdframe,stdhdu)
    if nspec == correct_nspec:
        print "success",nspec
    else:
        print "test failed at select_spec", nspec

    # second
    # make the sensstd str
    sens_str = run_sens.lrissenstd_str(stdfile,stdframe,correct_nspec)
    if sens_str == correct_sens_str :
        print "success",sens_str
    else:
        print "test failed on lrissenstd_str", sens_str

    # third
    # make exceutable
    executable = run_sens.writesens_str(plan,os.getcwd(),correct_sens_str,testdir)
    if executable == correct_executable:
        print "success", executable
    else:
        print "test failed on writsens_str", executable

    

except :

    print "Most likely the test file and test dir are incorrectly specified or do not exist"
