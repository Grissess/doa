set grid
set encoding utf8
period = 16
plot '< python filter.py' index 1 using 0:1 with linespoints title "tx bits", \
	'' index 0 using ($0/period):1 with linespoints title "tx sig", \
	'' index 1 using 0:2 with linespoints title "rx I", \
	'' index 1 using 0:3 with linespoints title "rx Q", \
	'' index 1 using 0:4 with linespoints title "μ", \
	'' index 1 using 0:5 with linespoints title "PLL I", \
	'' index 1 using 0:6 with linespoints title "PLL Q", \
	'' index 1 using 0:7 with linespoints title "freq off", \
	'' index 2 using 1:(2) with impulses title "syms", \
	'' index 2 using 1:(2.1):(sprintf("%d\n%d", $2, $3)) with labels notitle
