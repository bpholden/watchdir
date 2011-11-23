#!/usr/bin/env python 
import os, re, glob, os.path, subprocess, sys, stat
from model import Frame, Instrument
import XIDLLongPlanutil
import optparse

def find_dirs(filelist):
    dirs = []
    for cfile in filelist:
        if os.path.isdir(cfile):
            dirs.append(cfile)
    return(dirs)
        
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



def write_plan(dir,calibs):
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

        for fitsfile in fitsfiles:
            for calib in calibs:
                if calib.name in fitsfile:
                    line = XIDLLongPlanutil.genframestr(calib,calib.instrument.name)
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
#parser.add_option('-m','--maxjobs', dest='maxjobs', action='store',
#                   default=1,type="int",
#                   help="Maximum number of jobs to run at once.")

(options,args) = parser.parse_args()

# Now make the paths more useful

caldir = os.path.abspath(options.caldir) # get the absolute path - so we can use this later for path manipulations
callist = os.path.abspath(os.path.join(options.caldir,options.callist)) # get the absolute path - so we can use this later for path manipulations

calibs = makecallist(callist,caldir,".")


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
        idlrunfile.writelines( ["cd "+cwd+'\n','echo \"long_reduce\" | $IDL_DIR/bin/idl  \n','cd '+caldir + '\n'])
    wdirs = glob.glob(gdir+"/w*")
    for wdir in wdirs:
#        execstr = 'echo \"long_plan\" | $IDL_DIR/bin/idl'
        cwd = os.path.join(".",wdir)
        nfiles = write_plan(wdir,calibs)
        if nfiles:
            idlrunfile.writelines( ["cd "+cwd+'\n','echo \"long_reduce\" | $IDL_DIR/bin/idl  \n','cd '+caldir + '\n'])
    

idlrunfile.close()
os.chmod(os.path.join(caldir,"run_idl.csh"),(stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH))
