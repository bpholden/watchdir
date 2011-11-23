from datetime import datetime, date
from model import Frame, Instrument


import re, glob, pyfits, os, tarfile, os.path
import ephem, math

def lampson(lampstr):
    lamps = { 0 : "Hg",
              1 : "Ne",
              2 : "Ar",
              3 : "Cd",
              4 : "Zn",
              5 : "Qz",
        }
    outstr = ""
    for i,lmp in enumerate(lampstr.split(",")):
        if int(lmp): 
            outstr = outstr + lamps[i]
    return(outstr)


def istwilight(frame,hdr):

    keck1 = ephem.Observer()
    keck1.lat = '19:49:33.40757'
    keck1.long = '-155:28:28.98665'
    keck1.elevation = 4159.58
    keck1.date = frame.observedtime
    keck1.pressure = 0

    sun = ephem.Sun(keck1)
    sun.compute(keck1)
    sunalt = sun.alt*180/math.atan2(0,-1)
    print "sunalt =",sunalt
    istwilight = False
    if sunalt > -12:
        istwilight = True

    return(istwilight)


def frametype(frame,hdr):

    hdrkeys = hdr.ascardlist().keys()

    trapdoor = setval(hdr,'TRAPDOOR',hdrkeys)
    frame.exptime = float("%0.1f" % hdr['ELAPTIME'])
    slitposn = setval(hdr,'AZ',hdrkeys,-1e3)
    domeposn = setval(hdr,'DOMEPOSN',hdrkeys,-1e3)
    
    if slitposn > -1e3 and domeposn > -1e3:
        slitposn = (slitposn + 360.) % 360.
        domeposn = (domeposn + 360.) % 360.
    throughslit = True


    if (abs(domeposn - slitposn) > 4.):
        throughslit = False 
    if domeposn < -999 :
        throughslit = True

    if trapdoor == 'closed' and 'LAMPS' in hdrkeys:
        if hdr['LAMPS'] != "0,0,0,0,0,0":
            if hdr['LAMPS'] == "0,0,0,0,0,1":
                frame.type = "IntFlat"
            else:
                frame.type = "Line"


            frame.lamps = lampson(hdr['LAMPS'])
        else:
            if frame.exptime > 1:
                frame.type = 'Dark'
            else:
                frame.type = 'Bias'
    else:
        # trapdoor is open

        if not throughslit:
            frame.type = 'DmFlat'
        else:
            frame.type = 'Trace'


# we have to assume that frames that are direct
# and taken in twilight are standard star observations
# or "Trace" files
#
# The old logic below is for science observations where
# we assume direct images in twilight are PixFlat
#
#           elif twilight:
#            if frame.aperture == "direct":
#                frame.type = 'PixFlat'
#            else:
#                frame.type = 'Trace'

        

def addframelris(frame,hdr,instrument):
    """
    This takes a frame, reads the header and fills in the info.
    """

    hdrkeys = hdr.ascardlist().keys()

    frame.aperture = re.sub("/","_",setval(hdr,'SLITNAME',hdrkeys))
#    frame.observed = hdr['DATE']

    try:
        frame.target = re.sub("/","_",setval(hdr,'TARGNAME',hdrkeys))
        matches  = re.search("\A\s+\Z",frame.target)
        if matches:
            frame.target = frame.aperture            
    except:
        frame.target = frame.aperture

#    frame.xsize = hdr['NAXIS1']
#    frame.ysize = hdr['NAXIS2']
#    frame.xsize = 2048
#    frame.ysize = 4096

    frametype(frame,hdr)

    frame.mirror = setval(hdr,'DICHNAME',hdrkeys)

    if instrument == "lrisblue":
        frame.grating = setval(hdr,'GRISNAME',hdrkeys)
        frame.ffilter = setval(hdr,'BLUFILT',hdrkeys)
        frame.wavelength = 0.0
    else :
        frame.grating = setval(hdr,'GRANAME',hdrkeys)
        frame.ffilter = setval(hdr,'REDFILT',hdrkeys)

        if re.search(r'LONG',frame.aperture):
            frame.wavelength =  float("%0.1f" % setval(hdr,'WAVELEN',hdrkeys,-9999))
        elif re.search(r'direct',frame.aperture):
            frame.wavelength =  float("%0.1f" % setval(hdr,'WAVELEN',hdrkeys,-9999))
        else:
            frame.wavelength =  float("%0.1f" % setval(hdr,'MSWAVE',hdrkeys,-9999))

    frame.object = setval(hdr,'OBJECT',hdrkeys)
    frame.ra = setval(hdr,'RA',hdrkeys)
    frame.dec = setval(hdr,'DEC',hdrkeys)

    if 'BINNING' in hdrkeys:
        xb,yb = hdr['BINNING'].split(",")
    else:
        xb=1
        yb=1
    frame.xbinning = int(xb)
    frame.ybinning = int(yb)
        
    return frame

	
def setval(hdr,keyword,hdrkeys,default=""):
    value = default
    if keyword in hdrkeys:
        value = hdr[keyword]
    return(value)
