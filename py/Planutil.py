from datetime import datetime

from model import Plan, Frame, Instrument, Pipeline

import re, os, os.path, glob, pyfits, tarfile, tempfile, sys, shutil
import Frameutil

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

def determine_nslit(frame,camera):
    # XIDL and LRIS specific

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

def linkfiles(frame,plan,datapath):
    """linkfiles(plan,plan,datapath)
    This deals with the fact that XIDL can only have one datapath.
    Because input data can come from multiple sources, we will make links.
    This will assume a single frame, a plan and a datapath.
    
    """
    msg = ''
    inpath = os.path.join(datapath,frame.path,frame.display_name)
    outpath = os.path.join(datapath,plan.finalpath)
    if os.path.isfile(inpath) and os.path.isdir(outpath) and not os.path.isfile(os.path.join(outpath,frame.display_name)):
        try:
            os.link(inpath,os.path.join(outpath,frame.display_name))
	except:
            msg = "error linking %s to %s" % (inpath,os.path.join(outpath,frame.display_name))
    return(msg)


def makeplan_displayname(frame):

    if frame.instrument.name == "lrisblue":
        displayname = "b" + frame.target + "_"  +".plan"
    elif frame.instrument.name == "lrisred":
        displayname = "r" + frame.target + "_"  +".plan"
    elif frame.instrument.name == "kastb":
        displayname = "b" + frame.object + "_"  +".plan"
    elif frame.instrument.name == "kastr":
        displayname = "r" + frame.object + "_"  +".plan"
    else:
        displayname = frame.target + "_" + ".plan"


    displayname = re.sub('\s+','',displayname)

    return displayname

def buildplan(frame,planname,datapath,pipeline,flag):

    """The guts of plan making.

    Pass in a data frame, planname, integer, datapath object, pipeline object.

    The data frame determines the plan display name (based on the
    instrument).  Interger is for the name, to provide each plan a
    unique id (thus the user can have the multiple plans using the
    same data).
    
    Then, this builds plan object.

    The output path is the input frame path with rawdata changed to findata.
    # FIX for other paths

    Returns the plan object
    """

#    planname = frame.aperture + frame.user.user_name + ".plan"

    displayname = makeplan_displayname(frame)

    plan = Plan(planname,frame.path,frame.instrument,pipeline,
                frame.aperture,frame.target,displayname)


    plan.finalpath = frame.path

    fullpath = os.path.join(datapath,plan.finalpath)

    if not os.access(fullpath,os.F_OK):
        os.makedirs(fullpath)
        # I KNOW, I KNOW!!!
        os.chmod(fullpath,0777)
        os.chmod(os.path.dirname(fullpath.rstrip("/")),0777)
    elif  os.path.isdir(fullpath) and flag['redo']:
        files = glob.glob(fullpath + "/*.fits*")
        for cfile in files:
            if os.path.basename(cfile) != frame.name:
                os.remove(os.path.join(cfile))
        files = glob.glob(fullpath + "/*.???")
        for cfile in files:
            os.remove(os.path.join(cfile))
        if os.path.isdir(os.path.join(fullpath,"Science")):
            files = glob.glob(fullpath + "/Science/*")
            for cfile in files:
                os.remove(os.path.join(cfile))
            os.rmdir(os.path.join(fullpath,"Science"))
        
    plan.instrument = frame.instrument

    plan.pipeline = pipeline
       
    return (plan)

def updateplandata(plan,datapath):

    """This generates the pipeline specific information.
    This will ONLY work for XIDL and LRIS now. This does one thing.
    It builds up the actual plan file content, the plan file is written later.

    """

#    plan = XIDLLongPlanutil.buildplanlong(plan,datapath,plan.instrument.name )

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
                slitsize = determine_nslit(plan.frames[0],plan.instrument.name)
            else:
                slitsize = 20
            plan.data += "minslit %f \n" % slitsize
    else:
            if len(plan.frames) > 0:
                slitsize = determine_nslit(plan.frames[0],plan.instrument.name)
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
    if plan.instrument.name == "LRISRED":
        plan.data += " char wave[10];\n"
    else:
        plan.data += " char wave[1];\n"
    plan.data += " char maskname[18];\n} LEXP;\n"

    return(plan)

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
    
def writeplan(plan,datapath):

    """Writes the plan file.  This is what the software will actually execute.
    This is hard coded for the XIDL/LRIS specific content.
    """

#    cleanoutplandir(plan,datapath)
#    XIDLLongPlanutil.writelongplan(plan,datapath)
# def writelongplan(plan,datapath):

    camera = plan.instrument.name
    planpath = os.path.join(datapath, plan.finalpath, "plan.par")

    if os.path.exists(planpath):
        os.remove(planpath)

    numkindflat = determine_numkind_flats(plan)
    for frame in plan.frames:
        msg =linkfiles(frame,plan,datapath)
        if msg:
            sys.exit(msg)
            return 
    framestr = buildXIDLframestr(buildXIDLframelist(plan,camera))

    planfile = open(planpath,'w')
    if plan.data == '':
        updateplandata(plan,datapath)

    # if camera == "lrisblue" and numkindflat['PixFlat'] > 0:
    #     writepixflatplan(plan,datapath,camera)
    # elif camera == "kastb" and numkindflat['PixFlat'] > 0:
    #     writepixflatplan(plan,datapath,camera)

    planfile.write(plan.data)
    planfile.write(framestr)
    planfile.close()
    return()


def gatherframelist(plan):
    """This build up a framelist for a given plan.  
    It goes through the frames associated witha given plan and returns a list of them in 
    order of the type list (so object first, arcs second, etc.)
    """


    framelist = ""

    framelist = buildXIDLframelist(plan,plan.instrument.name )

    return(framelist)

def buildgenericframelist(plan):

    framelist = []

    outtag = { "Object" : "SCIENCENAME",
               "IntFlat" : "FLATNAME",
               "Flat" : "SKYFLATNAME",
               "DmFlat" : "DOMEFLATNAME",
               "Line" : "ARCNAME",
               "Bias" : "BIASNAME",
               "Dark" : "DARKNAME",
               "Trace" : "TRACENAME" }


    for frametype in plan.pipeline.typelist():
        frames = plan.framelisttype(type=frametype)

        for frame in frames:
            framelist.append(": ".join([outtag[frametype],frame.display_name]))
        
    return(framelist)

def buildXIDLframestr(framelist):

    framestr = ""
    for framestuff in framelist:
        framestr += "\n" + framestuff

    return(framestr)

def genXIDLframestr(frame,camera):

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


def buildXIDLframelist(plan,camera):

    framelist = []


    numflat = determine_numkind_flats(plan)

    for frametype in plan.pipeline.typelist():

        frames = plan.framelisttype(type=frametype)

        for frame in frames:
            framestr = genXIDLframestr(frame,camera)
            framelist.append(framestr)

    return(framelist)


def writegenericplan(plan,datapath):
    """
    Currently this writes out the default plan file.  This looks like the DEEP2 Pipeline file.
    
    """

    updateplandata(plan,plan.frames[0],datapath)
    planpath = os.path.join(datapath, plan.finalpath, plan.display_name)

    if os.path.exists(planpath):
        os.remove(planpath)
        
    planfile = open(planpath,'w')

    plan.data += "\n"

    planfile.write(plan.data)
    planfile.write(buildXIDLframestr(buildgenericframelist(plan)))
    planfile.close()
    return()

def genrunstr(plan,datapath):

    finalrunstr = ""
    if plan.instrument.name in inst_list():
        finalrunstr = XIDLmodrunstr(plan,datapath)
    else:
        finalrunstr = plan.pipeline.runstr % plan.display_name
        finalrunstr = finalrunstr + '\n'

    return(finalrunstr)

def XIDLmodrunstr(plan,datapath):

    # This relies on the run string 

    # The actual item stored in the model as the runstr is stripped of leading and trailing spaces.
    # If the camera is the lris blue and there are not pixel flats, then the PIXFLAT_ARCHIVE flag is added.
    
    # In addition, if the user has taken pixel flats (images with the dispersing element but without an aperture, usually on the sky)
    # then we need to run the pipeline twice.  Once with just the pixel flats in their own plan file, and once with everything.

    flags = strtodict(plan.runstr)


    runstr = plan.pipeline.runstr # % plan.display_name
    runstr = runstr + '\n'


    numflat = determine_numkind_flats(plan)
    if numflat["PixFlat"] == 0 and plan.instrument.name == "lrisblue":
        flags["PIXFLAT_ARCHIVE"] = "On"

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


    return(runstr)

def writerunstr(runpath,datapath,finalrunstr,idlenv):
    """Writes the actual run string.  This what gets executed by the runjob.py agent
    """

    if os.path.exists(runpath):
        os.remove(runpath)
        
    # FIX
    envstuff = u'#!/bin/csh\nsource ' + idlenv + '\n'
    # 'setenv IDL_DIR /usr/local/idl_80/idl\nsource /home/lris/idl/IPM/THROUGHPUT/watchdir_env/idlenv\n'
    
    rawpath = os.path.join(datapath)
    #    envstuff = envstuff + "#setenv DEIMOS_DATA " + rawpath + "\n"
    runfile = open(runpath,'w')
    runfile.write(envstuff)

    runfile.write(finalrunstr)
    runfile.close()

    os.chmod(runpath,0755)
    return(runpath)



def archiveresult(plan,datapath):

    """Builds the gzip'ed tar file of the output.
    The location is the parent directory of the plan output.
    """


    tfname = os.path.join(datapath,plan.finalpath)
    tfname = re.sub(r'/\Z',r'.tgz',tfname)
    tf = tarfile.open(tfname,"w:gz")
    tf.add(datapath + plan.finalpath)
    tf.close()
    return tf

def cleanplanpath(plan,datapath):
    """This removes the contents of the plan directory.
    This requires the plan and the datapath as input.

    The output (generated by archiveresult) is also removed.

    Nothing is deleted, by all is moved to the user's purge directory.

    """
    print "planpath:",os.path.join(datapath,plan.finalpath)
    if os.access(os.path.join(datapath,plan.finalpath),os.F_OK):
        startdir = os.path.join(datapath,plan.finalpath)
        tarfile = os.path.join(datapath,plan.finalpath)
        tarfile = re.sub(r'/\Z','',tarfile) + ".tgz"

        findir =  os.path.join(datapath,plan.finalpath)
        findir = re.sub(r'findata',r'purge',findir)

        findir = re.sub(r'/\Z',r'',findir)
        top = os.path.dirname(findir)
        if not os.path.isdir(top):
            os.makedirs(top)
        if not os.path.isdir(top):
            os.makedirs(top)
        tdir = tempfile.mkdtemp("","",top)

        fintarfile = os.path.join(tdir,"output")
        fintarfile = re.sub(r'/\Z','',fintarfile) + ".tgz"

        if  os.access(tarfile,os.F_OK):
            os.rename(tarfile,fintarfile)
            
        files = os.listdir(startdir)
        for f in files:
            try:
                os.rename(os.path.join(startdir,f),os.path.join(tdir,f))
            except OSError, (errno, strerror):
                print "OS error(%s): %s" % (errno, strerror)
                os.unlink(os.path.join(startdir,f))
    


def deleteplanpath(plan,datapath):

    """This removes the plan and the contents of the plan directory.
    This requires the plan and the datapath as input.

    The output (generated by archiveresult) is also removed.

    Nothing is deleted, by all is moved to the user's purge directory.

    """

    print "planpath:",os.path.join(datapath,plan.finalpath)
    if os.access(os.path.join(datapath,plan.finalpath),os.F_OK):
        startdir = os.path.join(datapath,plan.finalpath)
        tarfile = os.path.join(datapath,plan.finalpath)
        tarfile = re.sub(r'/\Z','',tarfile) + ".tgz"

        findir =  os.path.join(datapath,plan.finalpath)
        findir = re.sub(r'findata',r'purge',findir)

        findir = re.sub(r'/\Z',r'',findir)
        top = os.path.dirname(findir)
        if not os.path.isdir(top):
            os.makedirs(top)
        tdir = tempfile.mkdtemp("","",top)
        fintarfile = os.path.join(tdir,"output")
        fintarfile = re.sub(r'/\Z','',fintarfile) + ".tgz"

        try:
            os.rename(startdir,tdir)
        except OSError, (errno, strerror):
            print "OS error(%s): %s" % (errno, strerror)
            Userutil.recursive_rm_files(startdir)
        else :
            print "Unexpected error:", sys.exc_info()[0]

        if  os.access(tarfile,os.F_OK):
            os.rename(tarfile,fintarfile)
        

def prepplanpath(plan,datapath):

    """This removes the contents of the plan directory.
    This is done to make sure that the pipeline has a clean input for future runs.

    The output (generated by archiveresult) is also removed.

    Nothing is deleted, by all is moved to the user's purge directory.

    """

    print "planpath:",os.path.join(datapath,plan.finalpath)
    if os.access(os.path.join(datapath,plan.finalpath),os.F_OK):
        startdir = os.path.join(datapath,plan.finalpath)
        tarfile = os.path.join(datapath,plan.finalpath)
        tarfile = re.sub(r'/\Z','',tarfile) + ".tgz"

        findir =  os.path.join(datapath,plan.finalpath)
        findir = re.sub(r'findata',r'purge',findir)

        findir = re.sub(r'/\Z',r'',findir)
        top = os.path.dirname(findir)
        if not os.path.isdir(top):
            os.makedirs(top)
        tdir = tempfile.mkdtemp("","",top)
        fintarfile = os.path.join(tdir,"output")
        fintarfile = re.sub(r'/\Z','',fintarfile) + ".tgz"

        try:
            os.rename(startdir,tdir)
        except OSError, (errno, strerror):
            print "OS error(%s): %s" % (errno, strerror)
            Userutil.recursive_rm_files(startdir)
        else :
            print "Unexpected error:", sys.exc_info()[0]

        if  os.access(tarfile,os.F_OK):
            os.rename(tarfile,fintarfile)
        



def _makeplannameN(frame,n):

    planname = frame.instrument.name 
    if frame.aperture:
        planname += frame.aperture
    if frame.target:
        planname += frame.target
    elif frame.object:
        planname += frame.object

    planname = re.sub("(\+|\-)","p",planname)
    planname = re.sub("\s","_",planname)

    planname = planname + "_" + str(n) + "_plan"
    return(planname)

def makeplanname_new(frame):

    """Given a frame and a user, this guarentees that a new, unique plan name
       will be constructed.
    """
    n = 1
    planname = _makeplannameN(frame,n)

    curplan = Plan.query.filter_by(name=planname).first()

    if curplan:
        while curplan:
            n += 1        
            planname = _makeplannameN(frame,n)

            curplan = Plan.query.filter_by(name=planname).first()


    return(planname,n)

def appendframes(plan,framelist):

    if isinstance(framelist,list):
        for f in framelist:
            if isinstance(f,Frame):
                cframe = f
            else:
                cframe = Frame.query.filter_by(name=f).first()

            plan.addframe(cframe)
    else:
        if isinstance(framelist,Frame):
            cframe = framelist
        else:
            cframe = Frame.query.filter_by(name=framelist).first()

        plan.addframe(cframe)


    return(plan)


def appendframenamelist(plan,framenamelist):

    if isinstance(framelist,list):
        for f in framelist:
            cframe = Frame.query.filter_by(name=f).first()

            plan.addframe(cframe)
    else:
        cframe = Frame.query.filter_by(name=franekust).first()
        plan.addframe(cframe)

    return(plan)

def removeframes(plan,framelist):
    if isinstance(framelist,list):
        for f in framelist:
            plan.delframe(f)
    else:
        plan.delframe(framelist)

    return(plan)

def removeallframes(plan):
    framelist = [f for f in plan.frames]
    removeframes(plan,framelist)
    return(plan)

def gatherframes(plan,frame):
    """This gathers up all the frames that one might want to use
    in conjunction with a science frame.
    """

    types = plan.pipeline.framelist.split()
    for type in types:
        otherframes = []
        if type == "Object":
            otherframes = Frameutil.findlikeframes(frame)
        else:
            otherframes = Frameutil.findframestype(frame,type)
            
        appendframes(plan,otherframes)

    plan.update()


def swappipe(pipes,cpipeline):

    pipes.pop(pipes.index(cpipeline))
    pipes.insert(0,cpipeline )

    return(pipes)

def markup(data):
    newdata = '<p>'
    repdata = re.sub('\n+','<br>',data)
    newdata += repdata
    newdata += '</p>'
    return(newdata)
