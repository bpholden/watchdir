#!/usr/bin/env python
import pyfits, os, re, glob, os.path, stat
import optparse

parser = optparse.OptionParser(description='Create the calibration file list for LRIS standard observations')
parser.add_option('-l','--callist', dest='callist', action='store',
                   default="calibration.list",type="string",
                   help='File in calibration directory containing list of calibrations')
parser.add_option('-c','--caldir', dest='caldir', action='store',type="string",default=".",
                   help='Directory containing calibrations')
(options,args) = parser.parse_args()

caldir = os.path.abspath(options.caldir) # get the absolute path - so we can use this later for path manipulations
callist = os.path.abspath(os.path.join(options.caldir,options.callist)) # get the absolute path - so we can use this later for path manipulations


outfile = open(callist,"w")

rinputfiles = glob.glob(os.path.join(caldir,"r*.fits"))
binputfiles = glob.glob(os.path.join(caldir,"b*.fits"))
grinputfiles = glob.glob(os.path.join(caldir,"r*.fits.gz"))
gbinputfiles = glob.glob(os.path.join(caldir,"b*.fits.gz"))


inputfiles = binputfiles + rinputfiles + gbinputfiles + grinputfiles

if len(inputfiles) < 1:
    print "no input FITS files"
    exit()

for inputfile in inputfiles:
    hdr = pyfits.getheader(inputfile,0)

    hdrkeys = hdr.ascardlist().keys()

    instrument_hdr_val = hdr['INSTRUME']
    camera = ""
    cam = ""
    if re.match("LRISBLUE",instrument_hdr_val):
        camera = "lrisblue"
        cam = "b"
    elif re.match("LRIS",instrument_hdr_val):
        camera = "lrisred"
        cam = "r"
  

    frametype = ""
    if hdr['LAMPS'] == "0,0,0,0,0,1":
        frametype = "IntFlat"
    else:
        frametype = "Line"

    framegrating = ""
    framewavelength = "0"
    if re.match("LRISBLUE",instrument_hdr_val):
        framegrating = hdr['GRISNAME']
    elif re.match("LRIS",instrument_hdr_val):
        framegrating = hdr['GRANAME']
        framewavelength = ("%0.1f" % hdr['WAVELEN'])
    if 'BINNING' in hdrkeys:
        xb,yb = hdr['BINNING'].split(",")
    inputfile = os.path.basename(inputfile)
    print inputfile, cam, frametype, framegrating, framewavelength,xb,yb
    if cam:
        line = " ".join((inputfile, cam, frametype, framegrating, framewavelength,xb,yb,"\n"))
        outfile.write(line) 

outfile.close()
