from datetime import datetime

from model import Plan, Frame, Instrument, Pipeline

import re, os, os.path, glob, pyfits, tarfile, tempfile, sys, shutil
import XIDLLongPlanutil,  Frameutil


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
        files = glob.glob(fullpath + "/Science/*")
        for cfile in files:
            os.remove(os.path.join(cfile))
        os.rmdir(os.path.join(fullpath,"Science"))
        
    plan.instrument = frame.instrument

    plan.pipeline = pipeline
       
    return (plan)

def updateplandata(plan,frame,datapath):

    """This generates the pipeline specific information.
    """

    plan = XIDLLongPlanutil.buildplanlong(plan,datapath,plan.instrument.name )

    return(plan)

    
def writeplan(plan,datapath):

    """Writes the plan file.  This is what the software will actually execute.
    """

#    cleanoutplandir(plan,datapath)
    XIDLLongPlanutil.writelongplan(plan,datapath)


def gatherframelist(plan):
    """This build up a framelist for a given plan.  
    It goes through the frames associated witha given plan and returns a list of them in 
    order of the type list (so object first, arcs second, etc.)
    """


    framelist = ""

    framelist = XIDLLongPlanutil.buildframelist(plan,plan.instrument.name )

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

def buildframestr(framelist):

    framestr = ""
    for framestuff in framelist:
        framestr += "\n" + framestuff

    return(framestr)


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
    planfile.write(buildframestr(buildgenericframelist(plan)))
    planfile.close()
    return()

def genrunstr(plan,datapath):

    finalrunstr = ""
    if plan.instrument.name in XIDLLongPlanutil.inst_list():
        finalrunstr = XIDLLongPlanutil.modrunstr(plan,datapath)
    else:
        finalrunstr = plan.pipeline.runstr % plan.display_name
        finalrunstr = finalrunstr + '\n'

    return(finalrunstr)


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
