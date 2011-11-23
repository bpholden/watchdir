from model import Plan, Frame, Instrument, Pipeline
import re, os, os.path, glob, pyfits, tarfile, tempfile,  sys, shutil
import datetime
import Planutil

def dicttostr(dictionary):
	if isinstance(dictionary,dict):
		string= str(dictionary)
	else:
		# how did we get here?
		string = str({})
	return(string)

	
def strtodict(string) :
	if len(string):
		dictionary = eval(string)
	else:
		dictionary = {}
	return(dictionary)

def inst_list():

    return(["lrisred","lrisblue","kastb","kastr","nirspec"])

def determine_numkind_flats(plan):

    numflat = { "Flat" : 0,
                "DmFlat" : 0,
                "IntFlat" : 0,
                "PixFlat" : 0
                }
                
    for frame in plan.frames:
        if frame.type in numflat:
            numflat[frame.type] += 1

    return(numflat)

def genframestr(frame,camera):

    outtag = { "Object" : "\"science\"",
               "IntFlat" : "\"iflat\"",
               "Flat" : "\"twiflat\"",
               "DmFlat" : "\"domeflat\"",
               "Line" : "\"arc\"",
               "PixFlat" : "\"domeflat\"",
               "Trace" : "\"std\""
               }

    framestr = "LEXP " + frame.display_name
    if camera == "lrisred" and (frame.type== "Flat" or frame.type=="DmFlat" or frame.type=="IntFlat"):
        framestr  += " %s " % "bothflat"
    elif camera == "lrisblue" and (frame.type== "Flat" or frame.type=="DmFlat" or frame.type=="IntFlat"):
#        framestr  += " %s " % '\"twiflat\"'
        framestr  += " %s " % '\"bothflat\"'
    elif camera == "kastr" and (frame.type== "Flat" or frame.type=="DmFlat" or frame.type=="IntFlat"):
        framestr  += " %s " % "bothflat"
    elif camera == "kastb" and (frame.type== "Flat" or frame.type=="DmFlat" or frame.type=="IntFlat"):
        framestr  += " %s " % '\"twiflat\"'
    else:
        framestr  += " %s " % outtag[frame.type]

    plantarget = frame.target
    planaperture = frame.aperture
    if frame.target:
        framestr += " \"%s\" " % plantarget 
    else:
        framestr += " \"%s\" " % planaperture
    framestr += " %.1f " % float(frame.exptime)
    framestr += " %s " % camera 
    framestr += " %s " % frame.grating 
    if frame.wavelength :
        framestr += " %.2f " % float(frame.wavelength)
    else :
        framestr += " \"\" "
    framestr += " \"%s\" \n" % planaperture
    return(framestr)


def linkfiles(frame,plan,datapath):
    """linkfiles(plan,plan,datapath)
    This deals with the fact that XIDL can only have one datapath.
    Because input data can come from multiple sources, we will make links.
    This will assume a single frame, a plan and a datapath.
    
    """
    inpath = os.path.join(datapath,frame.path,frame.display_name)
    outpath = os.path.join(datapath,plan.finalpath)
    if os.path.isfile(inpath) and os.path.isdir(outpath) and not os.path.isfile(os.path.join(outpath,frame.display_name)):
        os.link(inpath,os.path.join(outpath,frame.display_name))
    return(outpath)

def writepixflatplan(plan,datapath,camera):


    planpath = os.path.join(datapath, plan.finalpath, plan.display_name)
    planpath = re.sub(r'\.plan',r'pixflat.plan',planpath)

    pixflatplandata = "logfile, '" + plan.name + "pixflat.log'   # Log file\n"
    pixflatplandata += "plotfile, '" + plan.name + "pixflat.ps'   # Plot file\n"
    pixflatplandata += "indir \'" + os.path.abspath(os.path.join(datapath,plan.finalpath)) + "/\'\n"
    pixflatplandata += "tempdir Temp\nscidir  Science\n"

    pixflatplandata += "idlutilsVersion \'NOCVS:idlutils\'\n"
    pixflatplandata += "LongslitVersion \'NOCVS:Unknown\'\n"

    pixflatplandata += "\ntypedef struct {\n char filename[45];\n"
    pixflatplandata += " char flavor[8];\n char target[12];\n"
    pixflatplandata += " float exptime;\n char instrument[9];\n"
    pixflatplandata += " char grating[9];\n" 
    pixflatplandata += " char wave[1];\n"
    pixflatplandata += " char maskname[18];\n} LEXP;\n"

    frames = plan.framelisttype(type='PixFlat')
    framelist = []
    for frame in frames:
        print frame
        linkfiles(frame,plan,datapath)
        framestr=genframestr(frame,camera)
        framelist.append(framestr)


    framestr = Planutil.buildframestr(framelist)

    planfile = open(planpath,'w')
    planfile.write(pixflatplandata)
    planfile.write(framestr)
    planfile.close()
    return()


    return plan

def determine_nslit(frame,camera):

    minslit = 20 # default to something sensible.
    if camera == "LRISBLUE":
        minslit = 40 / frame.xbinning
    elif camera == "LRISRED" or camera == "lrisred":
        if 'DETECTOR' in frame.header.ascardlist().keys():
            minslit = 40 / frame.xbinning
        else:
            minslit = 20 
        # this only works for the old LRIS red
        # this needs to be fixed for the new detectors.

    return(minslit)


def buildframelist(plan,camera):

    framelist = []


    numflat = determine_numkind_flats(plan)

    for frametype in plan.pipeline.typelist():

        frames = plan.framelisttype(type=frametype)

        for frame in frames:
            framestr = genframestr(frame,camera)
            framelist.append(framestr)

    return(framelist)


def parseslitdefs(slitdef):

    msg = ""
    lines = slitdef.splitlines()
    goodlines = []
    for line in lines:
        blank = re.search('\A\s*\Z',line)
        if not blank:
            match = re.search('\d+\.?\d*\s+\d+\.?\d*',line)
            if not match:
                msg="Slit definition can only be pairs of numbers"
                print msg
            else:
                print "OK: ",line
                goodlines.append(line)

    good = "".join(goodlines)
    if len(good) == 0:
        good = ""
    return(msg,good)

def parseoptions(curplan,kw):

    msg = ""
    if 'maxobj' in kw.keys():
        try:
            curplan.maxobj = int(kw['maxobj'])
        except ValueError:
            msg = "Bad value for maxobj"
    if 'minslit' in kw.keys():
        try:
            curplan.minslit = float(kw['minslit'])
        except ValueError:
            msg = msg + "Bad value for minslit"
    if 'reduxthresh' in kw.keys():
        try:
            curplan.reduxthres = float(kw['reduxthresh'])
        except ValueError:
            msg = msg + "Bad value for reduction threshold"

    if 'slitdefs' in kw.keys():
        msg,defs = parseslitdefs(kw['slitdefs'])
        if defs:
            kw['slitdefs']=defs
        else:
            del kw['slitdefs']

    if len(msg) == 0:
        msg = None
        
    return(msg)

def buildplanlong(plan,datapath,camera):

#    fq = frame.query.filter_by(user=Plan.user)
#    fq = fq.filter_by(instrument=frame.instrument)

#    plan.minslit = determine_nslit(frame,camera)
#    plan.maxobj = 5
#    plan.reduxthresh = 0.01;

    flags = strtodict(plan.runstr)


    plan.data = "logfile, '" + plan.name + ".log'   # Log file\n"
    plan.data += "plotfile, '" + plan.name + ".ps'   # Plot file\n"
    plan.data += "indir \'" + os.path.abspath(os.path.join(datapath,plan.finalpath)) + "/\'\n"
    plan.data += "tempdir Temp\nscidir  Science\n"
    if flags.has_key('maxobj'):
        try:
            plan.data += "maxobj %d \n" %  int(flags['maxobj'])
        except ValueError:
            plan.data += "maxobj %d \n" %  5

    else:
        plan.data += "maxobj %d \n" %  plan.maxobj
    if flags.has_key('minslit'):
        try:
            plan.data += "minslit %f \n" % float(flags['minslit'])
        except ValueError:
            if len(plan.frames) > 0:
                slitsize = determine_nslit(plan.frames[0],camera)
            else:
                slitsize = 20
            plan.data += "minslit %f \n" % slitsize
    else:
            if len(plan.frames) > 0:
                slitsize = determine_nslit(plan.frames[0],camera)
            else:
                slitsize = plan.minslit
            plan.data += "minslit %f \n" % slitsize

    if flags.has_key('reduxthresh'):
        try:
            plan.data += "reduxthresh %f \n" % float(flags['reduxthresh'])
        except ValueError:
            plan.data += "reduxthresh %f \n" % 0.01
    else:
        plan.data += "reduxthresh %f \n" % plan.reduxthresh

    plan.data += "idlutilsVersion \'NOCVS:idlutils\'\n"
    plan.data += "LongslitVersion \'NOCVS:Unknown\'\n"

    plan.data += "\ntypedef struct {\n char filename[45];\n"
    plan.data += " char flavor[8];\n char target[12];\n"
    plan.data += " float exptime;\n char instrument[9];\n"
    plan.data += " char grating[9];\n" 
    if camera == "LRISRED":
        plan.data += " char wave[10];\n"
    else:
        plan.data += " char wave[1];\n"
    plan.data += " char maskname[18];\n} LEXP;\n"

    return plan



def writelongplan(plan,datapath):

    camera = plan.instrument.name
    planpath = os.path.join(datapath, plan.finalpath, plan.display_name)

    if os.path.exists(planpath):
        os.remove(planpath)

    numkindflat = determine_numkind_flats(plan)
    for frame in plan.frames:
        linkfiles(frame,plan,datapath)

    framestr = Planutil.buildframestr(buildframelist(plan,camera))

    planfile = open(planpath,'w')
    if plan.data == None:
        buildplanlong(plan,datapath,camera)

    if camera == "lrisblue" and numkindflat['PixFlat'] > 0:
        writepixflatplan(plan,datapath,camera)
    elif camera == "kastb" and numkindflat['PixFlat'] > 0:
        writepixflatplan(plan,datapath,camera)

    planfile.write(plan.data)
    planfile.write(framestr)
    planfile.close()
    return()

def modrunstr(plan,datapath):

    # This relies on the run string as it is in the database 
    # Really, I need only one runstr (that associated with the Pipeline)
    # The plan object should be runstrflags or some such.

    # The actual item stored in the database as the runstr is stripped of leading and trailing spaces.
    # If the camera is the lris blue and there are not pixel flats, then the PIXFLAT_ARCHIVE flag is added.
    
    # In addition, if the user has taken pixel flats (images with the dispersing element but without an aperture, usually on the sky)
    # then we need to run the pipeline twice.  Once with just the pixel flats in their own plan file, and once with everything.

    flags = strtodict(plan.runstr)


    runstr = plan.pipeline.runstr % plan.display_name
    runstr = runstr + '\n'


    numflat = determine_numkind_flats(plan)
    if numflat["PixFlat"] == 0 and plan.instrument.name == "lrisblue":
        flags["PIXFLAT_ARCHIVE"] = "On"
    elif numflat["PixFlat"] > 0 and plan.instrument.name == "lrisblue":
        # to reduce PixFlat (actually twilight flats without a slit)
        # we need to run long_reduce twice, which also means two plan files
        planpath = os.path.join(datapath, plan.finalpath, plan.display_name)
        pixflatrunstr = plan.pipeline.runstr % plan.display_name
        pixflatrunstr = re.sub('\.plan','pixflat.plan',pixflatrunstr)
        pixflatrunstr = re.sub('\.log','_pixflat.log',pixflatrunstr)
        runstr = pixflatrunstr + "\n" + runstr
    elif numflat["PixFlat"] > 0 and plan.instrument.name == "kastb":
        # to reduce PixFlat (actually twilight flats without a slit)
        # we need to run long_reduce twice, which also means two plan files
        planpath = os.path.join(datapath, plan.finalpath, plan.display_name)
        pixflatrunstr = plan.pipeline.runstr % plan.display_name
        pixflatrunstr = re.sub('\.plan','pixflat.plan',pixflatrunstr)
        pixflatrunstr = re.sub('\.log','_pixflat.log',pixflatrunstr)
        runstr = pixflatrunstr + "\n" + runstr

    flagstr = ""
    if isinstance(flags,dict):
        for flagkey in flags.keys():
            flag = ""
            if flags[flagkey] == "On" and flagkey != "skytrace":
                flag = ",/" + flagkey.upper()
            elif flagkey == "skytrace" and flags[flagkey] == "On":
                flag = "," + flagkey.upper() + "=1"
            elif flagkey == "skytrace" and flags[flagkey] == "Off":
                flag = "," + flagkey.upper() + "=0"

            if flagkey == "slitdefs":
                flag = ",ADD_SLITS='slitlocations'"

                slitpath = os.path.join(datapath,plan.finalpath,'slitlocations')
                slitfile = open(slitpath,'w')
                slitfile.write(str(flags['slitdefs']))
                slitfile.close()
        
            flagstr += flag
        flagstr = " ".join([flagstr,'"','|'])
        
        runstr = re.sub('\"\s\|',flagstr,runstr)

    plan.runstr = dicttostr(flags)
    plan.update()

    return(runstr)
