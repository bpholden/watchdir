#!/usr/bin/env python 
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

from FileConfig import FileConfig
import run_sens 
import run_spec 
import watchdir_setup

def setup_options(options,fileconfig=None):


    # if there is a fileconfig, we overwrite the values
    if fileconfig:
        fcconfig = fileconfig.return_config()

        for key in fcconfig.keys():
            setattr(options,key,fcconfig[key])
            
    watchdir = os.path.abspath(options.watchdir) # get the absolute path - so we can use this later for path manipulations
    stddir = os.path.abspath(options.stddir) # get the absolute path - so we can use this later for path manipulations
    caldir = os.path.abspath(options.caldir) # get the absolute path - so we can use this later for path manipulations
    callist = os.path.abspath(os.path.join(options.caldir,options.callist)) # get the absolute path - so we can use this later for path manipulations
    starlist = os.path.abspath(os.path.join(options.kroot,options.starlist)) # get the absolute path - so we can use this later for path manipulations
    idlenv = os.path.abspath(options.idlenv)
    idlenv = os.path.abspath(options.logfilename)

    

    return watchdir,stddir,caldir,callist,starlist,idlenv,logfilename


# -- main 

lris_thru = "."
if os.environ.has_key('LRIS_THRU'):
    lris_thru = os.environ['LRIS_THRU']

parser = optparse.OptionParser(description='Watch a directory for LRIS standard observations, requires make_filelist.py and prep_dirs.py be run.')
parser.add_option('-w','--watchdir', dest='watchdir', action='store',type="string",default=".",
                   help='Directory to watch for standard observations')
parser.add_option('-s','--stddir', dest='stddir', action='store',type="string",default=lris_thru,
                   help='Parent directory of output of longreduce, the data reduction will be done in a subdirectory of this directory')
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
parser.add_option('-g','--logfile',dest='logfilename', action='store',
                  default="",type="string",
                  help='filename of logfile, this logs watchdir messages and output')

parser.add_option('-f','--file', dest='configfile', action='store',
                   default=None,type="string",
                   help="A configuration file containing values. Configuration values will override those set by flags")

(options,args) = parser.parse_args()

if options.configfile:
    # this was set, so we try to open it.
    fileconfig = FileConfig(filename=options.configfile)
else:
    fileconfig = None
    
watchdir,stddir,caldir,callist,starlist,idlenv,logfilename = setup_options(options,fileconfig)

# Now make the paths more useful

flag = dict(redo=False)

calibs = watchdir_setup.makecallist(callist,caldir,stddir)
if not calibs:
    print "file %s cannot be opened for reading" % (os.path.join(caldir,callist))
    sys.exit()

stars,msg = watchdir_setup.makestarlist(starlist)
if not stars:
    print msg
    sys.exit()
    
pathlist=['done']
watchdir_setup.prepdirs(os.path.join(watchdir),pathlist)

pipelist = watchdir_setup.prep_pipelines()

numjobs = 0
proclist = []
planlist = []

logfile = watchdir_setup.startlog(logfilename=logfilename)

logfile.write("watchdir = %s\n" % watchdir)
logfile.write("stddir = %s\n" % stddir)
logfile.write("caldir = %s\n" % caldir)
logfile.write("callist = %s\n" % callist)
logfile.write("starlist = %s\n" % starlist)
logfile.write("idlenv = %s\n" % idlenv)

while True:

    todolist = glob.glob(os.path.join(watchdir,'*.fits'))

    # first stuff the queue
    # this ends when either the queue is full or the todo list is empty
    while(len(todolist)):
        logfile.write("New files found:\n")
        logfile.write(" ".join(todolist) + "\n")
        filename = todolist.pop()
        logfile.write("Starting %s\n" % filename)
        
        msg,plan = run_spec.buildandrunplan(filename,watchdir,stddir,pipelist,calibs,stars,idlenv,flag)
        if msg == '':
            logfile.write("ran plan = %s at %s\n" % (plan.display_name,plan.finalpath) )
            donename = os.path.join(watchdir,"done",os.path.basename(filename))
            print filename, "=>" ,donename
            logfile.write("copying " + filename + " => " +donename + '\n')
            watchdir_setup.movetodone(filename,donename)
            logfile.write("Running lris_senstd for %s at %s\n"  % (cplan.display_name,cplan.finalpath) )
            msg = run_sens.run_sensstd(plan,stddir,idlenv)
            print msg
            logfile.write(msg+"\n")

        else:
            print msg
            print "%s appears to be have an issue, moving to done" % (filename)
            logfile.write(msg+"\n")
            logfile.write("%s appears to be have an issue, moving to done\n" % (filename))
            donename = os.path.join(watchdir,"done",os.path.basename(filename)) 
            print filename, "=>" ,donename
            logfile.write("copying " + filename + " => " +donename + "\n")
            watchdir_setup.movetodone(filename,donename)




    #
    time.sleep(10)
            

