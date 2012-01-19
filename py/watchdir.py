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

parser = optparse.OptionParser(description='Watch a directory for LRIS standard observations, requires make_filelist.py and prep_dirs.py be run.')
parser.add_option('-w','--watchdir', dest='watchdir', action='store',type="string",default=".",
                   help='Directory to watch for standard observations')
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
parser.add_option('-m','--maxjobs', dest='maxjobs', action='store',
                   default=1,type="int",
                   help="Maximum number of jobs to run at once.")

(options,args) = parser.parse_args()

# Now make the paths more useful

watchdir = os.path.abspath(options.watchdir) # get the absolute path - so we can use this later for path manipulations
stddir = os.path.abspath(options.stddir) # get the absolute path - so we can use this later for path manipulations
caldir = os.path.abspath(options.caldir) # get the absolute path - so we can use this later for path manipulations
callist = os.path.abspath(os.path.join(options.caldir,options.callist)) # get the absolute path - so we can use this later for path manipulations
starlist = os.path.abspath(os.path.join(options.kroot,options.starlist)) # get the absolute path - so we can use this later for path manipulations
idlenv = os.path.abspath(options.idlenv)

calibs = makecallist(callist,caldir,stddir)
if not calibs:
    print "file %s cannot be opened for reading" % (os.path.join(caldir,callist))
    sys.exit()

stars,msg = makestarlist(starlist)
if not stars:
    print msg
    sys.exit()
    
pathlist=['done']
prepdirs(os.path.join(watchdir),pathlist)

pipelist = prep_pipelines()

numjobs = 0
proclist = []
planlist = []

while True:

    todolist = glob.glob(os.path.join(watchdir,'*.fits'))

    # first stuff the queue
    # this ends when either the queue is full or the todo list is empty
    while(numjobs < options.maxjobs and len(todolist)):


        filename = todolist.pop()
          
        newproc,msg,plan = buildandrunplan(filename,watchdir,stddir,pipelist,calibs,stars,idlenv)
        if newproc:
            proclist.append(newproc)
            planlist.append(plan)
            
            newname = re.sub(r'fits',r'running',filename)
            newname += ".%d" % newproc.pid
        
            numjobs+=1
            pidfile = open(os.path.join(watchdir,newname),"w")
            pidfile.write("")
            pidfile.close()
            print "Added %s\nNow %d jobs in the queue, can run %d" % (newname,numjobs, options.maxjobs)
        else:
            print msg
            print "%s appears to be have an issue, moving to done" % (filename)
            newname = os.path.join(watchdir,"done",os.path.basename(filename)) 
            print filename, "=>" ,newname
            movetodone(filename,newname)


        

    # out of the loop now
    # now we need to clean up done processes

#    print proclist
    for numproc, proc in enumerate(proclist):

#        print "cleaning the queue", numjobs, options.maxjobs

        if proc.poll() != None:
            proclist.remove(proc)
            pids = "%d" % proc.pid
            files = glob.glob(watchdir + '/*.'+pids)
            if len(files) > 0:
                filename = files[0]
                print "%s (pid %d) has finished" % (filename,proc.pid)
                msg = run_sensstd(planlist.pop(numproc),stddir,idlenv)
                print msg
            os.unlink(filename)
            numjobs-=1

    #
    time.sleep(10)
            

