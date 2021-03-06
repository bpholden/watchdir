from model import Frame, Plan, Instrument, Pipeline
import Frameutil
import Planutil
import pyfits
import numpy
import os, os.path, sys
import re
import datetime

idlenv = os.path.abspath("test_data/idlenv")
testfile = "r101216_0093.fits.gz"
stdfile = "std-r101216_0093.fits.gz"
testfiledir = "r101216_0093"
testcalfile = "r101216_0092.fits.gz"
testdir = os.path.abspath("test_data")

if not os.path.isfile(os.path.join(testdir,testfile)):
	print "file %s does not exist, check test data and setup" % (os.path.join(testdir,testfile))
	sys.exit(-1)
hdr = pyfits.getheader(os.path.join(testdir,testfile),0)
calhdr = pyfits.getheader(os.path.join(testdir,testcalfile),0)
stdhdu = pyfits.open(os.path.join(testdir,testfiledir,'Science',stdfile))

instrument = Frameutil.find_instrument_name(hdr)
obsdate,obstime = Frameutil.getobsdate(hdr)
cobsdate,cobstime = Frameutil.getobsdate(calhdr)
nmsg,stdframe = Frameutil.addframe(testfile,hdr,obsdate,obstime,testfile,os.path.join(testdir,testfiledir),instrument)
nmsg,calframe = Frameutil.addframe(testcalfile,calhdr,cobsdate,cobstime,testcalfile,testdir,instrument)
xidlpipe = Pipeline(display_name="XIDL for LRIS",
		    runstr='idl -e long_reduce',
		    instrument=stdframe.instrument,
		    framelist="Object Line IntFlat Flat DmFlat Trace"                    
	)
pipes = [xidlpipe]
	
flag = dict(redo=False)
correctplan = Planutil.buildplan(stdframe,"test.plan",os.getcwd(),xidlpipe,flag)
correctplan.frames.append(stdframe)

calframes = [calframe]
stars = ["G191B2B","Feige 34","HZ 44","BD+33 2642","BD+28 4211","Feige 110"]
#
