#!/usr/bin/env python 
import os, re, glob, os.path, subprocess, sys, stat
from model import Frame, Instrument
import Planutil
import optparse

def find_dirs(filelist):
    dirs = []
    for cfile in filelist:
        if os.path.isdir(cfile):
            dirs.append(cfile)
    return(dirs)


def makeplanflags(filename):

    planflags = dict()
    try:
        flagfile = open(filename)
    except:
        print "WARNING: %s not found, proceeding with no additional flags for XIDL" % filename
        return(planflags)

    flagstrs = flagfile.read().splitlines()
    for fstr in flagstrs:
        (grating,binning,flag) = fstr.split()
        # let us assume the correct format
        fkey = "%s %s"  % (grating,binning)
        planflags[fkey] = flag


    return(planflags)
        
def makecallist(callist,caldir):
    """makecallist(callist, caldir)

    This reads in the file specified as callist.
    The path must be absolute, or the routine will return False

    The caldir is used to constructed the Frame object, so that future
    functions will know where the actual is located (thus, in theory,
    the calibration file and the callist can be in two different
    places.)

    
    """
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
            flags = " ".join(linearray[6:])
        else:
            return([])
        calframe = Frame(name=filename,path=caldir,display_name=filename)
        calframe.grating = grating
        calframe.wavelength = wavelen
        calframe.type = filetype
        calframe.xbinning = xb
        calframe.ybinning = yb
        calframe.flags = flags
        calframe.exptime = 1
        calframe.target = 'horizon lock'
        calframe.aperture = 'long_1.0'

        if camera == "r":
            calframe.instrument=Instrument(name=u'lrisred',display_name=u'LRISRED')
        elif camera == "b":
            calframe.instrument =Instrument(name=u'lrisblue',display_name=u'LRISBLUE')
        
        calframes.append(calframe)
#        make_gratingdir(filename,grating,stddir)

    
    return(calframes)

def gen_planrun(cwd,caldir,planflags):
    """gen_planrun(cwd,caldir,planflags)

    This generates the run string.  It first takes the flags and turns
    it into a IDL string e.g, ,foo=100,/bar Then it uses the path info
    to setup the shell script.  The actual idl string with the run
    string flags is built.
    """
    planflagstr = ""
    for k in planflags.keys():
        planflagstr += ",%s" % planflags[k]

    runstrs= []
    runstrs.append("cd %s\n" % cwd)
    runstrs.append('echo "long_reduce,\'plan.par\'%s" | $IDL_DIR/bin/idl \n' % planflagstr)
    runstrs.append("cd %s\n" % caldir)
    return(runstrs)
    

def gen_planflags(dir,calibs,flagdict):
    """gen_planflags(directory, calib list, flag dictionary)

    This generates the flags for a data reduction plan.  It uses the
    flag dictionary made in makeplanflags().  The dictionary keys by
    grating and binning in the y direction.  The function searches the
    directory (dir), and finds the fits files in the calibs list.  It
    then references the appropriate flags from the flagdict.
    
    """
    planflags=dict()
    fitsfiles = glob.glob(dir + "/*.fits*")
    for fitsfile in fitsfiles:
        for calib in calibs:
            if calib.name in fitsfile:
                fkey = "%s %s"  % (calib.grating,calib.ybinning)
                if fkey in flagdict.keys():
                    planflags[fkey] = flagdict[fkey]
    return planflags

def write_plan(dir,calibs):
    """ write_plan(dir,calibs)

    This reads in the directory passed.  For each file in that
    directory that is in the calibration list, it builts up a string
    for the plan file.  This routine also has all of the header
    information for the plan file.  All of this is written to a file
    in the specified directory (dir) called "plan.par".
    
    """
    fitsfiles = glob.glob(dir + "/*.fits*")
    #    print fitsfiles
    nfiles = len(fitsfiles)
    if nfiles > 0:

        hdrblock = "logfile 'plan.log'   # Log file\n"
        hdrblock += "plotfile 'plan.ps'   # Plot file\n"
        hdrblock += "indir './'   # Raw data directory\n"
        hdrblock += "tempdir Temp     # Temporary (working) directory\n"
        hdrblock += "scidir  Science  # Science output directory\n"
        hdrblock += "maxobj     5  # Maximum number of Objects per slit\n"
        hdrblock += "minslit 20  # Minimum slit width\n"
        hdrblock += "reduxthresh 0.01 # Sets the fraction of the brightest objects on each slit that is reduced\n"
        hdrblock += "idlutilsVersion ''  # Version of idlutils when building plan file\n"
        hdrblock += "LongslitVersion 'NOCVS:'  # Version of Longslit when building plan file\n\n"
        hdrblock += "typedef struct {\n"
        hdrblock += "char filename[24];\n"
        hdrblock += "char flavor[6];\n"
        hdrblock += "char target[13];\n"
        hdrblock += "float exptime;\n"
        hdrblock += "char instrument[5];\n"
        hdrblock += "char grating[10];\n"
        hdrblock += "char wave[10];\n"
        hdrblock += "char maskname[9];\n"
        hdrblock += "} LEXP;\n\n"

        rxidltypes = { "IntFlat" : "bothflat",
                      "Line" : "arc"}
        bxidltypes = { "IntFlat" : "twiflat",
                      "Line" : "arc"}


        planfile = open(os.path.join(dir,"plan.par"),"w")
        planfile.write(hdrblock)


        # note  - I just ASSUME that the files are all the same.

        for fitsfile in fitsfiles:
            for calib in calibs:
                if calib.name in fitsfile:
                    line = Planutil.genXIDLframestr(calib,calib.instrument.name)
                    planfile.write(line)

        planfile.close()

    return(nfiles)

lris_thru = "."
if os.environ.has_key('LRIS_THRU'):
    lris_thru = os.environ['LRIS_THRU']

parser = optparse.OptionParser(description='Run XIDL to process calibrations for LRIS standard observations')
parser.add_option('-c','--caldir', dest='caldir', action='store',type="string",default=".",
                   help='Directory containing calibrations')
parser.add_option('-l','--callist', dest='callist', action='store',
                   default="calibration.list",type="string",
                   help='File in calibration directory containing list of calibrations')
parser.add_option('-f','--flagfile', dest='flagfile', action='store',
                   default="calibration.flags",type="string",
                   help='File in calibration directory containing flags for running XIDL, a version can be found in the source directory')

#parser.add_option('-m','--maxjobs', dest='maxjobs', action='store',
#                   default=1,type="int",
#                   help="Maximum number of jobs to run at once.")

(options,args) = parser.parse_args()

# Now make the paths more useful

caldir = os.path.abspath(options.caldir) # get the absolute path - so we can use this later for path manipulations
callist = os.path.abspath(os.path.join(options.caldir,options.callist)) # get the absolute path - so we can use this later for path manipulations
flagfile = os.path.abspath(os.path.join(options.caldir,options.flagfile)) # get the absolute path - so we can use this later for path manipulations

calibs = makecallist(callist,caldir)
flagdict = makeplanflags(flagfile)

rdirs = find_dirs(glob.glob(os.path.join(caldir,"r*_*")))
bdirs = find_dirs(glob.glob(os.path.join(caldir,"b*_*")))

gdirs = bdirs+rdirs

if not calibs:
    print "file %s cannot be opened for reading" % (os.path.join(caldir,callist))
    sys.exit()


idlrunfile = open(os.path.join(caldir,"run_idl.csh"),"w")

for gdir in gdirs:
    cwd = os.path.join(".",gdir)
    nfiles = write_plan(gdir,calibs)
    if nfiles:
        idlrunfile.writelines( gen_planrun(cwd,caldir,planflags))
    wdirs = glob.glob(gdir+"/w*")
    for wdir in wdirs:
#        execstr = 'echo \"long_plan\" | $IDL_DIR/bin/idl'
        cwd = os.path.join(".",wdir)
        nfiles = write_plan(wdir,calibs)
        planflags = gen_planflags(wdir,calibs,flagdict)
        if nfiles:
            idlrunfile.writelines( gen_planrun(cwd,caldir,planflags))

    

idlrunfile.close()
os.chmod(os.path.join(caldir,"run_idl.csh"),(stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH))
