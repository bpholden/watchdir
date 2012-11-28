
;-----------------------------------------------------------------------
pro lris_throughput_master_web_page, outfile, gratings, href, outdir, master
;-----------------------------------------------------------------------

title = 'LRIS Throughput Data'
body = ''

;;----------------------------------------
;; Figures...
;;----------------------------------------
body += '<h2>Comparison of Grism/Grating Efficiency</h2>'
body += '<p/><img src="'+master.blue_fig_eff+'" alt="blue grisms efficiency plot">'
body += '<p/><img src="'+master.red_low_fig_eff+'" alt="red low resolution gratings efficiency plot">'
body += '<p/><img src="'+master.red_six_fig_eff+'" alt="red 600l/mm gratings efficiency plot">'
body += '<p/><img src="'+master.red_high_fig_eff+'" alt="red high resolution gratings efficiency plot">'

;;----------------------------------------
;; Links...
;;----------------------------------------
body += '<h2>LRIS Gratings</h2>'
body += '<ul>'
n_gratings = n_elements(gratings)
for i=0,n_gratings-1 do begin
     body += '<li> <a href="'+href[i]+'">'+gratings[i]+'</a>'
endfor
body += '</ul>'

lris_write_web_page, outfile, body, title=title

end



