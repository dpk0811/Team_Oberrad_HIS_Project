


Code from https://github.com/ethanwilloner/DNS-Amplification-Attack

This is a proof of concept for a DNS amplification attack. By sending 
UDP packets to a DNS server with the target spoofed as the source, you 
can effectively amplify your bandwidth to overload a hosts bandwidth. 
These attacks are becoming common, and show flaws in the DNS system. 
This is not a weaponized tool, but the dns.c and dns.h files are 
independent of and can function without the provided main.c code, just 
read the comments to figure out what is being passed to the functions.

This code must be run as root to be able to access Raw Sockets.

Tested and running on Debian Wheezy 7.0, compiles with both GCC and clang. 
Makefile uses clang.

In my Testing, I could not make this work on actual, real world targets. Why?
Because most common networks don't allow UDP source spoofing.
 I am not trying to weaponize it, so I have not put more than a few
hours into trying to figure out why, to no avail. Either way, it is still cool
to be able to target a machine on your LAN and see endless streams of DNS packets
showing up in Wireshark. 

This WILL saturate your network connection, and will probably render most 
other networking on the computer slow in the best case, unresponsive in the 
worst, while the tool is running.

This code was written with the help of code found at
http://www.binarytides.com/raw-udp-sockets-c-linux/
and
http://www.binarytides.com/dns-query-code-in-c-with-linux-sockets/
The code found at these URL's was not released under any license, but I like 
to give credit where credit it due. With no prior experience with in 
programming with Raw Sockets or the DNS system, these resources were invaluable.