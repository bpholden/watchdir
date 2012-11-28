function plot_select_gratings, gratings, outdir, $ 
                               selectgratings, title, root, $
                               MAX_EFFICIENCY=max_efficiency

  csize = 1.75
  template = '/tmp/temp.%.ps'
  angstrom = STRING(197B)


  n = size(gratings,/n_elements)
  usegratings = intarr(n)
  for i=0,n-1 do begin
     for j=0,size(selectgratings,/n_elements)-1 do begin
        if selectgratings[j] EQ gratings[i] then usegratings[i] = 1
     endfor
  endfor

  useind = where(usegratings,nug)
  if nug eq 0 then begin
     return,""
  endif

  fingratings = gratings[useind]

  effname = outdir + "/" + fingratings[0] + "/doc/eff_latest.fits" 

  effstr = mrdfits(effname,1)
  eff_plot = outdir + "/" + root + '.png'
  eff_pdf = outdir + "/" + root + '.pdf'

;; start plot...
  wav_min = min(effstr.wav, max=wav_max)
  eff_min = min(effstr.eff, max=eff_max)

  if wav_min LT 3200 then wav_min = 3200
  if wav_max GT 10800 then wav_max = 10800

  IF n_elements(max_efficiency) GT 0 THEN  eff_max = max_efficiency

  psfile = mktemp(template)
  psland, psfile
  DEVICE, SET_FONT='Helvetica', /TT_FONT  
  DEVICE, /ISOLATIN1
  plot, effstr.wav, effstr.eff, $
        xrange=[wav_min,wav_max], $
        yrange=[eff_min,eff_max], $
        charsize=csize, $
        xstyle=1, ystyle=1, $
        thick=10, xthick=1, ythick=1, $
        xtitle='Wavelength ['+Angstrom+']', $
        ytitle='End-to-end Efficiency', $
        title=title, font=0, $
        xmargin=[2,1], ymargin=[1,1]

  
  if nug gt 1 then begin
     for ng=1,nug-1 do begin
          effname = outdir + "/" + fingratings[ng] + "/doc/eff_latest.fits" 
          effstr = mrdfits(effname,1)
          oplot, effstr.wav, effstr.eff, linestyle=1
       endfor
  endif

  id, font=1
  device, /close
  ps2other, psfile, $
            png=eff_plot, $
            pdf=eff_pdf, $
            verbose=verbose, /delete
  
  
  eff_plot = root + '.png'
  return, eff_plot
end


;-----------------------------------------------------------------------
pro lris_throughput_master_grating_plots, outdir, gratings, master,$
                                          MAX_EFFICIENCY=max_efficiency
;-----------------------------------------------------------------------

  root = "beff_curr"
  btitle = 'Latest LRIS Efficiency Data for Blue Grisms'
  master.blue_fig_eff=plot_select_gratings(gratings,outdir, $
                                           ['b300_5000','b400_3400','b600_4000','b1200_3400'], $
                                           btitle,root,MAX_EFFICIENCY=max_efficiency)

  root = "rleff_curr"
  rtitle = 'Latest LRIS Efficiency Data for Lower-res Gratings'
  master.red_low_fig_eff=plot_select_gratings(gratings,outdir, $
                                              ['r150_7500','r300_5000','r400_8500' ], $
                                              rtitle,root,MAX_EFFICIENCY=max_efficiency)

  root = "rseff_curr"
  rstitle = 'Latest LRIS Efficiency Data for 600l/mm Gratings'
  master.red_six_fig_eff=plot_select_gratings(gratings,outdir, $
                                              ['r600_5000','r600_7500','r600_10000'], $
                                              rstitle,root,MAX_EFFICIENCY=max_efficiency)

  root = "rheff_curr"
  rhtitle = 'Latest LRIS Efficiency Data for Higher-res Gratings'
  master.red_high_fig_eff=plot_select_gratings(gratings,outdir, $
                                               ['r831_8200','r900_5500','r1200_7500'], $
                                               rhtitle,root,MAX_EFFICIENCY=max_efficiency)
  return
end
