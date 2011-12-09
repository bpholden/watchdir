;------------------------------------------------------------------------
pro do_deimos_throughput, INPUT=input, OUTPUT=output, $
  DEBUG=debug, CLOBBER=clobber, VERBOSE=verbose, PSFILE=psfile, $
  TARGNAME=targname, GRATENAM=gratenam, GZIP_TEST=gzip_test
;------------------------------------------------------------------------
;+
; NAME:
;	DO_DEIMOS_THROUGHPUT
;
; PURPOSE:
;	This routine will coordinate the extraction of DEIMOS
;	throughput measurements into the appropriate place for Xavier
;	Prochaska's analysis software to process it.
;
; CATEGORY:
;	Instrumentation
;
; CALLING SEQUENCE:
;	DO_DEIMOS_THROUGHPUT, INPUT=input, OUTPUT=output
;
; INPUT KEYWORDS:
;
;       INPUT: list of DEIMOS throughput images to extract.  Default
;       is to scan all of the directories in the raw/ partition and
;       extract any images which have not been extracted.
;
;	OUTPUT: list of files to generate.  Default is to place files
;	in the appropriate grating subdirectory in the output.
;
;       TARGNAME: set this keyword to limit reduction to the specified
;       target name.
;
;       GRATENAM: set this keyword to limit reduction to the specified
;       grating name.
;
;       PSFILE: set this keyword to generate a postscript output file
;       with diagnostic plots.
;
;       CLOBBER: if set, then overwrite existing files (default: no
;       overwrite) 
;
;       VERBOSE: set this keyword to print additional messages during
;       execution.
;
;       DEBUG: set this keyword to generate additional output for
;       debugging purposes.
;
;       GZIP_TEST: if set, verify the integrity of .gz file before
;       reading it and if it's bad then rename it
;
; REQUIREMENTS:
;       IDL must be invoked using the command
;               ~dmoseng/bin/do_deimos_throughput
;       in order to properly configure the IDL PATH
;
; INPUT FILES:
;       $DEIMOS_THRU_DIR/raw/YYYYmmmDD/*fits*
;               raw DEIMOS spectra of slitless standards
;       
; OUTPUT FILES:
;       $DEIMOS_THRU_DIR/extract/<grating>/YYYYmmmDD_dNNNN_NNNN.fits
;               FITS binary table with two extensions:
;                       - METADATA has keyword/value pairs
;                       - SPECTRUM has wavelength and flux
;       $DEIMOS_THRU_DIR/extract/<grating>/YYYYmmmDD_dNNNN_NNNN.ps
;               Postscript plot file showing profile, trace and extracted 1-D
;               spectrum for both the red and blue chip, plus combined
;               spectrum
;       $DEIMOS_THRU_DIR/extract/<grating>/YYYYmmmDD_dNNNN_NNNN.sav
;               IDL SAVE file with data
;       $DEIMOS_THRU_DIR/extract/<grating>/YYYYmmmDD_dNNNN_NNNN_M_trace.region
;               trace listing for chip M
;       $DEIMOS_THRU_DIR/extract/log/do_deimos_throughput.YYYY-MMM-DD-HH:MM:SS.log
;               logfile from execution of this routine
;               
;
; PROCEDURE:
;
; INVOKED SUBROUTINES:
;       deimos_throughput
;
; EXAMPLE:
;
; AUTHOR:
;	Gregory D. Wirth, W. M. Keck Observatory
;
; MODIFICATION HISTORY:
; 	2009-Oct-21	GDW	Original version
;-
;------------------------------------------------------------------------

;; define the special string which means default output file...
default = 'default'
thru_dir = getenv('DEIMOS_THRU_DIR')
if thru_dir eq '' then begin
    message, 'DEIMOS_THRU_DIR is not defined -- abort!'
endif
outdir = thru_dir + '/extract'

;; open logfile...
buf = strsplit( systime(0), ' ', /extract)
date = string( format='(i4,"-",a3,"-",i2.2)', buf[4], buf[1], buf[2])
time = buf[3]
logdir = outdir + '/log'
file_mkdir, logdir
logfile = logdir + '/do_deimos_throughput.' + date + '-' + time + '.log'
openw, logunit, logfile, /get_lun

;; define relevant files...
data_dir = thru_dir + '/dat/'
reject_list = data_dir + 'bad.lst'
center_list = data_dir + 'centers.lst'

;; read bad file list...
if file_test(reject_list) then begin
    got_rejects = 1B
    readcol, reject_list, rejected_files
endif else begin
    got_rejects = 0B
endelse 
print, 'reject_list=', reject_list
print, 'got_rejects =', got_rejects

;; read new centers...
if file_test(center_list) then begin
    got_centers = 1B
    result = read_csv(center_list)
    recentered_files = result.field1
    trace_centers = 0+result.field2
endif else begin
    got_centers = 0B
endelse 
print, 'center_list=', center_list
print, 'got_centers =', got_centers

;; build input and output file lists...
if keyword_set(INPUT) then begin

    infiles = input
    explicit_input_files = 1B

endif else begin
    
    ;; if no input, we scan the directories for all available FITS files...
    dir = getenv('DEIMOS_THRU_DIR') + '/raw'
    infiles = file_search(dir,'*.fits')
    infiles2 = file_search(dir,'*.fits.gz')
    if n_elements(infiles2) gt 0 then infiles = [infiles,infiles2]
    explicit_input_files = 0B

endelse
n_in = n_elements(infiles)

;; define output list if needed....
if keyword_set(OUTPUT) then begin
    
    ;; if both arrays exist, then they must be the same size...
    n_out = n_elements(output)
    if n_in ne n_out then begin
        message, 'input and output file lists must be the same length'
    endif
    outfiles = output

endif else begin
    outfiles = replicate( default, n_in)
endelse 

;; loop over input files...
for i=0,n_in-1 do begin

    ;; define input and output files...
    in = infiles[i]
    out = outfiles[i]
    
    if keyword_set(VERBOSE) then begin
        message, '----------------------------------------------------', /info
        message, 'Starting input file ' $
                 +stringify(i+1)+'/'+stringify(n_in), /info
        message, in, /info
    endif

    ;; check whether the input file is in the list of bad files...
    if got_rejects and ~ explicit_input_files then begin
        match = where( rejected_files eq in, count)
        if count gt 0 then begin
            buf = 'specified input file '+in+' appears in reject list; skipping'
            message, buf, /info
            printf, logunit, in, ' ', buf
            continue
        endif 
    endif 

    ;; verify existence of input file...
    if file_test( in, /regular) then begin
        if keyword_set(DEBUG) then begin
            message, 'verified input file '+in+' exists', /info
        endif 
    endif else begin
        buf = 'specified input file '+in+' not found; skipping'
        message, buf, /info
        printf, logunit, in, ' ', buf
        continue
    endelse

    ;; if .gz file, then verify that it's OK...
    if keyword_set(GZIP_TEST) and stregex( in, '.gz$', /bool) then begin
        if keyword_set(VERBOSE) then $
          message, 'Testing GZIP format file', /info
        cmd = 'gzip -t '+in
        spawn, cmd, buf, exit=status

        ;; if file is bad then rename it...
        if status ne 0 then begin
            badname = in+'.BAD'
            cmd = '/bin/mv '+in+' '+badname
            spawn, cmd, buf, exit=status
            if status eq 0 then begin
                message, 'WARNING: renamed bad GZIP file to '+badname, /info
            endif else begin
                message, 'WARNING: unable to rename bad GZIP file to '+badname, /info
            endelse 
            continue
        endif 
    endif

    ;; grab header...
    header = headfits( in)

    ;; verify validity of header...
    if n_elements(header) le 1 then begin
        buf = 'bad header in input file '+in+'; skipping'
        message, buf, /info
        printf, logunit, in, ' ', buf
        continue
    endif 

    ;; grab grating and target names...
    gratenam2 = strtrim(sxpar( header, 'gratenam'),2)
    targname2 = strtrim(sxpar( header, 'targname'),2)

    ;; optional match for targname...
    if keyword_set(TARGNAME) then begin
        if strtrim(TARGNAME,2) ne targname2 then begin
            buf = 'TARGNAME is not '+targname+' not found; skipping'
            message, buf, /info
            printf, logunit, in, ' ', buf
            continue
        endif 
    endif

    ;; optional match for graname...
    if keyword_set(GRATENAM) then begin
        if strtrim(GRATENAM,2) ne gratenam2 then begin
            buf = 'GRATENAM is not '+gratenam+' not found; skipping'
            message, buf, /info
            printf, logunit, in, ' ', buf
            continue
        endif 
    endif

    ;; generate default output file names...
    if out eq default then begin

        stem = raw2extract( in, header=header, subdir=subdir)
        out = stem + '.fits'
        sav = stem + '.sav'
        plotfile = stem + '.ps'
        tracefile = stem

        ;; create missing directory...
        if ~ file_test( subdir, /directory) then file_mkdir, subdir

    endif

    ;; verify non-existence of output file...
    if file_test( out) then begin
        if keyword_set(CLOBBER) then begin
            message, 'removing existing output file '+out, /info
            file_delete, out
        endif else begin
            buf = 'specified output file '+out+' exists; skipping'
            message, buf, /info
            printf, logunit, in, ' ', buf
            continue
        endelse 
    endif else begin
        if keyword_set(DEBUG) then begin
            message, 'verified output file '+out+' exists', /info
        endif 
    endelse 

    if ~ keyword_set(PSFILE) then plotfile = ''

    ;; check for new center...
    if got_centers then begin
        match = where( recentered_files eq in, count)
        if count eq 1 then begin
            trace_center = trace_centers[match]
            buf = 'using new center for input file '+in $
                  +' at '+string(trace_center)
            message, buf, /info
        endif else if count gt 1 then begin
            message, 'ERROR: multiple matches in center list '+center_list $
                     +' for image '+in
        endif 
    endif else begin
        message, 'setting trace_center to NaN', /info
        trace_center = !values.f_nan
    endelse 

    ;; extract data...
    deimos_throughput, in, wavelengths, counts, OUTFILE=out, $
                       SAVFILE=sav, STATUS=status, VERBOSE=verbose, $
                       ERRMSG=errmsg, PSFILE=plotfile, TRACEFILE=tracefile, $
                       TRACE_CENTER=trace_center

    ;; convert to sensitivity standard...
    if status then $
      deimos_sensstd_gdw, out, CLOBBER=clobber, PLOT=plot, COMPRESS='gzip'

    ;; update logfile...
    printf, logunit, in, ' ', errmsg

endfor

free_lun, logunit
end
