;-----------------------------------------------------------------------
function gdw_normalize, x, y
;-----------------------------------------------------------------------

;; fit background with B-spline...
nord = 4
fullbkpt = bspline_bkpts( x, nord=nord, nbkpts=15)
sset = bspline_iterfit( x, y, nord=nord, maxiter=0, yfit=yfit, fullbkpt=fullbkpt)

;; normalize...
norm = y / yfit
return, norm

end

;-----------------------------------------------------------------------
pro coalign_spectra, wave1, flux1, wave2, flux2
;-----------------------------------------------------------------------
; Given two similar spectra which may have a wavelength shift,
; measure the shift and shift the wavelength scale of the second
; spectrum to align with the first. 
;-----------------------------------------------------------------------

;; normalize the spectra...
norm1 = gdw_normalize( wave1, flux1)
norm2 = gdw_normalize( wave2, flux2)

;; determine the lag...
n = n_elements(norm1)
lag = indgen(700)
nlag = n_elements(lag)
lag = lag - lag[nlag/2]
result = C_CORRELATE(norm1, norm2, lag)
top = max( result, m)
mshift = lag[m]

;; shift spectrum2 to align with spectrum 1...
if mshift gt 0 then begin
    delta = wave1[0] - wave2[mshift]
endif else begin
    delta = wave1[-mshift] - wave2[0]
endelse 

;; modify wave2...
wave2 += delta

end
