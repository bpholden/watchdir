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


def prep_pipelines():

    xidlpipe = Pipeline(display_name="XIDL for LRIS",
                        # runstr=u'echo \"long_reduce,\'%s\'" | $IDL_DIR/bin/idl  > & longreduce.log\n',
                        runstr='idl -e long_reduce',
                        instrument = [],
                        framelist = "Object Line IntFlat Flat DmFlat Trace"
        )

    xidlpipe.instrument.append(Instrument(name=u'lrisred',display_name=u'LRISRED'))
    xidlpipe.instrument.append(Instrument(name=u'lrisblue',display_name=u'LRISBLUE'))
    

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
        msg = 'Cannot open star list %s for reading'  %(starlistname)
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

def findframe(startdir,camera,grating,filename):
    """findframe(startdir, camera, grating, filename)
    This routine will search for a filename.  It will start in startdir,
    then it will descend into a directory named after the camera+grating.
    After that, it will search subdirectories of the form w\d+.
    If the file is still not found, it fails
    """
    grating = re.sub("\/","_",grating)
    gdir = camera + grating
    if os.path.isfile(os.path.join(startdir,filename)):
        return(startdir)
    else:
        # now the grating directory
        if os.path.isfile(os.path.join(startdir,gdir,filename)):
            return(os.path.join(startdir,gdir))
        poswavedirs = glob.glob(os.path.join(startdir,gdir) + '/w*')
        wavedirs = []

        for pwd in poswavedirs:
            if re.search("w\d+",pwd):
                wavedirs.append(pwd) 


        for wd in wavedirs:
            # alright, now we search the subdirs
            if os.path.isfile(os.path.join(wd,filename)):
                return(wd)

    return(None)

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
        calframepath = findframe(caldir,camera,grating,filename)
        if calframepath:
            calframe = Frame(name=filename,path=calframepath,display_name=filename)
            calframe.grating = grating
            calframe.wavelength = float(wavelen)
            calframe.type = filetype
            calframe.xbinning = int(xb)
            calframe.ybinning = int(yb)
            calframe.flags = flags
            if camera == "r":
                calframe.instrument=Instrument(name=u'lrisred',display_name=u'LRISRED')
            elif camera == "b":
                calframe.instrument =Instrument(name=u'lrisblue',display_name=u'LRISBLUE')
            calframes.append(calframe)
            make_gratingdir(filename,grating,stddir)
        else:
            print "Cannot find file %s in %s or appropriate subdirectories." % (filename,caldir)
    
    return(calframes)

def movetodone(filename,newname):
    if not os.path.isdir(os.path.dirname(newname)):
        os.mkdir(newname)

    if not os.path.isfile(newname):
        try:
            os.rename( filename,newname) # stash it out of the way
        except:
            print "cannot move %s to %s!\n" % (filename,newname)
    else:
        # crap.  This means that the file is already in the done directory.
        gstr = filename + "*"
        files = glob.glob(gstr)
        newname = newname + "%d" % len(files)
        try:
            os.rename( filename,newname) # stash it out of the way
        except:
            print "cannot move %s to %s!\n" % (filename,newname)

def startlog(logfilename="watchdir.log"):
    
    logfile = open(logfilename,"a")
    return logfile
