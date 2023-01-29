from scapy.all import *
udp = UDP()
ip = IP(dst="10.10.10.5",ttl=128)
dns = DNS(rd=1,qd=DNSQR(qname="dnsrtgshop.com", qtype="ALL"), ar=DNSRROPT(rclass=8192))
packet = ip/udp/dns
x = sr1(packet, verbose=0)

