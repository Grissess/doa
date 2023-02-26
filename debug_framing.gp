set grid
plot '/tmp/cache' index 1 using 0:1 with linespoints title "signal", \
	'' index 1 using 0:2 with linespoints title "autoc", \
	'' index 1 using 0:3 with linespoints title "sync", \
	'' index 0 using 2:(10) with impulses title "start", \
	'' index 0 using ($2 + $3):(10) with impulses title "end", \
	'' index 0 using ($2 + $3):(10):4 with labels notitle, \
	'' index 2 using 1:(-10) with impulses title "msg", \
	'' index 2 using 1:(-10):2 with labels notitle, \
	'' index 3 using 1:(5) with impulses title "code", \
	'' index 3 using 1:(5):2 with labels notitle, \
	'' index 4 using 1:(-5) with impulses title "len", \
	'' index 4 using 1:(-5):2 with labels notitle
