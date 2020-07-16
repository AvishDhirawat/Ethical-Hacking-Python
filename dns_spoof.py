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
    print(scapy_packet.show())
    packet.accept()

try:
    choice = input("\n1 - Intersystem DNS Spoofing\n2 - Intrasystem DNS Spoofing\nEnter your choice: ")
    print(choice)
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
