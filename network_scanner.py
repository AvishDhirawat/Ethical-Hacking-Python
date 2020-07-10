#!/usr/bin/env python3
# @Author - Avish Dhirawat
# Date - 9 June 2020

import scapy.all as scapy
#import optparse # optparse is depreciated because its outdated and developers stopped providing its updates
import argparse # its new and we get its updates

def get_arguments():
    #parser = optparse.OptionParser()
    parser = argparse.ArgumentParser()
    #parser.add_option('-t', '--target', dest = "ip_range", help = "Range of target IP to look for ")
    parser.add_argument('-t', '--target', dest = "ip_range", help = "Range of target IP to look for ")
    #(options, arguments) = parser.parse_args()
    options = parser.parse_args()

    if not options.ip_range:
        parser.error("[-] Please specify the IP range to look for, use --help for more info")
    else:
        return options

def scan(ip_range):
    # Short way to do ARP
    #scapy.arping(ip)

    # Long way to do it
    arp_request = scapy.ARP(pdst = ip_range)
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
    #print("________________________________________________________")
    #print("IP\t\t\tMAC Address\n--------------------------------------------------------")

    clients_list = []
    for element in answered_list:
        client_dict = {"ip" : element[1].psrc, "MAC" : element[1].hwsrc}
        #print(element[1].show())
        clients_list.append(client_dict)
        #print(element[1].psrc + "\t\t" + element[1].hwsrc)
        #print(element[1].hwsrc)
        #print('----------------------------------------------------------')
    return clients_list
    #print(clients_list)

def print_result(result_list):
    print("________________________________________________")
    print("IP\t\t\tMAC Address\n------------------------------------------------")
    for client in result_list:
        #print(client)
        print(client['ip']+ "\t\t"+ client['MAC'])


#scan_result = scan("10.0.2.1/24")
options = get_arguments()
scan_result = scan(options.ip_range)
print_result(scan_result)
