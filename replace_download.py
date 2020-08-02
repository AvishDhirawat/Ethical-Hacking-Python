#!/usr/bin/env python3

# @Author - Avish Dhirawat
# Date - 16/08/2020

import netfilterqueue
import subprocess
import scapy.all as scapy
import argparse

def get_arguments(): # Function to get arguments in command line
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--target', dest = "target_website", help = "Target website you want to spoof")
    parser.add_argument('-d', '--destination', dest = "destination_website", help = "Destination website you want to forward the target")
    parser.add_argument('-c', '--choice', dest = "choice", help = "Choice for Intersystem Spoofing(1) and Intrasystem Spoofing(2)")
    options = parser.parse_args()
    if not options.target_website:
        parser.error("[-] Please specify the target webiste, use --help for more info")
    elif not options.destination_website:
        parser.error("[-] Please specify the destination IP, use --help for more info")
    elif options.choice not in [1,2,"1","2"]:
        parser.error("[-] Please enter correct options for choice, use --help for more info")
    else:
        return options

def process_packet(packet):
    scapy_packet = scapy.IP(packet.get_payload()) # Coverting the packet to scapy packet so that we can interact with them.
    if scapy_packet.haslayer(scapy.Raw): # Finding the DNS for specific site
        if scapy_packet[scapy.TCP].dport == 80:
            print("HTTP Request")
            print(scapy_packet.show())
        elif scapy_packet[scapy.TCP].sport == 80:
            print("HTTP Response")
            print(scapy_packet.show())
    packet.accept()

try:
    options = get_arguments()
    target_website = options.target_website
    destination_website = options.destination_website
    choice = options.choice

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
