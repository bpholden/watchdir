;-----------------------------------------------------------------------
pro lris_add_new_web_pages, gratingdir, sensfunc, CLOBBER=clobber, TEST=test
;-----------------------------------------------------------------------
;+
; NAME:
;	LRIS_THROUGHPUT_WEB_PAGES
;
; PURPOSE:
;	This procedure will generate web pages for LRIS throughput
;
; CATEGORY:
;	Instrument performance monitoring
;
; CALLING SEQUENCE:
;       lris_throughput_web_pages
;
; KEYWORDS:
;       CLOBBER:        if set, overwrite previously-generated plots;
;       otherwise, skip over them.
;
;       TEST:   run in test mode; only generate data for files in
;       directory "test".
;
; RESTRICTIONS:
;       Must run as lriseng or lris
;
; INPUT FILES:
;       $LRIS_THRU/<grating>/sens*.fits*
;
; OUTPUT FILES:
;       $LRIS_THRU/<grating>/doc/EFF_sens_<grating>_DDMMMYYY_NNN.pdf
;       $LRIS_THRU/<grating>/doc/EFF_sens_<grating>_DDMMMYYY_NNN.png
;       $LRIS_THRU/<grating>/doc/EFF_sens_<grating>_DDMMMYYY_NNN.txt
;       $LRIS_THRU/<grating>/doc/ZPANG_sens_<grating>_DDMMMYYY_NNN.pdf
;       $LRIS_THRU/<grating>/doc/ZPANG_sens_<grating>_DDMMMYYY_NNN.png
;       $LRIS_THRU/<grating>/doc/ZPANG_sens_<grating>_DDMMMYYY_NNN.txt
;       $LRIS_THRU/<grating>/doc/ZPPIX_sens_<grating>_DDMMMYYY_NNN.pdf
;       $LRIS_THRU/<grating>/doc/ZPPIX_sens_<grating>_DDMMMYYY_NNN.png
;       $LRIS_THRU/<grating>/doc/ZPPIX_sens_<grating>_DDMMMYYY_NNN.txt
;
; PROCEDURE:
;
; REQUIREMENTS:
;       IDL must be invoked using the command
;               ~dmoseng/bin/do_lris_throughput
;       in order to properly configure the IDL PATH
;
; EXAMPLE:
;       1) Update LRIS throughput web pages:
;               lris_throughput_web_pages
;
;
; PROCEDURES USED:
;       lris_throughput_grating_plots
;       lris_throughput_grating_detail_web_page
;       lris_throughput_grating_summary_plots
;       lris_throughput_grating_summary_web_page 
;       lris_throughput_master_web_page
;
; AUTHOR:
;	Gregory D. Wirth, W. M. Keck Observatory
;
; MODIFICATION HISTORY:
; 	2009-Oct-23	GDW	Original version
; 	2011-Dec-08	BPH     Adapted from DEIMOS version to LRIS
;-
;-----------------------------------------------------------------------

;; specify set of wavelengths at which to measure change over time,
;; plus an array of widths and an array to hold measurements...
lambda_eff = [4000, 5000., 7000., 8500., 9500.]
dlambda_eff = [500, 500., 500., 500., 500.]
efficiency = fltarr(n_elements(lambda_eff))
subdirs = ['b300_5000','b400_3400','b600_4000','b1200_3400','r150_7500','r300_5000', $
           'r400_8500','r600_5000','r600_7500','r600_10000','r831_8200','r900_5500', $
           'r1200_7500']
usedirs = intarr(size(subdirs,/n_elements))

STOP

rootoutdir = getenv('LRIS_WEB')
caldir = getenv('LRIS_THRU')
if caldir eq '' then message, 'LRIS_THRU envar not defined'
caldirs = file_search(caldir,count=ndir)
if ndir eq 0 then begin
   message, 'no directory '+caldir+' Reset LRIS_THRU environment variable and rerun'
   return 
endif

caldir = caldir + "/" + gratingdir ; now search for input grating directory
caldirs = file_search(caldir,count=ndirs)
if ndir eq 0 then begin
   message, 'no directory '+caldir+' Reset LRIS_THRU environment variable or check for existence of '+gratingdir+' and rerun'
   return 
endif

   


;; check for test mode...
if keyword_set(TEST) then subdirs = ['test']

;; define contents of a structure
foo = {PARAMS, infile:'', $
       dataset:'', $
       detail:'', $
       fig_eff:'', $
       fig_zp_pix:'', $
       fig_zp_ang:'', $
       fig_eff_pdf:'', $
       fig_zp_pix_pdf:'', $
       fig_zp_ang_pdf:'', $
       tab_eff:'', $
       tab_zp_pix:'', $
       tab_zp_ang:'', $
       date:'', $
       jd:0.d0, $
       std_name:'', $
       ra:'', $
       dec:'', $
       airmass:0., $
       blocking:'', $
       spec_bin:'', $
       grating:'', $
       cenlam:'', $
       slit_width:0., $
;       conditions:'', $
       lambda_eff:lambda_eff, $
       dlambda_eff:dlambda_eff, $
       efficiency:efficiency }

;; define structure for summary...
summary = { efficiency_current_plot:'', $
            efficiency_current_pdf:'', $
            efficiency_current_tab:'', $
            efficiency_current_bintab:'', $
            eff_vs_wavelength_plot:'', $
            eff_vs_wavelength_pdf:'', $
            eff_vs_wavelength_tab:'', $
            eff_vs_wavelength_bintab:'', $
            eff_vs_time_plot:'', $
            eff_vs_time_pdf:'', $
            eff_vs_time_tab:'', $
            eff_vs_time_bintab:''}

;; loop over directories (gratings)...
ng = 0

message, 'processing subdirectory '+gratingdir, /info

;; get list of files in directory...

newfiles = file_search( caldir, sensfunc, count=nnew)
files = file_search( caldir, 'sens_*.fits', count=nfiles)

;; no files ==> go to next subdir...
if nnew eq 0 then begin
   message, 'no file '+sensfunc+' in subdir '+subdir, /info
   return
endif 

newoutdir = 0
;; create output directory as needed...
;; note - will also have to remake master web page if this is the case
outdir = rootoutdir + '/'+grating + '/doc'
if ~ file_test( outdir, /dir) then begin 
   file_mkdir, outdir
   newoutdir = 1 ; This means that we will have to rebuild the master page
   for nsub = 0, size(subdirs,/n_elements)-1 do begin
      csubdir = outdir = rootoutdir + '/'+subdirs[nsub] + '/doc'
      if ~ file_test( csubdir, /dir) then usedirs[nsub] = 1
   endfor
endif

;; Sort by date
all_dates = dblarr(nfiles)
all_grating = strarr(nfiles)
for jj=0L,nfiles-1 do begin
   meta = xmrdfits(files[jj],1, /silent)
   ;; Convert to Julian
   all_dates[jj] = x_setjdate(meta.date)
   all_grating[jj] = strtrim(meta.grating,2)
endfor

new_dates = dblarr(nnew)
meta = xmrdfits(newfiles[0],1,/silent)
new_dates[0] = x_setjdate(meta.date)

uni = uniq(all_grating)
if n_elements(uni) GT 1 then begin
   message, 'directory '+subdir+' contains files from different gratings!', /inf
   return
endif


;; generate structure to hold data...
params = replicate({PARAMS}, nfiles)

;; intialize params...
params.infile = files
for jj=0L,nfiles-1 do begin
   params[jj].lambda_eff  = lambda_eff
   params[jj].dlambda_eff = dlambda_eff
   params[jj].jd = all_dates[jj]
endfor

;; generate plots...
lris_throughput_grating_plots, params, fig_time, OUTDIR=outdir, $
                               CLOBBER=clobber
newparam = replicate({PARAMS}, nnew)
newparam.infile = newfiles
newparam[0].lambda_eff = lambda_eff
newparam[0].dlambda_eff = dlambda_eff
newparam[0].jd = new_dates[0]

;; generate detail pages...
extn = '.html'
   
;; grab dataset name for input file...
istrt = strpos( newparams[0].infile, '/', /reverse_search) > 0L
iend = strpos( newparam[0].infile, '.fits')
dataset = strmid( newparam[0].infile, istrt+1, iend-istrt-1)

;; build output file name...
outfile = outdir + '/' + dataset + extn

newparam[0].detail = outfile
newparam[0].dataset = dataset
if keyword_set(VERBOSE) then begin
   message, 'creating detail page '+outfile, /in
endif
lris_throughput_grating_detail_web_page, newparam[0]
endfor

;; generate plots for grating summary...
lris_throughput_grating_summary_plots, params, summary, $
                                       OUTDIR=outdir, $
                                       CLOBBER=clobber

;; generate grating summary page...
extn = '.html'
outfile = outdir + '/index.html'
if keyword_set(VERBOSE) then begin
   message, 'creating summary page '+outfile, /in
endif 
lris_throughput_grating_summary_web_page, outfile, grating, $
                                          params, summary

;    ;; generate web page with plots...
;    outfile = outdir + '/plots.html'
;    lris_throughput_grating_web_page, $
;      outfile=outfile, $
;      TITLE='LRIS '+grating+' Throughput Measurements', $
;      INDEX='throughput: measurements for ' + grating, $
;      GRATING=grating, $
;      FIG_EFF=params[nfiles-1].fig_eff, $
;      FIG_ZP_ANG=params[nfiles-1].fig_zp_ang
;;;      FIG_TIME=fig_time

fulldirs = where(usedirs,nusedirs)
if nusedirs eq 0 then begin
   message, 'No grating or grism directories contain output of lris_sensstd.'
   return
endif 

;; lris_throughput_master_plot
outfile = rootoutdir +'/index.html'
gratings = subdirs[fulldirs]
href = subdirs[fulldirs] + '/doc/index.html'
if newoutdir eq 1 then lris_throughput_master_web_page, outfile, gratings, href

end
