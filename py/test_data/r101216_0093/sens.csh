#!/bin/csh
source ~/.idlenv
#setenv DEIMOS_DATA /Users/holden/Dropbox/src/autoThroughput/py
echo "lris_sensstd,'/Users/holden/Dropbox/src/autoThroughput/py/test_data/r101216_0093/Science/std-r101216_0093.fits.gz', CLOBBER=1, STD_OBJ=3" | $IDL_DIR/bin/idl >& sens.log
