;-----------------------------------------------------------------------
pro deimos_throughput_get_efficiency, thru_str, params, VERBOSE=verbose
;-----------------------------------------------------------------------
;+
; NAME:
;	DEIMOS_THROUGHPUT_GET_EFFICIENCY
;
; PURPOSE:
;	This routine will compute the average efficiency over the 
;       specified wavelength range.
;
; CATEGORY:
;	Instrument performance monitoring
;
; CALLING SEQUENCE:
;	DEIMOS_THROUGHPUT_GET_EFFICIENCY, params
;
; INPUTS:
;	params: structure storing the parameter set
;
; EXAMPLE:
;
; AUTHOR:
;	Gregory D. Wirth, W. M. Keck Observatory
;
; MODIFICATION HISTORY:
; 	2000-Nov-16	GDW	Original version
;-
;-----------------------------------------------------------------------

;; loop over passbands...
n = n_elements( params.lambda_eff)

for i=0,n-1 do begin

    ;; initial value is undefined...
    params.efficiency[i] = !values.f_nan

    ;; generate endpoints for wavelength range...
    lambda1 = params.lambda_eff[i] - 0.5 * params.dlambda_eff[i]
    lambda2 = lambda1 + params.dlambda_eff[i]

    ;; determine whether the passband is entirely contained within spectrum...
    good = where(thru_str.wav le lambda1, count1)
    good = where(thru_str.wav ge lambda2, count2)
    good = where(thru_str.wav ge lambda1 and thru_str.wav le lambda2, count3)
    if count1 lt 1 || count2 lt 1 || count3 lt 1 then begin
        if keyword_set(VERBOSE) then begin
            buf = 'passband at ' + stringify(params.lambda_eff[i]) $
                  + ' not entirely contained within spectrum for dataset ' $
                  + params.dataset
            message, buf, /info
        endif
        continue
    endif

    ;; get pixels in passband...
    good = where(thru_str.wav ge lambda1 $
                 and thru_str.wav le lambda2 $
                 and finite(thru_str.eff), count)

    ;; skip if no good pixels...
    if count lt 1 then begin
        if keyword_set(VERBOSE) then begin
            buf = 'no good pixels in passband at ' $
                  + stringify(params.lambda_eff[i]) $
                  + ' for dataset ' $
                  + params.dataset
            message, buf, /info
        endif
        continue
    endif

    ;; take median efficiency within region...
    params.efficiency[i] = median(thru_str.eff[good])

endfor 

end
