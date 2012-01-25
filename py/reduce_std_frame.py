#!/usr/bin/env python 
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
from run_sens import *
from run_spec import *
from watchdir_setup import * # yes, I KNOW, I KNOW!



# -- main 

lris_thru = "."
if os.environ.has_key('LRIS_THRU'):
    lris_thru = os.environ['LRIS_THRU']

parser = optparse.OptionParser(description='Reduce a LRIS standard observation, output the same as watchdir.py,\nrequires make_filelist.py and prep_dirs.py be run.')
parser.add_option('-f','--filepath', dest='filedir', action='store',type="string",default="",
                   help='Path observation to be reduced.')
parser.add_option('-s','--stddir', dest='stddir', action='store',type="string",default=lris_thru,
                   help='Parent directory of output of longreduce')
parser.add_option('-k','--kroot', dest='kroot', action='store',type="string",default='/kroot/starlists/',
                   help='Starlist parent directory')
parser.add_option('-t','--starlist', dest='starlist', action='store',type="string",default='0000_Throughput_standards.list',
                   help='Starlist file')
parser.add_option('-c','--caldir', dest='caldir', action='store',type="string",default=".",
                   help='Directory containing calibrations')
parser.add_option('-l','--callist', dest='callist', action='store',
                   default="calibration.list",type="string",
                   help='File in calibration directory containing list of calibrations')
parser.add_option('-i','--idlenv', dest='idlenv', action='store',
                   default="idlenv",type="string",
                   help='path to idlenv, file that contains all of the environment definitions required')
parser.add_option('-r','--redo', dest='redo', action='store_true',
                   help='Will rereduce a standard observation, otherwise will skip')
(options,args) = parser.parse_args()

# Now make the paths more useful

rootfiledir = os.path.abspath(options.filedir) # get the absolute path - so we can use this later for path manipulations
stddir = os.path.abspath(options.stddir) # get the absolute path - so we can use this later for path manipulations
caldir = os.path.abspath(options.caldir) # get the absolute path - so we can use this later for path manipulations
callist = os.path.abspath(os.path.join(options.caldir,options.callist)) # get the absolute path - so we can use this later for path manipulations
starlist = os.path.abspath(os.path.join(options.kroot,options.starlist)) # get the absolute path - so we can use this later for path manipulations
idlenv = os.path.abspath(options.idlenv)

flag = dict(redo=options.redo)

calibs = makecallist(callist,caldir,stddir)
if not calibs:
    print "file %s cannot be opened for reading" % (os.path.join(caldir,callist))
    sys.exit()

stars,msg = makestarlist(starlist)
if not stars:
    print msg
    sys.exit()
    

pipelist = prep_pipelines()


for infile in args:

    if not rootfiledir:
        filename = os.path.basename(infile)
        filedir = os.path.abspath(os.path.dirname(infile))
    else:
        filename = os.path.basename(infile)
        filedir = os.path.abspath(os.path.join(rootfiledir,os.path.dirname(infile)))
                            
    newproc,msg,plan = buildandrunplan(filename,filedir,stddir,pipelist,calibs,stars,idlenv,flag)
    if newproc:
        print "Running reduction, now we wait." 
        time.sleep(10)

        while newproc.poll() == None:
            time.sleep(10)

        print "%s has finished" % (filename)
        msg = run_sensstd(plan,stddir,idlenv)
        print msg

    else:
        print msg
        print "%s appears to be have an issue" % (infile)

            
