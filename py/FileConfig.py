import re

class FileConfig:
    def __init__(self,filename="config"):
        self.testing = False
        self.filename = filename
        try:
            configfile = open(filename)
            lines = configfile.readlines()
            for line in lines:
                # we have to clean the input file lines up
                # so we remove unneeded or wanted characters
                line = line.rstrip('\n')
                line = re.sub(r'\#.*\Z','',line) # anything after a # is tossed

                # finally, we split on a =, no =, we skip the line
                if re.search("=",line):
                    key,val = line.split("=")
                    if "testing" in key:
                        if re.search('True',val):
                            self.testing = True
                    else:
                        key = key.strip()
                        val = val.strip()
                        val = val.split(",")
                        if len(val) == 1:
                            val = val[0]
                        setattr(self,key,val)

        except Exception as e:
            print e
    def __repr__(self):
        return '< FileConfig %s >' % (self.filename)


    def return_config(self):
        config = dict()
        for val in dir(self):
            if "__" not in val:
                config[val] = getattr(self,val)
        for val in ["testing","filename","return_config"]:
            if val in config:
                del(config[val])
        return config
        


if __name__ == "__main__":
    
    
    config = FileConfig("config_file")
    print config
    print config.callist
    print config.kroot
    print config.idlenv
    print config.starlist

    print config.return_config()
