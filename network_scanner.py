#!/usr/bin/env python3
# @Author - Avish Dhirawat
# Date - 9 June 2020

import scapy.all as scapy

def scan(ip):
    # Short way to do ARP
    #scapy.arping(ip)

    # Long way to do it
    arp_request = scapy.ARP(pdst = ip)
    #print(arp_request.summary())
    #arp_request.show()
    #scapy.ls(scapy.ARP())
    broadcast = scapy.Ether(dst = "ff:ff:ff:ff:ff:ff") # Enter the MAC where we want to deliver the packet, ff:ff:ff:ff:ff:ff for braocast
    #print(broadcast.summary())
    #broadcast.show()
    #scapy.ls(scapy.Ether())
    arp_request_broadcast = broadcast/arp_request
    #print(arp_request_broadcast.summary())
    #arp_request_broadcast.show()
    #answered_list, unanswered_list = scapy.srp(arp_request_broadcast, timeout = 1) # Sending and Capturing packets
    answered_list = scapy.srp(arp_request_broadcast, timeout = 1, verbose = False)[0]
    #print(answered_list.summary())
    #print(unanswered_list.summary())
    print("________________________________________________________")
    print("IP\t\t\tMAC Address\n--------------------------------------------------------")

    for element in answered_list:
        #print(element[1].show())
        print(element[1].psrc + "\t\t" + element[1].hwsrc)
        #print(element[1].hwsrc)
        #print('----------------------------------------------------------')


scan("10.0.2.1/24")
