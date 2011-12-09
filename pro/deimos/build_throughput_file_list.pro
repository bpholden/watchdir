;-----------------------------------------------------------------------
pro build_throughput_file_list
;-----------------------------------------------------------------------
;+
; NAME:
;	BUILD_THROUGHPUT_FILE_LIST
;
; PURPOSE:
;	This routine will extract critical header parameters and put
;	them into a catalog file with info on 
;       filename, grating, cenlam, filter, and star
;
; CATEGORY:
;	IPM
;
; CALLING SEQUENCE:
;	build_throughput_file_list
;
; INPUTS:
;       None
;
; OUTPUTS:
;	Creates output file 'input.lst' which is used as input for
;	run_review_deimos_throughput
;
; RESTRICTIONS:
;
; EXAMPLE:
;       1) To generate list, first launch IDL with the correct
;       setup by executing this in the shell:
;               do_deimos_throughput
;       then at the IDL prompt type
;               build_throughput_file_list
;
; AUTHOR:
;	Gregory D. Wirth, W. M. Keck Observatory
;
; MODIFICATION HISTORY:
; 	2011-Oct-31	GDW	Original version
;-
;-----------------------------------------------------------------------

;; define files...
thru_dir = getenv('DEIMOS_THRU_DIR')
if thru_dir eq '' then $
  message, 'DEIMOS_THRU_DIR is not defined -- abort!'
data_dir = thru_dir + '/dat/'
raw_dir = thru_dir + '/raw/'
all_list = data_dir + 'all.lst'
input_list = data_dir + 'input.lst'

;; get list of files...
;; readcol, all_list, format='(a)', files
q = '''
;;
command = 'find ' + thru_dir + '/raw -name ' + $
          q + '*.fits*' + q + ' -print | fgrep -v BAD'
print, command
spawn, command, files
n_files = n_elements(files)

;; allocate output struct...
s = {filename:'', targname:'', gratenam:'', wavelen:0, dwfilnam:'', $
     dateobs:'', status:1B }
info = replicate(s, n_files)

;; scan through files...
for i=0,n_files-1 do begin

    ;; default status is "good"...
    t = s

    ;; read file header...
    file = files[i]
    print, '[', + stringify(i) + '/' + stringify(n_files) + '] file=', file
    hdr = headfits( file, exten=0)

    ;; check keywords...
    t.filename = file
    t.dateobs  = strtrim(sxpar( hdr, 'DATE-OBS'),2)
    t.targname = strtrim(sxpar( hdr, 'TARGNAME'),2)
    t.dwfilnam = strtrim(sxpar( hdr, 'DWFILNAM'),2)
    t.gratenam = strtrim(sxpar( hdr, 'GRATENAM'),2)
    gratepos = sxpar( hdr, 'GRATEPOS')
    if gratepos eq 3 then begin
        keyword = 'G3TLTWAV'
        t.wavelen = nint(sxpar( hdr, keyword))
    endif else if gratepos eq 4 then begin
        keyword = 'G4TLTWAV'
        t.wavelen = nint(sxpar( hdr, keyword))
    endif else begin
        message, 'WARNING: invalid GRATEPOS (' + $
                 strtrim(string(gratepos),2) + $
                 ') in file '+file, /info
        t.status = 0B
    endelse 

    ;; flag invalid dates...
    if stregex( t.dateobs, $
                '^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$', $
                /boolean) ne 1 then begin
        message, 'WARNING: invalid date in file '+files[i], /info
        t.status = 0B
    endif

    ;; insert into struct...
    info[i] = t

endfor 

;; remove invalid dates...
good = where( info.status eq 1B)
info = info[good]

;; sort by date...
order = sort(info.dateobs)
info = info[order]

;; write to file...
write_csv, input_list, info, $
           header=['filename', 'targname', 'gratenam', 'wavelen', $
                   'dwfilnam', 'dateobs', 'status' ]

end
