from datetime import datetime, date, time,timedelta
from model import Frame, Instrument

import re, glob, pyfits, os, tarfile, os.path
import LRISFrameutil


def instrument_name(instrument_hdr_val):
    if re.match("LRISBLUE",instrument_hdr_val):
        return("lrisblue")
    elif re.match("LRIS",instrument_hdr_val):
        return("lrisred")
    else :
        return("")

def find_instrument_name(hdr):
    hdrkeys = hdr.ascardlist().keys()
    instrument = ""
    if 'INSTRUME' in hdrkeys:
        instrument = instrument_name(hdr['INSTRUME'])
    else:
        if 'VERSION' in hdrkeys:
            instrument = instrument_name(hdr['VERSION'])
    
    return(instrument)


def getobsdate(hdr):
    # a list of keys in the header
    hdrkeys = hdr.ascardlist().keys()

    # a DEIMOS-like date stamp
    if 'DATE' in hdrkeys:
        match = re.search(r'(\d+)\-(\d+)\-(\d+)T(\d+)\:(\d+)\:(\d+)', hdr['DATE'])

        if match:
            obsdate = date(int(match.group(1)),int(match.group(2)),
                           int(match.group(3)))
            obstime = time(int(match.group(4)),int(match.group(5)),
                           int(match.group(6)))

        else:
            match = re.search(r'(\d+)\-(\d+)\-(\d+)', hdr['DATE'])
            obsyear = match.group(1)
            obsmon = match.group(2)
            obsday = match.group(3)


            if 'UT' in hdrkeys:
                match = re.search(r'(\d+)\:(\d+)\:(\d+)', hdr['UT'])
            elif  'TIME' in hdrkeys:
                match = re.search(r'(\d+)\:(\d+)\:(\d+)', hdr['TIME'])
            elif  'ST' in hdrkeys:
                match = re.search(r'(\d+)\:(\d+)\:(\d+)', hdr['ST'])
            else:
                #timeless but still can get a date
                match = False

            if match:
                obsdate = date(int(obsyear),int(obsmon),
                                   int(obsday))
                obstime = time(int(match.group(1)),int(match.group(2)),
                               int(match.group(3)))
            else:
                obsdate = date(int(obsyear),int(obsmon),
                                   int(obsday))
                obstime = time(int(12),int(0),int(0))

    elif  'DATE-OBS' in hdrkeys:
        # NIRSPEC or KAST
        match = re.search(r'(\d+)\-(\d+)\-(\d+)T(\d+)\:(\d+)\:(\d+)', hdr['DATE-OBS'])
        if match:
            # KAST
            obsdate = date(int(match.group(1)),int(match.group(2)),
                           int(match.group(3)))
            obstime = time(int(match.group(4)),int(match.group(5)),int(match.group(6)))
        else:
            match = re.search(r'(\d+)\-(\d+)\-(\d+)', hdr['DATE-OBS'])
            # NIRSPEC
            if match:
                obsyear = match.group(1)
                obsmon = match.group(2)
                obsday = match.group(3)
                obsdate = date(int(obsyear),int(obsmon),
                               int(obsday))
            else:
            # not talking to the telescope. 
            # the outdir string has the date in it as that is how Keck organizes things

                if 'OUTDIR' in hdrkeys:
                    match = re.search(r'nirspec/(\d+)(\w+)(\d+)', hdr['OUTDIR'])
                    if match:
                        obsyear = match.group(1)
                        obsday = match.group(3)
                        mons = { 'jan' : 1,
                                 'feb' : 2,
                                 'mar' : 3,
                                 'apr' : 4,
                                 'may' : 5,
                                 'jun' : 6,
                                 'jul' : 7,
                                 'aug' : 8,
                                 'sep' : 9,
                                 'oct' : 10,
                                 'nov' : 11,
                                 'dec' : 12 }
                        obsmon = mons[match.group(2)]
                        obsdate = date(int(obsyear),int(obsmon),
                                       int(obsday))
                    # there is no way to get the obs
                        obstime = time(int(12),int(0),int(0))
                        
    else:
        # a timeless FITS file 
        obsdate = date.today()
        obstime = time(int(12),int(0),int(0))

    return(obsdate,obstime)


def genframepathstr(filename,obsdate):


    dirname = re.sub('\.fit(s?).*\Z','',filename)

    months = ("jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec")
    datename = "%d%s%02d" % (obsdate.year,months[obsdate.month-1],obsdate.day)
    relpath = os.path.join(datename,dirname)

    return(relpath)

def genframepath(datapath,outpath):

    os.makedirs(os.path.join(datapath,outpath))


def ingestframe(filename,path,datapath,flag=dict(redo=False)):
    """
    ingestframe(filename, path, datapath)
    filename - filename on the file system of a fits file to ingest
    path - path to the file, whole path
    datapath - the output path

    this routine takes a file  and does the appropriate shuffling to
    move the file to the correct place in the filesystem
    the destination in the datapath value + Standards + date + longreduce
    
    """
    msg = ""
    frame = False
    try:
        hdr = pyfits.getheader(os.path.join(path,filename),0)
    except:
        print "cannot open %s in Frameutil.ingestframe()" %( os.path.join(path,filename))
        msg = "cannot open %s " % (filename)
        return(msg,frame)

    hdrkeys = hdr.ascardlist().keys()

    instrument = find_instrument_name(hdr)
    if instrument == "":
        msg = "%s not produced by an instrument we can deal with" % (filename)
        return(msg,frame)
    
    obsdate,obstime = getobsdate(hdr)

    frame_name = filename
    relpath = genframepathstr(os.path.basename(filename),obsdate)
    newpath = os.path.join(datapath,relpath,os.path.basename(filename))

    try:
        msg = "Added frame %s" % (filename)
        nmsg,frame = addframe(frame_name,hdr,obsdate,obstime,filename,relpath,instrument)
        frame.datapath = datapath
        msg += nmsg
        print msg
    except:
        msg = "Cannot ingest data frame %s" % (filename)


    if frame.type != "Trace":
        msg = "%s is not an observation of standard star, but appears to be of type %s" % (filename,frame.type)
        return(msg,False)


    if not  os.access(os.path.join(datapath,relpath),os.F_OK):

        try:
            failure = genframepath(datapath,relpath)

        except:
            msg = "There is some horrid error in the system and the path %s for this file cannot be made.  Please contact the administrator."  % (os.path.join(datapath,relpath))
            print msg
            return(msg,False)
        

#    relpath = os.path.join(str(owner.user_name) ,'rawdata',instrument)


    if not os.path.isfile(newpath) or flag['redo'] == True:
        os.link(os.path.join(path,filename),newpath)
    else:
        msg = "%s already in the system, and overwrite was not selected" % (filename)
        print msg
        return(msg,False)
         
    return(msg,frame)

def addframe(frame_name,hdr,obsdate,obstime,filename,path,instrument=""):
    """ addframe(frame_name,hdr,obsdate,obstime,filename,path,instrument)

    frame_name - the unique frame name
    hdr - FITS header
    obsdate- datetime object that is the date  from hdr
    obstime- datetime object that is the time  from hdr
    filename - the filename on the file system, this should be related to the
               frame_name
    path - the relative path to the object, not including what is the datapath

    This builds the actual frame instance.
    frame_name is a unique key for the name of the datafile.  Based on the hdr
    data, the routine fills in the information that the db needs to classify
    the file and run the pipelines with the correct input
    """
    msg = ''
    frame = Frame(frame_name,path,
                  filename,
                  header = hdr,
                  use_mark = True,
                  observeddate = obsdate,
                  observedtime = datetime.combine(obsdate,obstime))
    if instrument == "":
        instrument = find_instrument_name(hdr)

#    print "Instrument = ",instrument
    if instrument == "lrisred" :
#        print "Is a red frame!"
        frame.instrument = Instrument(name=u'lrisred',display_name=u'LRISRED'
                                      )
        frame = LRISFrameutil.addframelris(frame,hdr,instrument)
    elif instrument == "lrisblue":
        frame.instrument = Instrument(name=u'lrisblue',display_name=u'LRISBLUE',
                                      )

        frame = LRISFrameutil.addframelris(frame,hdr,instrument)
    if not frame:
        msg="There is something wrong with %s" % frame_name
        

    return(msg,frame)
            




def uniqlist(list,idfun=None):
    # a function to uniqify a list
    # stolen from the intertubes

    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in list:
        marker = idfun(item)
        if seen.has_key(marker): continue
        seen[marker] = 1
        result.append(item)
    return result



def cardlist(frame):

    cardlist = []
    for card in frame.header.ascardlist():
        if not re.search(r'\A\s+\Z',str(card)):
            cardlist.append(card)
    return(cardlist)

	
def setval(hdr,keyword,hdrkeys,default=""):
    value = default
    if keyword in hdrkeys:
        value = hdr[keyword]
    return(value)
