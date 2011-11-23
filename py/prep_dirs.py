#!/usr/bin/env python
import os, re, glob, os.path, stat
import optparse

parser = optparse.OptionParser(description='Prepare the calibration directory for LRIS standard observations - requires make_filelist.py be run')
parser.add_option('-l','--callist', dest='callist', action='store',
                   default="calibration.list",type="string",
                   help='File in calibration directory containing list of calibrations')
parser.add_option('-c','--caldir', dest='caldir', action='store',type="string",default=".",
                   help='Directory containing calibrations')
(options,args) = parser.parse_args()

caldir = os.path.abspath(options.caldir) # get the absolute path - so we can use this later for path manipulations
callist = os.path.abspath(os.path.join(options.caldir,options.callist)) # get the absolute path - so we can use this later for path manipulations


inputfile = open(callist,"r")
inputfilestr = inputfile.read()
inputfilelist = inputfilestr.split('\n')


for line in inputfilelist:
    if len(line.split()) >= 5:
        linevals = line.split()
        [filename,camera,filetype,grating,wavelen] = linevals[0:5]
        gname = "%s%s" % (camera,grating)
        gname = re.sub('/','_',gname)
        if wavelen:
            wname = "w%.0f" % float(wavelen)
        if not os.path.isdir(os.path.join(caldir,gname)):
            os.mkdir(os.path.join(caldir,gname))
            os.chmod(os.path.join(caldir,gname),(stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH))

        if float(wavelen) > 0:
            if not os.path.isdir(os.path.join(caldir,gname,wname)):
                os.mkdir(os.path.join(caldir,gname,wname))
                os.chmod(os.path.join(caldir,gname,wname),(stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH))
            
            if os.path.isfile(os.path.join(caldir,filename)) and not os.path.isfile(os.path.join(caldir,gname,wname,filename)):
                os.link(os.path.join(caldir,filename),os.path.join(caldir,gname,wname,filename))
                os.chmod(os.path.join(caldir,gname,wname,filename),(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH ))

        else:
            if os.path.isfile(os.path.join(caldir,filename)) and not os.path.isfile(os.path.join(caldir,gname,filename)):
                os.link(os.path.join(caldir,filename),os.path.join(caldir,gname,filename))
                os.chmod(os.path.join(caldir,gname,filename),(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH ))
