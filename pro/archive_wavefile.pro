pro archive_wavefile, filename, outputname

  if  N_params() LT 2 then begin 
     print,'Syntax - ' + $
           'archive_wavefile, inpute wavefile, output filename'
     return
  endif 

  restore, filename
  calib=xfit[0]
  archive_arc=arc1d[*,0]
  save, calib, archive_arc, filename=outputname
  return
end
