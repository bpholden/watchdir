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
import gzip

def speccopy(inputname,outputname):
    """ cpgunzip(inputname, outputname)
    this copies a gziped inputname to an uncompressed output name.
    """
    zipped = re.search("\.gz",inputname) # Is the file gzip'ed.  If it is, we need to check if the reduced cals are gzip'ed.
                                         # If the reduced cals are gzip'ed, we need to uncompress them in the plan directory

    if re.search("\.gz",outputname):
        outputname = re.sub("\.gz","",outputname)

    if zipped:

        if os.path.isfile(inputname) and not os.path.isfile(outputname):
            fin = gzip.open(inputname,"rb")
        else:
            return(False)
        try:
            fout = open(outputname,"wb")
            fout.writelines(fin)
            fout.close()
            fin.close()
        except:
            return(False)
    else :
        try:
            os.link(inputname,outputname)
        except:
            return(False)

    return(True)
    
def linkreduced(calib,plan,prefix,datapath):
    reducedname = prefix + calib.name

    match = re.match("wave",prefix)       # If this is a arc line file, we need to copy both the wave-blah.fits and the wave-blah.sav

    fullreducedname =  os.path.join(calib.path,reducedname) # current location
    finalreducedname =  os.path.join(datapath,plan.finalpath,reducedname) # final location

    if os.path.isfile(fullreducedname) :
        if speccopy(fullreducedname,finalreducedname):
            if match:
                reducedname = re.sub("\.fits(.gz)?",".sav",reducedname)
                fullreducedname =  os.path.join(calib.path,reducedname) # current location
                finalreducedname =  os.path.join(datapath,plan.finalpath,reducedname) # final location
                if os.path.isfile(fullreducedname) and not os.path.isfile(finalreducedname) :
                    os.link(fullreducedname,finalreducedname)
                else:
                    print "%s already exists" % finalreducedname
        else:
            return(False)
    else:
        return(False)


    return(True)

def matchframe(frame,calib):
    if calib.grating == frame.grating and abs( float(frame.wavelength) - float(calib.wavelength)) < 20 \
    and calib.instrument.name == frame.instrument.name and calib.xbinning == frame.xbinning and calib.ybinning == frame.ybinning:
        return(True)
    else:
        return(False)

def find_calibframes(frame,plan,calibs,datapath):
    """ find_calibframes(frame,plan,calibs,datapath)

    Given a data frame and a data reduction plan, this looks through
    the calib list and finds the matching calibrations for the frame.
    It returns a list of frame objects that are matches.
    If it does not find arcs or flats, it will return a message.

    The calibration frames are copied into the plan directory.  If
    reduced calibration frames are available, those are also copied
    into the plan directory.  All copies are done with a link, so they
    are not independent of the original data.
    
    """

    msg = ""
    matchs = []
    flats = []
    arcs = []
    for calib in calibs:
        if calib.type == "Line" and matchframe(frame,calib):
            arcs.append(calib)
            # check to see if the arc frame has been processed already, if so place processed file in
            # output directory
            # unprocessed frames are done automatically in Planutils
            linkreduced(calib,plan,"wave-",datapath)
                
        elif calib.type == "IntFlat" and matchframe(frame,calib):
            flats.append(calib)
            linkreduced(calib,plan,"slits-",datapath)
            linkreduced(calib,plan,"pixflat-",datapath)
            linkreduced(calib,plan,"illumflat-",datapath)

    if len(flats):
        matchs += flats
    else:
        msg = "No flats for frame %s" % (frame.display_name)
    if len(arcs):
        matchs += arcs
    else :
        msg = msg  + "\n" + "No arcs for frame %s" % (frame.display_name)

        
    return(matchs,msg)


def find_pipeline(frame,pipelines):

    pipeline = ""
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


def pipeflags(frame,pipeline):
    """ pipeflags(frame,pipeline)

    This adds pipeline specific plan flags.
    
    """
    if pipeline.display_name ==  "XIDL for LRIS":
        if frame.ybinning == 1:
            frame.flags = "bin_ratio=1"



def genplanflags(plan):
    """genplanflags(plan)

    Generates plan flags from a frame attached to the plan.  The flags
    are then bundled into a str using the dicttostr() function.
    """
    
    
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

def buildandrunplan(filename,watchdir,stddir,pipelines,calibs,stars,idlenv,flag):

    # first, we parse the input file and make the frame instance
    msg,frame= Frameutil.ingestframe(os.path.basename(filename),watchdir,stddir,flag)
    if not frame:
        return(False,msg,False)

    # second, we check to see if the input file is in the allowed list
    msg = check_if_std_frame(frame,stars)
    if msg:
        # crap - at this point we have already moved the to stddir
        if os.path.isfile(os.path.join(stddir,os.path.basename(filename))):
            os.remove(os.path.join(stddir,os.path.basename(filename)))
        return(False,msg,False)


    # given an acceptable frame, we make the plan file
    pipeline = find_pipeline(frame,pipelines)
    pipeflags(frame,pipeline)
    planname = re.sub(r"\.fit(s?)",r".plan",os.path.basename(filename))
    plan = Planutil.buildplan(frame,planname,stddir,pipeline,flag)
    plan.frames.append(frame)
    # now we use the calib file list in the calib directory
    # to find matching calibrations
    #
    # find_calibframes also will copy those frames into the plan
    # directory
    calframes,msg = find_calibframes(frame,plan,calibs,stddir)
    if not calframes or len(calframes) == 0:
        if os.path.isfile(os.path.join(stddir,os.path.basename(filename))):
            os.remove(os.path.join(stddir,os.path.basename(filename)))
        return(False,msg,False)        
    plan.frames += calframes
    # update with calibration data frames and write out the plan file
    plan = Planutil.updateplandata(plan,frame,stddir)
    executable = writeplan(plan,stddir,idlenv)
    # actually run the pipeline
    cwd = os.path.dirname(executable)
    outputfile = open(os.path.join(cwd,'processoutput'),"wb")
    erroroutputfile = open(os.path.join(cwd,'processerroroutput'),"wb")
    print "executable:",executable
    curproc = subprocess.Popen(executable,
                               cwd=cwd,stdout=outputfile,
                               stderr=erroroutputfile)

    return(curproc,msg,plan)
