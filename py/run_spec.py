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
