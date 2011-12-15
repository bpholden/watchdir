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

def select_spec(frame,hdu):

    tabhdr = hdu[5].header
    tabdata = hdu[5].data
    numspec = tabhdr['NAXIS2']

    if re.match("lrisred",frame.instrument.name):
        slitb_xpos = 2179
    else:
        slitb_xpos = 2179

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

def genplanflags(plan):

    flagsd = dict()
    for frame in plan.frames:
        if frame.flags != "":
            linearray = frame.flags.split()
            for element in linearray:
                key,value = element.split('=')
                flagsd[key]=value


    flags = XIDLLongPlanutil.dicttostr(flagsd)
    return(flags)

def writeplan(plan,datapath,idlenv):
    plan.runstr = genplanflags(plan) # for "legacy" reasons the additional flags for the idl procedure long_reduce are stored in the runstr of plan
    # This will make it into a form that can be parsed by Planutil.genrunstr()
    Planutil.writeplan(plan,datapath)
    runpath = os.path.join(datapath,plan.finalpath, plan.display_name+".csh")
    executable = Planutil.writerunstr(runpath,datapath,Planutil.genrunstr(plan,datapath),idlenv)

    plan.started=datetime.datetime.now()
    plan.finished=None
    plan.setstatus(1)

    return(executable)

def writesens_str(plan,datapath,sens_str,idlenv):
    runpath = os.path.join(datapath,plan.finalpath,"sens.csh")
    executable = Planutil.writerunstr(runpath,datapath,sens_str,idlenv)
    return(runpath)


def linkreduced(calib,plan,prefix,datapath):
    reducedname = prefix + calib.name

    zipped = re.search("fits\.gz",reducedname)
    if zipped:
        reducedname = re.sub("\.gz","",reducedname)

    match = re.search("wave",prefix)
    
    if os.path.isfile(os.path.join(calib.path,reducedname)) and not os.path.isfile(os.path.join(datapath,plan.finalpath,reducedname)):
        os.link(os.path.join(calib.path,reducedname),os.path.join(datapath,plan.finalpath,reducedname))
        if match:
            reducedname = re.sub("\.fits",".sav",reducedname)
            if os.path.isfile(os.path.join(calib.path,reducedname)) and not os.path.isfile(os.path.join(datapath,plan.finalpath,reducedname)):
                os.link(os.path.join(calib.path,reducedname),os.path.join(datapath,plan.finalpath,reducedname))
        return(True)
    else:
        return(False)

def find_calibframes(frame,plan,calibs,datapath):

    msg = ""
    matchs = []
    flats = []
    arcs = []
    for calib in calibs:
        if calib.type == "Line" and calib.grating == frame.grating and abs( float(frame.wavelength) - float(calib.wavelength)) < 20 and calib.instrument.name == frame.instrument.name:
            arcs.append(calib)
            # check to see if the arc frame has been processed already, if so place processed file in
            # output directory
            # unprocessed frames are done automatically in Planutils
            linkreduced(calib,plan,"wave-",datapath)
                
        elif calib.type == "IntFlat" and calib.grating == frame.grating and abs( float(frame.wavelength) - float(calib.wavelength)) < 20  and calib.instrument.name == frame.instrument.name:
            flats.append(calib)
            linkreduced(calib,plan,"slits-",datapath)
            linkreduced(calib,plan,"pixflat-",datapath)
            linkreduced(calib,plan,"illumflat-",datapath)

    if len(flats):
        matchs += flats
    else:
        msg = "No flats for frame %s" % (frame.display_name)
        matchs = False
    if len(arcs) and len(matchs):
        matchs += arcs
    elif len(arcs) == 0:
        msg = msg  + "\n" + "No arcs for frame %s" % (frame.display_name)
        matchs= False
    else:
        matchs= False
        
    return(matchs,msg)

def find_pipeline(frame,pipelines):

    for pipeline in pipelines:
        if type(pipeline.instrument) is types.ListType:
            for inst in pipeline.instrument:
                if inst.name == frame.instrument.name:
                    return(pipeline)
        else:
            if frame.instrument.name == pipeline.instrument.name:
                return(pipeline)
    return(None)


def find_if_okstar(fobject,stars):

    msg = ''
    matched = False
    for star in stars:
        # match = re.search(star.upper(),fobject.upper())
        match = (star.upper() == fobject.upper())
        if match:
            matched = True
    if not matched:
        msg = 'Frame observed %s which is not in star list' % fobject


    return(msg)

def check_if_std_frame(frame,stars):

    msg = ''
    # first check the aperture
    match = re.search('direct',frame.aperture)
    if not match:
        msg = 'Frame %s was not taken in direct (or slitless) mode, instead %s' % (frame.name,frame.aperture)

#    msg = find_if_okstar(frame.object,stars)
    msg = find_if_okstar(frame.target,stars)
    return(msg)    


def buildandrunplan(filename,watchdir,stddir,pipelines,calibs,stars,idlenv):

    # first, we parse the input file and make the frame instance
    msg,frame= Frameutil.ingestframe(os.path.basename(filename),watchdir,stddir)
    if not frame:
        return(False,msg,False)

    # first, we check to see if the input file is in the allowed list
    msg = check_if_std_frame(frame,stars)
    if msg:
        # crap - at this point we have already moved the to stddir
        if os.path.isfile(os.path.join(stddir,os.path.basename(filename))):
            os.rename(os.path.join(stddir,os.path.basename(filename)),os.path.join(watchdir,os.path.basename(filename)))
        return(False,msg,False)


    pipeline = find_pipeline(frame,pipelines);
    # given the frame, we make the plan file
    planname = re.sub(r"\.fit(s?)",r".plan",os.path.basename(filename))
    plan = Planutil.buildplan(frame,planname,stddir,pipeline)
    plan.frames.append(frame)
    # now we use the calib file list in the calib directory
    # to find matching calibrations
    calframes,msg = find_calibframes(frame,plan,calibs,stddir)
    if not calframes:
        return(False,msg)        
    plan.frames += calframes

    plan = Planutil.updateplandata(plan,frame,stddir)
    executable = writeplan(plan,stddir,idlenv)

    cwd = os.path.dirname(executable)
    outputfile = open(os.path.join(cwd,'processoutput'),"wb")
    erroroutputfile = open(os.path.join(cwd,'processerroroutput'),"wb")

    curproc = subprocess.Popen(executable,
                               cwd=cwd,stdout=outputfile,
                               stderr=erroroutputfile)

    return(curproc,msg,plan)


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


def lrissenstd_str(stdfile,spec):

    stdfile = "std-" + stdframe.name + ".gz"

    sens_str = 'echo "lris_sensstd,'
    sens_str += "'%s'" % (stdfile)
    sens_str += ', CLOBB=1, NO_UPD_WEB=0,'
    if stdframe.instrument.name == "lrisblue":
        sens_str += " WVTIME=[3500., 4500., 5500.], STD_OBJ=%d" % (spec)
    else:
        sens_str += " WVTIME=[6000., 7000., 8000., 9000., 10000.], STD_OBJ=%d" % (spec)
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
    
    stdfile = os.path.join(outputpath,stdfile)
    try:
        hdu = pyfits.open(stdfile)
        sens_str = lrissenstd_str(stdfile,select_spec(stdframe,hdu))
        executable = writesens_str(plan,stddir,sens_str,idlenv)

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
            

