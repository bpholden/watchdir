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

def writesens_str(plan,datapath,sens_str,idlenv):
    runpath = os.path.join(datapath,plan.finalpath,"sens.csh")
    executable = Planutil.writerunstr(runpath,datapath,sens_str,idlenv)
    return(runpath)

def select_spec(frame,hdu):

    tabhdr = hdu[5].header
    tabdata = hdu[5].data
    numspec = tabhdr['NAXIS2']

    if re.match("lrisred",frame.instrument.name):
        slitb_xpos = 2200
    else:
        slitb_xpos = 2200

    goodposes = []
    pkfluxes = []
    
    for specnum in range(numspec):
        pos = numpy.median(tabdata[specnum]['XPOS'])
        pos *= frame.xbinning # compare to fixed position with fixed offset
        if pos > slitb_xpos - 50 and pos < slitb_xpos + 50:
            goodposes.append(specnum)
            pkfluxes.append(tabdata[specnum]['PEAKFLUX'])

    maxval = -1
    maxspec = -1
    for i,specnum in enumerate(goodposes):
        if pkfluxes[i] > maxval:
            maxspec = specnum
            maxval = pkfluxes[i]

    return(maxspec)

def lrissenstd_str(stdfile,stdframe,spec):

    sens_str = 'echo "lris_sensstd,'
    sens_str += "'%s'" % (stdfile)
    sens_str += ', CLOBBER=1,'
    if stdframe.instrument.name == "lrisblue":
        sens_str += " STD_OBJ=%d" % (spec)
    else:
        sens_str += " STD_OBJ=%d" % (spec)
    sens_str += '" | $IDL_DIR/bin/idl >& sens.log'
    sens_str += "\n"

    return(sens_str)


def run_sensstd(plan,datapath,idlenv):

    stdframe = ""
    for frame in plan.frames:
        if frame.type == "Trace":
            #found the standard
            stdframe = frame
            
        
    msg = ""
    outputpath = os.path.join(datapath,plan.finalpath,'Science')

    if not os.environ.has_key('LRIS_THRU'):
        os.environ['LRIS_THRU'] = datapath
    
    stdfile = "std-" + stdframe.name
    if not re.search('gz\Z',stdfile) :
        stdfile += '.gz'
    stdfile = os.path.join(outputpath,stdfile)

    try:
        hdu = pyfits.open(stdfile)
        sens_str = lrissenstd_str(stdfile,stdframe,select_spec(stdframe,hdu))
        executable = writesens_str(plan,datapath,sens_str,idlenv)

        cwd = os.path.dirname(executable)
        outputfile = open(os.path.join(cwd,'sensprocessoutput'),"wb")
        erroroutputfile = open(os.path.join(cwd,'sensprocesserroroutput'),"wb")

        curproc = subprocess.Popen(executable,
                                   cwd=cwd,stdout=outputfile,
                                   stderr=erroroutputfile)
        curproc.wait()

    except IOError:
        msg = "cannot open std file %s: %s" % (stdfile,IOError)

    return msg
    
