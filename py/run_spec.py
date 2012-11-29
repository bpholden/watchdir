from model import Frame, Plan, Instrument, Pipeline
import types
import time
import glob
import Frameutil
import Planutil
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
import shlex


def speccopy(inputname,outputname):
    """ speccopy(inputname, outputname)
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
            msg = "Output %s exists" % outputname
            return(False,msg)
        try:
            fout = open(outputname,"wb")
            fout.writelines(fin)
            fout.close()
            fin.close()
        except:
            return(False,"Cannot write output %s" % outputname)
    else :
        try:
            os.link(inputname,outputname)
        except:
            return(False,"Cannot link output %s" % outputname)

    return(True,"")
    
def linkreduced(calib,plan,prefix,datapath):
    """This routine takes a selected calibration and a prefix, and puts it in the
    output data reduction directory, using a hard link. It copies both the raw file
    and the reduced file.

    There are four prefix's (wave, slit, illumflat, pixflat) but the wave is special
    as the .sav file along with the .fits.gz file must be copied.
    """
    reducedname = prefix + calib.name

    match = re.match("wave",prefix)       # If this is a arc line file, we need to copy both the wave-blah.fits and the wave-blah.sav

    fullreducedname =  os.path.join(calib.path,reducedname) # current location
    finalreducedname =  os.path.join(datapath,plan.finalpath,reducedname) # final location

    if os.path.isfile(fullreducedname) :
        retval,msg = speccopy(fullreducedname,finalreducedname)
        if retval:
            if match:
                reducedname = re.sub("\.fits(.gz)?",".sav",reducedname)
                fullreducedname =  os.path.join(calib.path,reducedname) # current location
                finalreducedname =  os.path.join(datapath,plan.finalpath,reducedname) # final location
                if os.path.isfile(fullreducedname) and not os.path.isfile(finalreducedname) :
                    os.link(fullreducedname,finalreducedname)
                else:
                    msg = "%s already exists" % finalreducedname
        else:
            return(False,msg)
    else:
        return(False,"No file %s" % fullreducedname)


    return(True,msg)

def matchframe(frame,calib):
    """Given a calibration frame and a data frame, this checks to see if they match.
    The requirements are on grating, binning and central wavelength. The latter is always the same
    for the blue side of LRIS or Kast, so grism and binning are compared.
    """
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

    finalmsg = ""
    matches = []
    flats = []
    arcs = []
    for calib in calibs:
        if calib.type == "Line" and matchframe(frame,calib):
            arcs.append(calib)
            # check to see if the arc frame has been processed already, if so place processed file in
            # output directory
            # unprocessed frames are done automatically in Planutils
            retval,msg = linkreduced(calib,plan,"wave-",datapath)
            if not retval:
                finalmsg += msg
                
        elif calib.type == "IntFlat" and matchframe(frame,calib):
            flats.append(calib)
            prefixes = ["slits-","pixflat-","illumflat-"]
            for prefix in prefixes:
                retval,msg = linkreduced(calib,plan,prefix,datapath)
                if not retval:
                    finalmsg += msg

    if len(flats):
        matches += flats
    else:
        msg = "No flats for frame %s" % (frame.display_name)
    if len(arcs):
        matches += arcs
    else :
        finalmsg = finalmsg  + "\n" + "No arcs for frame %s" % (frame.display_name)

        
    return(matches,finalmsg)


def find_pipeline(frame,pipelines):
    """This routine checks the frame instrument and compares it with the list of pipelines.
    It looks for a pipeline that supports that instrument and returns the pipeline.
    """
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

def find_if_okstar(ftarget,stars):
    """This checks to see if the target is in the list of stars.
    """
    msg = ''
    matched = False
    for star in stars:
        # match = re.search(star.upper(),ftarget.upper())
        match = (star.upper() == ftarget.upper())
        if match:
            matched = True
    if not matched:
        msg = 'Frame observed %s which is not in star list' % ftarget


    return(msg)

def check_if_std_frame(frame,stars):
    """This looks at the frame and checks two things.
    First, was the frame taken in direct (or slitless) mode.
    Second, is the observed target in the list of stars provided.
    """

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


    flags = Planutil.dicttostr(flagsd)
    return(flags)


    


def writeplan(plan,datapath,idlenv):
    """ Given a plan object, the datapath and the string containing the csh with
    the idl environment variables, this writes out the data reduction plan
    and returns the string neccessary to execute the idl code.
    
    """

    plan.runstr = genplanflags(plan) # for "legacy" reasons the additional flags for the idl
                                     # procedure long_reduce are stored in the runstr of plan
                                     # This will make it into a form that can be parsed by Planutil.genrunstr()
                                     #
    Planutil.writeplan(plan,datapath)
    runpath = os.path.join(datapath,plan.finalpath, plan.display_name)
    if os.path.isfile(runpath):
        os.remove(runpath)
    # executable = Planutil.writerunstr(runpath,datapath,Planutil.genrunstr(plan,datapath),idlenv)
    runstr = 'source %s;' % idlenv
    executable = Planutil.XIDLmodrunstr(plan,datapath)
    runstr += executable
    plan.started=datetime.datetime.now()
    plan.finished=None
    plan.setstatus(1)
    
    return runstr

def buildandrunplan(filename,watchdir,stddir,pipelines,calibs,stars,idlenv,flag):
    """This does what it name says. It requires a filename for a standard image,
    the directory that image lives in, the output directory, a list of pipelines, calibration
    frames, a starlist, a filename for a csh script containing the IDL env information
    and a dictionary of flags.

    This copies the file into the appropiate output directory. It checks the file to
    see if it is a standard star observation and the star is in the starlist. It checks to see
    if a pipeline that can proccess the file is in the pipline list. Then, it finds the appropriate
    calibration frames, builds the final data reduction plan and executes it.

    The routine returns the run data reduction plan and a message string. If the plan is False,
    then the routine failed, the message string should return an error. Otherwise, the string is empty.
    """

    # first, we parse the input file and make the frame instance
    # remember, this copies the file from the current location (watchdir)
    # to the final directory which is stddir/ + date_str/ + filename/ 
    msg,frame= Frameutil.ingestframe(os.path.basename(filename),watchdir,stddir,flag)
    if not frame:
        return(msg,False)

    # second, we check to see if the input file is in the allowed list
    msg = check_if_std_frame(frame,stars)
    if msg:
        # crap - at this point we have already moved the to stddir
        if os.path.isfile(os.path.join(stddir,os.path.basename(filename))):
            os.remove(os.path.join(stddir,os.path.basename(filename)))
        return(msg,False)


    # given an acceptable frame, we make the plan file
    pipeline = find_pipeline(frame,pipelines)
    pipeflags(frame,pipeline)
    #    planname = re.sub(r"\.fit(s?)",r".plan",os.path.basename(filename))
    planname = "plan.par"
    plan = Planutil.buildplan(frame,planname,stddir,pipeline,flag)
    plan.frames.append(frame)
    # now we use the calib file list in the calib directory
    # to find matching calibrations
    #
    # find_calibframes also will copy those frames into the plan
    # directory
    calframes,msg = find_calibframes(frame,plan,calibs,stddir)
    if not calframes or len(calframes) == 0:
        if os.path.isfile(os.path.join(stddir,plan.finalpath,os.path.basename(filename))):
            os.remove(os.path.join(stddir,plan.finalpath,os.path.basename(filename)))
        return(msg,False)        
    plan.frames += calframes
    # update with calibration data frames and write out the plan file
    plan = Planutil.updateplandata(plan,stddir)
    runstr = writeplan(plan,stddir,idlenv)
    # executable = shlex.split(runstr)
    # actually run the pipeline
    cwd = os.path.join(stddir,plan.finalpath)
    outputfile = open(os.path.join(cwd,'longreduce.log'),"wb")
    curproc = None
    try:
        curproc = subprocess.call(runstr,
            cwd=cwd,
            stdout=outputfile,
            stderr=outputfile,
            shell=True
            )
            # curproc.wait()
        
    except OSError as e:
        msg = "%s" % e.strerror
    except IOError as e:
        msg = "%s" % e.strerror

    return(msg,plan)
