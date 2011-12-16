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


def prep_pipelines():

    xidlpipe = Pipeline(display_name="XIDL for LRIS",
                        runstr=u'echo \"long_reduce,\'%s\'" | $IDL_DIR/bin/idl  > & longreduce.log\n')
    xidlpipe.instrument = []
    # This is really not necessary, just done for consistency with model.py file
    xidlpipe.instrument.append(Instrument(name=u'lrisred',display_name=u'LRISRED'))
    xidlpipe.instrument.append(Instrument(name=u'lrisblue',display_name=u'LRISBLUE'))
    
    xidlpipe.framelist = "Object Line IntFlat Flat DmFlat Trace"

    return([xidlpipe])

def prepdirs(cpath,dirlist):
    for dir in dirlist:
        if not os.access(os.path.join(cpath,dir),os.F_OK):
            os.mkdir(os.path.join(cpath,dir))

    return


def make_gratingdir(filename,grating,stddir):

    prefix = ""
    if re.match("r",filename):
        prefix = "r"
    if re.match("b",filename):
        prefix = "b"

    gstr = prefix + re.sub("/","_",grating)
    if not os.access(os.path.join(stddir,gstr),os.F_OK):
        os.mkdir(os.path.join(stddir,gstr))

    return()

def makestarlist(starlistname):

    msg = ''
    try:
        starfile = open(starlistname)
    except:
        msg = 'Cannot open star list %s for reading'  %(starlist)
        return([],msg)

    starlisttxt= starfile.read()
    starlistln = starlisttxt.splitlines()
    stars = []
    for sln in starlistln:
        match = re.match("\#",sln)
        if not match:
            wstar = sln[0:14] # trim off everything that, according to the docs, is not part of the name
            ind = wstar.find('  ') # this should find the end of the name.
            stars.append(wstar[0:ind])
            

    if len(stars) == 0:
        msg = 'Star list %s contains no stars!' % starlist


    return(stars,msg)

def makecallist(callist,caldir,stddir):

    try:
        calfile = open(callist)
    except:
        return(False)

    calfilestr = calfile.read()
    calfilelist = calfilestr.splitlines()

    calframes = []
    flags = ""
    for line in calfilelist:
        linearray = line.split()
        if len(linearray) == 7:
            [filename,camera,filetype,grating,wavelen,xb,yb] = linearray
        elif len(linearray) > 7:
            [filename,camera,filetype,grating,wavelen,xb,yb] = linearray[0:6]
            flags = " ".join(linearray[7:])
        else:
            return([])
        calframe = Frame(name=filename,path=caldir,display_name=filename)
        calframe.grating = grating
        calframe.wavelength = wavelen
        calframe.type = filetype
        calframe.xbinning = xb
        calframe.ybinning = yb
        calframe.flags = flags
        if camera == "r":
            calframe.instrument=Instrument(name=u'lrisred',display_name=u'LRISRED')
        elif camera == "b":
            calframe.instrument =Instrument(name=u'lrisblue',display_name=u'LRISBLUE')
        calframes.append(calframe)
        make_gratingdir(filename,grating,stddir)

    
    return(calframes)



# -- main 

lris_thru = "."
if os.environ.has_key('LRIS_THRU'):
    lris_thru = os.environ['LRIS_THRU']

parser = optparse.OptionParser(description='Watch a directory for LRIS standard observations, requires make_filelist.py and prep_dirs.py be run.')
parser.add_option('-w','--watchdir', dest='watchdir', action='store',type="string",default=".",
                   help='Directory to watch for standard observations')
parser.add_option('-s','--stddir', dest='stddir', action='store',type="string",default=lris_thru,
                   help='Parent directory, will contain config files and output of longreduce')
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
            if not os.path.isdir(os.path.dirname(newname)):
                os.mkdir(newname)
                
            os.rename( filename,newname) # stash it out of the way


        

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
            

