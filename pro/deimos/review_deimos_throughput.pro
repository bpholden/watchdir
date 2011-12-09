;-----------------------------------------------------------------------
pro display_extract, EXTRACT=extract, XPOS=xpos
;-----------------------------------------------------------------------

;; scale Y axis from sky to peak with 10% buffer
dy = extract.peak - extract.sky
y_min = extract.sky  - 0.1 * dy
y_max = extract.peak + 0.1 * dy

;; generate axes...
plot, extract.x, extract.flux, $
      xtitle='Column [px]', ytitle='Sky-subtracted Flux', $
      yrange=[y_min,y_max], ystyle=1, title='Extraction Profile'

;; overplot extraction region...
oplot, [extract.x1,extract.x2], [extract.peak,extract.peak], psym=-1

;; mark left sky region...
oplot, [extract.xleft1, extract.xleft2], [extract.sky,extract.sky], psym=-1

;; mark right sky region...
oplot, [extract.xright1, extract.xright2], [extract.sky,extract.sky], psym=-1

;; indicate sky level as dotted horizontal line...
oplot, !x.crange, [extract.sky,extract.sky], linestyle=1

;; plot dotted vertical line at the measured center...
oplot, [extract.center,extract.center], !y.crange, linestyle=1
xyouts, extract.center, extract.sky, $
        ' Center='+stringify(extract.center,'(f15.1)'), $
        orient=90.

;; annotate...
nxyouts, xpos, 0.55, $
         'Row='+stringify(extract.row)
nxyouts, xpos, 0.50, $
         'Sky='+stringify(nint(extract.sky),'(i10)')

end


;------------------------------------------------------------------------
pro display_profile, PROFILE=profile, XPOS=xpos
;------------------------------------------------------------------------
    plot, profile.u, profile.flux, $
          xtitle='Column [px]', ytitle='Sky-subtracted Flux', $
          xstyle=1, $
          title='Profile at Rows '+stringify(profile.v1)+ $
          '-'+stringify(profile.v2)
    oplot, [profile.u_center,profile.u_center], !y.crange, linestyle=1
    xyouts, profile.u_center, !y.crange[0], $
            ' Center='+stringify(profile.u_center,'(f15.1)'), $
            orient=90.
    nxyouts, xpos, 0.10, 'Sky='+stringify(nint(profile.sky),'(i10)')
    nxyouts, xpos, 0.05, 'S/N='+stringify(profile.s2n,'(f15.1)')
end

;------------------------------------------------------------------------
pro display_trace, TRACE=trace, PROFILE=profile, XPOS=xpos
;------------------------------------------------------------------------
; display the trace...
;------------------------------------------------------------------------

    x = [trace.good.v, trace.bad.v]
    y = [trace.good.u, trace.bad.u]
    x1 = min(x[where(x ne 0)], max=x2)
    y1 = min(y[where(y ne 0)], max=y2)
    plot, [0], [0], /nodata, xtitle='Y [px]', ytitle='X [px]', /yno, $
          xstyle=1, title='Trace', xrange=[x1,x2], yrange=[y1,y2]

    ;; plot good data...
    if trace.good.count gt 0 then $
      oplot, trace.good.v, trace.good.u, psym=6, symsize=0.25

    ;; plot bad data...
    if trace.bad.count gt 0 then $
      oplot, trace.bad.v, trace.bad.u, psym=7, symsize=0.5
    nxyouts, xpos, 0.55, stringify(trace.bad.count)+' bad points'
    nxyouts, xpos, 0.5, 'Sky='+stringify(nint(profile.sky),'(i10)')
    
    ;; add trace...
    if ( trace.fit.status ) then begin
        oplot, trace.fit.v, trace.fit.u
    endif else begin
        nxyouts, 0.5, 0.5, 'WARNING: BAD TRACE', align=0.5
    endelse 


end


;-----------------------------------------------------------------------
pro update_generic_list, filename, v1
;-----------------------------------------------------------------------

;; if file doesn't exist, then just create it...
if ~ file_test(filename) then begin
    openw, ounit, filename, /get_lun
    printf, ounit, v1
    free_lun, ounit

endif else begin

    ;; file already exists, so update it...

    ;; get current contents...
    readcol, filename, format='(a)', c1, /silent
    match = where( c1 eq v1, count)
    
    if count eq 0 then begin
        
        ;; add new value to file...
        openw, ounit, filename, /get_lun, /append
        printf, ounit, v1
        free_lun, ounit
        
    endif else begin
        message, 'WARNING: '+v1+' already appears in file '+filename, /info
    endelse 
endelse 

end

;-----------------------------------------------------------------------
pro update_commented_list, filename, v1, string
;-----------------------------------------------------------------------

;; if file doesn't exist, then just create it...
if ~ file_test(filename) then begin

    write_csv, filename, [v1], [string]

endif else begin

    ;; file already exists, so update it...

    ;; get current contents...
    result = read_csv(filename)
    
    ;; check for empty file...
    if size(result, /n_dim) eq 0 then begin
        write_csv, filename, [v1], [string]
    endif else begin
        
        c1 = result.field1
        c2 = result.field2
        match = where( c1 eq v1, count)
        
        if count eq 0 then begin
            
            ;; add new value to file...
            write_csv, filename, [c1,v1], [c2,string]
            
        endif else begin
            message, 'WARNING: '+v1+' already appears in file '+filename, /info
        endelse 
    endelse 
endelse 

end

;-----------------------------------------------------------------------
pro update_center_list, filename, infile, center
;-----------------------------------------------------------------------

;; if file doesn't exist, then just create it...
if ~ file_test(filename) then begin

    write_csv, filename, [infile], [center]

endif else begin

    ;; file already exists, so update it...

    ;; get current contents...
    result = read_csv(filename)
    c1 = result.field1
    c2 = result.field2
    match = where( c1 eq infile, count)
    
    if count eq 0 then begin
        
        ;; add new value to file...
        c1 = [c1, infile]
        c2 = [c2, center]
        
    endif else if count eq 1 then begin

        ;; replace existing value...
        c1[match] = infile
        c2[match] = center

    endif else begin
        message, 'ERROR: Center file '+filename+' already has mutiple entries for image '+infile, /info
        return
    endelse 

    ;; save results..
    write_csv, filename, c1, c2
endelse 

end

;;------------------------------------------------------------------------
pro view_trace, infile, chip, trace
;;------------------------------------------------------------------------
;; display the image...
;;------------------------------------------------------------------------

;; read image...
image = deimos_read_chip( infile, chip, header=header)

;; get rootname...
breakname, infile, dirname, rootname, extn
message, '  Displaying '+rootname+' in ATV...', /info

atv, image
message, '  Overplotting trace points in green', /info
if trace.good.count gt 0 then $
  atvplot, trace.good.u, trace.good.v, color='green', psym=6
if trace.bad.count gt 0 then $
  atvplot, trace.bad.u, trace.bad.v, color='red', psym=7
if ( trace.fit.status ) then begin
    color = 'cyan'
    message, '  Overplotting trace fit in '+color, /info
    atvplot, trace.fit.u, trace.fit.v, color=color
endif else begin
    message, '  Warning: bad trace fit!', /info
endelse

;; allow time for reflection...
message, '  Please press Q in the ATV window to continue...', /info
atv_activate

end

;-----------------------------------------------------------------------
pro review_deimos_throughput, infile, EXIT_STATUS=exit_status
;-----------------------------------------------------------------------
;+
; NAME:
;	REVIEW_DEIMOS_THROUGHPUT
;
; PURPOSE:
;	This procedure is used to review DEIMOS throughput
;	measurements and trigger re-reduction of data as desired.
;
; CATEGORY:
;	Data analysis
;
; CALLING SEQUENCE:
;       REVIEW_DEIMOS_THROUGHPUT, infile
;
; INPUTS:
;	infile:	name of file with input raw spectrum
;
; EXAMPLE:
;
; AUTHOR:
;	Gregory D. Wirth, W. M. Keck Observatory
;
; MODIFICATION HISTORY:
; 	2011-Jun-21	GDW	Original version
;-
; TODO:
;       - fix plotting problem
;       - allow fiducials
;       - add parsing of center list to reductions
;       - add parsing of reject list to reductions
;-----------------------------------------------------------------------

xwinsize = 500
ywinsize = 400

;; define constants...
xpos=0.025
default='A'
null = ''
exit_status = 0

;; define files...
thru_dir = getenv('DEIMOS_THRU_DIR')
if thru_dir eq null then $
  message, 'DEIMOS_THRU_DIR is not defined -- abort!'
data_dir = thru_dir + '/dat/'
;; reject_list = data_dir + 'bad.lst'
;; approve_list = data_dir + 'good.lst'
;; review_list = data_dir + 'review.lst'
center_list = data_dir + 'centers.lst'

;; read review database...
review_database = data_dir + 'review.fits'
review = mrdfits( review_database, 1)

;; generate save file name from infile...
stem = raw2extract( infile)
sav_file = stem + '.sav'

;; re-extract if no save file exists...
if ~ file_test( sav_file) then begin
    print, 'Re-extracting spectrum...'
    do_deimos_throughput, input=[infile], /clobber, /psfile
endif

;; check for file...
if ~ file_test( sav_file) then begin
    message, 'WARNING: no save file '+sav_file+' for infile '+infile+'; add to reject list and skip', /info
    reason = 'auto extraction failed'
    update_review_database, review_database, review, infile, status='bad', $
      comment=reason
    return
endif 

;; get existing record for this target...
record = parse_review_database( review, infile)

;; skip objects already considered "bad"...
if record.status eq 'bad' then begin
    message, 'WARNING: file '+infile+' previously rejected with this comment: '+ $
             record.comment+'; skip', /info
    return
endif

if record.status eq 'good' then begin
    message, 'WARNING: file '+infile+' previously approved; skip', /info  
    return
endif

;; read the input structures...
restore, sav_file, /verb

;; define windows...
profile_window = 0
extract_window = 1
trace_window = 2
spec_window = 3

;; create windows...
window, profile_window, xsize=xwinsize, ysize=ywinsize
window, extract_window, xsize=xwinsize, ysize=ywinsize
window, trace_window, xsize=xwinsize, ysize=ywinsize
window, spec_window, xsize=xwinsize, ysize=ywinsize

;; set graphics settings...
!p.font = 1
!p.multi = 0
!p.charsize = 1.5

;; loop over extensions...
for ext=0,1 do begin

    ;; give feedback...
    print, '  file      = ', meta.filename
    print, '  target    = ', meta.std_name
    print, '  grating   = ', meta.grating
    print, '  cenlam    = ', meta.central_wave
    print, '  dwfilnam  = ', meta.blocking
    print, '  extension = ', ext
    print, '  comment   = ', record.comment

    if ext eq 0 then begin
        trace = diag0.trace
        profile = diag0.profile
        spectrum = diag0.spectrum
        extract = diag0.extract
        infile = diag0.infile
        chip = diag0.chip
    endif else begin
        trace = diag1.trace
        profile = diag1.profile
        spectrum = diag1.spectrum
        extract = diag1.extract
        infile = diag1.infile
        chip = diag1.chip
    endelse 
    
    ;; display the trace...
    wset, trace_window
    display_trace, TRACE=trace, PROFILE=profile, XPOS=xpos

    ;; display the extracted profile...
    wset, extract_window
    display_extract, EXTRACT=extract, XPOS=xpos

    ;; display the spectrum...
    wset, spec_window
    plot, spectrum.pixel, spectrum.flux, xtitle='Row', ytitle='flux [e-/px]', $
          xstyle=1, title='Raw spectrum'

    ;; display the initial profile...
    wset, profile_window
    display_profile, PROFILE=profile, XPOS=xpos

    ;; display image and trace...
    view_trace, infile, chip, trace

    ;; determine next action...
    while 1 do begin
        prompt = '(A)ccept, (R)eject, (C)enter, (F)ollowup, or (Q)uit ['+default+']: '
        answer = null
        read, answer, prompt=prompt
        if answer eq null then answer = default
        answer = strupcase( answer)
        
        if answer eq 'Q' then begin
            print, 'Quitting...'
            exit_status=1
            return

        endif else if answer eq 'A' then begin
            print, 'Results accepted.'

        endif else if answer eq 'R' then begin

            prompt = 'Please enter comment (or none for no change): '
            reason = null
            read, reason, prompt=prompt
            if answer eq null then answer = record.comment
            print, 'Adding ', infile, ' to the list of rejects.'
            update_review_database, review_database, review, infile, $
              status='bad', comment=reason
            return

        endif else if answer eq 'F' then begin

            prompt = 'Please enter comment: '
            reason = null
            read, reason, prompt=prompt
            if answer eq null then answer = record.comment
            print, 'Adding ', infile, ' to the list of followups.'
            update_review_database, review_database, review, infile, $
              status='review', comment=reason
            return

        endif else if answer eq 'C' then begin

            ;; select and redisplay the profile to ensure that we get
            ;; the mapping correct...
            wset, profile_window
            display_profile, PROFILE=profile, XPOS=xpos
            print, 'Please place cursor at desired center and click the mouse...'
            cursor, xc, yc, /up, /data
            print, 'Got new center at X=', xc
            update_center_list, center_list, infile, xc

            ;; trigger re-analysis of spectrum...
            print, 'Re-extracting spectrum...'
            do_deimos_throughput, input=[infile], /clobber, /psfile

            ;; force re-do of this extension...
            ext--

        endif else begin
            print, 'Sorry, "', answer, '" is not a valid option.'
            continue

        endelse
        
        ;; if we got here, then we got a valid response...
        break
    endwhile

    ;; if we got here then the target is approved...
    if ext eq 1 then begin
        message, 'Adding target to approved list.', /info
        update_review_database, review_database, review, infile, $
          status='good'
    endif

endfor

end
