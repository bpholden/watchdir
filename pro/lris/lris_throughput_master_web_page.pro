;-----------------------------------------------------------------------
pro lris_throughput_master_web_page, outfile, gratings, href
;-----------------------------------------------------------------------

title = 'LRIS Throughput Data'
body = ''

;;----------------------------------------
;; Figures...
;;----------------------------------------
body += '<h2>Comparison of Grism/Grating Efficiency</h2>'
body += 'Figure TBD!'

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



