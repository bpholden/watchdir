;-----------------------------------------------------------------------
function unique, array
;-----------------------------------------------------------------------

;; return unique elements...
order = sort( array)
sorted = array[order]
return, sorted(uniq(sorted))

end

;-----------------------------------------------------------------------
pro throughput_file_stats
;-----------------------------------------------------------------------
;+
; NAME:
;	THROUHGPUT_FILE_STATS
;
; PURPOSE:
;	This procedure will generate a plot showing the status of
;	throughput measurements for DEIMOS.
;
; CATEGORY:
;       IPM
;
; CALLING SEQUENCE:
;       throughput_file_stats
;
; INPUTS:
;	NONE
;
; OUTPUTS:
;       NONE
;
; INPUT FILES:
;       $DEIMOS_THRU_DIR/dat/input.lst
;               Contains a listing of all throughput files.  Generated
;               by ??
;
; OUTPUT FILES:
;       throughput_file_stats.ps
;               File containing output PostScript plot
;
; RESTRICTIONS:
;	Describe any "restrictions" here.  Delete this section if there are
;	no important restrictions.
;
; PROCEDURE:
;       - read the input list from input.lst into result structure
;       - extract fields from result structure
;       - convert YYYY-MM-DD dates to decimal years
;       - reject data with bad dates
;       - generate lists of unique gratings and filters
;       - for each grating, create a plot of datasets in the form of
;         wavelength vs. time
;
; EXAMPLE:
;       1) To generate a plot, first launch IDL with the correct
;       setup by executing this in the shell:
;               do_deimos_throughput
;       then at the IDL prompt type
;               throughput_file_stats
;
; AUTHOR:
;	Gregory D. Wirth, W. M. Keck Observatory
;
; MODIFICATION HISTORY:
; 	2011-Nov-09     GDW     original version
;-
;-----------------------------------------------------------------------

;; disable debug mode...
debug = 0B

;; define location of files...
thru_dir = getenv('DEIMOS_THRU_DIR')
if thru_dir eq '' then $
  message, 'DEIMOS_THRU_DIR is not defined -- abort!'
data_dir = thru_dir + '/dat/'

;; define files...
input_list   = data_dir + 'input.lst'
good_list    = data_dir + 'good.lst'
bad_list     = data_dir + 'bad.lst'
review_list  = data_dir + 'review.lst'

;; get input list...
result = read_csv( input_list)

;; extract fields...
files    = result.field1
targname = result.field2
gratenam = result.field3
wavelen  = result.field4
dwfilnam = result.field5
dateobs  = result.field6
status   = result.field7

;; convert dates to decimal years...
n = n_elements(files)
year = fltarr(n)
status = bytarr(n) + 1B
for i=0,n-1 do begin

    ;; skip invalid dates...
    if stregex( dateobs[i], '^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$', /boolean) ne 1 then begin
        status[i] = 0B
        message, 'WARNING: invalid date in file '+files[i], /info
        continue
    endif

    ;; convert date to year...
    date = dateobs[i] + ' 00:00:00.00'
    buf = date_conv( date, 'V')
    year[i] = buf[0] + buf[1]/366.
endfor 

;; excise bad dates...
good = where( status eq 1B, count)
if count lt 1 then message, 'no good files'
files    = files[good]
targname = targname[good]
gratenam = gratenam[good]
wavelen  = wavelen[good]
dwfilnam = dwfilnam[good]
dateobs  = dateobs[good]
year     = year[good]

;; read the various lists...
result = read_csv( good_list)
good_files = result.field1
n_good = n_elements( good_files)

result = read_csv( bad_list)
bad_files = result.field1
n_bad = n_elements( bad_files)

result = read_csv( review_list)
review_files = result.field1
n_review = n_elements( review_files)

;; define strings...
review_status_unknown = 'unknown'
review_status_good    = 'good'
review_status_bad     = 'bad'
review_status_review  = 'review'

;; determine the review status of each file...
review_status = strarr(count)
for i=0,count-1 do begin

    ;; default value is unknown...
    review_status[i] = review_status_unknown

    ;; check the good list...
    for j=0,n_good-1 do $
      if files[i] eq good_files[j] then review_status[i] = review_status_good

    ;; check the bad list...
    for j=0,n_bad-1 do $
      if files[i] eq bad_files[j] then review_status[i] = review_status_bad

    ;; check the review_list
    for j=0,n_review-1 do $
      if files[i] eq review_files[j] then review_status[i] = review_status_review
    
endfor 

;; get unique gratings...
gratings = reverse(['600ZD','830G','900ZD','1200G'])
n_gratings = n_elements( gratings)
print, 'gratings: ', gratings

;; find unique filters within set...
filters = unique( dwfilnam)
n_filters = n_elements( filters)
print, 'filters: ',filters

;; get min and max wavelengths...
w_min = 4000
w_max = 10000

;; get min/max dates...
year_min = min( year)
year_max = max( year)

;; intialize plot file...
filename = data_dir + 'throughput_file_stats.ps'
psopen, filename, /color, /landscape, /helvetica, $
        xsize=11.0, ysize=8.5, /inches

symbols = [1,2,4,5,6,7,1,1]
default_color    = gdwcolor('black')
bad_color    = gdwcolor('red')
review_color = gdwcolor('cyan')
good_color   = gdwcolor('lime')

;; create plots...
!y.margin = [0,0]
m = n_gratings
!p.multi = [0,1,m]
!p.font = 1
!p.charsize = 1.95
!y.omargin=[6,4]
!x.omargin=[8,8]
!x.margin=[8,8]
xtickname = REPLICATE(' ', 60)

;; loop over gratings...
for i=0,n_gratings-1 do begin

    if i eq n_gratings-1 then begin
        extra = {}
    endif else begin
        extra = {xtickname:xtickname}
    endelse 

    ;; create plot...
    plot, [0], [0], xrange=[year_min, year_max+1], $
          yrange=[w_min, w_max], $
          /nodata, /yno, $
          ytitle=gratings[i], _EXTRA=extra

    filter_used = bytarr(n_filters)

    ;; loop over filters
    for j=0,n_filters-1 do begin

        ;; find matching points...
        good = where( gratenam eq gratings[i] and dwfilnam eq filters[j], $
                      count)

        ;; plot data points...
        if count gt 0 then begin
            filter_used[j] = 1B
            r = review_status[good]
            y = year[good]
            w = wavelen[ good]

            ;; determine whether files are good/bad/review/unknown...
            for k=0,count-1 do begin
                if r[k] eq review_status_good then begin
                    color = good_color
                endif else if r[k] eq review_status_bad then begin
                    color = bad_color
                endif else if r[k] eq review_status_review then begin
                    color = review_color
                endif else begin
                    color = default_color
                endelse 

                oplot, [y[k]], [w[k]], psym=symbols[j], color=color
            endfor 

            if debug then $
              for k=0,count-1 do print, stringify(i) + ' ' $
                + stringify(j) + ' ' $
                + gratings[i] + ' ' $
                + filters[j] + ' ' $
                + stringify(y[k]) + ' ' $
                + stringify(w[k])
        endif 

        ;; loop over wavelengths...
        waves = wavelen(good)
        uwaves = unique( waves)
        n_uwaves = n_elements(uwaves)
        for k=0,n_uwaves-1 do begin
            good2 = where( waves eq uwaves[k], count)
            sep = ','
            if count gt 1 then $
              print, gratings[i], sep, filters[j], sep, uwaves[k], sep, count
        endfor 

    endfor 

    ;; make legend...
    good = where( filter_used eq 1B)
    labels = filters[good]
    syms = symbols[good]
    gdwlegend, labels, psym=syms, /right, charsize=1.25
    
endfor 

;; add titles...
!p.multi = 0
TITLE='DEIMOS Throughput Database Contents'
xyouts, 0.5, 0.95, title, align=0.5, /norm
TITLE='Wavelength'
xyouts, 0.05, 0.5, title, align=0.5, /norm, orient=90.
TITLE='Year'
xyouts, 0.5, 0.04, title, align=0.5, /norm

;; close file...
psclose

end
