from datetime import datetime, date, time



class Plan(object):

    def __init__(self,name,datapath,instrument,pipeline,aperture,target,display_name):

        self.name = name
        self.datapath = datapath
        self.finalpath = ""

        self.display_name = display_name
        self.instrument = instrument
        self.aperture = aperture
        self.target = target

        self.created = datetime.now
        self.started = ""
        self.finished = ""
        self.status = 0
        # 0 not run
        # 1 running
        # 10 done
        self.maxobj = 5
        self.minslit = 20
        self.reduxthresh = 0.01

        self.frames = []

        self.data = ""

        self.utitle = ""
        self.description = ""

        self.runstr = ""
        
        self.instrument = instrument
        self.pipeline = pipeline

    def __repr__(self):
        return '<Plan %s at %s >' % (self.display_name, self.datapath)


    def addframe(self,frame):

        self.frames.append(frame)

    def delframe(self,frame):

        if self.frames.count(frame):
                self.frames.remove(frame)


    def removeframes(self):
        [self.frames.pop() for i in range(len(self.frames))]

    def framelisttype(self,type=""):
        outlist = []
        for curframe in self.frames:
            if type and curframe.type == type:
                outlist.append(curframe)
            elif not type:
                outlist.append(curframe)

        return(outlist)

    def setstatus(self,status=0):
        self.status = status
        self.update()

        return(self)

    def update(self):
        return(self)


class Frame(object):

    def __init__(self,name,path,display_name,header="",observeddate="",observedtime="",use_mark=True):
        self.name = name
        self.path = path
        self.display_name = display_name

        self.description = ""

        self.aperture = ""
        self.target = ""
        self.type = ""
        self.object = ""
        self.target = ""
        self.lamps = ""
        self.ffilter = ""
        self.grating = ""
        self.mirror = ""

        self.ra = ""
        self.dec = ""

        self.decimalra = 0
        self.decimaldec = 0

        self.xsize = 0
        self.ysize = 0
        self.xbinning = 1
        self.ybinning = 1
    
        self.wavelength = 0
        self.secondangle = 0
        self.exptime = -1

        self.flags = ""
    
        self.delmark = False
        self.use_mark = use_mark

        self.added = datetime.now
        self.observeddate = observeddate
        self.observedtime = observedtime

        self.header = header
        
        self.instrument = ""
        self.datapath = path

    def __repr__(self):
        return '<Frame %s at %s of type %s>' % (self.display_name, self.path, self.type)

    def markforupdate(self):
        if self.delmark == True:
            self.delmark = False
        else:
            self.delmark = True

    def changeuse(self):
        if self.use_mark == True:
            self.use_mark = False
        else:
            self.use_mark = True

    def typelist(self):
        typelist = ["Object","IntFlat","Line","Trace","Dark","Bias","Flat","DmFlat","PixFlat"]
        if self.type in typelist:
            typelist.remove(self.type)
        typelist.insert(0,self.type)

        return(typelist)

    def copy(self):
        new = Frame(self.name,self.path,self.display_name,self.header,self.observeddate,self.observedtime,self.use_mark)
        return(new)
        

class Instrument(object):

    def __init__(self,name,display_name):
        self.name = name
        self.display_name = display_name


    def __repr__(self):
        return '%s' % (self.display_name)



class Pipeline(object):


    def __init__(self,display_name,runstr,instrument,framelist):

        self.display_name = display_name
        self.runstr = runstr
    
        self.instrument = instrument
        self.framelist = framelist

    def __repr__(self):
        return '%s' % (self.display_name)

    def typelist(self):
        typestr = self.framelist
        typelist = typestr.split()
        return(typelist)


